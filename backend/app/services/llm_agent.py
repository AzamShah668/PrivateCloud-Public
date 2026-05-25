# =============================================================================
# backend/app/services/llm_agent.py
# =============================================================================
# This file serves as the Generative AI Agent Orchestrator. It translates
# incoming strings into validated Pydantic parameter payload execution trees.
# =============================================================================

import os
import json
import logging
from collections import deque
from typing import Any, Dict, List

from openai import AsyncOpenAI

from app.models.user import UserInDB
from app.models.vm import VMCreateRequest, VMUpdateRequest, VMAction, OS_Choice
from app.routes.vm_routes import create_vm, update_vm, delete_vm, list_my_vms
from fastapi import BackgroundTasks, Response

logger = logging.getLogger(__name__)

# --- TOOL SCHEMA DEFINITIONS FOR THE LLM (OpenAI function-calling JSON Schema)
# =============================================================================


def get_openai_tools() -> List[Dict[str, Any]]:
    """Returns tool definitions for the OpenAI Chat Completions API."""

    return [
        {
            "type": "function",
            "function": {
                "name": "deploy_virtual_machine",
                "description": (
                    "Deploys a new Virtual Machine. Only call this when the user "
                    "has confirmed the OS. cpu_cores, ram_mb, and storage_gb are "
                    "optional — use sensible defaults (2 cores, 2048 MB, 20 GB) "
                    "if the user does not specify them."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vm_name": {
                            "type": "string",
                            "description": "Unique name for the VM. 3-30 chars, alphanumeric and hyphens.",
                        },
                        "os_choice": {
                            "type": "string",
                            "enum": ["ubuntu-22.04", "ubuntu-24.04", "debian-12", "centos-9", "windows-11"],
                            "description": "Operating system. MUST be explicitly confirmed by the user — never assume.",
                        },
                        "cpu_cores": {
                            "type": "integer",
                            "description": "vCPU cores (1-16). Default 2 if not specified.",
                        },
                        "ram_mb": {
                            "type": "integer",
                            "description": "RAM in MB (512-65536). Default 2048 if not specified.",
                        },
                        "storage_gb": {
                            "type": "integer",
                            "description": "Disk in GB (10-500). Default 20 if not specified.",
                        },
                    },
                    "required": ["vm_name", "os_choice"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "modify_vm_power_state",
                "description": (
                    "Start, stop, or restart one or multiple VMs. The user can refer to the VMs "
                    "by their names (e.g. 'my-server'), by job IDs, or by relative "
                    "reference like 'last'. Use get_active_inventory first "
                    "if you need to resolve names."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vm_identifiers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of VM names, job IDs, or relative references.",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["start", "stop", "restart"],
                            "description": "Power operation to perform.",
                        },
                    },
                    "required": ["vm_identifiers", "action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "terminate_virtual_machine",
                "description": (
                    "Permanently deletes one or multiple VMs. The user can refer to them by name, "
                    "job ID, or 'last'. Always confirm before deleting."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vm_identifiers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of VM names, job IDs, or relative references.",
                        },
                    },
                    "required": ["vm_identifiers"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_active_inventory",
                "description": "Lists all of the user's VMs with their status, IP, and resource info.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]


# Maximum number of user+assistant turn pairs to keep per user
MAX_HISTORY_TURNS = 10


class CloudAgentService:
    """Orchestration system that evaluates user query intent and maps outputs to services."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # Per-user conversation memory: { username: deque([{role, content}, ...]) }
        self._history: Dict[str, deque] = {}
        if not self.api_key:
            self.client = None
        else:
            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            base_url = os.getenv("OPENAI_BASE_URL")
            if base_url:
                kwargs["base_url"] = base_url
            self.client = AsyncOpenAI(**kwargs)

    def _get_history(self, username: str) -> deque:
        """Returns the conversation history deque for a given user."""
        if username not in self._history:
            self._history[username] = deque(maxlen=MAX_HISTORY_TURNS * 2)
        return self._history[username]

    def _append_turn(self, username: str, user_msg: str, assistant_msg: str) -> None:
        """Appends a user+assistant exchange to the conversation history."""
        history = self._get_history(username)
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})

    async def execute_agent_loop(
        self,
        user_prompt: str,
        current_user: UserInDB,
        background_tasks: BackgroundTasks,
    ) -> Dict[str, Any]:
        """Evaluates user requests, calls underlying endpoints, and returns operational states."""
        if not self.client:
            logger.error("OPENAI_API_KEY environment variable is not set.")
            return {
                "response": "AI Assistant capabilities are offline. Set OPENAI_API_KEY in the environment.",
                "tool_called": None,
                "execution_status": "error",
            }

        tools = get_openai_tools()

        system_instruction = (
            "You are CloudOps AI, a friendly and helpful DevOps assistant for the AZNA Private Cloud platform. "
            "You help users create, manage, and monitor their virtual machines through natural conversation.\n\n"
            "RULES:\n"
            "1. When the user wants to CREATE a VM and provides a name but NOT the OS, you MUST ask them which "
            "operating system they want. Available options: Ubuntu 22.04, Ubuntu 24.04, Debian 12, CentOS 9, Windows 11. "
            "Do NOT default the OS — always ask.\n"
            "2. For CPU, RAM, and storage — if the user doesn't specify, use smart defaults based on the OS. "
            "For Linux (Ubuntu, Debian, CentOS): 2 cores, 2048 MB RAM, 20 GB disk. "
            "For Windows 11: 4 cores, 4096 MB RAM, 64 GB disk. "
            "Mention the defaults you're using in your response.\n"
            "3. Users can refer to VMs by name (e.g. 'my-server'), by job ID (e.g. '49'), or by relative "
            "references like 'my last VM', 'the one I just created'. If using a relative reference, call "
            "get_active_inventory first to resolve it.\n"
            "4. For destructive actions (delete), always confirm with the user before proceeding.\n"
            "5. Be concise but friendly. Use emojis sparingly. Do NOT promise to \\\"update the user later\\\" or \\\"let them know when it's done\\\", because you run synchronously. Just tell them it's provisioning in the background.\n"
            "6. Resource limits: vCPUs 1-16, RAM 512-65536 MB, Disk 10-500 GB.\n"
            "7. Bulk Operations: You can start, stop, restart, or terminate MULTIPLE VMs at once. "
            "When a user confirms a bulk action (e.g. 'yes delete both'), you MUST pass ALL their job IDs or names "
            "as an array to the tool in a single call. Do NOT do it one by one."
        )

        try:
            # Build messages with conversation history for context
            history = self._get_history(current_user.username)
            messages = [{"role": "system", "content": system_instruction}]
            messages.extend(list(history))  # prior turns
            messages.append({"role": "user", "content": user_prompt})

            completion = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            choice = completion.choices[0]
            msg = choice.message
            tool_calls = msg.tool_calls

            if not tool_calls:
                text = (msg.content or "").strip() or "(No response text from model.)"
                # Save conversational turn to history
                self._append_turn(current_user.username, user_prompt, text)
                return {
                    "response": text,
                    "tool_called": None,
                    "execution_status": "conversational",
                }

            tc = tool_calls[0]
            tool_name = tc.function.name
            raw_args = tc.function.arguments or "{}"
            try:
                tool_args = json.loads(raw_args)
            except json.JSONDecodeError as je:
                logger.error("Invalid JSON in tool arguments: %s — %s", raw_args, je)
                return {
                    "response": "The model returned malformed tool arguments; please retry with a clearer request.",
                    "tool_called": tool_name,
                    "execution_status": "failed",
                }

            if not isinstance(tool_args, dict):
                tool_args = {}

            logger.info("LLM Agent tool call: %s with parameters: %s", tool_name, tool_args)
            result = await self._dispatch_tool(tool_name, tool_args, current_user, background_tasks)
            # Save turn to history
            self._append_turn(current_user.username, user_prompt, result.get("response", ""))
            return result

        except Exception as err:
            logger.error("AI orchestration error: %s", err, exc_info=True)
            return {
                "response": f"An error occurred while contacting the language model: {err!s}",
                "tool_called": None,
                "execution_status": "failed",
            }

    def _resolve_job_id(self, identifier: str, user: UserInDB) -> int:
        """
        Resolve a VM identifier (name, job ID, or 'last') to a numeric job ID.

        Supports:
          - Numeric ID: "49" → 49
          - VM name: "web-server" → looks up in user's VMs
          - Relative: "last" → returns the most recently created VM
        """
        cleaned = str(identifier).strip().lower()

        # Direct numeric ID
        if cleaned.isdigit():
            return int(cleaned)

        # Fetch user's VMs for name/relative resolution
        vms = list_my_vms(current_user=user)
        if not vms:
            raise ValueError("You don't have any VMs yet.")

        # Relative reference: "last", "latest", "most recent", "the one I just created"
        if cleaned in ("last", "latest", "most recent", "newest"):
            return vms[0].id  # list_my_vms returns newest first

        # Name-based lookup (case-insensitive)
        for vm in vms:
            if vm.vm_name.lower() == cleaned:
                return vm.id

        # Fuzzy partial match as fallback
        for vm in vms:
            if cleaned in vm.vm_name.lower():
                return vm.id

        raise ValueError(
            f"Could not find a VM matching '{identifier}'. "
            f"Your VMs: {', '.join(v.vm_name for v in vms)}"
        )

    async def _dispatch_tool(
        self,
        name: str,
        args: Dict[str, Any],
        user: UserInDB,
        background_tasks: BackgroundTasks,
    ) -> Dict[str, Any]:
        """Dispatches tool calls into existing VM route handlers."""

        if name == "deploy_virtual_machine":
            try:
                os_raw = args.get("os_choice", "ubuntu-24.04")
                cpu = int(args.get("cpu_cores", 2))
                ram = int(args.get("ram_mb", 2048))
                storage = int(args.get("storage_gb", 20))

                request_model = VMCreateRequest(
                    vm_name=args["vm_name"],
                    os_choice=OS_Choice(os_raw),
                    cpu_cores=cpu,
                    ram_mb=ram,
                    storage_gb=storage,
                )

                job_response = create_vm(
                    vm_request=request_model,
                    current_user=user,
                )

                defaults_used = []
                if "cpu_cores" not in args:
                    defaults_used.append(f"{cpu} vCPUs")
                if "ram_mb" not in args:
                    defaults_used.append(f"{ram} MB RAM")
                if "storage_gb" not in args:
                    defaults_used.append(f"{storage} GB disk")

                defaults_note = ""
                if defaults_used:
                    defaults_note = f" (using defaults: {', '.join(defaults_used)})"

                return {
                    "response": (
                        f"VM '{args['vm_name']}' is now queued for deployment "
                        f"with {os_raw}{defaults_note}. "
                        f"Tracking as Job #{job_response.id} — I'll update you when it's ready!"
                    ),
                    "tool_called": name,
                    "execution_status": "success",
                    "data": job_response.model_dump(),
                }
            except ValueError as val_err:
                return {
                    "response": f"Parameter validation failed: {val_err!s}",
                    "tool_called": name,
                    "execution_status": "rejected",
                }
            except Exception as exc:
                return {
                    "response": f"Could not create the VM: {exc!s}",
                    "tool_called": name,
                    "execution_status": "failed",
                }

        elif name == "modify_vm_power_state":
            try:
                identifiers = args.get("vm_identifiers", [])
                action_str = args["action"]
                update_payload = VMUpdateRequest(action=VMAction(action_str))
                mock_response = Response()

                success_list = []
                for ident in identifiers:
                    try:
                        job_id = self._resolve_job_id(ident, user)
                        job_response = update_vm(
                            job_id=job_id,
                            update=update_payload,
                            response=mock_response,
                            current_user=user,
                        )
                        success_list.append(job_response.vm_name)
                    except Exception as loop_e:
                        logger.warning("Bulk modify failed for %s: %s", ident, loop_e)

                action_past = {"start": "started", "stop": "stopped", "restart": "restarted"}
                
                if not success_list:
                    return {
                        "response": f"Failed to {action_str} any of the specified VMs.",
                        "tool_called": name,
                        "execution_status": "failed",
                    }
                
                return {
                    "response": (
                        f"Done! Successfully {action_past.get(action_str, action_str)} "
                        f"{len(success_list)} VM(s): {', '.join(success_list)}."
                    ),
                    "tool_called": name,
                    "execution_status": "success",
                    "data": success_list,
                }
            except ValueError as ve:
                return {
                    "response": str(ve),
                    "tool_called": name,
                    "execution_status": "failed",
                }
            except Exception as exc:
                return {
                    "response": f"Power state change failed: {exc!s}",
                    "tool_called": name,
                    "execution_status": "failed",
                }

        elif name == "terminate_virtual_machine":
            try:
                identifiers = args.get("vm_identifiers", [])
                mock_response = Response()

                success_list = []
                for ident in identifiers:
                    try:
                        job_id = self._resolve_job_id(ident, user)
                        job_response = delete_vm(
                            job_id=job_id,
                            response=mock_response,
                            current_user=user,
                        )
                        success_list.append(job_response.vm_name)
                    except Exception as loop_e:
                        logger.warning("Bulk delete failed for %s: %s", ident, loop_e)

                if not success_list:
                    return {
                        "response": "Failed to delete any of the specified VMs. Check names and try again.",
                        "tool_called": name,
                        "execution_status": "failed",
                    }

                return {
                    "response": (
                        f"Initiated deletion for {len(success_list)} VM(s): {', '.join(success_list)}. "
                        f"This may take a moment to fully clean up on the cluster."
                    ),
                    "tool_called": name,
                    "execution_status": "success",
                    "data": success_list,
                }
            except ValueError as ve:
                return {
                    "response": str(ve),
                    "tool_called": name,
                    "execution_status": "failed",
                }
            except Exception as exc:
                return {
                    "response": f"Deletion failed: {exc!s}",
                    "tool_called": name,
                    "execution_status": "failed",
                }

        elif name == "get_active_inventory":
            try:
                vms_list = list_my_vms(current_user=user)
                serialized_vms = [vm.model_dump() for vm in vms_list]

                if not serialized_vms:
                    return {
                        "response": "You don't have any VMs yet. Want me to create one for you?",
                        "tool_called": name,
                        "execution_status": "success",
                        "data": [],
                    }

                summary = "\n".join(
                    [
                        f"• **{v['vm_name']}** (Job #{v['id']}) — "
                        f"Status: {v['live_status']} | "
                        f"IP: {v['vm_ip'] or 'Pending'}"
                        for v in serialized_vms
                    ]
                )
                response_text = (
                    f"Here are your {len(serialized_vms)} VM(s):\n\n{summary}"
                )

                return {
                    "response": response_text,
                    "tool_called": name,
                    "execution_status": "success",
                    "data": serialized_vms,
                }
            except Exception as exc:
                return {
                    "response": f"Failed to list VMs: {exc!s}",
                    "tool_called": name,
                    "execution_status": "failed",
                }

        return {
            "response": "The selected tool is not implemented.",
            "tool_called": name,
            "execution_status": "unsupported",
        }





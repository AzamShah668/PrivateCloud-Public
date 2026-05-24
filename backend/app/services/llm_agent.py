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
                "description": "Deploys or creates a new Virtual Machine (VM) compute instance on the private cloud cluster.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vm_name": {
                            "type": "string",
                            "description": "Unique identifier name for the VM. 3-30 characters, alphanumeric and hyphens only (e.g., 'web-server-01').",
                        },
                        "os_choice": {
                            "type": "string",
                            "enum": ["ubuntu-22.04", "ubuntu-24.04", "debian-12", "centos-9", "windows-11"],
                            "description": "Operating system choice. Defaults to 'ubuntu-24.04' if not explicit.",
                        },
                        "cpu_cores": {
                            "type": "integer",
                            "description": "Number of allocated vCPU cores. Acceptable bounds: 1 to 16 cores.",
                        },
                        "ram_mb": {
                            "type": "integer",
                            "description": "System volatile memory capacity assigned to the guest in Megabytes (MB). E.g., 2GB is 2048.",
                        },
                        "storage_gb": {
                            "type": "integer",
                            "description": "Main root system disk allocation space in Gigabytes (GB). Range bounds: 10 to 500.",
                        },
                    },
                    "required": ["vm_name", "cpu_cores", "ram_mb", "storage_gb"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "modify_vm_power_state",
                "description": "Alters power sequences for a VM by job ID (start, stop, or restart).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "integer",
                            "description": "The internal database Job ID (not the Proxmox vmid).",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["start", "stop", "restart"],
                            "description": "Power operation to perform.",
                        },
                    },
                    "required": ["job_id", "action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "terminate_virtual_machine",
                "description": "Permanently deletes a Virtual Machine from the cluster and inventory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "integer",
                            "description": "Database primary key Job ID for the VM to delete.",
                        },
                    },
                    "required": ["job_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_active_inventory",
                "description": "Lists the user's VMs with live status and networking hints.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]


# Maximum number of user+assistant turn pairs to keep per user
MAX_HISTORY_TURNS = 6


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
            "You are the unified system automation engine for azna-cloud private environment infrastructure. "
            "Your critical function is evaluating user messages and producing precise function arguments. "
            "Assert limits: vCPUs must be in [1, 16], RAM in [512, 65536] MB. If the user asks for resources "
            "outside limits or you lack required parameters (e.g. VM name), refuse or ask for clarification "
            "instead of calling tools with guesses."
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

                request_model = VMCreateRequest(
                    vm_name=args["vm_name"],
                    os_choice=OS_Choice(os_raw),
                    cpu_cores=int(args["cpu_cores"]),
                    ram_mb=int(args["ram_mb"]),
                    storage_gb=int(args["storage_gb"]),
                )

                job_response = create_vm(
                    vm_request=request_model,
                    background_tasks=background_tasks,
                    current_user=user,
                )

                return {
                    "response": (
                        f"Acknowledged. I have initialized the backend resource sequence pipelines. "
                        f"Tracking Job #{job_response.id} is now queued for deployment."
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
                    "response": f"Infrastructure engine rejected provisioning tasks: {exc!s}",
                    "tool_called": name,
                    "execution_status": "failed",
                }

        elif name == "modify_vm_power_state":
            try:
                job_id = int(args["job_id"])
                update_payload = VMUpdateRequest(action=VMAction(args["action"]))

                mock_response = Response()
                job_response = update_vm(
                    job_id=job_id,
                    update=update_payload,
                    response=mock_response,
                    current_user=user,
                )

                return {
                    "response": (
                        f"Power state updated. Action '{args['action']}' dispatched for job ID {job_id}."
                    ),
                    "tool_called": name,
                    "execution_status": "success",
                    "data": job_response.model_dump(),
                }
            except Exception as exc:
                return {
                    "response": f"Power state change failed: {exc!s}",
                    "tool_called": name,
                    "execution_status": "failed",
                }

        elif name == "terminate_virtual_machine":
            try:
                job_id = int(args["job_id"])
                mock_response = Response()

                job_response = delete_vm(
                    job_id=job_id,
                    response=mock_response,
                    current_user=user,
                )

                return {
                    "response": (
                        f"Deletion initiated for job ID {job_id}; the VM is being removed from the cluster."
                    ),
                    "tool_called": name,
                    "execution_status": "success",
                    "data": job_response.model_dump(),
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

                summary = "\n".join(
                    [
                        f"• ID: {v['id']} | Name: {v['vm_name']} | Status: {v['live_status']} | IP: {v['vm_ip'] or 'Allocation Pending'}"
                        for v in serialized_vms
                    ]
                )
                response_text = (
                    f"Retrieved cluster registry maps successfully. Found {len(serialized_vms)} operational entities:\n\n{summary}"
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

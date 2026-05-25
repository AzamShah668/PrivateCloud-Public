# 03 — AI ChatOps Agent: Smart Defaults & Name-Based VM Lookup

**Commit:** `e400d3e` · **Date:** 2026-05-24 · **File:** `backend/app/services/llm_agent.py`

## What changed

The ChatOps agent (the in-dashboard "talk to your cloud" assistant) was rebuilt from a rigid, robotic function-caller into a friendly conversational DevOps assistant. Three concrete capabilities were added:

1. **Smart defaults** — the user only has to give a VM **name** and **OS**; CPU/RAM/disk are optional and filled with sensible values.
2. **Name-based & relative VM references** — power and delete actions accept a VM **name** or `"last"`, not just a numeric job ID.
3. **A conversational system prompt** — the model asks for the OS instead of guessing, confirms destructive actions, and speaks like a helpful human.

## Architecture recap

The agent is OpenAI-style tool-calling. `get_openai_tools()` returns JSON tool schemas; the model decides which to call; `_dispatch_tool()` maps each call onto the existing REST service functions (`create_vm`, `update_vm`, `delete_vm`, `list_my_vms`). The change touched the **tool schemas**, the **system prompt**, the **dispatcher**, and added a **resolver** helper.

```
User message ─► LLM ─► tool call (JSON args) ─► _dispatch_tool ─► existing service fn ─► DB/Celery
                 ▲                                     │
                 └──────── natural-language reply ◄─────┘
```

## Change 1 — Optional sizing with smart defaults

### Tool schema: fewer required fields

`deploy_virtual_machine` previously **required** `vm_name`, `cpu_cores`, `ram_mb`, `storage_gb`. Now it requires only the two things a human actually must decide:

```python
"required": ["vm_name", "os_choice"],
```

The numeric params became optional, and their descriptions tell the model the defaults:

```python
"cpu_cores":  {"type": "integer", "description": "vCPU cores (1-16). Default 2 if not specified."},
"ram_mb":     {"type": "integer", "description": "RAM in MB (512-65536). Default 2048 if not specified."},
"storage_gb": {"type": "integer", "description": "Disk in GB (10-500). Default 20 if not specified."},
"os_choice":  {"type": "string", "enum": [...], "description": "Operating system. MUST be explicitly confirmed by the user — never assume."},
```

### Dispatcher: apply defaults and report them

In `_dispatch_tool`, the `deploy_virtual_machine` branch defaults the missing values **and tells the user which defaults it used** so nothing is silently assumed:

```python
cpu     = int(args.get("cpu_cores", 2))
ram     = int(args.get("ram_mb", 2048))
storage = int(args.get("storage_gb", 20))

request_model = VMCreateRequest(
    vm_name=args["vm_name"],
    os_choice=OS_Choice(os_raw),
    cpu_cores=cpu, ram_mb=ram, storage_gb=storage,
)
job_response = create_vm(vm_request=request_model, background_tasks=background_tasks, current_user=user)

defaults_used = []
if "cpu_cores"  not in args: defaults_used.append(f"{cpu} vCPUs")
if "ram_mb"     not in args: defaults_used.append(f"{ram} MB RAM")
if "storage_gb" not in args: defaults_used.append(f"{storage} GB disk")
defaults_note = f" (using defaults: {', '.join(defaults_used)})" if defaults_used else ""

return {
    "response": (
        f"VM '{args['vm_name']}' is now queued for deployment "
        f"with {os_raw}{defaults_note}. "
        f"Tracking as Job #{job_response.id} — I'll update you when it's ready!"
    ),
    "tool_called": name,
    ...
}
```

## Change 2 — Refer to VMs by name or "last"

The power and delete tools dropped the `job_id` integer in favour of a free-form `vm_identifier` string:

```python
"vm_identifier": {
    "type": "string",
    "description": "VM name, job ID, or 'last' for the most recently created VM.",
}
```

A new resolver translates whatever the user said into a numeric job ID:

```python
def _resolve_job_id(self, identifier: str, user: UserInDB) -> int:
    """Resolve a VM identifier (name, job ID, or 'last') to a numeric job ID."""
    cleaned = str(identifier).strip().lower()

    if cleaned.isdigit():                       # "49" → 49
        return int(cleaned)

    vms = list_my_vms(current_user=user)
    if not vms:
        raise ValueError("You don't have any VMs yet.")

    if cleaned in ("last", "latest", "most recent", "newest"):
        return vms[0].id                        # list_my_vms returns newest first

    for vm in vms:                              # exact name match (case-insensitive)
        if vm.vm_name.lower() == cleaned:
            return vm.id

    for vm in vms:                              # fuzzy partial match fallback
        if cleaned in vm.vm_name.lower():
            return vm.id

    raise ValueError(
        f"Could not find a VM matching '{identifier}'. "
        f"Your VMs: {', '.join(v.vm_name for v in vms)}"
    )
```

**Resolution order:** numeric ID → relative keyword (`last`/`latest`/…) → exact name → partial name → error listing the user's real VMs (so the model can re-ask intelligently).

## Change 3 — A conversational system prompt

The old prompt told the model it was a "unified system automation engine" and to "produce precise function arguments." The new one gives it personality and explicit behavioural rules:

```python
system_instruction = (
    "You are CloudOps AI, a friendly and helpful DevOps assistant for the AZNA Private Cloud platform. "
    "You help users create, manage, and monitor their virtual machines through natural conversation.\n\n"
    "RULES:\n"
    "1. When the user wants to CREATE a VM and provides a name but NOT the OS, you MUST ask them which "
    "operating system they want. ... Do NOT default the OS — always ask.\n"
    "2. For CPU, RAM, and storage — if the user doesn't specify, use smart defaults: 2 cores, 2 GB RAM, 20 GB disk. "
    "Mention the defaults you're using in your response.\n"
    "3. Users can refer to VMs by name, by job ID, or by relative references like 'my last VM'. "
    "If using a relative reference, call get_active_inventory first to resolve it.\n"
    "4. For destructive actions (delete), always confirm with the user before proceeding.\n"
    "5. Be concise but friendly. Use emojis sparingly. Don't be robotic.\n"
    "6. Resource limits: vCPUs 1-16, RAM 512-65536 MB, Disk 10-500 GB.\n"
    "7. If a user says 'stop all my VMs' ... handle each VM one at a time by first listing them, then confirming."
)
```

Also bumped `MAX_HISTORY_TURNS` from `6` to `10` so multi-step conversations (ask OS → confirm → create) keep enough context.

## The key design tension

OS is the one parameter the agent is **forbidden** to default (rule 1: "always ask"), while CPU/RAM/disk are the ones it **must** default (rule 2). Rationale: picking the wrong OS produces a fundamentally wrong machine; picking conservative compute is cheap and easily resized. So the contract is "name + OS from the human, everything else from the assistant."

## Teaching summary

| | |
|---|---|
| **Before** | Robotic; required 4 fields; only accepted numeric job IDs. |
| **After** | Friendly; requires name+OS only; resolves names/`last`; confirms deletes. |
| **New helper** | `_resolve_job_id()` — numeric → relative → exact name → fuzzy → helpful error. |
| **Guardrail** | Never default the OS; always default compute and announce it. |

Superseded by [04 — Multi-VM Bulk Operations](04-ai-agent-multi-vm-bulk-ops.md), which generalizes the single `vm_identifier` into an array.

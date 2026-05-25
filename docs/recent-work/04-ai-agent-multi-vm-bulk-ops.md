# 04 — AI ChatOps Agent: Multi-VM Bulk Operations

**Commit:** `c6a9749` · **Date:** 2026-05-25 · **File:** `backend/app/services/llm_agent.py`

## What changed

This builds directly on [03](03-ai-agent-smart-defaults-name-lookup.md). The agent can now act on **several VMs in a single instruction** — "stop both my servers", "restart web-1 and web-2", "delete all of them" — instead of being forced to handle one VM per tool call. Three smaller refinements rode along: OS-aware defaults, a corrected provisioning call signature, and an honest prompt about synchronous execution.

## Change 1 — `vm_identifier` (string) → `vm_identifiers` (array)

Both `modify_vm_power_state` and `terminate_virtual_machine` now take a **list** of identifiers:

```python
"vm_identifiers": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of VM names, job IDs, or relative references.",
},
# required:
"required": ["vm_identifiers", "action"],   # power
"required": ["vm_identifiers"],             # terminate
```

The element type is still "name, job ID, or relative reference", so each entry flows through the same `_resolve_job_id()` resolver from doc 03.

## Change 2 — Dispatcher loops over the list, tolerating partial failure

The power-state branch now iterates, resolving and acting on each VM independently. **One bad identifier doesn't abort the whole batch** — it's logged and skipped, and the reply reports what actually succeeded:

```python
elif name == "modify_vm_power_state":
    try:
        identifiers = args.get("vm_identifiers", [])
        action_str  = args["action"]
        update_payload = VMUpdateRequest(action=VMAction(action_str))
        mock_response  = Response()

        success_list = []
        for ident in identifiers:
            try:
                job_id = self._resolve_job_id(ident, user)
                job_response = update_vm(
                    job_id=job_id, update=update_payload,
                    response=mock_response, current_user=user,
                )
                success_list.append(job_response.vm_name)
            except Exception as loop_e:
                logger.warning("Bulk modify failed for %s: %s", ident, loop_e)

        action_past = {"start": "started", "stop": "stopped", "restart": "restarted"}

        if not success_list:
            return {
                "response": f"Failed to {action_str} any of the specified VMs.",
                "tool_called": name, "execution_status": "failed",
            }

        return {
            "response": (
                f"Done! Successfully {action_past.get(action_str, action_str)} "
                f"{len(success_list)} VM(s): {', '.join(success_list)}."
            ),
            "tool_called": name, "execution_status": "success",
            "data": success_list,
        }
```

The `terminate_virtual_machine` branch follows the same loop-and-collect pattern.

### Why per-item try/except

If the user says "stop web-1 and typo-name", we still want web-1 stopped. Wrapping each iteration means a single unresolved name degrades gracefully instead of failing the whole command. The `data` field returns the list of names actually affected, so the UI/model can report precisely.

## Change 3 — OS-aware smart defaults (refinement of doc 03)

Rule 2 of the system prompt evolved from a single default to per-OS defaults, because Windows needs more headroom than Linux:

```python
"2. For CPU, RAM, and storage — if the user doesn't specify, use smart defaults based on the OS. "
"For Linux (Ubuntu, Debian, CentOS): 2 cores, 2048 MB RAM, 20 GB disk. "
"For Windows 11: 4 cores, 4096 MB RAM, 64 GB disk. "
"Mention the defaults you're using in your response.\n"
```

## Change 4 — New bulk-operations rule + honesty about sync execution

Rule 7 was rewritten to **instruct the model to batch**, and rule 5 was corrected so the agent stops making promises it can't keep:

```python
"5. Be concise but friendly. Use emojis sparingly. Do NOT promise to \"update the user later\" "
"or \"let them know when it's done\", because you run synchronously. Just tell them it's provisioning "
"in the background.\n"
...
"7. Bulk Operations: You can start, stop, restart, or terminate MULTIPLE VMs at once. "
"When a user confirms a bulk action (e.g. 'yes delete both'), you MUST pass ALL their job IDs or names "
"as an array to the tool in a single call. Do NOT do it one by one."
```

The old prompt told it to "handle each VM one at a time" — which fought against the new array tool. The new rule aligns prompt and schema: **confirm once, then send the whole array in one call.**

## Change 5 — Fixed `create_vm` call signature

The deploy branch dropped a stale `background_tasks=background_tasks` argument that `create_vm` no longer accepts in this path:

```python
job_response = create_vm(
    vm_request=request_model,
    current_user=user,          # background_tasks removed
)
```

## Teaching summary

| | |
|---|---|
| **Core change** | `vm_identifier: string` → `vm_identifiers: array` on power + terminate tools. |
| **Dispatcher** | Loop with per-item try/except; collect `success_list`; report count + names. |
| **Failure model** | Partial success is allowed; only "zero succeeded" is a failure. |
| **Prompt alignment** | Rule 7 now *requires* batching; rule 5 stops false "I'll update you" promises. |
| **Bonus fixes** | OS-aware defaults (Windows 4c/4GB/64GB); removed stale `background_tasks` arg. |

Builds on [03 — Smart Defaults & Name Lookup](03-ai-agent-smart-defaults-name-lookup.md).

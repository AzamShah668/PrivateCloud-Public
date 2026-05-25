# Recent Work — May 24–25, 2026

This folder documents every change made to PrivateCloud over the **24th and 25th of May 2026**, across both Claude Code sessions and the Antigravity agent. Each concept lives in its own file. Every file explains **what** was built, **how** it works, the **structure**, and the **exact code** that implements it.

> Source of truth: commits `7027dfd → 5dd75e8` on branch `azams-branch`. These docs distill the diffs + sprint journals 016/017/018 into teaching-grade explanations.

## Commits covered

| Commit | Date | Title |
|---|---|---|
| `7027dfd` | 05-24 19:23 | Fix Celery auto-discovery, Docker healthcheck, add Sprint Journal 016 |
| `d6d7988` | 05-24 19:40 | Auto-promote first user to admin |
| `e400d3e` | 05-24 20:23 | Upgrade AI agent: smart defaults, name-based VM lookup, friendly prompt |
| `c6a9749` | 05-25 11:27 | feat: support multi-VM operations in AI ChatOps agent |
| `dcbffd9` | 05-25 11:29 | feat: cross-device console and remote desktop access |
| `5dd75e8` | 05-25 11:32 | fix: recover VM IP/credentials after failed provisioning, hide deleted VMs |

## Files in this folder

| # | File | Concept | Layer |
|---|---|---|---|
| 01 | [01-celery-autodiscovery-healthcheck.md](01-celery-autodiscovery-healthcheck.md) | Why Celery silently dropped `vm.provision` tasks and how explicit imports + a Celery-native healthcheck fixed it | Infra / Celery |
| 02 | [02-auto-promote-first-admin.md](02-auto-promote-first-admin.md) | First-ever registered user is automatically made an admin | DB / Auth |
| 03 | [03-ai-agent-smart-defaults-name-lookup.md](03-ai-agent-smart-defaults-name-lookup.md) | ChatOps agent: optional sizing with smart defaults + referring to VMs by name or "last" | Backend / LLM |
| 04 | [04-ai-agent-multi-vm-bulk-ops.md](04-ai-agent-multi-vm-bulk-ops.md) | ChatOps agent: start/stop/restart/delete **multiple** VMs in one instruction | Backend / LLM |
| 05 | [05-cross-device-console-desktop.md](05-cross-device-console-desktop.md) | Make ttyd console + Guacamole RDP reachable from phones/other LAN devices; generalize RDP→RDP+SSH | Frontend + Backend |
| 06 | [06-vm-ip-credential-self-heal.md](06-vm-ip-credential-self-heal.md) | Recover `vm_ip` + credentials when initial provisioning crashed mid-way; hide deleted VMs; fix a latent rename bug | Backend / DB |

## How these concepts connect

```
Provisioning (Celery)  ──01── reliable task delivery
        │
        ├──06── if it crashes mid-way, IP/credentials self-heal later
        │
Access layer ──05── console + desktop reachable cross-device
        │
ChatOps agent ──03,04── natural-language create/manage, single or bulk
        │
Auth ──02── first user becomes admin so the portal is usable day one
```

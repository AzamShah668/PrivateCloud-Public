# PrivateCloud Knowledge Base (MOC)

> Map of Content for AI-assisted retrieval. Each file is a distilled topic.
> Updated: 2026-06-04

## Architecture & Infrastructure
- [[01-network-topology]] - IP subnets, port proxying, firewall rules
- [[02-docker-infrastructure]] - Compose services, env vars, build pipeline
- [[03-celery-provisioning]] - Async task system, Redis broker, worker config

## Frontend
- [[04-frontend-architecture]] - Component tree, key props, modal patterns
- [[05-console-connectivity]] - ttyd setup, cross-device URL rewriting
- [[06-guacamole-integration]] - RDP/SSH via Guacamole, URL rewriting

## AI / Agent
- [[10-rag-knowledge-base]] - Agentic RAG: ChatOps agent answers from uploaded docs (ChromaDB + local embeddings + OpenRouter)

## Clone-from-Template (Sprint 5)
- [[11-clone-templates]] - Teacher publishes a VM as a template, bulk-clones it to a class of students (full/linked clones)

## State & Configuration (Iteration 6)
- [[12-state-reconciliation]] - DB↔Proxmox reconciliation: soft-delete VMs deleted out-of-band so the DB stays truthful and the UI reads the corrected DB
- [[13-config-and-setup-wizard]] - Config moved from .env into DB-backed encrypted settings + first-run setup wizard (Proxmox/LLM/Guacamole)

## Operations
- [[07-debugging-journal]] - Resolved issues with root causes
- [[08-pending-work]] - Unfinished items with exact state
- [[09-viva-preparation]] - Key talking points for university presentation

## Retrieval Protocol
1. **Graphify** `py -3 -m graphify query "<topic>" --budget 2000` for code structure
2. **This knowledge base** for decisions, context, infrastructure
3. **Raw source files** only if the above two are insufficient

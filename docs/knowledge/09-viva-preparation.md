# Viva Preparation - Key Talking Points

## Architecture Overview
- **3-tier**: React Frontend -> FastAPI Backend -> Proxmox Hypervisor
- **Async provisioning**: Celery + Redis for non-blocking VM creation
- **Remote access**: ttyd (Linux terminal), Guacamole (Windows RDP)
- **Auth**: JWT tokens, bcrypt password hashing, role-based access (admin/user)

## Why Celery? (Expect this question)
VM provisioning takes 30-120 seconds. Without Celery, each request blocks a FastAPI worker thread. With only 4 workers, 4 simultaneous requests = complete service freeze. Celery offloads to a separate process pool.

## Cross-Device Access (Impressive demo point)
Show creating a VM from laptop, then accessing its console from a phone:
1. The phone hits the laptop's Wi-Fi IP (192.168.31.157)
2. Frontend dynamically resolves URLs using window.location.hostname
3. Port proxy bridges the Wi-Fi subnet to the VM's internal subnet
4. No VPN, no Tailscale - pure network engineering

## Database Design
- PostgreSQL for app data (users, vm_jobs, audit_logs)
- MySQL for Guacamole (required by Apache Guacamole, separate concern)
- Schema-on-startup via db/database.py (ThreadedConnectionPool, CREATE IF NOT EXISTS)

## Security Measures
- JWT with expiry, bcrypt password hashing
- Daily VM creation quotas (prevent abuse)
- Audit logging for all actions
- CORS configuration for frontend

## ChatOps / AI Integration
- Natural language VM management via LLM agent
- System prompt includes OS-specific defaults
- Commands: 'create an ubuntu vm', 'show my vms', 'delete vm 5'
- Sprint 5: multi-VM operations ('stop both my Linux VMs'), name-based lookup,
  smart spec defaults

## Sprint 5 — RAG Knowledge Base (Agentic Retrieval)
Admin uploads PDF/MD docs; the ChatOps agent answers Proxmox/platform questions
from them instead of hallucinating.
- **Stack:** ChromaDB (self-hosted) + local SentenceTransformers embeddings
  (no external API call for embeddings) + OpenRouter for generation
- **Pattern:** "agentic RAG" — the LLM decides per turn whether to call
  `search_knowledge_base()` as a tool, then synthesises with the retrieved chunks
- **Why it matters:** answers stay accurate to OUR platform's docs, costs ~$0
  per query (only LLM-generation tokens), and the doc set is fully under admin
  control via `/admin/knowledge`
- **See:** [[10-rag-knowledge-base]], journal 019

## Sprint 5 — Clone-from-Template (Lab/Class Provisioning)
Solves the "every student wastes 20 minutes installing the lab app" problem.
Admin/teacher pre-bakes one VM, publishes it as a **template**, then
**bulk-clones** it to a whole **class** of students in one action.
- **Why this is novel here:** the platform already cloned golden images on every
  provision — I exposed cloning as a teacher-driven feature, and cloned student
  VMs go into the EXISTING `vm_jobs` table so console/RDP/expiry all work unchanged.
- **5 new tables:** `vm_templates`, `class_groups`, `class_enrollments`,
  `clone_batches`, `clone_jobs` — all added via the existing
  schema-on-startup `init_db()`.
- **Full vs linked clones:** teacher chooses per template. Linked = near-instant
  (shares the source disk) but freezes the source; full = independent disk.
- **Race-free VMID allocation:** Proxmox's `nextid` returns the same id until
  consumed. I added `get_free_vmids(count, extra_reserved=...)` that excludes
  Proxmox in-use + our DB-reserved VMIDs, wrapped in a Redis lock so two
  concurrent distributions can't collide.
- **Quota bypass:** teacher-distributed clones intentionally skip the per-student
  daily quota — the whole point is everyone gets one instantly.
- **See:** [[11-clone-templates]], journal 020,
  `docs/design/clone-templates-architecture.md`

## Likely tutor questions & ready answers

**Q: "How does cloning work without new infrastructure?"**
Proxmox already clones golden images on every VM creation. I generalised that
primitive into a teacher-driven feature and reused the `vm_jobs` table so all
existing access paths just work.

**Q: "What stops two simultaneous bulk clones from colliding on the same VMID?"**
Three layers: (1) `get_free_vmids` excludes VMIDs reserved in our `vm_jobs`
table (not just Proxmox's in-use list), (2) a Redis lock serialises the
allocate+create block across requests, (3) Celery tasks fan out only AFTER
the rows commit and the lock releases.

**Q: "Why RAG instead of fine-tuning the LLM?"**
RAG keeps the doc set under admin control, has near-zero cost (no fine-tune,
no retraining), and the LLM only sees relevant chunks — accuracy stays high
even when docs change.

**Q: "What was the hardest bug?"**
The IP/credentials recovery story (journal 018) — when initial provisioning
failed before the IP poll, `vm_ip` and credentials stayed NULL forever. I added
three self-heal hooks (post-action long poll, GET inline poll, credential
backfill) so the VM dashboard recovers itself on the next page load.

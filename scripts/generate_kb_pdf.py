"""
Generate the AZNA Private Cloud knowledge-base PDF for the RAG agent.

WHY Q&A (not raw JSON): the RAG pipeline chunks this PDF every ~500 chars and
embeds each chunk. Self-contained question/answer pairs in plain language give
the cleanest, most retrievable chunks - the user's question embeds close to the
stored question, and each answer stands alone. Raw JSON would be sliced
mid-object and retrieve poorly.

WHAT IS EXCLUDED (security): no passwords, API keys, JWT/DB/Proxmox/Guacamole
credentials, exact internal IPs/ports, or default VM login values. Everything
here is safe for an end user to read.

Run:  py -3 scripts/generate_kb_pdf.py
Out:  docs/rag-source/PrivateCloud-Knowledge-Base.pdf
"""

import os
from datetime import date

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# fpdf2 multi_cell leaves the cursor at the right edge by default; this returns
# it to the left margin on the next line so consecutive full-width blocks work.
NL = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "rag-source")
OUT_PATH = os.path.join(OUT_DIR, "PrivateCloud-Knowledge-Base.pdf")

# Each section: (title, [(question, answer), ...]).
# Answers are kept ASCII-only (fpdf core fonts are latin-1) and self-contained
# so each Q&A survives chunking as a standalone, meaningful unit.
SECTIONS = [
    ("1. Platform Overview", [
        ("What is AZNA Private Cloud?",
         "AZNA Private Cloud (also called PrivateCloud) is a self-hosted private "
         "cloud platform for managing virtual machines (VMs). Users sign in, "
         "create and control VMs through a web dashboard or by chatting with an "
         "AI assistant, and then connect to those VMs through a browser-based "
         "console or remote desktop."),
        ("What can I do with this platform?",
         "You can: register and log in to your own account; create virtual "
         "machines running Linux or Windows; start, stop, restart, resize, and "
         "delete those VMs; view their live status and IP address; open a "
         "web console (Linux) or remote desktop (Windows) from any device; and "
         "manage everything in plain English through the built-in AI ChatOps "
         "assistant. Administrators can additionally publish templates, group "
         "students into classes, and bulk-clone a template to a whole class."),
        ("Who is this platform for?",
         "It is for users who need on-demand virtual machines without dealing "
         "with the underlying virtualization manually. Regular users manage "
         "their own VMs. Administrators additionally manage users, quotas, "
         "audit logs, platform settings, the AI knowledge base, VM templates, "
         "and student classes. A common use case is university labs, where a "
         "teacher pre-bakes one VM with the lab software and distributes a "
         "ready-to-run clone to every student in seconds."),
        ("What technology powers the platform?",
         "A FastAPI (Python) backend, a PostgreSQL database, asynchronous "
         "background jobs via Celery and Redis, virtualization on Proxmox VE, "
         "and a React + TypeScript web frontend. Remote access uses a web "
         "terminal for Linux and Apache Guacamole for Windows remote desktop. "
         "The AI knowledge base uses ChromaDB-style local vector search."),
        ("Is this multi-user?",
         "Yes. Many users can register and log in concurrently. Each user only "
         "sees their own VMs. Administrators see all VMs across all users and "
         "can manage the platform globally."),
    ]),

    ("2. Accounts and Sign-In", [
        ("How do I create an account?",
         "On the sign-in page, click 'Register', then choose a username and "
         "password. Your account is created instantly and you can sign in right "
         "away. The very first account created on a new system becomes an "
         "administrator automatically."),
        ("How do I log in?",
         "Open the platform in your browser, enter your username and password on "
         "the sign-in page, and click 'Sign In'. After signing in you are taken "
         "to your dashboard, which lists your virtual machines."),
        ("I get 'Invalid username or password' but my details are correct. Why?",
         "First confirm the username and password are exactly right, including "
         "capitalization. If correct credentials still fail for everyone, it is "
         "usually a backend or service issue rather than your account; contact "
         "an administrator to check the platform status."),
        ("How do I change my username or password?",
         "Once signed in, open your account settings and update your username "
         "and/or password there. The change takes effect immediately and you "
         "continue using the platform with the new credentials."),
        ("What is a daily quota?",
         "Each user can create only a limited number of VMs per day. This daily "
         "quota prevents over-use of the shared hardware. If you reach your "
         "limit you will see a message telling you to try again the next day or "
         "ask an administrator to raise your quota. Note: VMs created by a "
         "teacher distributing a template to a class do NOT count against the "
         "student's daily quota."),
        ("What is the difference between a user and an administrator?",
         "A regular user manages only their own virtual machines. An "
         "administrator can additionally view and manage all users, change "
         "roles and quotas, review audit logs, adjust platform settings, "
         "upload documents to the AI knowledge base, publish VM templates, "
         "create student classes, and bulk-distribute templates to classes."),
        ("How is my password stored?",
         "Passwords are hashed with bcrypt before being saved. The platform "
         "never stores or sees your plain password. Even an administrator "
         "looking at the database sees only the hash, not the original."),
        ("How long does my session last?",
         "After signing in, the platform issues a JSON Web Token (JWT) that is "
         "valid for a set period (typically several hours). When it expires you "
         "are returned to the sign-in page."),
    ]),

    ("3. Creating Virtual Machines", [
        ("How do I create a virtual machine?",
         "From the dashboard, open the VM creation page (or just ask the AI "
         "assistant). Give the VM a name, choose an operating system, and "
         "optionally set CPU, memory, and disk size. Submit the request and the "
         "VM is provisioned in the background; you can watch its status change "
         "from queued to running."),
        ("Which operating systems can I choose?",
         "You can choose Ubuntu 22.04, Ubuntu 24.04, Debian 12, CentOS 9, or "
         "Windows 11. The Linux options are reached through a web console; "
         "Windows 11 is reached through a remote desktop session."),
        ("What CPU, memory, and disk sizes are allowed?",
         "vCPUs can be 1 to 16, memory can be 512 MB to 65536 MB, and disk can "
         "be 10 GB to 500 GB. Values outside these ranges are rejected so the "
         "shared hardware stays healthy."),
        ("What happens if I do not specify CPU, memory, or disk?",
         "Sensible defaults are applied. For Linux (Ubuntu, Debian, CentOS) the "
         "defaults are 2 vCPUs, 2048 MB memory, and 20 GB disk. For Windows 11 "
         "the defaults are higher: 4 vCPUs, 4096 MB memory, and 64 GB disk. The "
         "assistant tells you which defaults it used."),
        ("How long does it take to create a VM?",
         "Creation runs in the background and is not instant. After you submit, "
         "the VM is 'queued', then provisioned on the virtualization host, then "
         "becomes 'running'. Linux VMs are usually ready in 1-3 minutes; "
         "Windows VMs can take 5-10 minutes, especially during first-boot setup."),
        ("What do the VM statuses mean?",
         "'queued' means the request is accepted and waiting to be provisioned. "
         "'running' (or 'done') means the VM is up and ready. 'stopped' means "
         "it is powered off. 'failed' means provisioning hit an error; the "
         "error message explains what went wrong (for example a resource "
         "limit). 'deleted' means the VM has been destroyed."),
        ("Must I confirm the operating system before a VM is created?",
         "Yes. The AI assistant will never guess the operating system. If you "
         "ask it to create a VM without naming the OS, it asks you to pick one "
         "first. This prevents accidentally creating the wrong kind of machine."),
        ("What happens behind the scenes when I create a VM?",
         "The backend gets a unique VM ID from Proxmox, records the request in "
         "the database with status 'queued', and immediately returns. A Celery "
         "background worker then clones the appropriate golden image (Ubuntu or "
         "Windows), applies your CPU/memory/disk, starts the VM, waits for the "
         "guest agent to report an IP, and writes the IP and login details back "
         "to the database. Your dashboard updates as each stage completes."),
    ]),

    ("4. Managing Virtual Machines", [
        ("How do I start, stop, or restart a VM?",
         "Use the controls on the VM's card or detail page, or ask the AI "
         "assistant (for example 'stop my web-server'). Starting powers the VM "
         "on, stopping powers it off, and restarting reboots it."),
        ("How do I resize a VM (change CPU, memory, or disk)?",
         "Open the VM and use the resize option to change its vCPUs, memory, or "
         "disk within the allowed limits. Resizing generally requires the VM to "
         "be stopped first, and on restart the new resources take effect."),
        ("How do I delete a VM?",
         "Delete it from the VM's page or ask the AI assistant. Deletion is "
         "permanent and destroys the VM, so the assistant always asks you to "
         "confirm before deleting. Deleted VMs no longer appear in your list."),
        ("How do I see all my VMs and their details?",
         "Your dashboard lists every VM you own with its name, status, IP "
         "address, and resources. You can also ask the AI assistant to 'list my "
         "VMs' and it returns the same summary."),
        ("Why does my VM not show an IP address yet?",
         "A VM only reports an IP once it is running and its guest agent has "
         "started. Newly created or just-started VMs may show 'Pending' for a "
         "short time. Refreshing the VM page lets the platform re-check and fill "
         "in the IP automatically once it becomes available."),
        ("What is the 2-hour auto-expire on my VM?",
         "Regular user-created VMs are leased for 2 hours by default. After "
         "the lease elapses a background scheduler automatically stops the VM "
         "to free shared resources. You can simply start it again to extend "
         "the session. VMs cloned from a teacher template do NOT auto-expire."),
        ("Can I see live CPU and memory usage of my VM?",
         "Yes. The VM detail page polls Proxmox for live status - CPU "
         "percentage, memory used, uptime, and network in/out - so you see "
         "real numbers, not just on/off."),
    ]),

    ("5. Connecting to Your VMs", [
        ("How do I open the console of a Linux VM?",
         "Open the Linux VM's page and click the console option. A web-based "
         "terminal (ttyd) opens in your browser, giving you command-line access "
         "to the VM without installing anything."),
        ("How do I open the remote desktop of a Windows VM?",
         "Open the Windows VM's page and click the remote desktop option. A "
         "full graphical Windows desktop opens in your browser through Apache "
         "Guacamole, so you do not need a separate RDP client."),
        ("Can I connect from my phone or a different device?",
         "Yes. Both the web console and the remote desktop run in the browser "
         "and are designed to work across devices on the same network, so you "
         "can connect from a laptop, phone, or tablet. The URLs are rewritten "
         "to use the host name your browser already trusts, so the connection "
         "works without VPN or extra setup."),
        ("The console or desktop will not load. What should I check?",
         "First, make sure the VM is running and has an IP address. Newly "
         "started VMs may need a minute before remote access works. If a "
         "Windows desktop fails right after creation, give it time to finish "
         "first-boot setup, then refresh the VM page and try again."),
        ("I see 'VM is running but no IP was reported'. What do I do?",
         "Simply refresh the VM page. The platform re-checks the running VM for "
         "its IP and credentials and fills them in automatically, so the banner "
         "clears on its own once the VM's guest agent responds. You do not need "
         "to rebuild the VM."),
        ("What is ttyd and why is it used for Linux?",
         "ttyd is a tiny program that streams a Linux terminal into a browser "
         "tab through WebSockets. It is light and works on any device, so a "
         "phone can open a Linux shell as easily as a laptop without needing "
         "any SSH client."),
        ("What is Guacamole and why is it used for Windows?",
         "Apache Guacamole is a clientless remote desktop gateway: it speaks "
         "RDP to the Windows VM on one side and a browser HTML5 canvas on the "
         "other. The result is a full Windows desktop in a tab, again on any "
         "device, with no separate RDP client to install."),
    ]),

    ("6. The AI ChatOps Assistant", [
        ("What is the AI ChatOps assistant?",
         "It is a built-in chat assistant that understands plain English. It can "
         "both DO things (create and manage your VMs) and ANSWER things "
         "(explain how the platform and cloud concepts work) from the same chat "
         "box. You do not need to pick a mode; it decides based on your message."),
        ("What actions can I ask the assistant to perform?",
         "You can ask it to create a VM, start, stop, restart, resize, or delete "
         "VMs, and list your VMs. For example: 'Deploy an Ubuntu 24.04 server "
         "named web-prod with 4 cores and 4GB RAM', or 'stop my database VM', "
         "or 'show me all my VMs'."),
        ("What knowledge questions can I ask the assistant?",
         "You can ask conceptual or how-to questions such as 'How do I connect "
         "to a Windows VM?', 'What operating systems are available?', 'What is a "
         "daily quota?', or 'How does VM provisioning work?'. The assistant "
         "answers using the platform's knowledge base."),
        ("Can the assistant operate on several VMs at once?",
         "Yes. It supports bulk actions. If you confirm something like 'stop "
         "both of them' or 'delete all three', it performs the action on all the "
         "named VMs in one go rather than one at a time."),
        ("Can I refer to VMs by name or by 'my last VM'?",
         "Yes. You can refer to a VM by its name, by its job number, or with "
         "relative phrases like 'my last VM' or 'the one I just created'. The "
         "assistant resolves these to the correct VM automatically."),
        ("Does the assistant remember the conversation?",
         "Yes, within a session it keeps recent context, so you can have a "
         "back-and-forth (for example it asks which OS you want, and you reply) "
         "without repeating yourself each time."),
        ("How does the assistant decide between doing and answering?",
         "If your message is a request to act on VMs (deploy, start, stop, "
         "restart, delete, list), it performs that action. If your message is a "
         "question about how something works, it searches the knowledge base and "
         "writes a grounded answer that cites its sources."),
        ("Why does the assistant sometimes refuse to answer?",
         "When the knowledge base genuinely does not contain an answer, the "
         "assistant is designed to say so rather than make something up. This "
         "is by design: a refusal is a sign the system is being honest, not "
         "broken."),
    ]),

    ("7. The Knowledge Base (RAG)", [
        ("What is the knowledge base?",
         "The knowledge base is a collection of documents that the AI assistant "
         "reads from to answer your questions. When you ask something, the "
         "assistant retrieves the most relevant passages and uses them to write "
         "an accurate, grounded answer instead of guessing."),
        ("How does the assistant answer from the knowledge base?",
         "It follows three steps: Retrieve (find the most relevant passages by "
         "meaning, not just keywords), Augment (add those passages to the "
         "prompt), and Generate (write the answer from that context and cite the "
         "source). This is the standard Retrieval-Augmented Generation approach."),
        ("Why does the assistant cite a source on some answers?",
         "When an answer comes from the knowledge base, the assistant shows a "
         "'From Knowledge Base' note with the document name. This tells you the "
         "answer is grounded in an uploaded document rather than general "
         "knowledge."),
        ("Who can add documents to the knowledge base?",
         "Only administrators can upload or remove documents. Every signed-in "
         "user can then benefit from that knowledge by asking the assistant "
         "questions. This keeps the shared knowledge curated and trustworthy."),
        ("What if the assistant cannot find an answer in the knowledge base?",
         "It tells you honestly that it could not find the information rather "
         "than inventing an answer. An administrator may then upload a document "
         "that covers the topic."),
        ("What file types can be uploaded to the knowledge base?",
         "PDF files (text is extracted automatically) and raw text. Both go "
         "through the same chunk + embed pipeline so retrieval treats them "
         "identically once indexed."),
        ("Why agentic RAG instead of always injecting documents?",
         "Agentic RAG exposes the knowledge search as a tool the assistant "
         "calls only when the question needs it. A simple action like 'stop my "
         "VM' does not waste tokens retrieving from the knowledge base; a "
         "documentation question does. This keeps responses fast and answers "
         "focused on the right context."),
    ]),

    ("8. Administrator Features", [
        ("What can administrators do that regular users cannot?",
         "Administrators can view all users and all VMs across the platform, "
         "change a user's role or daily quota, suspend or remove users, review "
         "the audit log of important actions, adjust platform settings, manage "
         "the AI knowledge base, publish VM templates, create student classes, "
         "and bulk-distribute templates to classes."),
        ("What is the audit log?",
         "The audit log records important actions on the platform, such as "
         "logins, VM lifecycle events, template publishes, and class "
         "distributions, with who did what and when. Administrators use it to "
         "review activity and investigate issues."),
        ("How do administrators manage the knowledge base?",
         "Administrators open the Knowledge Base section of the admin console, "
         "upload PDF documents (or paste text), and can see what is indexed and "
         "remove documents. Uploaded documents become available to the AI "
         "assistant for answering questions."),
        ("Can administrators change platform limits and settings?",
         "Yes. Administrators can adjust runtime platform settings and per-user "
         "daily VM quotas. Changes take effect without needing to restart the "
         "platform."),
        ("What admin sections are in the sidebar?",
         "Dashboard (live stats), Virtual Machines (all VMs across users), "
         "Templates (publish + distribute), Classes (student groups), User "
         "Management, Audit Logs, Knowledge Base, and Admin Settings."),
        ("Can an administrator template another user's VM?",
         "Yes. By design, an administrator is the platform operator and may "
         "publish ANY user's finished VM as a template. The source VM must be "
         "in 'done' status. Note that a LINKED-clone template freezes the "
         "source VM into a Proxmox template irreversibly, so administrators "
         "should typically use FULL clone mode when templating someone else's "
         "VM unless they coordinate with the owner."),
    ]),

    ("9. Templates (Clone-from-Template feature)", [
        ("What is a VM template?",
         "A template is a frozen, ready-to-use copy of a VM that an "
         "administrator has built and published. The template captures the "
         "operating system PLUS any software the administrator pre-installed "
         "(for example a lab application). Cloning from the template gives "
         "every student an identical, working environment instantly, instead "
         "of each student spending 20-30 minutes installing software."),
        ("Why does this feature exist?",
         "Classroom labs typically lose the first half-hour of every session "
         "to students installing or configuring software, with inconsistent "
         "results. Pre-baking the environment ONCE and cloning it for "
         "everyone solves this completely: every student gets the same "
         "working VM at the start of class."),
        ("How does an administrator publish a template?",
         "Build a VM, install and configure the software, verify it runs, then "
         "open the admin Templates page and click 'Publish Template'. Pick the "
         "finished VM from the list, give the template a name and description, "
         "choose Full or Linked clone mode, and set default CPU/RAM. The "
         "template appears in the list and can be distributed."),
        ("Must the source VM be running or stopped to publish?",
         "The source VM must be in 'done' status. For Full clone mode the VM "
         "may stay running. For Linked clone mode the platform converts the "
         "source into a Proxmox template (irreversible), so the VM should be "
         "stopped first to avoid an error."),
        ("What is the difference between Full and Linked clone?",
         "Full clone makes an independent disk copy. It is robust (the source "
         "can change or be deleted) and slower (a few minutes per clone, more "
         "disk used). Linked clone shares the source's base disk and stores "
         "only deltas: it is near-instant (~30-45 seconds per clone) and uses "
         "very little disk, but the source VM is frozen as a template and "
         "cannot be started normally again. Linked is ideal for a 60-minute "
         "lab; Full is safer for long-lived workloads."),
        ("Can a published template be edited or removed?",
         "Yes. Administrators can change a template's name, description, "
         "default CPU/RAM, or archive it. Archiving hides it from new "
         "distributions but keeps its history. Existing clones already given "
         "to students are unaffected."),
        ("Does a clone count against the student's daily quota?",
         "No. Teacher-distributed clones intentionally bypass the per-user "
         "daily VM quota - the whole point is everyone gets one immediately. "
         "Clones also do not auto-expire by default (no 2-hour stop) because "
         "the teacher manages their lifecycle."),
        ("Do students see the clone in their own dashboard?",
         "Yes. Each clone lands in the student's normal VM list with their "
         "own access (console for Linux, RDP for Windows), credentials, and "
         "live status. Students do not need to do anything special - the VM "
         "is simply already there."),
    ]),

    ("10. Classes (Student Groups)", [
        ("What is a class in this platform?",
         "A class is a reusable group of students. An administrator creates a "
         "class (for example 'ML-Batch-2026'), enrolls students into it, and "
         "then distributes templates to the entire class in one action. The "
         "same class can be reused for many labs."),
        ("How do I create a class?",
         "Open the admin Classes page and click 'New Class'. Give it a name "
         "(letters, digits, spaces, hyphens, underscores; 3-40 characters) "
         "and an optional description. The class starts empty."),
        ("How do I add students to a class?",
         "Open the class and choose students from the active user list. You "
         "can add multiple students at once. Administrators cannot be enrolled "
         "as students - the platform blocks this to avoid confusing lineage "
         "and quota conflicts."),
        ("How do I remove a student from a class?",
         "Open the class detail and click the trash icon next to the student's "
         "name. Removal does not delete any clones the student already "
         "received from earlier distributions."),
        ("Can a student belong to more than one class?",
         "Yes. A student can be enrolled in multiple classes at the same time "
         "and receive distributions from each."),
        ("Can I distribute a template to a class with no students?",
         "No. The platform returns an error explaining the class has no "
         "active enrolled students. Add at least one student first."),
    ]),

    ("11. Distributing a Template to a Class", [
        ("How do I distribute a template to a class?",
         "Open the admin Templates page, click 'Distribute' on the template, "
         "pick the class, optionally adjust CPU/RAM, and click 'Clone to "
         "class'. A progress modal opens that shows each student's clone "
         "going from queued to cloning to done in real time."),
        ("How long does distribution take?",
         "Full clones take roughly 2-4 minutes per VM. Linked clones take "
         "roughly 30-60 seconds per VM. With the platform processing two "
         "clones in parallel by default, a 30-student linked distribution "
         "completes in about 8-10 minutes; a Full distribution in roughly 30 "
         "minutes."),
        ("What does the batch progress show?",
         "For each student: their username, their clone's status (queued, "
         "cloning, done, failed), the new VM's VM ID, and the IP once "
         "assigned. There is a progress bar showing how many of the total are "
         "done. The view polls every few seconds while in progress."),
        ("What are the possible final states of a distribution?",
         "Completed (every student succeeded), Failed (every student failed), "
         "Partial (a mix of done and failed clones), or In Progress (still "
         "running). Partial usually means a few transient issues - re-running "
         "the distribution will retry the failed students."),
        ("Can I distribute the same template to the same class twice?",
         "Not while a previous distribution is still 'in progress' - the "
         "platform returns a 409 conflict to prevent duplicate clones. Once "
         "the first batch finishes (completed, partial, or failed), you can "
         "distribute again safely."),
        ("Can I publish a template as Full and distribute as Linked, or vice versa?",
         "No. The chosen clone mode is fixed at publish time because Linked "
         "needs the source VM frozen as a Proxmox template. Distributing a "
         "Full template as Linked returns a 400 with a clear error."),
        ("What if Proxmox rejects a clone mid-distribution?",
         "Each failure is recorded on that student's clone job with the exact "
         "Proxmox error message. Other students' clones continue independently. "
         "The batch ends as 'partial' so you know some succeeded and some did "
         "not, and you can re-distribute to pick up the failed students."),
        ("Why does each student get a unique VM ID?",
         "The platform pre-allocates a distinct Proxmox VM ID for every "
         "student before any cloning starts. It also takes a short-lived lock "
         "so two simultaneous distributions cannot allocate overlapping IDs. "
         "This way no two students collide on the same hypervisor slot."),
        ("Why are clones of the same template run sequentially?",
         "Proxmox holds an exclusive lock on the source VM's config during "
         "every clone read. Two simultaneous clones from the same source "
         "would race on that lock and one would fail. The platform "
         "automatically serializes same-source clones with a Redis lock so "
         "they queue politely. Clones from DIFFERENT templates still run in "
         "parallel."),
    ]),

    ("12. How the System Works (Conceptual)", [
        ("How does VM provisioning work end to end?",
         "When you request a VM, the backend records the request and hands the "
         "slow work to a Celery background worker. The worker clones the OS "
         "golden image, waits for it to come up, applies your CPU/RAM, starts "
         "the VM, polls the guest agent for an IP, and records access details. "
         "Your dashboard reflects each stage from queued to running."),
        ("Why is VM creation asynchronous?",
         "Provisioning a VM takes time (cloning an image, booting, network "
         "setup). Doing it in the background means the web request returns "
         "immediately with a 'queued' status, and you can keep using the "
         "platform while the VM is being built. Without this, a busy moment "
         "would tie up every web worker and freeze the platform."),
        ("How does the AI assistant work behind the scenes?",
         "It is an AI agent with tools. For actions it calls the platform's own "
         "VM functions. For questions it searches the knowledge base, then a "
         "language model writes the answer from the retrieved passages. The "
         "same language model powers both modes."),
        ("How does the knowledge search find relevant passages?",
         "Documents are split into small passages and converted into numeric "
         "vectors that capture meaning. Your question is converted the same way, "
         "and the system finds the passages whose meaning is closest to your "
         "question. This is why it can match ideas even when the words differ."),
        ("Is my data kept private?",
         "The platform is self-hosted and designed for private use. The "
         "virtual machines run on local virtualization, and the knowledge-base "
         "search runs locally rather than sending your documents to an outside "
         "search service."),
        ("Why does cloning need an exclusive lock on the source VM?",
         "Proxmox takes an OS-level file lock on the source VM's config file "
         "for the duration of a clone read to guarantee a consistent snapshot. "
         "If two clones tried to read the same source at the same time, the "
         "second would time out on that lock. The platform serializes these "
         "automatically so this is invisible to users."),
        ("Why does the platform pre-allocate VM IDs before fan-out?",
         "If each Celery worker asked Proxmox 'give me a free ID' independently, "
         "two workers might receive the same ID and one would fail at clone "
         "time. Pre-allocating all IDs in a single locked step before any "
         "cloning starts guarantees uniqueness."),
        ("Why does the platform use Postgres advisory locks during startup?",
         "When several worker processes start at once they each try to "
         "verify-and-update the database schema, which can deadlock on the "
         "ALTER TABLE statements. A Postgres advisory lock makes only one "
         "process run the schema setup at a time; the others queue and then "
         "see the schema is ready."),
    ]),

    ("13. Troubleshooting - Account and Sign-In", [
        ("My login keeps failing even with the right password.",
         "Re-check capitalization and that you are using the correct account. "
         "If valid credentials fail for everyone, the sign-in service may be "
         "down; ask an administrator to check the platform. A single wrong "
         "attempt simply shows 'Invalid username or password'."),
        ("I get 'Could not validate credentials. Please log in again.'",
         "Your session token has expired or the backend was restarted. Sign "
         "in again to get a fresh token. There is no data loss - everything "
         "you saved is still there."),
        ("I registered but I do not have admin access.",
         "Only the very first user on a fresh database is auto-promoted to "
         "admin. If another user registered first, you start as a regular "
         "user. An administrator can promote you, or in a fresh install the "
         "first registration becomes admin automatically."),
        ("The admin sidebar items are missing for my account.",
         "Your role is 'user', not 'admin'. Ask an existing administrator to "
         "promote you. After your role changes, sign out and sign in again so "
         "the new permissions take effect."),
    ]),

    ("14. Troubleshooting - VM Creation and Lifecycle", [
        ("My VM is stuck in 'queued' for a long time.",
         "Provisioning can take a few minutes, and only a limited number of VMs "
         "build at once, so during busy periods yours may wait its turn. If it "
         "stays queued far longer than usual, ask an administrator to check the "
         "background worker."),
        ("My VM shows 'failed'. What now?",
         "Open the VM to read its error message, which explains the cause (for "
         "example exceeding a resource limit, or a temporary hypervisor issue). "
         "Adjust the request accordingly and try creating the VM again, or ask "
         "an administrator for help."),
        ("My VM failed with 'MAX X vcpus allowed per VM on this node'.",
         "The Proxmox host has a per-VM CPU cap. Re-create the VM with fewer "
         "vCPUs and it will succeed. An administrator can also raise the cap "
         "on the host, but lowering your request is the quicker fix."),
        ("My VM created successfully but the dashboard shows 'VM is running but no IP was reported'.",
         "This means provisioning finished but the guest agent did not "
         "respond within the polling window. Simply refresh the VM page: the "
         "platform automatically re-checks the running VM and fills in the IP "
         "and credentials when the agent responds. No rebuild needed."),
        ("After provisioning failed, the IP and credentials are blank forever.",
         "The platform now self-heals this on both the next page load (GET) "
         "and on the next action (start/restart). Refresh the VM page or "
         "trigger a start; the IP and credentials are recovered automatically "
         "if the VM is actually running."),
        ("My VM auto-stopped after a couple of hours.",
         "Regular user VMs have a 2-hour lease and are automatically stopped "
         "by a background scheduler to free shared resources. Simply start "
         "the VM again from your dashboard. Teacher-distributed clones do "
         "NOT have this lease."),
        ("Daily quota exceeded - I cannot create more VMs today.",
         "Each user has a daily VM creation cap (default 3) to prevent "
         "over-use of shared hardware. The cap resets at midnight UTC. An "
         "administrator can raise your per-user quota if you legitimately "
         "need more."),
    ]),

    ("15. Troubleshooting - Remote Access", [
        ("Remote desktop or console works on one device but not another.",
         "Make sure both devices are on the same network and the VM is running "
         "with an IP. The browser-based console and desktop are built to work "
         "across devices, but a VM that is still booting will not accept "
         "connections yet."),
        ("Windows desktop fails with 'VM is missing IP or credentials'.",
         "The credentials may not have been written during a failed initial "
         "provision. Reloading the VM page triggers an automatic backfill of "
         "the username and password from the platform's stored defaults for "
         "that OS. The desktop button then works without rebuilding."),
        ("Console (Linux terminal) loads then disconnects immediately.",
         "Usually the VM is still booting or the guest agent has not started "
         "sshd yet. Wait 30-60 seconds after the VM reaches 'running' and "
         "try again. If it persists, restart the VM."),
        ("Console URL works on the laptop but not on my phone.",
         "The platform rewrites the console URL to use the hostname your "
         "browser already used, so it should work on any device. If it does "
         "not, check that your phone is on the same network as the host."),
    ]),

    ("16. Troubleshooting - AI ChatOps", [
        ("The assistant says 'knowledge base is unavailable'.",
         "No documents are uploaded yet or the knowledge service is still "
         "starting. An administrator needs to upload at least one PDF or "
         "text document under the Knowledge Base section. Once indexed, "
         "ask your question again."),
        ("The assistant gave me a wrong answer about a Proxmox command.",
         "If the answer was NOT cited as 'From Knowledge Base', it came from "
         "the model's general training and may be wrong about this specific "
         "platform. Ask the question again and the assistant should search "
         "the knowledge base. If the knowledge base lacks the topic, an "
         "administrator should upload a document covering it."),
        ("The assistant refused to act on 'delete everything'.",
         "Destructive bulk actions require explicit confirmation by name or "
         "by clear scope. The assistant deliberately refuses ambiguous "
         "destructive instructions to prevent accidental loss."),
        ("The assistant created a VM with the wrong specs.",
         "If you did not specify CPU/RAM/disk it used the per-OS defaults "
         "(see 'What happens if I do not specify CPU, memory, or disk?'). "
         "You can resize the VM after creation, or be more explicit in the "
         "next request."),
    ]),

    ("17. Troubleshooting - Templates and Distribution", [
        ("'Source VM must be in done status' when publishing a template.",
         "The chosen source VM is queued, failed, or deleted. Pick a VM "
         "whose status is 'done' (fully provisioned). For Linked clone mode "
         "the VM should also be stopped before publishing."),
        ("'Cannot distribute as linked: this template was not published as linked.'",
         "Clone mode is fixed at publish time because Linked needs the "
         "source frozen as a Proxmox template. Either publish a new template "
         "with Linked mode, or distribute this template as Full."),
        ("'A distribution for this template and class is already in progress.'",
         "A previous distribution of the same template to the same class has "
         "not finished yet. Wait until the batch reaches Completed, Failed, "
         "or Partial, then distribute again. This guard prevents accidental "
         "duplicate clones (a double-click)."),
        ("'Class has no enrolled active students.'",
         "Either the class is empty or all enrolled students are suspended/"
         "deleted. Add at least one active student to the class and retry."),
        ("'Could not reach Proxmox to allocate VMIDs.'",
         "Proxmox was briefly unreachable when the platform tried to "
         "pre-allocate VM IDs for the distribution. Try again in a moment. "
         "If it persists, check the Proxmox host is up and reachable from "
         "the backend."),
        ("Some students' clones failed with 'unable to find configuration file for VM X'.",
         "The source VM was deleted from Proxmox while still recorded as "
         "'done' in our database. Re-publish a template from a different "
         "live VM and re-distribute. The platform records the exact error "
         "on each failed clone so you can identify this case quickly."),
        ("Some students' clones failed with 'can't lock file ... got timeout'.",
         "Proxmox itself holds an exclusive lock on the source VM's config "
         "during cloning. The platform serializes same-source clones with "
         "a Redis lock to avoid this, so the most common cause today is "
         "another administrator distributing the same template at the same "
         "moment. Wait and re-distribute; the failures will succeed on retry."),
        ("Batch finished as 'partial' - what do I do?",
         "Partial means some clones succeeded and some failed. The student "
         "view shows clearly which clones are usable. You can re-distribute "
         "the template to the same class: students who already have a clone "
         "will get a SECOND clone, so for now the practical workaround is "
         "to manually delete the failed clones and re-distribute. A native "
         "retry-just-failed endpoint is on the future-work list."),
    ]),

    ("18. Troubleshooting - Knowledge Base / RAG", [
        ("'There was an error parsing the body' when I upload text.",
         "The text contained a character your tool did not encode as UTF-8 "
         "(an em-dash, smart quote, etc.). Either save the text to a UTF-8 "
         "file and upload via file, or replace special characters with plain "
         "ASCII equivalents."),
        ("After uploading a PDF, the assistant still says 'not in knowledge base'.",
         "Confirm the upload reported a chunk count greater than zero. If the "
         "PDF is image-only (scanned pages with no embedded text), the "
         "extractor cannot pull any text. Re-export the PDF with selectable "
         "text, or paste the content as text via upload-text."),
        ("How many pages or how big a PDF can I upload?",
         "There is no hard cap, but very large PDFs take longer to chunk and "
         "embed. A practical maximum per document is a few hundred pages; "
         "split bigger material into smaller logical PDFs for cleaner retrieval."),
        ("How do I remove a document from the knowledge base?",
         "Open the admin Knowledge Base page and use the delete control next "
         "to the source. All chunks for that source are removed from the "
         "vector index in one operation."),
    ]),

    ("19. Troubleshooting - Installation and Docker", [
        ("'docker compose up --build' fails at 'exporting to image'.",
         "Docker Desktop's build cache is out of sync with its image store. "
         "This is not a code bug. Run 'docker builder prune -af' to clear "
         "only the build cache (NOT your data) and retry. If it persists, "
         "Docker Desktop Troubleshoot menu has a 'Clean / Purge data' "
         "option. Volumes and project files are not affected by builder prune."),
        ("'no such service: build' when running docker compose.",
         "The correct flag is '--build' (two dashes, no space). 'docker "
         "compose up -- build' is parsed as service name 'build' which "
         "does not exist. Use 'docker compose up --build' instead."),
        ("Backend container restarts immediately.",
         "Check 'docker logs <backend-container>' for the error. The most "
         "common causes are missing environment variables (PROXMOX_HOST, "
         "OPENROUTER_API_KEY) or Postgres not yet ready. The healthcheck "
         "waits for Postgres so this is rare in normal operation."),
        ("Celery worker container is unhealthy.",
         "The Celery worker has its own healthcheck. If it stays unhealthy, "
         "check 'docker logs <celery-worker>' - common causes are an "
         "import error in a new task file or Redis not yet reachable."),
        ("Frontend serves but API calls 404.",
         "The frontend Nginx proxies '/api' to the backend container. If "
         "you changed the backend service name or port, also update the "
         "Nginx config. Otherwise check that the backend container is up "
         "and healthy."),
    ]),

    ("20. Common Patterns and Architecture (User-Friendly)", [
        ("Why is the database schema applied on startup?",
         "The backend runs CREATE TABLE IF NOT EXISTS and ALTER TABLE "
         "statements at startup. This means upgrading to a new version is "
         "just 'pull and restart' - no separate migration step. Existing "
         "data is preserved; only missing tables or columns are added."),
        ("Why does the platform reuse the existing VM table for clones?",
         "Cloned student VMs land in the same vm_jobs table as regular VMs. "
         "This means the student dashboard, console, remote desktop, "
         "credentials self-heal, and audit logging all work UNCHANGED for "
         "cloned VMs - the new feature did not need any rework of these "
         "existing components."),
        ("Why are there both 'audit log' and 'activity feed'?",
         "The audit log is the immutable record of what happened (used for "
         "compliance and admin review). The activity feed on the dashboard "
         "is a live view of the most recent events for quick visibility. "
         "Both read from the same source of truth."),
        ("Why a single Q&A PDF for the knowledge base?",
         "RAG retrieval works best when each chunk is a meaningful, "
         "self-contained unit. A Q&A pair survives chunking gracefully "
         "because the question states the intent and the answer is "
         "complete on its own. Long prose articles get cut mid-sentence "
         "and retrieve poorly."),
        ("Why does the platform need both Postgres and MySQL?",
         "Postgres holds the application data (users, VMs, audit, templates, "
         "etc.). MySQL is a requirement of Apache Guacamole - its database "
         "schema is published only for MySQL. Treating Guacamole as a "
         "self-contained add-on with its own DB keeps our main schema "
         "clean and lets Guacamole upgrade independently."),
    ]),

    ("21. Quick Reference", [
        ("What operating systems are supported, in short?",
         "Ubuntu 22.04, Ubuntu 24.04, Debian 12, CentOS 9, and Windows 11."),
        ("What are the resource limits, in short?",
         "vCPUs 1 to 16, memory 512 MB to 65536 MB, disk 10 GB to 500 GB."),
        ("What are the default resources, in short?",
         "Linux defaults: 2 vCPUs, 2048 MB memory, 20 GB disk. Windows 11 "
         "defaults: 4 vCPUs, 4096 MB memory, 64 GB disk."),
        ("What access method does each OS use, in short?",
         "Linux VMs use a browser-based web console (terminal). Windows VMs use "
         "a browser-based remote desktop."),
        ("What can the AI assistant do, in short?",
         "Create, start, stop, restart, resize, delete, and list VMs (including "
         "several at once), and answer questions about the platform from the "
         "knowledge base."),
        ("Distribution speed, in short?",
         "Linked clone: about 30-60 seconds per VM. Full clone: about 2-4 "
         "minutes per VM. With 2-way Celery parallelism, a 30-student "
         "Linked distribution finishes in roughly 8-10 minutes."),
        ("Auto-expiry, in short?",
         "Regular user-created VMs auto-stop after 2 hours of lease. "
         "Teacher-distributed clones do NOT auto-expire."),
        ("Quota, in short?",
         "Default 3 VMs per user per day; admins can adjust per user. "
         "Resets at midnight UTC. Distributed clones do not count."),
        ("Admin sidebar sections, in short?",
         "Dashboard, Virtual Machines, Templates, Classes, User Management, "
         "Audit Logs, Knowledge Base, Admin Settings."),
        ("Clone mode quick guide, in short?",
         "Full = independent, robust, slower. Linked = near-instant, tiny "
         "disk, freezes the source. Pick Linked for short labs; Full for "
         "long-lived work."),
    ]),
]


class KBPdf(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        half = self.epw / 2
        self.cell(half, 8, "AZNA Private Cloud - Knowledge Base", align="L")
        self.cell(half, 8, f"Page {self.page_no()}", align="R")
        self.ln(10)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "Internal user documentation - no credentials or secrets included", align="C")
        self.set_text_color(0, 0, 0)


def build() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    pdf = KBPdf(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(20, 18, 20)
    pdf.add_page()

    # --- Title block ---
    pdf.set_font("Helvetica", "B", 22)
    pdf.ln(20)
    pdf.multi_cell(0, 11, "AZNA Private Cloud", **NL)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(70, 70, 70)
    pdf.multi_cell(0, 9, "Knowledge Base for the AI Assistant", **NL)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0, 6,
        "This document is the source material for the platform's AI ChatOps "
        "assistant. It is written as self-contained question-and-answer pairs so "
        "the assistant can retrieve precise, accurate answers for users.\n\n"
        "It covers every major feature: account management, VM creation and "
        "lifecycle, remote access, AI ChatOps, RAG knowledge base, the admin "
        "portal, templates and class-based distribution (Sprint 5), and "
        "extensive troubleshooting for accounts, VM creation, remote access, "
        "ChatOps, templates, knowledge base, and Docker installation.\n\n"
        "It contains only information that is safe for users to read. It "
        "deliberately excludes passwords, API keys, internal addresses, and any "
        "other sensitive configuration.\n\n"
        f"Generated: {date.today().isoformat()}",
        **NL,
    )
    pdf.ln(2)

    # --- Sections ---
    for title, qas in SECTIONS:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(20, 30, 50)
        pdf.set_text_color(255, 255, 255)
        pdf.multi_cell(0, 9, f"  {title}", fill=True, **NL)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        for question, answer in qas:
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, f"Q: {question}", **NL)
            pdf.set_font("Helvetica", "", 10.5)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 5.6, f"A: {answer}", **NL)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)

    pdf.output(OUT_PATH)
    n_qa = sum(len(qas) for _, qas in SECTIONS)
    print(f"Wrote {OUT_PATH}")
    print(f"Sections: {len(SECTIONS)}  Q&A pairs: {n_qa}  Pages: {pdf.page_no()}")


if __name__ == "__main__":
    build()

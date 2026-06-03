"""
Generate the AZNA Private Cloud knowledge-base PDF for the RAG agent.

WHY Q&A (not raw JSON): the RAG pipeline chunks this PDF every ~500 chars and
embeds each chunk. Self-contained question/answer pairs in plain language give
the cleanest, most retrievable chunks — the user's question embeds close to the
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
         "assistant."),
        ("Who is this platform for?",
         "It is for users who need on-demand virtual machines without dealing "
         "with the underlying virtualization manually. Regular users manage "
         "their own VMs. Administrators additionally manage users, quotas, "
         "audit logs, platform settings, and the AI knowledge base."),
        ("What technology powers the platform?",
         "At a high level: a FastAPI (Python) backend, a PostgreSQL database, "
         "asynchronous background jobs via Celery and Redis, virtualization on "
         "Proxmox VE, and a React and TypeScript web frontend. Remote access "
         "uses a web terminal for Linux and Apache Guacamole for Windows remote "
         "desktop."),
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
         "ask an administrator to raise your quota."),
        ("What is the difference between a user and an administrator?",
         "A regular user manages only their own virtual machines. An "
         "administrator can additionally view and manage all users, change "
         "roles and quotas, review audit logs, adjust platform settings, and "
         "upload documents to the AI knowledge base."),
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
         "becomes 'running'. Linux VMs are usually ready in a few minutes; "
         "Windows VMs can take longer, especially during first-boot setup."),
        ("What do the VM statuses mean?",
         "'queued' means the request is accepted and waiting to be provisioned. "
         "'running' (or 'done') means the VM is up. 'stopped' means it is "
         "powered off. 'failed' means provisioning hit an error; the error "
         "message explains what went wrong (for example a resource limit)."),
        ("Must I confirm the operating system before a VM is created?",
         "Yes. The AI assistant will never guess the operating system. If you "
         "ask it to create a VM without naming the OS, it asks you to pick one "
         "first. This prevents accidentally creating the wrong kind of machine."),
    ]),

    ("4. Managing Virtual Machines", [
        ("How do I start, stop, or restart a VM?",
         "Use the controls on the VM's card or detail page, or ask the AI "
         "assistant (for example 'stop my web-server'). Starting powers the VM "
         "on, stopping powers it off, and restarting reboots it."),
        ("How do I resize a VM (change CPU, memory, or disk)?",
         "Open the VM and use the resize option to change its vCPUs, memory, or "
         "disk within the allowed limits. Resizing generally requires the VM to "
         "be restarted for the new resources to take effect."),
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
    ]),

    ("5. Connecting to Your VMs", [
        ("How do I open the console of a Linux VM?",
         "Open the Linux VM's page and click the console option. A web-based "
         "terminal opens in your browser, giving you command-line access to the "
         "VM without installing anything."),
        ("How do I open the remote desktop of a Windows VM?",
         "Open the Windows VM's page and click the remote desktop option. A "
         "full graphical Windows desktop opens in your browser through Apache "
         "Guacamole, so you do not need a separate RDP client."),
        ("Can I connect from my phone or a different device?",
         "Yes. Both the web console and the remote desktop run in the browser "
         "and are designed to work across devices on the same network, so you "
         "can connect from a laptop, phone, or tablet."),
        ("The console or desktop will not load. What should I check?",
         "Make sure the VM is running and has an IP address. Newly started VMs "
         "may need a minute before remote access works. If a Windows desktop "
         "fails right after creation, give it time to finish first-boot setup, "
         "then refresh the VM page and try again."),
        ("I see 'VM is running but no IP was reported'. What do I do?",
         "Simply refresh the VM page. The platform re-checks the running VM for "
         "its IP and credentials and fills them in automatically, so the banner "
         "clears on its own once the VM's guest agent responds. You do not need "
         "to rebuild the VM."),
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
    ]),

    ("8. Administrator Features", [
        ("What can administrators do that regular users cannot?",
         "Administrators can view all users and all VMs across the platform, "
         "change a user's role or daily quota, suspend or remove users, review "
         "the audit log of important actions, adjust platform settings, and "
         "manage the AI knowledge base."),
        ("What is the audit log?",
         "The audit log records important actions on the platform, such as "
         "logins and VM lifecycle events, with who did what and when. "
         "Administrators use it to review activity and investigate issues."),
        ("How do administrators manage the knowledge base?",
         "Administrators open the Knowledge Base section of the admin console, "
         "upload PDF documents (or paste text), and can see what is indexed and "
         "remove documents. Uploaded documents become available to the AI "
         "assistant for answering questions."),
        ("Can administrators change platform limits and settings?",
         "Yes. Administrators can adjust runtime platform settings and per-user "
         "daily VM quotas. Changes take effect without needing to restart the "
         "platform."),
    ]),

    ("9. How the System Works (Conceptual)", [
        ("How does VM provisioning work end to end?",
         "When you request a VM, the backend records the request and hands the "
         "slow work to a background worker. The worker creates the VM on the "
         "virtualization host, waits for it to come up, and records its IP and "
         "access details. Your dashboard reflects each stage, from queued to "
         "running."),
        ("Why is VM creation asynchronous?",
         "Provisioning a VM takes time (cloning an image, booting, network "
         "setup). Doing it in the background means the web request returns "
         "immediately with a 'queued' status, and you can keep using the "
         "platform while the VM is being built."),
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
    ]),

    ("10. Troubleshooting", [
        ("My login keeps failing even with the right password.",
         "Re-check capitalization and that you are using the correct account. "
         "If valid credentials fail for everyone, the sign-in service may be "
         "down; ask an administrator to check the platform. A single wrong "
         "attempt simply shows 'Invalid username or password'."),
        ("My VM is stuck in 'queued' for a long time.",
         "Provisioning can take a few minutes, and only a limited number of VMs "
         "build at once, so during busy periods yours may wait its turn. If it "
         "stays queued far longer than usual, ask an administrator to check the "
         "background worker."),
        ("My VM shows 'failed'. What now?",
         "Open the VM to read its error message, which explains the cause (for "
         "example exceeding a resource limit). Adjust the request accordingly "
         "and try creating the VM again, or ask an administrator for help."),
        ("The assistant says the knowledge base is unavailable.",
         "This means no documents are ready yet or the knowledge service is "
         "still starting. An administrator needs to upload documents under the "
         "Knowledge Base section. Once ready, ask your question again."),
        ("Remote desktop or console works on one device but not another.",
         "Make sure both devices are on the same network and the VM is running "
         "with an IP. The browser-based console and desktop are built to work "
         "across devices, but a VM that is still booting will not accept "
         "connections yet."),
    ]),

    ("11. Quick Reference", [
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

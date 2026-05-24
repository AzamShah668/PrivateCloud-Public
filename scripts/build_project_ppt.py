"""
Builds PrivateCloud_Project_ppt.pptx modelled on DOA_Project_ppt.pptx layout.
- 16:9 (9144000 x 5143500 EMU)
- Title bar at top, body below (matches reference)
- Box-and-arrow architecture diagrams drawn natively
- Proxmox framed as a KVM-based hypervisor only (DigitalOcean analogy)
"""

from pptx import Presentation
from pptx.util import Emu, Pt, Inches
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# --- Palette (deep-blue academic) ---
NAVY      = RGBColor(0x0B, 0x1F, 0x3A)
DEEP_BLUE = RGBColor(0x12, 0x3C, 0x69)
ACCENT    = RGBColor(0x1E, 0x88, 0xE5)
LIGHT_BG  = RGBColor(0xF4, 0xF7, 0xFB)
PANEL     = RGBColor(0xE8, 0xEF, 0xF7)
BORDER    = RGBColor(0xC3, 0xD1, 0xE6)
TEXT_DARK = RGBColor(0x1A, 0x1A, 0x1A)
TEXT_MUT  = RGBColor(0x42, 0x55, 0x6E)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
GREEN     = RGBColor(0x2E, 0x7D, 0x32)
AMBER     = RGBColor(0xE6, 0x9A, 0x00)

SLIDE_W, SLIDE_H = 9144000, 5143500

prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H
blank = prs.slide_layouts[6]


# ---------------- helpers ----------------
def add_slide():
    return prs.slides.add_slide(blank)

def set_fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color

def set_line(shape, color, width_pt=0.75):
    shape.line.color.rgb = color
    shape.line.width = Pt(width_pt)

def no_line(shape):
    shape.line.fill.background()

def add_rect(slide, x, y, w, h, fill=WHITE, line=BORDER, line_w=0.75, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    set_fill(s, fill)
    if line is None:
        no_line(s)
    else:
        set_line(s, line, line_w)
    s.shadow.inherit = False
    return s

def add_textbox(slide, x, y, w, h, text, *, size=14, bold=False, color=TEXT_DARK,
                align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font="Calibri"):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(36000); tf.margin_right = Emu(36000)
    tf.margin_top  = Emu(18000); tf.margin_bottom = Emu(18000)
    tf.vertical_anchor = anchor
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
    return tb

def add_bullets(slide, x, y, w, h, items, *, size=14, color=TEXT_DARK, line_space=1.15, bullet_char="•"):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(72000); tf.margin_right = Emu(36000)
    tf.margin_top  = Emu(36000); tf.margin_bottom = Emu(18000)
    for i, item in enumerate(items):
        indent = 0
        text = item
        if isinstance(item, tuple):
            indent, text = item
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.level = indent
        p.line_spacing = line_space
        p.space_after = Pt(4)
        run = p.add_run()
        run.text = f"{bullet_char}  {text}" if indent == 0 else f"–  {text}"
        run.font.name = "Calibri"
        run.font.size = Pt(size - (1 if indent else 0))
        run.font.color.rgb = color
    return tb

def add_title_bar(slide, title):
    # Dark navy bar across the top
    bar = add_rect(slide, Emu(0), Emu(0), Emu(SLIDE_W), Emu(760000), fill=NAVY, line=None)
    # Accent stripe
    add_rect(slide, Emu(0), Emu(760000), Emu(SLIDE_W), Emu(40000), fill=ACCENT, line=None)
    add_textbox(slide, Emu(311700), Emu(180000), Emu(SLIDE_W - 623400), Emu(500000),
                title, size=26, bold=True, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)

def add_footer(slide, page_num, total):
    add_rect(slide, Emu(0), Emu(SLIDE_H - 220000), Emu(SLIDE_W), Emu(220000),
             fill=NAVY, line=None)
    add_textbox(slide, Emu(200000), Emu(SLIDE_H - 220000), Emu(4000000), Emu(220000),
                "PrivateCloud  |  Department of Information Technology",
                size=10, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    add_textbox(slide, Emu(SLIDE_W - 1200000), Emu(SLIDE_H - 220000),
                Emu(1000000), Emu(220000),
                f"{page_num} / {total}", size=10, color=WHITE,
                align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)

def content_slide(title, page, total):
    s = add_slide()
    # Light background
    add_rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=LIGHT_BG, line=None)
    add_title_bar(s, title)
    add_footer(s, page, total)
    return s

def arrow(slide, x1, y1, x2, y2, color=ACCENT, w=1.75):
    con = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    con.line.color.rgb = color
    con.line.width = Pt(w)
    # style as arrow via underlying XML
    from pptx.oxml.ns import qn
    ln = con.line._get_or_add_ln()
    tail = ln.find(qn('a:tailEnd'))
    if tail is None:
        tail = ln.makeelement(qn('a:tailEnd'), {'type':'triangle','w':'med','len':'med'})
        ln.append(tail)
    else:
        tail.set('type','triangle')
    return con

def labeled_box(slide, x, y, w, h, title, subtitle=None, *,
                fill=WHITE, border=DEEP_BLUE, title_color=DEEP_BLUE, sub_color=TEXT_MUT,
                title_size=13, sub_size=10):
    add_rect(slide, x, y, w, h, fill=fill, line=border, line_w=1.25)
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Emu(40000); tf.margin_right = Emu(40000)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = title
    r.font.name = "Calibri"; r.font.size = Pt(title_size); r.font.bold = True
    r.font.color.rgb = title_color
    if subtitle:
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run(); r2.text = subtitle
        r2.font.name = "Calibri"; r2.font.size = Pt(sub_size)
        r2.font.color.rgb = sub_color

TOTAL = 23
page = 0
def nextp():
    global page
    page += 1
    return page


# ========================================================================
# Slide 1 — Front Page
# ========================================================================
s = add_slide()
nextp()
add_rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=NAVY, line=None)
# Accent diagonal panel
add_rect(s, 0, Emu(3400000), Emu(SLIDE_W), Emu(40000), fill=ACCENT, line=None)

add_textbox(s, Emu(311700), Emu(600000), Emu(SLIDE_W - 623400), Emu(250000),
            "Major Project  |  Final Year",
            size=12, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)

add_textbox(s, Emu(311700), Emu(900000), Emu(SLIDE_W - 623400), Emu(900000),
            ["PrivateCloud",
             "A Self-Hosted On-Demand Virtual Machine Provisioning Platform"],
            size=30, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

# Team
add_textbox(s, Emu(2200000), Emu(2050000), Emu(4744000), Emu(900000),
            ["Azam Shah Rizwan", "Bilal ", "Narsheed "],
            size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

add_textbox(s, Emu(2200000), Emu(3500000), Emu(4744000), Emu(350000),
            "Guide: [Guide Name]",
            size=14, color=WHITE, align=PP_ALIGN.CENTER)

add_textbox(s, Emu(0), Emu(4550000), Emu(SLIDE_W), Emu(450000),
            ["Department of Information Technology",
             "[University / Institute Name]"],
            size=12, color=WHITE, align=PP_ALIGN.CENTER)


# ========================================================================
# Slide 2 — Table of Contents
# ========================================================================
s = content_slide("Table of Contents", nextp(), TOTAL)
items = [
    "1.  Introduction",
    "2.  Problem Statement",
    "3.  Objectives",
    "4.  Scope of the Project",
    "5.  Literature Review / Existing Systems",
    "6.  Proposed System",
    "7.  Methodology",
    "    – System Architecture",
    "    – How Proxmox (KVM Hypervisor) Works",
    "    – Frontend ↔ Backend Communication",
    "    – Docker & Three-Tier Container Architecture",
    "    – Golden Image Creation",
    "8.  Work Done So Far",
    "9.  References",
]
tb = s.shapes.add_textbox(Emu(600000), Emu(1000000),
                          Emu(SLIDE_W - 1200000), Emu(3800000))
tf = tb.text_frame; tf.word_wrap = True
for i, line in enumerate(items):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.alignment = PP_ALIGN.LEFT
    p.space_after = Pt(6)
    r = p.add_run(); r.text = line
    r.font.name = "Calibri"
    r.font.size = Pt(17 if not line.startswith("    ") else 14)
    r.font.bold = not line.startswith("    ")
    r.font.color.rgb = DEEP_BLUE if not line.startswith("    ") else TEXT_MUT


# ========================================================================
# Slide 3 — Introduction
# ========================================================================
s = content_slide("Introduction", nextp(), TOTAL)
add_bullets(s, Emu(500000), Emu(1000000), Emu(SLIDE_W - 1000000), Emu(3700000), [
    "Cloud computing has become the backbone of modern IT — enabling on-demand access "
    "to compute, storage, and networking over the internet.",
    "Public providers such as AWS, Google Cloud, and DigitalOcean offer virtual "
    "machines at scale, but organisations with data-sensitivity, cost, or "
    "compliance constraints cannot always rely on the public cloud.",
    "A private cloud hosts the same self-service capabilities inside an "
    "organisation’s own infrastructure, using a hypervisor to run isolated "
    "virtual machines on physical servers.",
    "Our project, PrivateCloud, builds such a self-service platform: a user logs in "
    "through a web portal, requests a VM, and the system provisions, tracks, and "
    "audits that VM on a physical server running a KVM-based hypervisor "
    "(Proxmox VE).",
    "This mirrors how DigitalOcean uses KVM under the hood — the value lies in the "
    "management, automation, and user-experience layer built on top.",
], size=15)


# ========================================================================
# Slide 4 — Introduction (Cloud Deployment Models visual)
# ========================================================================
s = content_slide("Introduction — Cloud Deployment Models", nextp(), TOTAL)

# Three panels: Public / Private / Hybrid
colW = Emu(2650000); colH = Emu(2600000)
gap  = Emu(180000)
startX = Emu((SLIDE_W - 3*colW - 2*gap)//2)
topY   = Emu(1100000)

def model_card(x, title, subtitle, points, highlight=False):
    fill = PANEL if not highlight else RGBColor(0xDE, 0xEB, 0xFA)
    border = DEEP_BLUE if highlight else BORDER
    add_rect(s, x, topY, colW, colH, fill=fill, line=border, line_w=1.5)
    add_textbox(s, x, topY + Emu(80000), colW, Emu(360000),
                title, size=16, bold=True, color=DEEP_BLUE, align=PP_ALIGN.CENTER)
    add_textbox(s, x, topY + Emu(430000), colW, Emu(280000),
                subtitle, size=10, color=TEXT_MUT, align=PP_ALIGN.CENTER)
    add_bullets(s, x, topY + Emu(780000), colW, Emu(1700000),
                points, size=11)

model_card(startX,
           "Public Cloud",
           "AWS · GCP · Azure · DigitalOcean",
           ["Pay-as-you-go", "Shared infrastructure", "Limited data control"])
model_card(startX + colW + gap,
           "Private Cloud",
           "Our Project",
           ["Self-hosted on own servers",
            "Full data & policy control",
            "Cost-predictable"], highlight=True)
model_card(startX + 2*(colW + gap),
           "Hybrid Cloud",
           "Public + Private",
           ["Combines both models",
            "Workload portability",
            "Higher integration cost"])

add_textbox(s, Emu(500000), Emu(3850000), Emu(SLIDE_W - 1000000), Emu(600000),
            "PrivateCloud implements the Infrastructure-as-a-Service (IaaS) layer of a "
            "private cloud — abstracting a physical server into many user-owned VMs.",
            size=12, color=TEXT_MUT, align=PP_ALIGN.CENTER)


# ========================================================================
# Slide 5 — Problem Statement
# ========================================================================
s = content_slide("Problem Statement", nextp(), TOTAL)

# Quoted statement box
qx = Emu(500000); qy = Emu(1000000)
qw = Emu(SLIDE_W - 1000000); qh = Emu(900000)
add_rect(s, qx, qy, qw, qh, fill=PANEL, line=ACCENT, line_w=1.5)
add_textbox(s, qx + Emu(60000), qy, qw - Emu(120000), qh,
            "“How can a university give every AI / ML student fair, isolated, "
            "GPU-accelerated compute on its own lab hardware — without the chaos "
            "of a shared server?”",
            size=14, bold=True, color=DEEP_BLUE, anchor=MSO_ANCHOR.MIDDLE,
            align=PP_ALIGN.CENTER)

add_bullets(s, Emu(500000), Emu(2050000), Emu(SLIDE_W - 1000000), Emu(2600000), [
    "In our universities in Kashmir, AI / ML students need GPUs for their "
    "projects, but the computer labs have no dedicated GPU management — a "
    "handful of GPUs sit inside a single server.",
    "To use a GPU, a student must request access from the administrator, wait, "
    "and then SSH into the shared server alongside everyone else.",
    "On that one shared server there is no per-student environment, no data "
    "isolation, no data integrity, and no compatibility between conflicting "
    "project dependencies (Python / CUDA / framework versions).",
    "Raw hypervisors (libvirt / KVM / virt-manager) could solve isolation, but "
    "they need Linux admin expertise and have no built-in users, quotas, or "
    "audit — unusable directly by students.",
    "A private cloud on the same lab server solves this: each student gets "
    "their own VM, GPUs are assigned to VMs (GPU passthrough), and per-user "
    "limits cap how many VMs and how much GPU-time each student can consume.",
], size=12)


# ========================================================================
# Slide 6 — Objectives
# ========================================================================
s = content_slide("Objectives", nextp(), TOTAL)
add_bullets(s, Emu(500000), Emu(1000000), Emu(SLIDE_W - 1000000), Emu(3700000), [
    "Design and implement a web-based self-service portal for on-demand VM "
    "provisioning on a KVM-based hypervisor.",
    "Build a secure REST API (FastAPI) that authenticates users with JWT and "
    "authorises every VM operation against role-based permissions.",
    "Integrate with the hypervisor through its API so that create / start / stop / "
    "delete operations on VMs are fully automated — no manual SSH access.",
    "Introduce cloud-style abstractions missing at the hypervisor level: users, "
    "roles (user / admin), daily provisioning quotas, and an immutable audit log.",
    "Use a pre-configured golden image so that every provisioned VM boots in "
    "seconds with a known-good OS template, SSH keys, and cloud-init.",
    "Deliver a modern React + TypeScript frontend (Aether Cloud Orchestrator UI) "
    "that hides all hypervisor complexity from the end-user.",
], size=14)


# ========================================================================
# Slide 7 — Scope of the Project
# ========================================================================
s = content_slide("Scope of the Project", nextp(), TOTAL)
# In-scope / Out-of-scope two-column
lw = Emu(4100000); rh = Emu(3500000)
lx = Emu(311700); rx = Emu(SLIDE_W - lw - 311700)
ty = Emu(1000000)

add_rect(s, lx, ty, lw, rh, fill=WHITE, line=GREEN, line_w=1.5)
add_rect(s, lx, ty, lw, Emu(380000), fill=GREEN, line=None)
add_textbox(s, lx, ty, lw, Emu(380000), "In Scope",
            size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE)
add_bullets(s, lx, ty + Emu(420000), lw, rh - Emu(420000), [
    "User registration & JWT login",
    "VM lifecycle: create / list / get / start / stop / delete",
    "Admin panel: user management, audit log, settings",
    "Per-user daily VM creation quota",
    "Immutable audit log of every privileged action",
    "Single-node Proxmox VE server as the KVM hypervisor",
    "Postgres 16 for persistence (no ORM, raw psycopg2)",
    "Docker Compose based deployment",
], size=12)

add_rect(s, rx, ty, lw, rh, fill=WHITE, line=AMBER, line_w=1.5)
add_rect(s, rx, ty, lw, Emu(380000), fill=AMBER, line=None)
add_textbox(s, rx, ty, lw, Emu(380000), "Out of Scope",
            size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE)
add_bullets(s, rx, ty + Emu(420000), lw, rh - Emu(420000), [
    "Multi-tenancy billing / metered billing",
    "High-availability multi-node hypervisor clustering",
    "Software-defined networking (custom VPC, overlay nets)",
    "Block-storage as a separate service",
    "Container orchestration (Kubernetes as a service)",
    "Marketplace of pre-built application images",
    "Public-cloud style global regions",
], size=12)


# ========================================================================
# Slide 8 — Literature Review / Existing Systems (table)
# ========================================================================
s = content_slide("Literature Review — Existing Systems", nextp(), TOTAL)

rows = [
    ["System", "Type", "Hypervisor / Tech", "Strengths", "Limitations for us"],
    ["DigitalOcean",          "Public IaaS", "KVM + custom stack",
     "Simple UX, one-click droplets", "Public cloud; data leaves premises"],
    ["AWS EC2",               "Public IaaS", "Nitro / KVM",
     "Huge feature set, global scale",  "High cost & complexity; overkill"],
    ["OpenStack",             "Open-source IaaS", "KVM + many services",
     "Full cloud stack", "Very heavy; >10 services to operate"],
    ["Apache CloudStack",     "Open-source IaaS", "KVM / XenServer",
     "Proven, multi-tenant",    "Steep learning curve; Java stack"],
    ["Raw libvirt / KVM",     "Hypervisor tool", "KVM",
     "Lightweight, simple",     "No users, quotas, audit, or portal"],
    ["PrivateCloud (ours)",   "Self-hosted IaaS", "KVM via Proxmox VE",
     "Minimal, portal + API, audit, quotas",
     "Single-node scope (by design)"],
]
tblx = Emu(250000); tbly = Emu(1000000)
tblw = Emu(SLIDE_W - 500000); tblh = Emu(3500000)
tbl_shape = s.shapes.add_table(len(rows), len(rows[0]), tblx, tbly, tblw, tblh)
tbl = tbl_shape.table

col_widths = [1400000, 1350000, 1700000, 2150000, 2000000]
for i, w in enumerate(col_widths):
    tbl.columns[i].width = Emu(w)

for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.margin_left = Emu(36000); cell.margin_right = Emu(36000)
        cell.margin_top  = Emu(24000); cell.margin_bottom = Emu(24000)
        cell.fill.solid()
        if r == 0:
            cell.fill.fore_color.rgb = DEEP_BLUE
        elif row[0].startswith("PrivateCloud"):
            cell.fill.fore_color.rgb = RGBColor(0xDE, 0xEB, 0xFA)
        else:
            cell.fill.fore_color.rgb = WHITE if r % 2 else PANEL
        tf = cell.text_frame
        tf.word_wrap = True
        tf.paragraphs[0].text = ""
        run = tf.paragraphs[0].add_run()
        run.text = val
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.bold = (r == 0) or (c == 0)
        run.font.color.rgb = WHITE if r == 0 else TEXT_DARK


# ========================================================================
# Slide 9 — Proposed System (overview text)
# ========================================================================
s = content_slide("Proposed System", nextp(), TOTAL)
add_bullets(s, Emu(500000), Emu(1000000), Emu(SLIDE_W - 1000000), Emu(3700000), [
    "A three-tier private cloud platform: Frontend (React) → Backend API "
    "(FastAPI) → Hypervisor (Proxmox VE / KVM) with PostgreSQL as the system "
    "of record.",
    "The backend is the only component that talks to the hypervisor — users "
    "never see Proxmox, SSH, or libvirt. The API is the single trusted boundary.",
    "All VM operations are authorised (JWT + role check), validated (Pydantic "
    "schemas), executed (via the hypervisor API), persisted (Postgres), and "
    "audit-logged — atomically inside one request.",
    "Pre-baked golden image + cloud-init make VMs ready in seconds, just like "
    "DigitalOcean droplets — no manual OS install per VM.",
    "Entire platform is deployable with docker-compose up on a single physical "
    "server, making it practical for labs, SMEs, and academic institutions.",
], size=14)


# ========================================================================
# Slide 10 — Proposed System — High-level Architecture diagram
# ========================================================================
s = content_slide("Proposed System — High-Level Architecture", nextp(), TOTAL)

# Columns: User | Frontend | Backend | DB | Hypervisor | VMs
# Lay them out horizontally
row_top = Emu(1150000)
row_h   = Emu(700000)
col_gap = Emu(160000)
# 5 cards
col_w = Emu((SLIDE_W - 620000 - 4*160000)//5)
cx = Emu(310000)

labeled_box(s, cx,                       row_top, col_w, row_h,
            "User", "Browser")
labeled_box(s, cx + 1*(col_w + col_gap), row_top, col_w, row_h,
            "Frontend", "React + Vite + TS")
labeled_box(s, cx + 2*(col_w + col_gap), row_top, col_w, row_h,
            "Backend API", "FastAPI (Python)",
            fill=RGBColor(0xDE, 0xEB, 0xFA))
labeled_box(s, cx + 3*(col_w + col_gap), row_top, col_w, row_h,
            "Hypervisor", "Proxmox VE (KVM)")
labeled_box(s, cx + 4*(col_w + col_gap), row_top, col_w, row_h,
            "VMs", "Ubuntu / Debian guests")

# arrows between them
ay = row_top + Emu(350000)
for i in range(5):
    if i < 4:
        x1 = cx + (i+1)*col_w + i*col_gap
        x2 = x1 + col_gap
        arrow(s, x1, ay, x2, ay, color=DEEP_BLUE, w=2.0)

# Second row: DB attached to Backend
db_x = cx + 2*(col_w + col_gap)
db_y = row_top + row_h + Emu(350000)
labeled_box(s, db_x, db_y, col_w, Emu(600000),
            "PostgreSQL 16",
            "users · vms · audit · quotas",
            fill=PANEL)
# Vertical arrow
arrow(s, db_x + col_w//2, row_top + row_h,
         db_x + col_w//2, db_y, color=DEEP_BLUE, w=2.0)

# protocol labels
def mini_label(x, y, txt, w=Emu(600000)):
    tb = s.shapes.add_textbox(x, y, w, Emu(230000))
    tf = tb.text_frame; tf.margin_left = 0; tf.margin_top = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = txt
    r.font.name = "Calibri"; r.font.size = Pt(9); r.font.italic = True
    r.font.color.rgb = TEXT_MUT

for i, txt in enumerate(["HTTPS", "REST / JSON", "HTTPS API", "QEMU-KVM"]):
    mid = cx + (i+1)*col_w + i*col_gap + col_gap//2 - Emu(300000)
    mini_label(mid, ay - Emu(260000), txt)

# Legend / caption
add_textbox(s, Emu(500000), Emu(3900000), Emu(SLIDE_W - 1000000), Emu(350000),
            "Every VM request flows through a single authorised path: "
            "user → portal → API → Proxmox → VM. Nothing bypasses the backend.",
            size=12, color=TEXT_MUT, align=PP_ALIGN.CENTER)


# ========================================================================
# Slide 11 — Methodology — Backend Architectural Design
# ========================================================================
s = content_slide("Methodology — Backend Architecture", nextp(), TOTAL)

# Layered boxes on left, explanation on right
lx = Emu(310000); ly = Emu(1000000); lw = Emu(3800000)
layer_h = Emu(500000); gap = Emu(70000)

layers = [
    ("Route Layer",        "auth_routes · vm_routes · admin_routes", ACCENT),
    ("Service / Logic",    "JWT auth · quota check · audit writer",  DEEP_BLUE),
    ("Hypervisor Client",  "proxmox_client.py  (REST calls)",        RGBColor(0x33, 0x72, 0xA6)),
    ("Data Access",        "database.py  (raw psycopg2 pool)",       RGBColor(0x5A, 0x8A, 0xC0)),
    ("PostgreSQL 16",      "users · vms · audit_log · quotas",       RGBColor(0x0B, 0x1F, 0x3A)),
]
for i, (t, sub, color) in enumerate(layers):
    y = ly + i*(layer_h + gap)
    add_rect(s, lx, y, lw, layer_h, fill=color, line=None)
    add_textbox(s, lx + Emu(60000), y, lw - Emu(120000), layer_h,
                t, size=13, bold=True, color=WHITE,
                anchor=MSO_ANCHOR.MIDDLE)
    add_textbox(s, lx + Emu(60000), y, lw - Emu(120000), layer_h,
                sub, size=10, color=WHITE,
                anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)

# Right-hand explanation
rx = Emu(4250000); rw = Emu(SLIDE_W - rx - Emu(310000))
add_bullets(s, rx, ly, rw, Emu(3500000), [
    "FastAPI exposes routes under /auth, /vms, and /admin.",
    "Each route depends on get_current_user() which validates the "
    "JWT and loads the caller from Postgres.",
    "VM routes call proxmox_client — the only module allowed to "
    "talk to the hypervisor API.",
    "Writes to Postgres use a ThreadedConnectionPool (psycopg2) — "
    "no ORM, full SQL control.",
    "Every privileged operation appends a row to audit_log in the "
    "same transaction, so the log can never fall out of sync.",
    "Pydantic models validate every request/response body, giving "
    "automatic OpenAPI docs at /docs.",
], size=12)


# ========================================================================
# Slide 12 — Methodology — How Proxmox (KVM) Works
# ========================================================================
s = content_slide("Methodology — How the KVM Hypervisor Works", nextp(), TOTAL)

# Diagram: physical hardware → KVM kernel module → QEMU processes (VMs)
# Stacked layers bottom-up
bx = Emu(500000); bw = Emu(3700000)
bh = Emu(500000); gap = Emu(50000)
base_y = Emu(3100000)

stack = [
    ("Physical Server (CPU · RAM · Disks · NIC)", NAVY),
    ("Linux Kernel + KVM module  (virtualisation support)", DEEP_BLUE),
    ("QEMU user-space emulator per VM (virtual CPU, disk, NIC)", RGBColor(0x33,0x72,0xA6)),
    ("Guest OS  — Ubuntu / Debian / etc.", RGBColor(0x5A,0x8A,0xC0)),
]
for i, (txt, color) in enumerate(stack):
    y = base_y - i*(bh + gap)
    add_rect(s, bx, y, bw, bh, fill=color, line=None)
    add_textbox(s, bx, y, bw, bh, txt,
                size=11, bold=True, color=WHITE,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# right-side bullets
rx = Emu(4400000); rw = Emu(SLIDE_W - rx - Emu(310000))
add_bullets(s, rx, Emu(1000000), rw, Emu(3700000), [
    "KVM (Kernel-based Virtual Machine) is a Linux kernel module that turns "
    "the host kernel into a type-1-style hypervisor.",
    "QEMU creates one user-space process per VM; KVM provides the hardware "
    "acceleration (Intel VT-x / AMD-V) so the guest runs at near-native speed.",
    "Proxmox VE packages KVM + QEMU + management tooling and exposes a "
    "REST API we can call programmatically.",
    "Just like DigitalOcean’s hypervisor fleet runs KVM under the hood, we "
    "run KVM through Proxmox VE — the difference is only the management "
    "layer around it.",
    "Our backend never touches QEMU directly — it calls the hypervisor "
    "API: “create a VM with these specs on this node from this template.”",
], size=12)


# ========================================================================
# Slide 13 — Methodology — Frontend ↔ Backend Communication
# ========================================================================
s = content_slide("Methodology — Frontend ↔ Backend Communication", nextp(), TOTAL)

# Horizontal sequence diagram: Browser → API → DB/Hypervisor
boxes = [
    ("React UI",         "Vite + TS + Tailwind"),
    ("API Client",       "fetch / axios · JWT header"),
    ("FastAPI",          "validate · authorise · dispatch"),
    ("Postgres / Proxmox", "persist · provision"),
]

bw = Emu(1850000); bh = Emu(700000)
by = Emu(1050000)
gap = Emu(100000)
startX = Emu((SLIDE_W - 4*bw - 3*gap)//2)

for i, (t, sub) in enumerate(boxes):
    x = startX + i*(bw + gap)
    labeled_box(s, x, by, bw, bh, t, sub,
                fill=PANEL if i % 2 == 0 else WHITE)
    if i < 3:
        arrow(s, x + bw, by + bh//2,
                 x + bw + gap, by + bh//2, color=DEEP_BLUE, w=2.0)

# Flow description bullets
add_bullets(s, Emu(500000), Emu(2000000), Emu(SLIDE_W - 1000000), Emu(2800000), [
    "Step 1 — User fills a form (e.g. “create VM”) in the React UI.",
    "Step 2 — API client sends a JSON request to the FastAPI backend, "
    "attaching the JWT from localStorage as an Authorization: Bearer header.",
    "Step 3 — FastAPI validates the body with Pydantic, decodes the JWT, "
    "loads the user, and checks the user’s role + remaining daily quota.",
    "Step 4 — If allowed, the backend calls the hypervisor API to create "
    "the VM from the golden image, writes a row into the vms table, and "
    "appends an entry to audit_log — all inside one DB transaction.",
    "Step 5 — The backend returns a JSON response; React updates the "
    "dashboard in real time and the new VM appears in the user’s list.",
], size=12)


# ========================================================================
# Slide 14 — Methodology — Why Docker (Containerisation)
# ========================================================================
s = content_slide("Methodology — Why Docker (Containerisation)", nextp(), TOTAL)

# Left: VM vs Container comparison block
lx = Emu(310000); ly = Emu(1000000); lw = Emu(3900000); lh = Emu(3500000)
add_rect(s, lx, ly, lw, Emu(380000), fill=DEEP_BLUE, line=None)
add_textbox(s, lx, ly, lw, Emu(380000), "What is a Docker Container?",
            size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE)
add_rect(s, lx, ly + Emu(380000), lw, lh - Emu(380000),
         fill=WHITE, line=DEEP_BLUE, line_w=1.25)
add_bullets(s, lx, ly + Emu(420000), lw, lh - Emu(440000), [
    "A container is a lightweight, isolated package holding an "
    "application and all its dependencies.",
    "Unlike a VM, it shares the host kernel — no separate OS — so it "
    "starts in milliseconds and uses very little RAM.",
    "Guaranteed reproducibility: the same image runs identically on a "
    "laptop and on the lab server. No “works on my machine.”",
    "Orchestrated with Docker Compose: one YAML file, one command.",
    "Runs on the host server alongside Proxmox — the platform layer, "
    "not the VM layer.",
], size=12)

# Right: how our stack uses docker compose
rx = Emu(4350000); rw = Emu(SLIDE_W - rx - Emu(310000))
add_textbox(s, rx, Emu(1000000), rw, Emu(350000),
            "How we use it",
            size=14, bold=True, color=DEEP_BLUE)
add_bullets(s, rx, Emu(1350000), rw, Emu(3200000), [
    "Entire backend stack defined in docker-compose.yml.",
    "Three services, one network (proxmox_net), one command:",
    "    docker compose up --build",
    "Environment-variable driven — single .env file configures every "
    "service consistently.",
    "Postgres data kept in a named Docker volume — survives restarts, "
    "upgrades, and rebuilds.",
    "Health checks ensure the backend waits for Postgres to be ready "
    "before starting.",
    "Deployment on a new lab server = clone repo + docker compose up.",
], size=12)


# ========================================================================
# Slide 15 — Methodology — Three-Tier Container Architecture
# ========================================================================
s = content_slide("Methodology — Three-Tier Container Architecture", nextp(), TOTAL)

# Outer host server box
hx = Emu(450000); hy = Emu(1000000)
hw = Emu(SLIDE_W - 900000); hh = Emu(2550000)
add_rect(s, hx, hy, hw, hh, fill=WHITE, line=NAVY, line_w=1.5)
add_textbox(s, hx + Emu(60000), hy + Emu(40000), hw - Emu(120000), Emu(300000),
            "Host Server  (Docker Engine)  —  proxmox_net  (bridge network)",
            size=11, bold=True, color=NAVY)

# 3 container cards inside the host
cy = hy + Emu(450000); ch = Emu(1500000)
cw = Emu((hw - Emu(4*150000)) // 3)
cx0 = hx + Emu(150000)

tiers = [
    ("Presentation Tier",
     "proxmox_frontend",
     "React · Vite · TS",
     "Host port 3000 → container 80",
     ACCENT),
    ("Application Tier",
     "proxmox_backend",
     "FastAPI · Python 3.12",
     "Host port 8000 → container 8000",
     DEEP_BLUE),
    ("Data Tier",
     "proxmox_postgres",
     "PostgreSQL 16 · Alpine",
     "Host port 5432 · volume postgres_data",
     RGBColor(0x33, 0x72, 0xA6)),
]
for i, (tier, name, tech, ports, color) in enumerate(tiers):
    x = cx0 + i*(cw + Emu(150000))
    add_rect(s, x, cy, cw, ch, fill=WHITE, line=color, line_w=1.5)
    add_rect(s, x, cy, cw, Emu(340000), fill=color, line=None)
    add_textbox(s, x, cy, cw, Emu(340000), tier,
                size=12, bold=True, color=WHITE,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_textbox(s, x + Emu(40000), cy + Emu(370000),
                cw - Emu(80000), Emu(280000),
                name, size=11, bold=True, color=color,
                align=PP_ALIGN.CENTER)
    add_textbox(s, x + Emu(40000), cy + Emu(660000),
                cw - Emu(80000), Emu(280000),
                tech, size=10, color=TEXT_DARK,
                align=PP_ALIGN.CENTER)
    add_textbox(s, x + Emu(40000), cy + Emu(960000),
                cw - Emu(80000), Emu(450000),
                ports, size=9, color=TEXT_MUT,
                align=PP_ALIGN.CENTER)

# Arrows between containers
ay = cy + ch // 2
for i in range(2):
    x1 = cx0 + (i+1)*cw + i*Emu(150000)
    x2 = x1 + Emu(150000)
    arrow(s, x1, ay, x2, ay, color=NAVY, w=2.0)

# Caption
add_bullets(s, Emu(450000), Emu(3650000), Emu(SLIDE_W - 900000), Emu(1100000), [
    "Each tier lives in its own container, isolated and independently "
    "upgradable.",
    "Containers communicate over the private proxmox_net bridge using "
    "service names (e.g. the backend connects to host “postgres”, not "
    "localhost) — Postgres is not exposed to the public internet.",
    "The browser talks only to the frontend (3000) and backend API (8000); "
    "the database tier stays behind the network boundary.",
], size=11)


# ========================================================================
# Slide 16 — Methodology — Golden Image Creation
# ========================================================================
s = content_slide("Methodology — Golden Image Creation", nextp(), TOTAL)

# Pipeline arrows: Base ISO → Install → Harden → Cloud-init → Template → Clone
steps = [
    ("Base OS",      "Ubuntu 22.04 ISO"),
    ("Install",      "Minimal packages"),
    ("Harden",       "Users, SSH, firewall"),
    ("cloud-init",   "First-boot config"),
    ("Template",     "Convert to template"),
    ("Linked Clone", "New VM = instant clone"),
]
sw = Emu(1330000); sh = Emu(640000)
sy = Emu(1050000)
gap = Emu(70000)
sx0 = Emu((SLIDE_W - 6*sw - 5*gap)//2)

for i, (t, sub) in enumerate(steps):
    x = sx0 + i*(sw + gap)
    fill = RGBColor(0xDE, 0xEB, 0xFA) if i == len(steps)-1 else PANEL
    labeled_box(s, x, sy, sw, sh, t, sub,
                fill=fill, title_size=12, sub_size=9)
    if i < len(steps)-1:
        arrow(s, x + sw, sy + sh//2, x + sw + gap, sy + sh//2,
              color=ACCENT, w=1.75)

add_bullets(s, Emu(500000), Emu(2000000), Emu(SLIDE_W - 1000000), Emu(2800000), [
    "Why a golden image? — Installing an OS per VM from an ISO takes "
    "15–20 minutes. We do it once, then clone.",
    "Step 1 — Install Ubuntu 22.04 on a base VM with only the packages "
    "we actually need (qemu-guest-agent, openssh-server, curl).",
    "Step 2 — Harden the image: disable root password login, preload the "
    "admin SSH public key, set time-zone, enable the firewall.",
    "Step 3 — Install and enable cloud-init. On first boot cloud-init "
    "reads metadata (hostname, SSH key, user) injected by the hypervisor "
    "and configures the VM in seconds.",
    "Step 4 — Convert the base VM into a template. New VMs are created as "
    "linked clones of this template — provisioning time drops from minutes "
    "to a few seconds, exactly like DigitalOcean droplets.",
], size=12)


# ========================================================================
# Slide 15 — Methodology — Hardware & Software
# ========================================================================
s = content_slide("Methodology — Hardware & Software Stack", nextp(), TOTAL)

# Two columns
lw = Emu(4100000); lh = Emu(3500000)
lx = Emu(311700); rx = Emu(SLIDE_W - lw - 311700)
ty = Emu(1000000)

# Software
add_rect(s, lx, ty, lw, lh, fill=WHITE, line=DEEP_BLUE, line_w=1.5)
add_rect(s, lx, ty, lw, Emu(380000), fill=DEEP_BLUE, line=None)
add_textbox(s, lx, ty, lw, Emu(380000), "Software Stack",
            size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE)
add_bullets(s, lx, ty + Emu(420000), lw, lh - Emu(420000), [
    "Backend — Python 3.12 + FastAPI 0.110",
    "Database — PostgreSQL 16 (psycopg2, no ORM)",
    "Frontend — React 18 + Vite + TypeScript + Tailwind",
    "Auth — JWT (PyJWT), bcrypt password hashing",
    "Hypervisor — Proxmox VE (KVM-based)",
    "Infra — Docker · Docker Compose",
    "Tooling — Pydantic v2, uvicorn, cloud-init",
    "Dev — Git, GitHub Actions, VS Code",
], size=12)

# Hardware
add_rect(s, rx, ty, lw, lh, fill=WHITE, line=DEEP_BLUE, line_w=1.5)
add_rect(s, rx, ty, lw, Emu(380000), fill=DEEP_BLUE, line=None)
add_textbox(s, rx, ty, lw, Emu(380000), "Hardware Requirements",
            size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE)
add_bullets(s, rx, ty + Emu(420000), lw, lh - Emu(420000), [
    "Host Server — x86-64 CPU with VT-x / AMD-V enabled",
    "Minimum: 4 cores, 16 GB RAM, 256 GB SSD",
    "Recommended: 8+ cores, 32 GB RAM, 1 TB NVMe",
    "Networking — 1 Gbps NIC, static IP",
    "Client — any modern browser (Chrome / Edge / Firefox)",
    "Development — laptop with Docker Desktop",
    "Optional — second disk for VM storage pool",
], size=12)


# ========================================================================
# Slide 16 — Work Done So Far — Sprint Progress table
# ========================================================================
s = content_slide("Work Done So Far — Sprint Progress", nextp(), TOTAL)

rows = [
    ["Module",                   "Feature",                                     "Status"],
    ["Authentication",           "Register / Login / JWT issue & validate",     "Done"],
    ["Authentication",           "Role-based access (user / admin)",            "Done"],
    ["VM Management",            "Create / List / Get VM via hypervisor API",   "Done"],
    ["VM Management",            "Start / Stop / Delete VM",                    "Done"],
    ["VM Management",            "Per-user daily quota enforcement",            "Done"],
    ["Audit",                    "Immutable audit log on every privileged op",  "Done"],
    ["Admin Panel",              "User management UI + audit viewer",           "Done"],
    ["Admin Panel",              "Settings page (quota config)",                "In Progress"],
    ["Frontend",                 "Aether Cloud Orchestrator — full UI",         "Done"],
    ["Deployment",               "Docker Compose bring-up, schema on startup",  "Done"],
    ["Golden Image",             "Ubuntu 22.04 template with cloud-init",       "In Progress"],
    ["Monitoring",               "CPU / RAM / disk metrics per VM",             "Planned"],
]

tblx = Emu(400000); tbly = Emu(1000000)
tblw = Emu(SLIDE_W - 800000); tblh = Emu(3500000)
tbl_shape = s.shapes.add_table(len(rows), 3, tblx, tbly, tblw, tblh)
tbl = tbl_shape.table
tbl.columns[0].width = Emu(2100000)
tbl.columns[1].width = Emu(4400000)
tbl.columns[2].width = Emu(1900000)

status_color = {
    "Done": GREEN,
    "In Progress": AMBER,
    "Planned": TEXT_MUT,
}
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.margin_left = Emu(36000); cell.margin_right = Emu(36000)
        cell.margin_top  = Emu(14000); cell.margin_bottom = Emu(14000)
        cell.fill.solid()
        if r == 0:
            cell.fill.fore_color.rgb = DEEP_BLUE
        else:
            cell.fill.fore_color.rgb = WHITE if r % 2 else PANEL
        tf = cell.text_frame; tf.word_wrap = True
        tf.paragraphs[0].text = ""
        run = tf.paragraphs[0].add_run()
        run.text = val
        run.font.name = "Calibri"
        run.font.size = Pt(11)
        run.font.bold = (r == 0)
        if r == 0:
            run.font.color.rgb = WHITE
        elif c == 2:
            run.font.bold = True
            run.font.color.rgb = status_color.get(val, TEXT_DARK)
        else:
            run.font.color.rgb = TEXT_DARK


# ========================================================================
# Slide 17 — Work Done So Far — Feature Snapshots
# ========================================================================
s = content_slide("Work Done So Far — Feature Snapshots", nextp(), TOTAL)

# 4 feature cards in a 2x2 grid
cards = [
    ("Secure Auth",
     "JWT + bcrypt",
     "Register, login, role-based guards "
     "on every endpoint."),
    ("VM Lifecycle",
     "Create · Start · Stop · Delete",
     "Full CRUD against the hypervisor "
     "API from the portal."),
    ("Daily Quota",
     "Per-user limit",
     "Rate-limits how many VMs a user can "
     "create per day, prevents abuse."),
    ("Audit Log",
     "Every action recorded",
     "Immutable table in Postgres — "
     "admin can inspect who did what, when."),
]

cw = Emu(4050000); ch = Emu(1550000)
gap = Emu(200000)
startX = Emu((SLIDE_W - 2*cw - gap)//2)
startY = Emu(1050000)
for i, (t, sub, body) in enumerate(cards):
    r = i // 2; c = i % 2
    x = startX + c*(cw + gap)
    y = startY + r*(ch + gap)
    add_rect(s, x, y, cw, ch, fill=WHITE, line=DEEP_BLUE, line_w=1.25)
    add_rect(s, x, y, cw, Emu(340000), fill=DEEP_BLUE, line=None)
    add_textbox(s, x + Emu(40000), y, cw - Emu(80000), Emu(340000),
                t, size=13, bold=True, color=WHITE,
                anchor=MSO_ANCHOR.MIDDLE)
    add_textbox(s, x + Emu(40000), y, cw - Emu(80000), Emu(340000),
                sub, size=10, color=WHITE,
                anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)
    add_textbox(s, x + Emu(40000), y + Emu(360000),
                cw - Emu(80000), ch - Emu(380000),
                body, size=12, color=TEXT_DARK)


# ========================================================================
# Slide 18 — Expected Outcomes & Applications
# ========================================================================
s = content_slide("Expected Outcomes & Applications", nextp(), TOTAL)

add_textbox(s, Emu(500000), Emu(1000000), Emu(SLIDE_W - 1000000), Emu(350000),
            "Expected Outcomes",
            size=16, bold=True, color=DEEP_BLUE)
add_bullets(s, Emu(500000), Emu(1350000), Emu(SLIDE_W - 1000000), Emu(1500000), [
    "A working, self-hosted VM-provisioning platform deployable on one server.",
    "End-to-end automation: portal → API → hypervisor → running VM in seconds.",
    "Measurable: sub-minute provisioning time, full audit coverage, zero manual steps.",
], size=12)

add_textbox(s, Emu(500000), Emu(2950000), Emu(SLIDE_W - 1000000), Emu(350000),
            "Applications",
            size=16, bold=True, color=DEEP_BLUE)
add_bullets(s, Emu(500000), Emu(3300000), Emu(SLIDE_W - 1000000), Emu(1500000), [
    "University / college labs that need disposable student VMs on demand.",
    "SMEs that cannot (or do not want to) move workloads to the public cloud.",
    "DevOps test environments — spin up a throwaway VM, run CI, tear it down.",
    "Research groups handling sensitive data that must stay on-premises.",
], size=12)


# ========================================================================
# Slide 19 — References (1)
# ========================================================================
s = content_slide("References", nextp(), TOTAL)

refs = [
    "1.  Armbrust, M. et al. (2010). A view of cloud computing. "
    "Communications of the ACM, 53(4), 50–58.",
    "2.  Mell, P., & Grance, T. (2011). The NIST Definition of Cloud "
    "Computing. NIST Special Publication 800-145.",
    "3.  Kivity, A., Kamay, Y., Laor, D., Lublin, U., & Liguori, A. "
    "(2007). KVM: the Linux Virtual Machine Monitor. "
    "Proceedings of the Linux Symposium.",
    "4.  Bellard, F. (2005). QEMU, a Fast and Portable Dynamic Translator. "
    "USENIX Annual Technical Conference.",
    "5.  Sefraoui, O., Aissaoui, M., & Eleuldj, M. (2012). OpenStack: "
    "Toward an Open-Source Solution for Cloud Computing. "
    "International Journal of Computer Applications, 55(3), 38–42.",
    "6.  Proxmox Server Solutions GmbH. Proxmox VE Administration Guide "
    "(latest). https://pve.proxmox.com/pve-docs/",
]
add_bullets(s, Emu(400000), Emu(1000000), Emu(SLIDE_W - 800000), Emu(3700000),
            refs, size=12, bullet_char=" ")


# ========================================================================
# Slide 20 — References (2)
# ========================================================================
s = content_slide("References (contd.)", nextp(), TOTAL)
refs2 = [
    "7.  Canonical Ltd. cloud-init Documentation. "
    "https://cloudinit.readthedocs.io/",
    "8.  Tiangolo, S. FastAPI — Modern, fast web framework for building "
    "APIs with Python. https://fastapi.tiangolo.com/",
    "9.  PostgreSQL Global Development Group. PostgreSQL 16 Documentation. "
    "https://www.postgresql.org/docs/16/",
    "10. Jones, M., Bradley, J., & Sakimura, N. (2015). JSON Web Token (JWT). "
    "RFC 7519, IETF.",
    "11. Provos, N., & Mazières, D. (1999). A Future-Adaptable Password "
    "Scheme (bcrypt). USENIX Annual Technical Conference.",
    "12. Merkel, D. (2014). Docker: Lightweight Linux Containers for "
    "Consistent Development and Deployment. Linux Journal, 2014(239).",
    "13. Sotomayor, B., Montero, R. S., Llorente, I. M., & Foster, I. "
    "(2009). Virtual Infrastructure Management in Private and Hybrid Clouds. "
    "IEEE Internet Computing, 13(5), 14–22.",
]
add_bullets(s, Emu(400000), Emu(1000000), Emu(SLIDE_W - 800000), Emu(3700000),
            refs2, size=12, bullet_char=" ")


# ========================================================================
# Slide 21 — Thank You
# ========================================================================
s = add_slide()
add_rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=NAVY, line=None)
add_rect(s, 0, Emu(2500000), Emu(SLIDE_W), Emu(40000), fill=ACCENT, line=None)
add_textbox(s, Emu(311700), Emu(1500000), Emu(SLIDE_W - 623400), Emu(900000),
            "Thank You", size=60, bold=True, color=WHITE,
            align=PP_ALIGN.CENTER)
add_textbox(s, Emu(311700), Emu(2700000), Emu(SLIDE_W - 623400), Emu(450000),
            "Questions & Discussion",
            size=22, color=ACCENT, align=PP_ALIGN.CENTER)


# Save — fall back to a versioned filename if the primary is locked (file open in PowerPoint)
primary = r"C:\Users\AZAM RIZWAN\Desktop\PrivateCloud\PrivateCloud_Project_ppt.pptx"
try:
    prs.save(primary)
    out = primary
except PermissionError:
    out = r"C:\Users\AZAM RIZWAN\Desktop\PrivateCloud\PrivateCloud_Project_ppt_v2.pptx"
    prs.save(out)
print(f"Saved: {out}")
print(f"Total slides: {len(prs.slides)}")

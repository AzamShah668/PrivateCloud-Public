# Iteration 3 — UML Diagrams

Deliverables for Sprint 3 of PrivateCloud.

## Files

| File | Purpose |
|------|---------|
| `class_diagram_i3.puml` | Class diagram covering the I3 additions (Admin Portal, profile self-service, enriched VM details, system settings, soft-delete users, audit taxonomy). |
| `sequence_diagram_i3.puml` | Four key I3 sequence flows: (1) admin soft-delete user, (2) view + update profile, (3) enriched VM details with live Proxmox poll, (4) admin update system setting. |

## Scope (what I3 actually shipped)

Backed by `docs/ARCHITECTURE.md` and journal entries 011–014:

- Admin Dashboard: `/admin/stats`, `/admin/users`, `/admin/vms`, `/admin/audit-logs`, `/admin/settings`
- Soft-delete users (`status`, `deleted_at` columns + suspend / delete / reactivate endpoints)
- Audit action taxonomy (`action_type` enum: `user.*`, `vm.*`, `settings.*`, `auth.*`)
- Admin action attribution (`target_user_id` FK on `audit_logs`)
- System settings table (`system_settings` key/value with typed value)
- User profile view/update (`GET` + `PATCH /auth/me`, `UserUpdateRequest`)
- VM details + live Proxmox status enrichment (`VMEnrichedResponse`, `GET /vms/{id}`, `GET /vms/`)

## How to render

### Option A — VS Code
1. Install the **PlantUML** extension (`jebbs.plantuml`).
2. Open either `.puml` file.
3. `Alt+D` to preview, or right-click → *Export Current Diagram* → PNG / SVG.

### Option B — Browser (no install)
1. Copy the file contents.
2. Paste into <https://www.plantuml.com/plantuml/uml/> or <https://planttext.com>.
3. Download PNG / SVG.

### Option C — Command line
```bash
# Requires Java + plantuml.jar
java -jar plantuml.jar diagrams/iteration3/class_diagram_i3.puml
java -jar plantuml.jar diagrams/iteration3/sequence_diagram_i3.puml
```

This produces `class_diagram_i3.png` and `sequence_diagram_i3.png` next to the source files.

### Option D — draw.io
1. In draw.io: *Arrange → Insert → Advanced → PlantUML*.
2. Paste the file contents.
3. The diagram appears as an editable shape that can be exported to PNG/SVG/PDF.

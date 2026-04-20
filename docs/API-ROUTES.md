# API Routes Reference

## Authentication (`/api/auth`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/auth/register` | None | Create user account |
| POST | `/auth/login` | None | Get JWT token |
| GET | `/auth/me` | JWT | Get current user profile |
| PATCH | `/auth/me` | JWT | Update username/password/quota |

## VM Management (`/api/vms`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/vms` | JWT | Create VM (async, returns job_id) |
| GET | `/vms` | JWT | List user's VMs |
| GET | `/vms/{job_id}` | JWT | Get VM details + live status |
| PATCH | `/vms/{job_id}` | JWT | Perform action (start/stop/restart/resize/delete) |
| DELETE | `/vms/{job_id}` | JWT | Destroy VM |

## Admin (`/api/admin`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/admin/stats` | JWT+Admin | Dashboard stats (user/VM counts) |
| GET | `/admin/users` | JWT+Admin | List all users with quotas |
| GET | `/admin/users?include_deleted=true` | JWT+Admin | Include soft-deleted users |
| GET | `/admin/vms` | JWT+Admin | List all VMs (all users, with owner) |
| GET | `/admin/audit` | JWT+Admin | Audit log entries (paginated) |
| GET | `/admin/audit?action_type=user.create` | JWT+Admin | Filter audit by action_type |
| PATCH | `/admin/users/{id}/role` | JWT+Admin | Change user role (user\|admin) |
| PATCH | `/admin/users/{id}/quota` | JWT+Admin | Update daily VM quota |
| POST | `/admin/users/{id}/suspend` | JWT+Admin | Soft-suspend user (new) |
| POST | `/admin/users/{id}/reactivate` | JWT+Admin | Reactivate soft-deleted user (new) |
| GET | `/admin/settings` | JWT+Admin | List all platform settings |
| PATCH | `/admin/settings/{key}` | JWT+Admin | Update a setting value (new) |

---

## Request/Response Shapes

### POST /auth/register
```json
// Request
{
  "username": "alice",
  "password": "securepassword123"
}

// Response (201)
{
  "id": 1,
  "username": "alice",
  "role": "user",
  "daily_quota": 3,
  "created_at": "2026-04-20T12:00:00Z"
}
```

### POST /auth/login
```json
// Request
{
  "username": "alice",
  "password": "securepassword123"
}

// Response (200)
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### POST /vms
```json
// Request
{
  "vm_name": "my-server",
  "os_choice": "ubuntu-22"
}

// Response (202)
{
  "id": 42,
  "user_id": 1,
  "vmid": 200,
  "vm_name": "my-server",
  "os_choice": "ubuntu-22",
  "status": "queued",
  "created_at": "2026-04-20T12:00:00Z",
  "updated_at": "2026-04-20T12:00:00Z",
  "vm_ip": null,
  "vm_username": null,
  "vm_password": null,
  "proxmox_status": null
}
```

### GET /vms/{job_id}
```json
// Response (200) — same shape as POST /vms, but status = 'done'
{
  "id": 42,
  "vm_ip": "192.168.1.100",
  "vm_username": "root",
  "vm_password": "generatedpass123",
  "status": "done",
  "proxmox_status": "running"
}
```

### GET /admin/stats
```json
{
  "total_users": 8,
  "total_admins": 2,
  "total_vms": 24,
  "active_vms": 18,
  "failed_vms": 2,
  "queued_vms": 4,
  "deleted_vms": 0,
  "total_audit_entries": 156,
  "vms_created_today": 3
}
```

### GET /admin/audit
```json
[
  {
    "id": 156,
    "user_id": 1,
    "action_type": "vm.create",
    "action": "Created VM 'web-server'",
    "target_type": "vm_job",
    "target_id": "42",
    "target_user_id": null,
    "details": {
      "vm_name": "web-server",
      "os_choice": "ubuntu-22"
    },
    "created_at": "2026-04-20T12:30:00Z"
  },
  {
    "id": 155,
    "user_id": 1,
    "action_type": "user.role_change",
    "action": "Changed role of user 'bob' from user to admin",
    "target_type": "user",
    "target_id": "3",
    "target_user_id": 3,
    "details": {
      "old_role": "user",
      "new_role": "admin"
    },
    "created_at": "2026-04-20T12:15:00Z"
  }
]
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 202 | Accepted (async job queued) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 409 | Conflict (e.g., username taken, quota exceeded) |
| 429 | Too Many Requests (daily quota hit) |
| 500 | Internal Server Error |

---

## Error Response Format

All errors return:
```json
{
  "detail": "Human-readable error message"
}
```

Example:
```json
{
  "detail": "Daily quota (3 VMs) exceeded for user alice. Reset at 00:00 UTC tomorrow."
}
```

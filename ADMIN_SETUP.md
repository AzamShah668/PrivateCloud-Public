# Admin User Setup Guide

This guide explains how to create an admin user when deploying PrivateCloud to a new server.

---

## Quick Start

### Option 1: Create Admin via API (Recommended for First-Time Setup)

Use `curl` to register the first admin user:

```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "securepassword123",
    "role": "admin",
    "daily_quota": 10
  }'
```

**On Windows (PowerShell):**
```powershell
curl -X POST http://localhost:3000/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{
    "username": "admin",
    "password": "securepassword123",
    "role": "admin",
    "daily_quota": 10
  }'
```

If successful, you'll see a response like:
```json
{
  "id": 1,
  "username": "admin",
  "role": "admin",
  "daily_quota": 10,
  "created_at": "2026-04-16T12:34:56Z"
}
```

### Option 2: Upgrade Existing User to Admin (via Database)

If the user already exists as a regular user, upgrade them directly:

```bash
docker exec postgres-container psql -U postgres -d proxmox_app \
  -c "UPDATE users SET role = 'admin' WHERE username = 'azam';"
```

Or connect to the database interactively:
```bash
docker exec -it postgres-container psql -U postgres -d proxmox_app
# Then run: UPDATE users SET role = 'admin' WHERE username = 'azam';
```

---

## Understanding the curl Command

For beginners, here's what each part of the curl command means:

```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{...}'
```

| Part | Meaning |
|------|---------|
| `curl` | A command-line tool for sending HTTP requests |
| `-X POST` | Use the POST method (create/send new data) |
| `http://localhost:3000/api/auth/register` | Send to the registration endpoint on your local machine |
| `-H "Content-Type: application/json"` | Tell the server "I'm sending JSON data" |
| `-d '{...}'` | The data payload (user information) |

### The User Data

```json
{
  "username": "admin",           // Login name (3+ chars, no spaces)
  "password": "securepassword123", // Password (8+ chars)
  "role": "admin",               // User role: "admin" or "user"
  "daily_quota": 10              // Max VMs per day (default: 3)
}
```

**Important:** This data is sent to the backend, which:
1. Validates the username and password
2. Hashes the password using bcrypt (never stored in plain text)
3. Stores the user in PostgreSQL
4. Returns the created user (password is NOT included in response)

---

## Deployment Checklist

### 1. Configure `.env` File

Copy the example file and update it for your server:

```bash
cp .env.example .env
```

**Required changes:**

| Variable | What to Change | Example |
|----------|---|---|
| `JWT_SECRET_KEY` | Generate a random secret | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DB_PASSWORD` | Change from `postgres` to secure password | `MySecure#Pass123` |
| `PROXMOX_HOST` | Your Proxmox server IP | `192.168.1.100` |
| `PROXMOX_USER` | Proxmox login user | `root@pam` |
| `PROXMOX_PASSWORD` | Proxmox password | `your_proxmox_password` |
| `PROXMOX_TOKEN_ID` | Token from Proxmox UI | `root@pam!proxmox` |
| `PROXMOX_TOKEN_SECRET` | Token secret from Proxmox | `7ccd2821-...` |

### 2. Start the Application

```bash
docker-compose up -d
```

Wait 10-15 seconds for PostgreSQL to initialize:

```bash
sleep 15
```

### 3. Create the First Admin User

**Using curl (recommended):**

```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "YourSecurePassword123",
    "role": "admin",
    "daily_quota": 10
  }'
```

**Using database (if already registered as user):**

```bash
docker exec postgres-container psql -U postgres -d proxmox_app \
  -c "UPDATE users SET role = 'admin' WHERE username = 'admin';"
```

### 4. Log In

- **URL:** `http://localhost:3000`
- **Username:** `admin` (or whatever you set)
- **Password:** Your chosen password

### 5. Access Admin Portal

Once logged in, click the **Admin Portal** link in the sidebar (amber shield icon).

---

## Why Admin Registration is NOT in the Frontend

You may notice there's no "Create Admin" button in the PrivateCloud UI. This is **intentional** for security:

1. **One-time setup** — Admin creation happens only during deployment
2. **Access control** — Only the person deploying should know how to create admins
3. **Prevents privilege escalation** — Regular users can't see how to make themselves admins

**Workflow:**
- ✅ Users can register themselves via the frontend (as regular users)
- ❌ Admin creation is NOT exposed in the UI
- ✅ Admins can only be created via:
  - API with `curl` (for first-time setup)
  - Database query (for upgrading existing users)
  - Internal admin panel (future feature)

---

## Troubleshooting

### "Connection refused" Error

The backend isn't running. Check:

```bash
docker-compose ps
# Should show: postgres, backend, nginx all running
```

Start the stack if needed:
```bash
docker-compose up -d
```

### "Username already exists" Error

Response: `409 Conflict`

The username is taken. Try a different username.

### "Password must be at least 8 characters" Error

Response: `422 Unprocessable Entity`

Your password is too short. Use 8+ characters.

### "role must be one of {'user', 'admin'}" Error

You typed the role incorrectly. Use exactly `"role": "admin"` or `"role": "user"`.

### Can't Access http://localhost:3000

- Make sure docker containers are running: `docker-compose ps`
- Wait 10-15 seconds for services to start
- Check if nginx is on port 3000: `docker-compose logs nginx`

---

## Next Steps

Once you have an admin account:

1. **Explore Admin Portal** — Navigate to `/admin` to see dashboards, user management, VM tracking
2. **Create User Accounts** — Have regular users register themselves
3. **Manage Quotas** — Use the admin panel to set daily VM creation limits per user
4. **Monitor VMs** — Track all VMs across all users from the admin dashboard
5. **Review Audit Logs** — See who did what and when

---

## Questions?

- Check the main [README.md](README.md)
- See architecture details in [.claude/docs/architecture.md](.claude/docs/architecture.md)
- View API routes in [.claude/docs/api-routes.md](.claude/docs/api-routes.md)

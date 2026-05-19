# Apache Guacamole (in-browser RDP)

This folder holds the **MySQL schema** used to initialise the `mysql-guacamole`
service in `docker-compose.yml`.

- `schema/001-create-schema.sql` — official Apache Guacamole 1.5.5 JDBC schema
- `schema/002-create-admin-user.sql` — default admin user `guacadmin` / `guacadmin`

## First-time Docker setup

1. Ensure `docker/guacamole/schema/*.sql` are present (they are committed).
2. `docker compose up -d` — MySQL runs the scripts on **first** volume init only.
3. Open `http://localhost:9080/guacamole/` and log in as **guacadmin** / **guacadmin** (change the password in production).
4. The PrivateCloud API mints per-VM RDP connections via `POST /vms/{job_id}/desktop-session` using the same admin account (configure `GUACAMOLE_ADMIN_PASSWORD` in `.env`).

## Changing passwords

- **Guacamole web admin:** change in the Guacamole UI or by updating MySQL rows.
- **MySQL root / guacamole user:** set `GUACAMOLE_MYSQL_ROOT_PASSWORD` and `GUACAMOLE_MYSQL_PASSWORD` in `.env` **before** the first `docker compose up` (or recreate the MySQL volume).

## Networking notes

`guacd` must be able to open **TCP 3389** (RDP) to your VM IP addresses. If VMs live on another VLAN, place `guacd` on a network path that can reach them (host networking, VPN sidecar, or routing rules).

## Re-initialising MySQL

If you need to rebuild the Guacamole database:

```bash
docker compose down
docker volume ls | grep mysql_guacamole   # note the full volume name
docker volume rm <that_volume_name>
docker compose up -d mysql-guacamole guacd guacamole
```

# PrivateCloud

Development setup for the Proxmox Cloud VM API.

## 🚀 Quick Start (Docker)

1.  **Environment Setup**:
    ```bash
    cp .env.example .env
    ```
    *Edit `.env` and provide your Proxmox credentials (and optional OpenAI / Guacamole overrides).*

2.  **Run the Stack**:
    ```bash
    docker compose up --build
    ```
    *The API will be available at http://localhost:8000/docs*

3.  **Guacamole (Windows RDP in the browser)**:
    - Guacamole UI: [http://localhost:9080/guacamole/](http://localhost:9080/guacamole/) — default login `guacadmin` / `guacadmin` (change in production).
    - On a Windows 11 VM detail page, use **Desktop** to open an HTML5 RDP session (minted via `POST /vms/{job_id}/desktop-session`).
    - See [docker/guacamole/README.md](docker/guacamole/README.md) for schema, passwords, and networking.

## 💡 Troubleshooting "DB Errors"

- **Port Conflicts**: Ensure port `5432` isn't already used by a local Postgres on your machine.
- **Dependency Issues**: If you see `ModuleNotFoundError: No module named 'db'`, ensure you are using the latest `docker-compose.yml` which includes the `db/` package.
- **Database Connection**: The backend waits for the `postgres` healthy status. If it stalls, check the postgres logs with `docker compose logs postgres`.
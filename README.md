# PrivateCloud

Development setup for the Proxmox Cloud VM API.

## 🚀 Quick Start (Docker)

1.  **Environment Setup**:
    ```bash
    cp backend/.env.example .env
    ```
    *Edit `.env` and provide your Proxmox credentials.*

2.  **Run the Stack**:
    ```bash
    docker compose up --build
    ```
    *The API will be available at http://localhost:8000/docs*

## 💡 Troubleshooting "DB Errors"

- **Port Conflicts**: Ensure port `5432` isn't already used by a local Postgres on your machine.
- **Dependency Issues**: If you see `ModuleNotFoundError: No module named 'db'`, ensure you are using the latest `docker-compose.yml` which includes the `db/` package.
- **Database Connection**: The backend waits for the `postgres` healthy status. If it stalls, check the postgres logs with `docker compose logs postgres`.
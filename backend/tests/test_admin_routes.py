"""Tests for admin API endpoints (RED → GREEN TDD)."""

from unittest.mock import patch

import pytest


# ── GET /admin/stats ────────────────────────────────────────────────────────

class TestGetStats:
    def test_returns_stats_for_admin(self, client, admin_headers):
        mock_stats = {
            "total_users": 5,
            "total_admins": 1,
            "total_vms": 12,
            "active_vms": 8,
            "failed_vms": 2,
            "queued_vms": 1,
            "deleted_vms": 1,
            "total_audit_entries": 50,
            "vms_created_today": 3,
        }
        with patch("app.routes.admin_routes.database.get_admin_stats", return_value=mock_stats):
            resp = client.get("/admin/stats", headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_users"] == 5
        assert data["active_vms"] == 8
        assert data["vms_created_today"] == 3

    def test_rejects_regular_user(self, client, user_headers):
        resp = client.get("/admin/stats", headers=user_headers)
        assert resp.status_code == 403

    def test_rejects_unauthenticated(self, client):
        resp = client.get("/admin/stats")
        assert resp.status_code == 401


# ── GET /admin/users ────────────────────────────────────────────────────────

class TestListUsers:
    def test_returns_users_for_admin(self, client, admin_headers):
        mock_users = [
            {"id": 1, "username": "admin1", "role": "admin", "daily_quota": 10, "created_at": "2025-01-01T00:00:00+00:00"},
            {"id": 2, "username": "user1", "role": "user", "daily_quota": 3, "created_at": "2025-02-01T00:00:00+00:00"},
        ]
        with patch("app.routes.admin_routes.database.list_all_users", return_value=mock_users):
            resp = client.get("/admin/users", headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["username"] == "admin1"

    def test_rejects_regular_user(self, client, user_headers):
        resp = client.get("/admin/users", headers=user_headers)
        assert resp.status_code == 403


# ── GET /admin/vms ──────────────────────────────────────────────────────────

class TestListAllVMs:
    def test_returns_all_vms_for_admin(self, client, admin_headers):
        mock_jobs = [
            {
                "id": 1, "user_id": 2, "owner_username": "user1",
                "vmid": 100, "vm_name": "test-vm", "os_choice": "ubuntu-22.04",
                "status": "done", "request_payload": {}, "proxmox_response": None,
                "error_message": None, "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
            },
        ]
        with patch("app.routes.admin_routes.database.list_all_vm_jobs", return_value=mock_jobs):
            resp = client.get("/admin/vms", headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["owner_username"] == "user1"

    def test_rejects_regular_user(self, client, user_headers):
        resp = client.get("/admin/vms", headers=user_headers)
        assert resp.status_code == 403


# ── GET /admin/audit-logs ──────────────────────────────────────────────────

class TestListAuditLogs:
    def test_returns_logs_for_admin(self, client, admin_headers):
        mock_logs = [
            {
                "id": 1, "user_id": 1, "action": "vm.create",
                "target_type": "vm_job", "target_id": "1",
                "details": {"vmid": 100}, "created_at": "2025-01-01T00:00:00+00:00",
            },
        ]
        with patch("app.routes.admin_routes.database.list_audit_logs", return_value=mock_logs):
            resp = client.get("/admin/audit-logs", headers=admin_headers)

        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_rejects_regular_user(self, client, user_headers):
        resp = client.get("/admin/audit-logs", headers=user_headers)
        assert resp.status_code == 403


# ── PATCH /admin/users/{id}/role ────────────────────────────────────────────

class TestChangeUserRole:
    def test_updates_role(self, client, admin_headers):
        updated = {
            "id": 2, "username": "user1", "role": "admin",
            "daily_quota": 3, "created_at": "2025-01-01T00:00:00+00:00",
        }
        with (
            patch("app.routes.admin_routes.database.update_user_role", return_value=updated),
            patch("app.routes.admin_routes.database.add_audit_log"),
        ):
            resp = client.patch(
                "/admin/users/2/role",
                json={"role": "admin"},
                headers=admin_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_rejects_invalid_role(self, client, admin_headers):
        resp = client.patch(
            "/admin/users/2/role",
            json={"role": "superuser"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_returns_404_for_missing_user(self, client, admin_headers):
        with patch("app.routes.admin_routes.database.update_user_role", return_value=None):
            resp = client.patch(
                "/admin/users/999/role",
                json={"role": "admin"},
                headers=admin_headers,
            )
        assert resp.status_code == 404


# ── PATCH /admin/users/{id}/quota ───────────────────────────────────────────

class TestChangeUserQuota:
    def test_updates_quota(self, client, admin_headers):
        updated = {
            "id": 2, "username": "user1", "role": "user",
            "daily_quota": 10, "created_at": "2025-01-01T00:00:00+00:00",
        }
        with (
            patch("app.routes.admin_routes.database.update_user_quota", return_value=updated),
            patch("app.routes.admin_routes.database.add_audit_log"),
        ):
            resp = client.patch(
                "/admin/users/2/quota",
                json={"daily_quota": 10},
                headers=admin_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["daily_quota"] == 10

    def test_rejects_negative_quota(self, client, admin_headers):
        resp = client.patch(
            "/admin/users/2/quota",
            json={"daily_quota": -1},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_rejects_regular_user(self, client, user_headers):
        resp = client.patch(
            "/admin/users/2/quota",
            json={"daily_quota": 10},
            headers=user_headers,
        )
        assert resp.status_code == 403

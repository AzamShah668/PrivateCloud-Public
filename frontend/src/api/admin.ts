import { api } from "./client";
import type { UserResponse } from "./auth";

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface AdminStats {
  total_users: number;
  total_admins: number;
  total_vms: number;
  active_vms: number;
  failed_vms: number;
  queued_vms: number;
  deleted_vms: number;
  total_audit_entries: number;
  vms_created_today: number;
}

export interface VMJobAdmin {
  id: number;
  user_id: number;
  owner_username: string;
  vmid: number;
  vm_name: string;
  os_choice: string;
  status: string;
  request_payload: Record<string, unknown>;
  proxmox_response: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  user_id: number;
  action: string;
  target_type: string;
  target_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getAdminStats(): Promise<AdminStats> {
  return api.get("admin/stats").json<AdminStats>();
}

export async function listAllUsers(): Promise<UserResponse[]> {
  return api.get("admin/users").json<UserResponse[]>();
}

export async function listAllVMs(): Promise<VMJobAdmin[]> {
  return api.get("admin/vms").json<VMJobAdmin[]>();
}

export async function listAuditLogs(): Promise<AuditLog[]> {
  return api.get("admin/audit-logs").json<AuditLog[]>();
}

export async function updateUserRole(
  userId: number,
  role: string,
): Promise<UserResponse> {
  return api
    .patch(`admin/users/${userId}/role`, { json: { role } })
    .json<UserResponse>();
}

export async function updateUserQuota(
  userId: number,
  dailyQuota: number,
): Promise<UserResponse> {
  return api
    .patch(`admin/users/${userId}/quota`, { json: { daily_quota: dailyQuota } })
    .json<UserResponse>();
}

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

/** Extended user row with I3 soft-delete fields. */
export interface AdminUser {
  id: number;
  username: string;
  role: string;
  daily_quota: number;
  created_at: string;
  deleted_at: string | null;
  status: "active" | "suspended" | "deleted";
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
  vm_ip: string | null;
  vm_username: string | null;
  vm_password: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  user_id: number;
  action: string;
  action_type: string;
  target_type: string;
  target_id: string | null;
  target_user_id: number | null;
  actor_username: string | null;
  target_username: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export type SettingValueType = "string" | "integer" | "boolean" | "json";

export interface PlatformSetting {
  key: string;
  value: string;
  value_type: SettingValueType;
  typed_value: unknown;
  description: string | null;
  updated_at: string;
  updated_by: number | null;
  updated_by_username: string | null;
}

export interface AuditLogFilters {
  actionType?: string;
  targetUserId?: number;
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getAdminStats(): Promise<AdminStats> {
  return api.get("admin/stats").json<AdminStats>();
}

export async function listAllUsers(
  includeDeleted = false,
): Promise<AdminUser[]> {
  const searchParams = includeDeleted ? { include_deleted: "true" } : undefined;
  return api
    .get("admin/users", { searchParams })
    .json<AdminUser[]>();
}

export async function listAllVMs(verifyProxmox = false): Promise<VMJobAdmin[]> {
  const searchParams = verifyProxmox ? { verify_proxmox: "true" } : undefined;
  return api.get("admin/vms", { searchParams }).json<VMJobAdmin[]>();
}

export async function listAuditLogs(
  filters: AuditLogFilters = {},
): Promise<AuditLog[]> {
  const searchParams: Record<string, string> = {};
  if (filters.actionType) searchParams.action_type = filters.actionType;
  if (filters.targetUserId !== undefined)
    searchParams.target_user_id = String(filters.targetUserId);
  if (filters.limit !== undefined) searchParams.limit = String(filters.limit);
  if (filters.offset !== undefined) searchParams.offset = String(filters.offset);
  return api
    .get("admin/audit-logs", {
      searchParams: Object.keys(searchParams).length ? searchParams : undefined,
    })
    .json<AuditLog[]>();
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

// --- I3: User lifecycle actions ---------------------------------------------

export async function suspendUser(userId: number): Promise<AdminUser> {
  return api
    .post(`admin/users/${userId}/suspend`)
    .json<AdminUser>();
}

export async function deleteUser(userId: number): Promise<AdminUser> {
  return api
    .post(`admin/users/${userId}/delete`)
    .json<AdminUser>();
}

export async function reactivateUser(userId: number): Promise<AdminUser> {
  return api
    .post(`admin/users/${userId}/reactivate`)
    .json<AdminUser>();
}

// --- I3: Platform settings --------------------------------------------------

export async function listSettings(): Promise<PlatformSetting[]> {
  return api.get("admin/settings").json<PlatformSetting[]>();
}

export async function updateSetting(
  key: string,
  value: unknown,
): Promise<PlatformSetting> {
  return api
    .patch(`admin/settings/${encodeURIComponent(key)}`, { json: { value } })
    .json<PlatformSetting>();
}

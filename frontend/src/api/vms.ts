import { api } from "./client";

export interface VMJob {
  id: number;
  user_id: number;
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

export interface VMEnriched extends VMJob {
  live_status: string;
  cpu_usage: number | null;
  mem_usage: number | null;
  max_mem: number | null;
  uptime: number | null;
  netin: number | null;
  netout: number | null;
}

export interface CreateVMPayload {
  vm_name: string;
  os_choice: string;
  cpu_cores: number;
  ram_mb: number;
  storage_gb: number;
  node?: string;
  use_template?: boolean;
}

export interface UpdateVMPayload {
  action: "start" | "stop" | "restart" | "resize";
  cpu_cores?: number;
  ram_mb?: number;
}

export async function listVMs(): Promise<VMEnriched[]> {
  return api.get("vms/").json<VMEnriched[]>();
}

export async function getVM(jobId: number): Promise<VMEnriched> {
  return api.get(`vms/${jobId}`).json<VMEnriched>();
}

export async function createVM(payload: CreateVMPayload): Promise<VMJob> {
  return api.post("vms/", { json: payload }).json<VMJob>();
}

export async function updateVM(
  jobId: number,
  payload: UpdateVMPayload,
): Promise<VMJob> {
  return api.patch(`vms/${jobId}`, { json: payload }).json<VMJob>();
}

export async function deleteVM(jobId: number): Promise<VMJob> {
  return api.delete(`vms/${jobId}`).json<VMJob>();
}

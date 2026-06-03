import { api } from "@/api/client";

// First-run setup (Iteration 6). Mirrors backend/app/routes/setup_routes.py.

export interface SetupStatus {
  completed: boolean;
  proxmox_configured: boolean;
  missing_required: string[];
}

export interface SetupResult {
  ok: boolean;
  completed: boolean;
  proxmox_ok: boolean | null;
  error: string | null;
}

export async function getSetupStatus(): Promise<SetupStatus> {
  return api.get("setup/status").json<SetupStatus>();
}

export async function applySetup(
  settings: Record<string, unknown>,
  testConnection = true,
): Promise<SetupResult> {
  return api
    .post("setup", { json: { settings, test_connection: testConnection } })
    .json<SetupResult>();
}

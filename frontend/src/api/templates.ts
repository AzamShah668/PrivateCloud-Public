import { api } from "./client";

// ---------------------------------------------------------------------------
// Types — Clone-from-Template (Sprint 5)
// ---------------------------------------------------------------------------

export type CloneMode = "full" | "linked";
export type TemplateStatus = "draft" | "published" | "archived";

export interface VMTemplate {
  id: number;
  owner_id: number;
  name: string;
  description: string | null;
  source_vmid: number;
  os_choice: string;
  clone_mode: CloneMode;
  default_cpu: number;
  default_ram_mb: number;
  status: TemplateStatus;
  created_at: string;
  updated_at: string;
}

export interface ClassGroup {
  id: number;
  owner_id: number;
  name: string;
  description: string | null;
  created_at: string;
  student_count: number;
}

export interface ClassStudent {
  id: number;
  username: string;
  enrolled_at: string | null;
}

export interface ClassDetail extends ClassGroup {
  students: ClassStudent[];
}

export interface CloneJob {
  id: number;
  student_id: number;
  username: string | null;
  vm_job_id: number | null;
  status: "queued" | "cloning" | "done" | "failed";
  error_message: string | null;
  vm_name: string | null;
  vmid: number | null;
  vm_status: string | null;
  vm_ip: string | null;
  updated_at: string | null;
}

export interface CloneBatch {
  id: number;
  template_id: number;
  class_id: number;
  initiated_by: number;
  clone_mode: CloneMode;
  cpu_cores: number;
  ram_mb: number;
  total: number;
  status: "in_progress" | "completed" | "partial" | "failed";
  created_at: string;
  updated_at: string;
}

export interface BatchProgress extends CloneBatch {
  clones: CloneJob[];
}

// --- Request bodies ---------------------------------------------------------

export interface CreateTemplateBody {
  name: string;
  vm_job_id: number;
  description?: string;
  clone_mode?: CloneMode;
  default_cpu?: number;
  default_ram_mb?: number;
}

export interface UpdateTemplateBody {
  name?: string;
  description?: string;
  clone_mode?: CloneMode;
  default_cpu?: number;
  default_ram_mb?: number;
  status?: TemplateStatus;
}

export interface DistributeBody {
  class_id: number;
  cpu_cores?: number;
  ram_mb?: number;
  clone_mode?: CloneMode;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function listTemplates(includeArchived = false): Promise<VMTemplate[]> {
  const searchParams = includeArchived ? { include_archived: "true" } : undefined;
  return api.get("templates", { searchParams }).json<VMTemplate[]>();
}

export async function getTemplate(id: number): Promise<VMTemplate> {
  return api.get(`templates/${id}`).json<VMTemplate>();
}

export async function createTemplate(body: CreateTemplateBody): Promise<VMTemplate> {
  return api.post("templates", { json: body }).json<VMTemplate>();
}

export async function updateTemplate(id: number, body: UpdateTemplateBody): Promise<VMTemplate> {
  return api.patch(`templates/${id}`, { json: body }).json<VMTemplate>();
}

export async function distributeTemplate(id: number, body: DistributeBody): Promise<CloneBatch> {
  return api.post(`templates/${id}/distribute`, { json: body }).json<CloneBatch>();
}

export async function getBatchProgress(batchId: number): Promise<BatchProgress> {
  return api.get(`clone-batches/${batchId}`).json<BatchProgress>();
}

// --- Classes ---------------------------------------------------------------

export async function listClasses(): Promise<ClassGroup[]> {
  return api.get("classes").json<ClassGroup[]>();
}

export async function getClass(id: number): Promise<ClassDetail> {
  return api.get(`classes/${id}`).json<ClassDetail>();
}

export async function createClass(body: { name: string; description?: string }): Promise<ClassGroup> {
  return api.post("classes", { json: body }).json<ClassGroup>();
}

export async function enrollStudents(classId: number, studentIds: number[]): Promise<{ enrolled: number }> {
  return api
    .post(`classes/${classId}/students`, { json: { student_ids: studentIds } })
    .json<{ enrolled: number }>();
}

export async function unenrollStudent(classId: number, studentId: number): Promise<void> {
  await api.delete(`classes/${classId}/students/${studentId}`);
}

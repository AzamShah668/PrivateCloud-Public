import { z } from "zod";

export const createVMSchema = z.object({
  vm_name: z
    .string()
    .min(3, "Name must be at least 3 characters")
    .max(30, "Name must be at most 30 characters")
    .regex(
      /^[a-zA-Z0-9-]+$/,
      "Only letters, digits, and hyphens allowed",
    ),
  os_choice: z.enum([
    "ubuntu-22.04",
    "ubuntu-24.04",
    "debian-12",
    "centos-9",
    "windows-11",
  ]),
  cpu_cores: z.number().int().min(1).max(16),
  ram_mb: z.number().int().min(512).max(65536),
  storage_gb: z.number().int().min(10).max(500),
  node: z.string().default("pve"),
});

export type CreateVMValues = z.infer<typeof createVMSchema>;

export const updateVMSchema = z.object({
  action: z.enum(["start", "stop", "restart", "resize"]),
  cpu_cores: z.number().int().min(1).max(16).optional(),
  ram_mb: z.number().int().min(512).max(65536).optional(),
});

export type UpdateVMValues = z.infer<typeof updateVMSchema>;

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Rocket } from "lucide-react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import OSSelector from "./OSSelector";
import ResourceSliders from "./ResourceSliders";
import TemplateSelector from "./TemplateSelector";
import { createVMSchema, type CreateVMValues } from "@/schemas/vm.schema";
import { useCreateVM } from "@/hooks/use-vms";
import { useTemplates, useStudentTemplates, useDeployFromTemplate } from "@/hooks/use-templates";
import { useAuthStore } from "@/stores/auth-store";
import type { VMTemplate } from "@/api/templates";
import type { OSValue } from "@/lib/constants";

export default function CreateVMForm() {
  const navigate = useNavigate();
  const createMutation = useCreateVM();
  const deployMutation = useDeployFromTemplate();

  // Admin sees all published templates; students see their assigned templates.
  const isAdmin = useAuthStore((s) => s.user?.role === "admin");
  const adminTemplatesQuery = useTemplates(false, isAdmin);
  const studentTemplatesQuery = useStudentTemplates(!isAdmin);

  // Normalize student assignments into the VMTemplate shape so TemplateSelector works.
  const studentAssignments = studentTemplatesQuery.data ?? [];
  const templates: VMTemplate[] = isAdmin
    ? (adminTemplatesQuery.data ?? [])
    : studentAssignments.map((a) => ({
        id: a.template_id,
        owner_id: 0,
        name: a.template_name,
        description: a.description,
        source_vmid: 0,
        template_vmid: a.template_vmid,
        os_choice: a.os_choice,
        clone_mode: a.clone_mode,
        default_cpu: a.cpu_cores,
        default_ram_mb: a.ram_mb,
        status: a.template_status as VMTemplate["status"],
        created_at: a.assigned_at,
        updated_at: a.assigned_at,
      }));

  // When a template is selected the form deploys from it instead of the OS.
  const [templateId, setTemplateId] = useState<number | null>(null);

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<CreateVMValues>({
    resolver: zodResolver(createVMSchema),
    defaultValues: {
      vm_name: "",
      os_choice: "ubuntu-24.04",
      cpu_cores: 2,
      ram_mb: 2048,
      storage_gb: 20,
    },
  });

  const values = watch();
  const selectedTemplate = templates.find((t) => t.id === templateId) ?? null;
  const isSubmitting = createMutation.isPending || deployMutation.isPending;

  function formatRam(mb: number): string {
    return mb >= 1024
      ? `${(mb / 1024).toFixed(mb % 1024 === 0 ? 0 : 1)} GB`
      : `${mb} MB`;
  }

  async function onSubmit(data: CreateVMValues) {
    if (templateId !== null) {
      // Deploy from a published template — OS/storage come from the template.
      const job = await deployMutation.mutateAsync({
        id: templateId,
        body: {
          vm_name: data.vm_name,
          cpu_cores: data.cpu_cores,
          ram_mb: data.ram_mb,
        },
      });
      navigate(`/vms/${job.id}`);
      return;
    }
    const job = await createMutation.mutateAsync(data);
    navigate(`/vms/${job.id}`);
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8 max-w-3xl relative z-20">
      {/* VM Name */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <Input
          label="VM Name"
          placeholder="my-web-server"
          error={errors.vm_name?.message}
          {...register("vm_name")}
        />
      </motion.div>

      {/* OS Selection */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <Controller
          name="os_choice"
          control={control}
          render={({ field }) => (
            <OSSelector
              value={field.value as OSValue}
              onChange={(v) => {
                field.onChange(v);
                // Picking an OS leaves template-deploy mode.
                setTemplateId(null);
              }}
            />
          )}
        />
        {errors.os_choice && (
          <p className="text-xs text-accent-red mt-1">{errors.os_choice.message}</p>
        )}
      </motion.div>

      {/* Templates (admin or students with assigned templates) */}
      {templates.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <TemplateSelector
            templates={templates}
            selectedId={templateId}
            onSelect={setTemplateId}
          />
        </motion.div>
      )}

      {/* Resource Sliders */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <Controller
          name="cpu_cores"
          control={control}
          render={({ field: cpuField }) => (
            <Controller
              name="ram_mb"
              control={control}
              render={({ field: ramField }) => (
                <Controller
                  name="storage_gb"
                  control={control}
                  render={({ field: storageField }) => (
                    <ResourceSliders
                      cpuCores={cpuField.value}
                      ramMb={ramField.value}
                      storageGb={storageField.value}
                      onCpuChange={(v) => cpuField.onChange(v)}
                      onRamChange={(v) => ramField.onChange(v)}
                      onStorageChange={(v) => storageField.onChange(v)}
                    />
                  )}
                />
              )}
            />
          )}
        />
      </motion.div>

      {/* Bottom review bar */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="sticky bottom-0 -mx-8 px-8 py-4 bg-surface/80 backdrop-blur-sm border-t border-border-subtle"
      >
        <div className="flex items-center justify-between max-w-3xl">
          <div className="flex items-center gap-6 text-xs text-secondary font-mono">
            {selectedTemplate ? (
              <span className="text-accent-cyan">⬡ {selectedTemplate.name}</span>
            ) : (
              <span>{values.os_choice}</span>
            )}
            <span className="text-border-subtle">|</span>
            <span>{values.cpu_cores} vCPU</span>
            <span className="text-border-subtle">|</span>
            <span>{formatRam(values.ram_mb)}</span>
            {!selectedTemplate && (
              <>
                <span className="text-border-subtle">|</span>
                <span>{values.storage_gb} GB</span>
              </>
            )}
          </div>
          <Button type="submit" loading={isSubmitting}>
            <Rocket className="h-4 w-4" />
            Create Instance
          </Button>
        </div>
      </motion.div>
    </form>
  );
}

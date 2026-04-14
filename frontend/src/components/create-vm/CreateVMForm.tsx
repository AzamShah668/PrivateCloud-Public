import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Rocket, Info } from "lucide-react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import OSSelector from "./OSSelector";
import ResourceSliders from "./ResourceSliders";
import { createVMSchema, type CreateVMValues } from "@/schemas/vm.schema";
import { useCreateVM } from "@/hooks/use-vms";
import type { OSValue } from "@/lib/constants";

export default function CreateVMForm() {
  const navigate = useNavigate();
  const createMutation = useCreateVM();

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
      node: "pve",
      use_template: false,
    },
  });

  const values = watch();

  function formatRam(mb: number): string {
    return mb >= 1024
      ? `${(mb / 1024).toFixed(mb % 1024 === 0 ? 0 : 1)} GB`
      : `${mb} MB`;
  }

  async function onSubmit(data: CreateVMValues) {
    await createMutation.mutateAsync(data);
    navigate("/");
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8 max-w-3xl">
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
              onChange={(v) => field.onChange(v)}
            />
          )}
        />
        {errors.os_choice && (
          <p className="text-xs text-accent-red mt-1">{errors.os_choice.message}</p>
        )}
      </motion.div>

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

      {/* Template toggle */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <Controller
          name="use_template"
          control={control}
          render={({ field }) => (
            <label className="flex items-center gap-3 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-5 rounded-full bg-elevated border border-border-subtle transition-colors peer-checked:bg-accent-blue/20 peer-checked:border-accent-blue" />
                <div className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-muted transition-all peer-checked:translate-x-5 peer-checked:bg-accent-blue" />
              </div>
              <span className="text-sm text-secondary group-hover:text-primary transition-colors">
                Use cloud-init template (faster)
              </span>
              <span className="relative group/tip">
                <Info className="h-3.5 w-3.5 text-muted" />
                <span className="absolute left-6 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-[var(--radius-sm)] bg-elevated border border-border-subtle text-xs text-secondary whitespace-nowrap opacity-0 pointer-events-none group-hover/tip:opacity-100 transition-opacity z-10">
                  Clones a pre-configured template instead of installing from ISO
                </span>
              </span>
            </label>
          )}
        />
      </motion.div>

      {/* Bottom review bar */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="sticky bottom-0 -mx-8 px-8 py-4 bg-surface/80 backdrop-blur-sm border-t border-border-subtle"
      >
        <div className="flex items-center justify-between max-w-3xl">
          <div className="flex items-center gap-6 text-xs text-secondary font-mono">
            <span>{values.os_choice}</span>
            <span className="text-border-subtle">|</span>
            <span>{values.cpu_cores} vCPU</span>
            <span className="text-border-subtle">|</span>
            <span>{formatRam(values.ram_mb)}</span>
            <span className="text-border-subtle">|</span>
            <span>{values.storage_gb} GB</span>
            {values.use_template && (
              <>
                <span className="text-border-subtle">|</span>
                <span className="text-accent-cyan">template</span>
              </>
            )}
          </div>
          <Button type="submit" loading={createMutation.isPending}>
            <Rocket className="h-4 w-4" />
            Create VM
          </Button>
        </div>
      </motion.div>
    </form>
  );
}

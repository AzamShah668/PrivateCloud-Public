import { useState } from "react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import ResourceSliders from "@/components/create-vm/ResourceSliders";

interface ResizeModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (cpuCores: number, ramMb: number) => void;
  currentCpu: number;
  currentRam: number;
  isPending: boolean;
}

export default function ResizeModal({
  open,
  onClose,
  onConfirm,
  currentCpu,
  currentRam,
  isPending,
}: ResizeModalProps) {
  const [cpu, setCpu] = useState(currentCpu);
  const [ram, setRam] = useState(currentRam);

  const hasChanges = cpu !== currentCpu || ram !== currentRam;

  return (
    <Modal open={open} onClose={onClose} title="Resize VM">
      <div className="space-y-6">
        <p className="text-sm text-secondary">
          Adjust CPU and RAM allocation. The VM may need to be restarted for
          changes to take effect.
        </p>

        <ResourceSliders
          cpuCores={cpu}
          ramMb={ram}
          storageGb={0}
          onCpuChange={setCpu}
          onRamChange={setRam}
          onStorageChange={() => {}}
        />

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => onConfirm(cpu, ram)}
            disabled={!hasChanges || isPending}
            loading={isPending}
          >
            Apply Resize
          </Button>
        </div>
      </div>
    </Modal>
  );
}

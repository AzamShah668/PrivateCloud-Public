import { useState } from "react";
import Modal from "@/components/ui/Modal";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

interface DeleteConfirmProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  vmName: string;
  isPending: boolean;
}

export default function DeleteConfirm({
  open,
  onClose,
  onConfirm,
  vmName,
  isPending,
}: DeleteConfirmProps) {
  const [typed, setTyped] = useState("");
  const matches = typed === vmName;

  return (
    <Modal open={open} onClose={onClose} title="Delete Virtual Machine">
      <div className="space-y-4">
        <div className="rounded-[var(--radius-md)] bg-accent-red/5 border border-accent-red/20 p-4">
          <p className="text-sm text-accent-red font-medium mb-1">
            This action is irreversible
          </p>
          <p className="text-xs text-secondary">
            The VM and all associated data will be permanently destroyed. This
            cannot be undone.
          </p>
        </div>

        <p className="text-sm text-secondary">
          Type <span className="font-mono font-semibold text-primary">{vmName}</span> to
          confirm deletion:
        </p>

        <Input
          placeholder={vmName}
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          autoFocus
        />

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={onConfirm}
            disabled={!matches || isPending}
            loading={isPending}
          >
            Permanently Delete
          </Button>
        </div>
      </div>
    </Modal>
  );
}

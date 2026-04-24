import { Play, Square, RotateCw, Scaling, Trash2, TerminalSquare } from "lucide-react";
import Button from "@/components/ui/Button";

interface ActionBarProps {
  liveStatus: string;
  vmIP?: string | null;
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
  onResize: () => void;
  onConsole: () => void;
  onDelete: () => void;
  isPending: boolean;
}

export default function ActionBar({
  liveStatus,
  vmIP,
  onStart,
  onStop,
  onRestart,
  onResize,
  onConsole,
  onDelete,
  isPending,
}: ActionBarProps) {
  const isRunning = liveStatus === "running";
  const isStopped = liveStatus === "stopped";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant="secondary"
        size="sm"
        onClick={onStart}
        disabled={isRunning || isPending}
        loading={isPending}
      >
        <Play className="h-3.5 w-3.5" />
        Start
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={onStop}
        disabled={isStopped || isPending}
        loading={isPending}
      >
        <Square className="h-3.5 w-3.5" />
        Stop
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={onRestart}
        disabled={isStopped || isPending}
        loading={isPending}
      >
        <RotateCw className="h-3.5 w-3.5" />
        Restart
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={onConsole}
        disabled={!isRunning || !vmIP || isPending}
        title={!vmIP ? "IP not yet available" : !isRunning ? "VM must be running" : "Open web console"}
      >
        <TerminalSquare className="h-3.5 w-3.5" />
        Console
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={onResize}
        disabled={isPending}
      >
        <Scaling className="h-3.5 w-3.5" />
        Resize
      </Button>

      <div className="flex-1" />

      <Button
        variant="danger"
        size="sm"
        onClick={onDelete}
        disabled={isPending}
      >
        <Trash2 className="h-3.5 w-3.5" />
        Delete
      </Button>
    </div>
  );
}

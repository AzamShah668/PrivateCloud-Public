import Badge from "@/components/ui/Badge";

interface StatusBadgeProps {
  status: string;
  liveStatus?: string;
}

export default function StatusBadge({ status, liveStatus }: StatusBadgeProps) {
  // Show live Proxmox status if available, otherwise use job status
  const displayStatus = liveStatus && liveStatus !== "unknown" ? liveStatus : status;
  return <Badge status={displayStatus} />;
}

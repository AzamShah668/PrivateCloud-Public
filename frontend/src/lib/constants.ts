export const OS_OPTIONS = [
  { value: "ubuntu-22.04", label: "Ubuntu 22.04", icon: "ubuntu" },
  { value: "ubuntu-24.04", label: "Ubuntu 24.04", icon: "ubuntu" },
  { value: "debian-12", label: "Debian 12", icon: "debian" },
  { value: "centos-9", label: "CentOS 9", icon: "centos" },
  { value: "windows-11", label: "Windows 11", icon: "windows" },
] as const;

export type OSValue = (typeof OS_OPTIONS)[number]["value"];

export const STATUS_COLORS: Record<string, string> = {
  running: "var(--color-accent-cyan)",
  stopped: "var(--color-muted)",
  paused: "var(--color-accent-amber)",
  queued: "var(--color-accent-amber)",
  done: "var(--color-accent-green)",
  failed: "var(--color-accent-red)",
  deleted: "var(--color-muted)",
  unknown: "var(--color-muted)",
};

export const API_BASE =
  import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

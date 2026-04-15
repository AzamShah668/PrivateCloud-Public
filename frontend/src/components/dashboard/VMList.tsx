import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { Cloud, PlusCircle } from "lucide-react";
import VMCard from "./VMCard";

import Button from "@/components/ui/Button";
import Skeleton from "@/components/ui/Skeleton";
import type { VMEnriched } from "@/api/vms";

interface VMListProps {
  vms: VMEnriched[] | undefined;
  isLoading: boolean;
}

export default function VMList({ vms, isLoading }: VMListProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-[180px]" />
        ))}
      </div>
    );
  }

  if (!vms || vms.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="flex flex-col items-center justify-center py-20 text-center"
      >
        <div
          className="h-20 w-20 rounded-full flex items-center justify-center mb-6"
          style={{
            background: "linear-gradient(135deg, rgba(10,239,255,0.05), rgba(59,130,246,0.03))",
            border: "1px solid rgba(10,239,255,0.1)",
          }}
        >
          <Cloud className="h-10 w-10 text-accent-cyan/40" />
        </div>
        <h2
          className="text-xl font-bold text-primary mb-2"
          style={{ fontFamily: "var(--font-display)" }}
        >
          No instances deployed
        </h2>
        <p className="text-sm text-secondary mb-6 max-w-sm">
          Deploy your first compute instance to start building your private cloud infrastructure.
        </p>
        <Link to="/vms/create">
          <Button size="lg">
            <PlusCircle className="h-4 w-4" />
            Deploy first instance
          </Button>
        </Link>
      </motion.div>
    );
  }

  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-4">
      {vms
        .filter((vm) => vm.status !== "deleted")
        .map((vm, i) => (
          <VMCard key={vm.id} vm={vm} index={i} />
        ))}
    </div>
  );
}

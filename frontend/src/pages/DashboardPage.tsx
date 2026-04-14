import { Link } from "react-router-dom";
import { PlusCircle } from "lucide-react";
import Header from "@/components/layout/Header";
import QuotaIndicator from "@/components/dashboard/QuotaIndicator";
import VMList from "@/components/dashboard/VMList";
import Button from "@/components/ui/Button";
import { useVMs } from "@/hooks/use-vms";

export default function DashboardPage() {
  const { data: vms, isLoading } = useVMs();

  const todayCount =
    vms?.filter((vm) => {
      const created = new Date(vm.created_at);
      const now = new Date();
      return (
        created.getFullYear() === now.getFullYear() &&
        created.getMonth() === now.getMonth() &&
        created.getDate() === now.getDate()
      );
    }).length ?? 0;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Your Virtual Machines"
        subtitle="Monitor and manage your cloud infrastructure"
        actions={
          <div className="flex items-center gap-4">
            <QuotaIndicator usedToday={todayCount} />
            <Link to="/vms/create">
              <Button>
                <PlusCircle className="h-4 w-4" />
                New VM
              </Button>
            </Link>
          </div>
        }
      />
      <main className="flex-1 overflow-y-auto p-8">
        <VMList vms={vms} isLoading={isLoading} />
      </main>
    </div>
  );
}

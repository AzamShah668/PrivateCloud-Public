import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import Header from "@/components/layout/Header";
import Button from "@/components/ui/Button";
import CreateVMForm from "@/components/create-vm/CreateVMForm";

export default function CreateVMPage() {
  return (
    <div className="flex flex-col h-full">
      <Header
        title="Deploy Compute Instance"
        subtitle="Configure and deploy a new instance to your cluster"
        actions={
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          </Link>
        }
      />
      <main className="flex-1 overflow-y-auto p-6">
        <CreateVMForm />
      </main>
    </div>
  );
}

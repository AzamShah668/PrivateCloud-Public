import AIChatOps from "@/components/dashboard/AIChatOps";
import { motion } from "motion/react";

export default function ChatOpsPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-80px)] max-w-5xl mx-auto w-full p-4 md:p-8">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h1 className="text-2xl font-bold tracking-wider text-primary uppercase" style={{ fontFamily: "var(--font-display)" }}>
          Cognitive Engine <span className="text-accent-cyan">Console</span>
        </h1>
        <p className="text-sm text-secondary mt-1" style={{ fontFamily: "var(--font-body)" }}>
          Direct interface to the Azna-Cloud orchestration AI. Issue natural language commands to deploy, manage, and monitor infrastructure.
        </p>
      </motion.div>
      <div className="flex-1 overflow-hidden min-h-0">
        <AIChatOps fullHeight={true} />
      </div>
    </div>
  );
}

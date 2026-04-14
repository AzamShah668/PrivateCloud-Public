import { Outlet } from "react-router-dom";
import { motion } from "motion/react";
import Sidebar from "./Sidebar";

export default function AppShell() {
  return (
    <div className="flex h-dvh bg-deepest overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          className="flex-1"
        >
          <Outlet />
        </motion.div>
      </main>
    </div>
  );
}

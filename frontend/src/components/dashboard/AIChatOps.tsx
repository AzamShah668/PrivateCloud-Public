// =============================================================================
// frontend/src/components/dashboard/AIChatOps.tsx
// =============================================================================

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Terminal, Cpu, Send, Circle } from "lucide-react";
import { api } from "@/api/client";
import { useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";

interface Message {
  sender: "user" | "system";
  text: string;
  toolCalled?: string | null;
  status?: string;
}

const STORAGE_KEY = "azna-chatops-messages";
const DEFAULT_MSG: Message = {
  sender: "system",
  text: "AZNA-CLOUD COGNITIVE ENGINE SECURE CONSOLE READY. DISPATCH PROXMOX PROVISIONING OR lifecycle INSTRUCTIONS.",
  status: "ready"
};

function loadMessages(): Message[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Message[];
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch { /* ignore corrupt data */ }
  return [DEFAULT_MSG];
}

interface AIChatOpsProps {
  fullHeight?: boolean;
}

export default function AIChatOps({ fullHeight = false }: AIChatOpsProps = {}) {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>(loadMessages);
  const [isPending, setIsPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Persist messages to sessionStorage on every change
  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isPending) return;

    const userPrompt = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { sender: "user", text: userPrompt }]);
    setIsPending(true);

    try {
      const response = await api
        .post("ai/chat", { json: { prompt: userPrompt } })
        .json<{ response: string; tool_called: string | null; execution_status: string }>();

      setMessages((prev) => [
        ...prev,
        {
          sender: "system",
          text: response.response,
          toolCalled: response.tool_called,
          status: response.execution_status
        }
      ]);

      // If infrastructure state mappings mutated, instantly synchronize background tables
      if (response.tool_called) {
        queryClient.invalidateQueries({ queryKey: ["vms"] });
        queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "system",
          text: "CRITICAL FAILURE PATH: TRANSACTION ENGINE WAS UNABLE TO PARSE RUNTIME MATRICES.",
          status: "failed"
        }
      ]);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={`glass-panel rounded-xl flex flex-col overflow-hidden border border-border-subtle relative group ${
        fullHeight ? "h-full min-h-[600px]" : "h-[460px]"
      }`}
    >
      {/* Brutalist terminal status row top border matrix line */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-accent-cyan/40 to-transparent" />
      
      {/* Interactive header metadata dashboard */}
      <div className="px-4 py-3 border-b border-border-subtle bg-surface/80 flex items-center justify-between shrink-0 font-mono">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-accent-cyan drop-shadow-[0_0_6px_#0AEFFF]" />
          <span className="text-xs font-bold uppercase tracking-widest text-primary">Core Agent ChatOps</span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-muted uppercase">
          <Circle className={`h-2 w-2 fill-current ${isPending ? "text-accent-amber animate-pulse" : "text-accent-cyan"}`} />
          <span>SYS_NODE: OPENAI_API</span>
        </div>
      </div>

      {/* Terminal lines execution space */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs bg-[#030712]/90 grid-bg-dense"
      >
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: msg.sender === "user" ? 10 : -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className={`flex flex-col max-w-[85%] ${msg.sender === "user" ? "ml-auto items-end" : "mr-auto items-start"}`}
            >
              <div
                className={`p-3 rounded-lg border leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-border-subtle/30 border-border-subtle text-primary"
                    : "bg-surface/90 border-accent-cyan/10 text-accent-cyan shadow-[inset_0_0_12px_rgba(10,239,255,0.02)]"
                }`}
              >
                {msg.sender === "system" && (
                  <span className="text-accent-blue font-bold mr-1.5">&gt;&gt;</span>
                )}
                {msg.text}

                {msg.toolCalled && (
                  <div className="mt-2 pt-2 border-t border-accent-cyan/10 flex items-center gap-1.5 text-[10px] text-accent-teal uppercase tracking-wider font-bold">
                    <Cpu className="h-3 w-3" />
                    <span>Dispatched Pipeline Matrix: {msg.toolCalled}</span>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {isPending && (
          <div className="flex items-center gap-2 text-muted italic animate-pulse">
            <span>&gt;&gt; EVALUATING TEXT MATRIX RUNTIME ENGINES...</span>
          </div>
        )}
      </div>

      {/* Terminal prompt command entry baseline layout */}
      <form 
        onSubmit={handleSendMessage}
        className="p-3 border-t border-border-subtle bg-surface/50 flex items-center gap-2 shrink-0 font-mono"
      >
        <span className="text-accent-cyan font-bold pl-1">&gt;</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Deploy Ubuntu Server named web-prod with 4 cores, 4GB RAM..."
          disabled={isPending}
          className="flex-1 bg-transparent text-xs text-primary placeholder:text-muted outline-none border-0 focus:ring-0"
        />
        <Button 
          type="submit" 
          disabled={!input.trim() || isPending}
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0 rounded-md hover:bg-accent-cyan/10 hover:text-accent-cyan border border-transparent hover:border-accent-cyan/20 cursor-pointer"
        >
          <Send className="h-3.5 w-3.5" />
        </Button>
      </form>
    </motion.div>
  );
}
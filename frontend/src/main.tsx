import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: "rgba(10, 22, 40, 0.95)",
            backdropFilter: "blur(16px)",
            border: "1px solid rgba(10,239,255,0.1)",
            color: "var(--color-primary)",
            fontFamily: "var(--font-body)",
            boxShadow: "0 8px 24px rgba(0,0,0,0.4), 0 0 20px rgba(10,239,255,0.03)",
          },
        }}
      />
    </QueryClientProvider>
  </StrictMode>,
);

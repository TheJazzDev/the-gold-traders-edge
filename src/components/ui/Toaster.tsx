"use client";

import { useEffect, useState } from "react";
import { X, CheckCircle, AlertTriangle, Info, Bell } from "lucide-react";
import { cn } from "@/lib/utils";

interface Toast {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message?: string;
  duration?: number;
}

let toastId = 0;
const listeners: Set<(toast: Toast) => void> = new Set();

export function toast(toast: Omit<Toast, "id">) {
  const newToast = { ...toast, id: `toast-${++toastId}` };
  listeners.forEach((listener) => listener(newToast));
}

export function Toaster() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const listener = (toast: Toast) => {
      setToasts((prev) => [...prev, toast]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toast.id));
      }, toast.duration || 5000);
    };

    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const icons = {
    success: CheckCircle,
    error: AlertTriangle,
    warning: Bell,
    info: Info,
  };

  const colors = {
    success: "border-profit/30 bg-profit/10",
    error: "border-loss/30 bg-loss/10",
    warning: "border-pending/30 bg-pending/10",
    info: "border-blue-500/30 bg-blue-500/10",
  };

  const iconColors = {
    success: "text-profit",
    error: "text-loss",
    warning: "text-pending",
    info: "text-blue-400",
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((toast) => {
        const Icon = icons[toast.type];
        return (
          <div
            key={toast.id}
            className={cn(
              "flex items-start gap-3 p-4 rounded-xl border backdrop-blur-xl animate-slide-up",
              colors[toast.type]
            )}
          >
            <Icon className={cn("w-5 h-5 shrink-0", iconColors[toast.type])} />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-white">{toast.title}</p>
              {toast.message && (
                <p className="text-sm text-secondary-300 mt-1">{toast.message}</p>
              )}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="p-1 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4 text-secondary-400" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from "react";
import { cn } from "@/utils/cn";
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from "lucide-react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  toast: (t: Omit<Toast, "id">) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

function useToastContext() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

let _counter = 0;

const CONFIG: Record<ToastType, { icon: ReactNode; accent: string; bg: string; border: string }> = {
  success: {
    icon: <CheckCircle size={16} className="text-emerald-500" />,
    accent: "bg-emerald-500",
    bg: "bg-white",
    border: "border-gray-100",
  },
  error: {
    icon: <AlertCircle size={16} className="text-red-500" />,
    accent: "bg-red-500",
    bg: "bg-white",
    border: "border-red-100",
  },
  warning: {
    icon: <AlertTriangle size={16} className="text-amber-500" />,
    accent: "bg-amber-500",
    bg: "bg-white",
    border: "border-amber-100",
  },
  info: {
    icon: <Info size={16} className="text-blue-500" />,
    accent: "bg-blue-500",
    bg: "bg-white",
    border: "border-blue-100",
  },
};

function ToastItem({ t, onDismiss }: { t: Toast; onDismiss: (id: string) => void }) {
  const cfg = CONFIG[t.type];
  return (
    <div
      role="alert"
      aria-live="assertive"
      className={cn(
        "animate-slide-in-right relative flex items-start gap-3 rounded-2xl border shadow-lg shadow-black/5 overflow-hidden",
        cfg.bg, cfg.border,
      )}
    >
      {/* Left accent bar */}
      <div className={cn("absolute left-0 top-0 bottom-0 w-1 rounded-l-2xl", cfg.accent)} />

      <div className="flex items-start gap-3 pl-5 pr-4 py-3.5 min-w-0 flex-1">
        <span className="mt-0.5 shrink-0">{cfg.icon}</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-gray-900 leading-tight">{t.title}</p>
          {t.message && (
            <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{t.message}</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDismiss(t.id)}
          className="shrink-0 mt-0.5 text-gray-300 hover:text-gray-600 transition-colors"
          aria-label="Dismiss"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const toast = useCallback(
    (t: Omit<Toast, "id">) => {
      const id = `toast-${++_counter}`;
      const duration = t.duration ?? 4000;
      setToasts((prev) => [...prev, { ...t, id }]);
      timers.current.set(id, setTimeout(() => dismiss(id), duration));
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ toasts, toast, dismiss }}>
      {children}
      <div
        className="fixed bottom-5 right-5 z-[100] flex flex-col-reverse gap-2.5 w-[340px]"
        aria-label="Notifications"
      >
        {toasts.map((t) => (
          <ToastItem key={t.id} t={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useToastContext();
}

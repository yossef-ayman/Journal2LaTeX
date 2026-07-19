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

const icons: Record<ToastType, ReactNode> = {
  success: <CheckCircle size={16} className="text-emerald-500" />,
  error: <AlertCircle size={16} className="text-destructive" />,
  warning: <AlertTriangle size={16} className="text-amber-500" />,
  info: <Info size={16} className="text-primary" />,
};

const borderColors: Record<ToastType, string> = {
  success: "border-l-emerald-500",
  error: "border-l-destructive",
  warning: "border-l-amber-500",
  info: "border-l-primary",
};

function ToastItem({ t, onDismiss }: { t: Toast; onDismiss: (id: string) => void }) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className={cn(
        "animate-slide-in-right flex items-start gap-3 rounded-lg border bg-card px-4 py-3 shadow-lg border-l-4",
        borderColors[t.type],
      )}
    >
      <span className="mt-0.5 shrink-0">{icons[t.type]}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">{t.title}</p>
        {t.message && <p className="text-xs text-muted-foreground">{t.message}</p>}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(t.id)}
        className="shrink-0 text-muted-foreground hover:text-foreground"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
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
        className="fixed bottom-4 right-4 z-[100] flex flex-col-reverse gap-2 w-80"
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

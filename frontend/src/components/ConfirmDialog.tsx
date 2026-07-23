import { cn } from "@/utils/cn";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLabel?: string;
  className?: string;
}

export function ConfirmDialog({
  open,
  title,
  message,
  onConfirm,
  onCancel,
  confirmLabel = "Delete",
  className,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/40 backdrop-blur-xs" onClick={onCancel} />
      <div
        className={cn(
          "relative z-50 mx-4 w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-lg space-y-4 animate-scale-in",
          className,
        )}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600">
            <AlertTriangle size={20} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-zinc-900">{title}</h2>
            <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">{message}</p>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2 border-t border-zinc-100">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onCancel}
            className="text-xs h-8"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={onConfirm}
            className="text-xs h-8"
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

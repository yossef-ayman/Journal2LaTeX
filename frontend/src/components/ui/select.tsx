import * as React from "react";
import { cn } from "@/utils/cn";
import { Check, ChevronDown } from "lucide-react";

interface SelectContextValue {
  value: string;
  onValueChange: (value: string) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
}

const SelectContext = React.createContext<SelectContextValue | null>(null);

function useSelectContext() {
  const ctx = React.useContext(SelectContext);
  if (!ctx) throw new Error("Select components must be wrapped in <Select>");
  return ctx;
}

interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
}

function Select({ value, onValueChange, children }: SelectProps) {
  const [open, setOpen] = React.useState(false);
  return (
    <SelectContext.Provider value={{ value, onValueChange, open, setOpen }}>
      <div className="relative">{children}</div>
    </SelectContext.Provider>
  );
}

const SelectTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, children, ...props }, ref) => {
  const { open, setOpen } = useSelectContext();
  return (
    <button
      ref={ref}
      type="button"
      onClick={() => setOpen(!open)}
      className={cn(
        "flex h-9 w-full items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1 focus:border-emerald-400 disabled:cursor-not-allowed disabled:opacity-50 hover:border-gray-300",
        open && "ring-2 ring-emerald-500 border-emerald-400",
        className,
      )}
      {...props}
    >
      {children}
      <ChevronDown
        className={cn("h-4 w-4 text-gray-400 transition-transform duration-200 shrink-0", open && "rotate-180")}
      />
    </button>
  );
});
SelectTrigger.displayName = "SelectTrigger";

const SelectValue = React.forwardRef<
  HTMLSpanElement,
  React.HTMLAttributes<HTMLSpanElement>
>(({ className, ...props }, ref) => (
  <span ref={ref} className={cn("text-sm truncate", className)} {...props} />
));
SelectValue.displayName = "SelectValue";

interface SelectContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

function SelectContent({ className, children }: SelectContentProps) {
  const { open, setOpen } = useSelectContext();
  if (!open) return null;
  return (
    <>
      <div
        className="fixed inset-0 z-40"
        onClick={() => setOpen(false)}
      />
      <div
        className={cn(
          "absolute z-50 top-full mt-1.5 max-h-60 w-full overflow-auto rounded-xl border border-gray-100 bg-white text-gray-900 shadow-lg shadow-black/10 animate-scale-in py-1",
          className,
        )}
      >
        {children}
      </div>
    </>
  );
}

interface SelectItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

const SelectItem = React.forwardRef<HTMLDivElement, SelectItemProps>(
  ({ className, value, children, ...props }, ref) => {
    const { value: selected, onValueChange, setOpen } = useSelectContext();
    const isSelected = selected === value;
    return (
      <div
        ref={ref}
        onClick={() => {
          onValueChange(value);
          setOpen(false);
        }}
        className={cn(
          "relative flex cursor-pointer select-none items-center px-3 py-2 text-sm outline-none transition-colors hover:bg-emerald-50 hover:text-emerald-700 rounded-lg mx-1",
          isSelected && "bg-emerald-50 text-emerald-700 font-medium",
          className,
        )}
        {...props}
      >
        <span className="flex-1">{children}</span>
        {isSelected && <Check className="ml-2 h-3.5 w-3.5 text-emerald-600" />}
      </div>
    );
  },
);
SelectItem.displayName = "SelectItem";

export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem };

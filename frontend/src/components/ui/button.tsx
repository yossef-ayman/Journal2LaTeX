import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/utils/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.97] [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-current cursor-pointer select-none",
  {
    variants: {
      variant: {
        default:
          "bg-emerald-600 text-white shadow-sm hover:bg-emerald-700 hover:shadow-md hover:-translate-y-[1px] disabled:bg-emerald-200 disabled:text-emerald-400 disabled:shadow-none",
        destructive:
          "bg-red-600 text-white shadow-sm hover:bg-red-700 hover:-translate-y-[1px] disabled:bg-red-200 disabled:text-red-400",
        outline:
          "border border-emerald-300 bg-white text-emerald-700 shadow-sm hover:bg-emerald-50 hover:border-emerald-400 hover:-translate-y-[1px] disabled:bg-zinc-50 disabled:text-zinc-400 disabled:border-zinc-200",
        secondary:
          "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 hover:border-emerald-300 hover:-translate-y-[1px] disabled:bg-zinc-50 disabled:text-zinc-400",
        ghost:
          "bg-transparent text-zinc-600 hover:bg-emerald-50 hover:text-emerald-700 disabled:text-zinc-400",
        "ghost-destructive":
          "bg-transparent text-zinc-500 hover:bg-red-50 hover:text-red-600 disabled:text-zinc-400",
        link:
          "bg-transparent text-emerald-700 underline-offset-4 hover:underline hover:text-emerald-800",
        "zinc":
          "bg-zinc-900 text-white shadow-sm hover:bg-zinc-800 hover:-translate-y-[1px] disabled:bg-zinc-200 disabled:text-zinc-400",
      },
      size: {
        default: "h-9 px-4 py-2 text-sm",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-11 rounded-xl px-6 text-sm font-semibold",
        xl: "h-12 rounded-xl px-8 text-base font-semibold",
        icon: "h-9 w-9",
        "icon-sm": "h-7 w-7",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };

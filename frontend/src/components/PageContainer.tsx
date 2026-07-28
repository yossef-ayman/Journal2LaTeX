import type { ReactNode } from "react";
import { cn } from "@/utils/cn";

interface PageContainerProps {
  children: ReactNode;
  className?: string;
}

export function PageContainer({ children, className }: PageContainerProps) {
  return (
    <div className={cn("mx-auto max-w-5xl space-y-8 px-6 py-8 md:px-8 md:py-10", className)}>
      {children}
    </div>
  );
}

import { useAppStore } from "@/store/useAppStore";
import { useLocation } from "react-router-dom";
import { Menu, Leaf } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/utils/cn";

const PAGE_LABELS: Record<string, string> = {
  "/": "Dashboard",
  "/upload": "Upload Document",
  "/history": "Conversion History",
  "/document-generator": "Document Generator",
  "/settings": "Settings",
  "/about": "About",
};

export function Header() {
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const isMobile = useIsMobile();
  const location = useLocation();

  const pageLabel = (() => {
    if (location.pathname.startsWith("/processing/")) return "Processing";
    if (location.pathname.startsWith("/result/")) return "Results";
    return PAGE_LABELS[location.pathname] ?? "Journal2LaTeX";
  })();

  return (
    <header className="flex h-16 items-center gap-3 border-b border-gray-100 bg-white/90 backdrop-blur-md px-4 md:px-6 shrink-0 sticky top-0 z-30">
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleSidebar}
        aria-label="Toggle sidebar"
        className="shrink-0 h-8 w-8 text-gray-500 hover:text-gray-900"
      >
        <Menu size={17} />
      </Button>

      {isMobile && (
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 text-white shadow-sm">
            <Leaf size={14} strokeWidth={2.5} />
          </div>
          <span className="text-sm font-bold text-gray-900 tracking-tight">J2L</span>
        </div>
      )}

      {/* Page context breadcrumb */}
      <div className={cn("flex items-center gap-2", isMobile ? "hidden" : "flex")}>
        <span className="text-sm text-gray-400">/</span>
        <span className="text-sm font-semibold text-gray-900">{pageLabel}</span>
      </div>

      <div className="flex-1" />

      {/* System status */}
      <div className="flex items-center gap-2.5 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1.5">
        <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-500 status-dot-pulse" />
        <span className="text-[11px] font-medium text-emerald-700 hidden sm:block">System Ready</span>
      </div>
    </header>
  );
}

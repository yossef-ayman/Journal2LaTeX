import { useAppStore } from "@/store/useAppStore";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useIsMobile } from "@/hooks/use-mobile";

export function Header() {
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const isMobile = useIsMobile();

  return (
    <header className="flex h-14 items-center gap-3 border-b border-zinc-200 bg-white px-4">
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleSidebar}
        aria-label="Toggle sidebar"
        className="shrink-0 h-8 w-8 text-zinc-600 hover:text-zinc-900"
      >
        <Menu size={16} />
      </Button>

      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-zinc-900 text-white font-bold text-[10px] md:hidden">
          J2L
        </div>
        <div className="flex flex-col">
          <h1 className="text-xs font-semibold leading-tight text-zinc-900 tracking-tight">
            Journal2LaTeX
          </h1>
        </div>
      </div>

      <div className="flex-1" />

      {!isMobile && (
        <div className="flex items-center gap-2 rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs text-zinc-600">
          <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span className="text-[11px] font-medium text-zinc-600">System Ready</span>
        </div>
      )}
    </header>
  );
}

import { NavLink } from "react-router-dom";
import { cn } from "@/utils/cn";
import { useAppStore } from "@/store/useAppStore";
import { Separator } from "@/components/ui/separator";
import {
  LayoutDashboard,
  Upload,
  History,
  Settings,
  Info,
} from "lucide-react";

const navItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Upload", href: "/upload", icon: Upload },
  { label: "History", href: "/history", icon: History },
  { label: "Settings", href: "/settings", icon: Settings },
  { label: "About", href: "/about", icon: Info },
];

export function Sidebar() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-zinc-200 bg-white transition-all duration-200 ease-in-out",
        sidebarOpen ? "w-56" : "w-0 overflow-hidden md:w-14",
      )}
      aria-label="Main navigation"
    >
      <div
        className={cn(
          "flex h-14 items-center gap-2.5 border-b border-zinc-200 px-4",
          !sidebarOpen && "md:justify-center md:px-0",
        )}
      >
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-white font-bold text-xs shadow-xs">
          J2L
        </div>
        <span
          className={cn(
            "text-xs font-bold tracking-wider uppercase text-zinc-900 transition-opacity",
            !sidebarOpen && "md:hidden",
          )}
        >
          Journal2LaTeX
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-2" role="navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            end={item.href === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                isActive
                  ? "bg-zinc-100 text-zinc-900 font-semibold"
                  : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900",
                !sidebarOpen && "md:justify-center md:px-0",
              )
            }
            aria-label={item.label}
          >
            <item.icon size={16} className="shrink-0" aria-hidden="true" />
            <span
              className={cn(
                "transition-opacity",
                !sidebarOpen && "md:hidden",
              )}
            >
              {item.label}
            </span>
          </NavLink>
        ))}
      </nav>

      <div className="p-2">
        <Separator className="mb-2 bg-zinc-200" />
        <div
          className={cn(
            "flex items-center justify-between rounded-md px-2.5 py-1 text-[11px] text-zinc-400 font-mono",
            !sidebarOpen && "md:justify-center md:px-0",
          )}
        >
          <span className={cn(!sidebarOpen && "md:hidden")}>
            v1.0.0
          </span>
        </div>
      </div>
    </aside>
  );
}

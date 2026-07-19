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
  FileText,
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
        "flex flex-col border-r bg-card transition-all duration-300",
        sidebarOpen ? "w-60" : "w-0 overflow-hidden md:w-16",
      )}
      aria-label="Main navigation"
    >
      <div
        className={cn(
          "flex h-14 items-center gap-3 border-b px-4",
          !sidebarOpen && "md:justify-center md:px-0",
        )}
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary">
          <FileText size={16} className="text-primary-foreground" />
        </div>
        <span
          className={cn(
            "text-sm font-semibold text-foreground transition-opacity",
            !sidebarOpen && "md:hidden",
          )}
        >
          Journal2LaTeX
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-3" role="navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            end={item.href === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                !sidebarOpen && "md:justify-center md:px-2",
              )
            }
            aria-label={item.label}
          >
            <item.icon size={18} className="shrink-0" aria-hidden="true" />
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

      <div className="p-3">
        <Separator className="mb-3" />
        <div
          className={cn(
            "flex items-center gap-3 rounded-md px-3 py-2 text-xs text-muted-foreground",
            !sidebarOpen && "md:justify-center md:px-2",
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

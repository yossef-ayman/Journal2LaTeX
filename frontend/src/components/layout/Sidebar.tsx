import { NavLink } from "react-router-dom";
import { cn } from "@/utils/cn";
import { useAppStore } from "@/store/useAppStore";
import {
  LayoutDashboard,
  Upload,
  History,
  FileArchive,
  FileSignature,
  Settings,
  Info,
  Leaf,
} from "lucide-react";

const navItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Upload", href: "/upload", icon: Upload },
  { label: "History", href: "/history", icon: History },
  { label: "Templates", href: "/templates", icon: FileArchive },
  { label: "Document Generator", href: "/document-generator", icon: FileSignature },
  { label: "Settings", href: "/settings", icon: Settings },
  { label: "About", href: "/about", icon: Info },
];

export function Sidebar() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-gray-100 bg-white transition-all duration-300 ease-in-out shrink-0",
        sidebarOpen ? "w-60" : "w-0 overflow-hidden md:w-[60px]",
      )}
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div
        className={cn(
          "flex h-16 items-center gap-3 border-b border-gray-100 px-4 shrink-0",
          !sidebarOpen && "md:justify-center md:px-0",
        )}
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 text-white shadow-sm shadow-emerald-200">
          <Leaf size={16} strokeWidth={2.5} />
        </div>
        <div
          className={cn(
            "flex flex-col transition-opacity duration-200 min-w-0",
            !sidebarOpen && "md:hidden",
          )}
        >
          <span className="text-sm font-bold tracking-tight text-gray-900 leading-none">
            Journal2LaTeX
          </span>
          <span className="text-[10px] text-emerald-600 font-medium leading-none mt-0.5">
            Academic Converter
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5" role="navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            end={item.href === "/"}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500",
                isActive
                  ? "bg-emerald-50 text-emerald-700 shadow-sm shadow-emerald-100"
                  : "text-gray-500 hover:bg-gray-50 hover:text-gray-900",
                !sidebarOpen && "md:justify-center md:px-0",
              )
            }
            aria-label={item.label}
          >
            {({ isActive }) => (
              <>
                <item.icon
                  size={17}
                  className={cn(
                    "shrink-0 transition-colors",
                    isActive ? "text-emerald-600" : "text-gray-400 group-hover:text-gray-600",
                  )}
                  aria-hidden="true"
                />
                <span
                  className={cn(
                    "transition-opacity leading-none",
                    !sidebarOpen && "md:hidden",
                  )}
                >
                  {item.label}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className={cn("px-3 py-4 border-t border-gray-100", !sidebarOpen && "md:px-0 md:flex md:justify-center")}>
        <div
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg",
            !sidebarOpen && "md:px-0 md:justify-center",
          )}
        >
          <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
          <span
            className={cn(
              "text-[11px] text-gray-400 font-mono transition-opacity",
              !sidebarOpen && "md:hidden",
            )}
          >
            v1.0.0 · Ready
          </span>
        </div>
      </div>
    </aside>
  );
}

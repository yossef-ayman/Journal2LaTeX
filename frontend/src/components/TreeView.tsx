import { useState, type ReactNode } from "react";
import { cn } from "@/utils/cn";
import { ChevronRight, ChevronDown } from "lucide-react";

interface TreeNode {
  id: string;
  label: string;
  icon?: ReactNode;
  children?: TreeNode[];
  data?: Record<string, unknown>;
}

interface TreeViewProps {
  nodes: TreeNode[];
  className?: string;
  defaultExpanded?: boolean;
}

function TreeNodeRow({
  node,
  depth,
  defaultExpanded,
}: {
  node: TreeNode;
  depth: number;
  defaultExpanded: boolean;
}) {
  const [open, setOpen] = useState(defaultExpanded);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent",
          depth > 0 && "ml-4",
        )}
        style={{ marginLeft: depth * 16 }}
      >
        {hasChildren ? (
          open ? (
            <ChevronDown size={14} className="shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight size={14} className="shrink-0 text-muted-foreground" />
          )
        ) : (
          <span className="w-3.5" />
        )}
        {node.icon}
        <span className="font-medium text-foreground">{node.label}</span>
      </button>
      {open && hasChildren &&
        node.children!.map((child) => (
          <TreeNodeRow
            key={child.id}
            node={child}
            depth={depth + 1}
            defaultExpanded={defaultExpanded}
          />
        ))}
    </>
  );
}

export function TreeView({ nodes, className, defaultExpanded = false }: TreeViewProps) {
  return (
    <div className={cn("space-y-0.5", className)}>
      {nodes.map((node) => (
        <TreeNodeRow
          key={node.id}
          node={node}
          depth={0}
          defaultExpanded={defaultExpanded}
        />
      ))}
    </div>
  );
}

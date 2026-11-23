"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface TabItem {
  value: string;
  label: string;
  icon?: ReactNode;
  content: ReactNode;
}

export function Tabs({
  items,
  value,
  onValueChange,
  className,
}: {
  items: TabItem[];
  value: string;
  onValueChange: (value: string) => void;
  className?: string;
}) {
  return (
    <div className={cn("flex min-h-0 flex-1 flex-col", className)}>
      <div role="tablist" className="flex shrink-0 gap-1 border-b px-4 pt-3">
        {items.map((item) => (
          <button
            key={item.value}
            role="tab"
            aria-selected={value === item.value}
            onClick={() => onValueChange(item.value)}
            className={cn(
              "flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              value === item.value
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="min-h-0 flex-1 overflow-hidden">
        {items.find((item) => item.value === value)?.content}
      </div>
    </div>
  );
}

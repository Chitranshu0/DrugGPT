"use client";

import { MessageSquare, Plus, Pill, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn, formatDate } from "@/lib/utils";
import type { Conversation } from "@/lib/api/types";

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  loading,
  variant,
  className,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  loading: boolean;
  variant: "patient" | "professional";
  className?: string;
}) {
  return (
    <aside className={cn("flex w-64 shrink-0 flex-col border-r bg-card/50 sm:w-72", className)}>
      <div className="flex items-center justify-between gap-2 p-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          {variant === "professional" ? <Stethoscope className="h-4 w-4 text-primary" /> : <Pill className="h-4 w-4 text-primary" />}
          Conversations
        </div>
        <Button size="sm" variant="outline" onClick={onNew} className="h-8 px-2.5 text-xs">
          <Plus className="h-3.5 w-3.5" />
          New
        </Button>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 space-y-1 overflow-y-auto px-2 pb-3">
        {loading ? (
          <p className="px-2 py-4 text-xs text-muted-foreground">Loading conversations…</p>
        ) : conversations.length === 0 ? (
          <p className="px-2 py-4 text-xs text-muted-foreground">No conversations yet. Start a new one.</p>
        ) : (
          conversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              onClick={() => onSelect(conversation.id)}
              className={cn(
                "flex w-full items-start gap-2 rounded-md px-2.5 py-2.5 text-left text-sm transition-colors",
                activeId === conversation.id ? "bg-primary/10 font-medium text-primary" : "hover:bg-accent",
              )}
            >
              <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 opacity-70" aria-hidden />
              <span className="min-w-0 flex-1">
                <span className="block truncate">{conversation.title}</span>
                <span className="block truncate text-[11px] font-normal text-muted-foreground">
                  {formatDate(conversation.updated_at)}
                </span>
              </span>
            </button>
          ))
        )}
      </div>

      <div className="border-t p-3 text-[11px] leading-relaxed text-muted-foreground">
        Personal medication decisions are paused for clinician review.
      </div>
    </aside>
  );
}

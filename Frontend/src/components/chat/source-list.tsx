import { BookOpen, ChevronDown, ExternalLink } from "lucide-react";
import type { SourceCitation } from "@/lib/api/types";

export function SourceList({ sources }: { sources: SourceCitation[] }) {
  if (!sources.length) return null;

  return (
    <details className="group mt-3 rounded-lg border bg-background/60 text-xs">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 font-medium text-muted-foreground hover:text-foreground">
        <BookOpen className="h-3.5 w-3.5" aria-hidden />
        Sources ({sources.length})
        <ChevronDown className="ml-auto h-3.5 w-3.5 transition-transform group-open:rotate-180" aria-hidden />
      </summary>
      <div className="space-y-2 border-t px-3 py-3">
        {sources.map((source) => (
          <div key={`${source.id}-${source.path}`} className="rounded-md border bg-card p-2.5">
            <div className="flex items-start justify-between gap-2">
              <p className="font-medium leading-snug">
                [{source.id}] {source.title}
                {source.page != null ? ` — page ${source.page}` : ""}
              </p>
              <span className="shrink-0 rounded-full bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-secondary-foreground">
                {Math.round(source.relevance_score * 100)}%
              </span>
            </div>
            <p className="mt-1.5 leading-relaxed text-muted-foreground">{source.excerpt}</p>
            <p className="mt-1.5 flex items-center gap-1 text-[10px] text-muted-foreground/80">
              <ExternalLink className="h-3 w-3" aria-hidden />
              {source.path}
            </p>
          </div>
        ))}
      </div>
    </details>
  );
}

import { ShieldAlert } from "lucide-react";
import { isMockMode } from "@/lib/api";

export function Disclaimer({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-center text-xs text-muted-foreground">
      <span className="inline-flex items-center gap-1.5">
        <ShieldAlert className="h-3.5 w-3.5" aria-hidden />
        For educational purposes only. Not medical advice. Do not enter real patient data.
      </span>
      {!compact && (
        <span className="rounded-full bg-secondary px-2 py-0.5 font-medium text-secondary-foreground">
          {isMockMode ? "Demo data — no backend connected" : "Connected to backend"}
        </span>
      )}
    </div>
  );
}

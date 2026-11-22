"use client";

import { Moon, Pill, Stethoscope, Sun, UserRound } from "lucide-react";
import { ChatView } from "@/components/chat/chat-view";
import { Disclaimer } from "@/components/disclaimer";
import { ProfessionalWorkspace } from "@/components/professional/professional-workspace";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useRole } from "@/lib/role-context";
import { useTheme } from "@/lib/theme-context";
import type { Role } from "@/lib/api/types";

export function AppShell({ role }: { role: Role }) {
  const { setRole } = useRole();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <header className="z-20 shrink-0 border-b bg-card/95 backdrop-blur">
        <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Pill className="h-5 w-5" aria-hidden />
          </div>
          <div className="mr-auto min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold leading-tight">DrugGPT</h1>
              <span className="hidden text-xs text-muted-foreground sm:inline">Medicine &amp; drug education</span>
            </div>
          </div>

          <div
            role="group"
            aria-label="Select role"
            className="flex items-center rounded-lg border bg-background p-1"
          >
            <RoleButton active={role === "patient"} onClick={() => setRole("patient")} icon={<UserRound className="h-3.5 w-3.5" />} label="Patient" />
            <RoleButton
              active={role === "professional"}
              onClick={() => setRole("professional")}
              icon={<Stethoscope className="h-3.5 w-3.5" />}
              label="Professional"
            />
          </div>

          <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle color theme">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
        <div className="border-t bg-background/60 px-4 py-1.5">
          <Disclaimer compact />
        </div>
      </header>

      <main className="min-h-0 flex-1">
        {role === "patient" ? <ChatView variant="patient" /> : <ProfessionalWorkspace />}
      </main>
    </div>
  );
}

function RoleButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors sm:px-3 sm:text-sm",
        active ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

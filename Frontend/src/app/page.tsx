"use client";

import { AppShell } from "@/components/app-shell";
import { RoleGate } from "@/components/role-gate";
import { useRole } from "@/lib/role-context";

export default function HomePage() {
  const { role } = useRole();
  return role ? <AppShell role={role} /> : <RoleGate />;
}

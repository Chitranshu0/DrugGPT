"use client";

import { ArrowRight, BookOpenText, CheckCircle2, ClipboardList, MessageCircle, Pill, Stethoscope, UserRound } from "lucide-react";
import { Disclaimer } from "@/components/disclaimer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useRole } from "@/lib/role-context";

const patientFeatures = [
  "Ask questions about medicines and health topics",
  "Read answers with visible medical sources",
  "Get clinician-reviewed guidance when needed",
];

const professionalFeatures = [
  "Drug & pharmacology chat with clinical framing",
  "Review requests submitted by users",
  "Approve, reject, or reply directly in the chat",
];

export function RoleGate() {
  const { setRole } = useRole();

  return (
    <main className="flex min-h-screen flex-col bg-gradient-to-b from-accent/40 via-background to-background">
      <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-6 py-10 sm:py-16">
        <header className="mb-10 text-center">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
            <Pill className="h-7 w-7" aria-hidden />
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">DrugGPT</h1>
          <p className="mx-auto mt-3 max-w-2xl text-base text-muted-foreground sm:text-lg">
            Source-grounded medicine and drug education. Choose how you want to use it.
          </p>
        </header>

        <div className="grid gap-5 md:grid-cols-2">
          <Card className="group flex flex-col border-2 transition-all hover:-translate-y-0.5 hover:border-primary/60 hover:shadow-xl">
            <CardHeader>
              <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-secondary text-primary">
                <UserRound className="h-6 w-6" aria-hidden />
              </div>
              <CardTitle className="text-2xl">Normal user</CardTitle>
              <CardDescription>Patient — everyday questions in plain language</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col">
              <ul className="mb-6 flex-1 space-y-3 text-sm">
                {patientFeatures.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <Button size="lg" className="w-full" onClick={() => setRole("patient")}>
                <MessageCircle className="h-4 w-4" aria-hidden />
                Continue as patient
                <ArrowRight className="ml-auto h-4 w-4" aria-hidden />
              </Button>
            </CardContent>
          </Card>

          <Card className="group flex flex-col border-2 transition-all hover:-translate-y-0.5 hover:border-primary/60 hover:shadow-xl">
            <CardHeader>
              <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-secondary text-primary">
                <Stethoscope className="h-6 w-6" aria-hidden />
              </div>
              <CardTitle className="text-2xl">Drug professional</CardTitle>
              <CardDescription>Doctor, paramedic, or pharmacist workflow</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col">
              <ul className="mb-6 flex-1 space-y-3 text-sm">
                {professionalFeatures.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <Button size="lg" variant="outline" className="w-full" onClick={() => setRole("professional")}>
                <ClipboardList className="h-4 w-4" aria-hidden />
                Continue as professional
                <ArrowRight className="ml-auto h-4 w-4" aria-hidden />
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="mt-10 flex items-start justify-center gap-3 rounded-lg border bg-card/60 p-4 text-sm text-muted-foreground">
          <BookOpenText className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
          <p>
            Answers come from a local medical source index with a clinician review gate for personal medication
            decisions. You can switch roles at any time from the header.
          </p>
        </div>

        <div className="mt-8">
          <Disclaimer />
        </div>
      </div>
    </main>
  );
}

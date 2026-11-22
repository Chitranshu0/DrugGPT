"use client";

import { ClipboardList, MessageSquareText, Stethoscope } from "lucide-react";
import { useState } from "react";
import { ChatView } from "@/components/chat/chat-view";
import { RequestsConsole } from "@/components/professional/requests-console";
import { Badge } from "@/components/ui/badge";
import { Tabs } from "@/components/ui/tabs";

export function ProfessionalWorkspace() {
  const [tab, setTab] = useState("chat");

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center gap-2 border-b bg-secondary/40 px-4 py-2 text-xs text-muted-foreground">
        <Stethoscope className="h-3.5 w-3.5 text-primary" aria-hidden />
        <span>Drug professional workspace</span>
        <Badge variant="info">Review workflow</Badge>
      </div>
      <Tabs
        className="min-h-0 flex-1"
        value={tab}
        onValueChange={setTab}
        items={[
          {
            value: "chat",
            label: "Pro Chat",
            icon: <MessageSquareText className="h-4 w-4" aria-hidden />,
            content: <ChatView variant="professional" />,
          },
          {
            value: "requests",
            label: "Requests",
            icon: <ClipboardList className="h-4 w-4" aria-hidden />,
            content: <RequestsConsole />,
          },
        ]}
      />
    </div>
  );
}

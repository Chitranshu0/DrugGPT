"use client";

import { AlertCircle, MessageSquareText, Sparkles, Stethoscope, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ChatResponse, Conversation, ConversationMessage, Patient } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Composer } from "@/components/chat/composer";
import { ConversationSidebar } from "@/components/chat/conversation-sidebar";
import { MessageBubble } from "@/components/chat/message-bubble";

const PATIENT_STARTERS = [
  "How does aspirin work in the body?",
  "What is the difference between a symptom and a side effect?",
  "Can you explain what a blood pressure reading means?",
];

const PROFESSIONAL_STARTERS = [
  "Summarise the pharmacology of aspirin and its bleeding risk.",
  "What sources cover first-line treatment of hypertension?",
  "Explain the mechanism of metformin in type 2 diabetes.",
];

const errorMessage = (error: unknown) => (error instanceof Error ? error.message : "Something went wrong.");

export function ChatView({ variant = "patient" }: { variant?: "patient" | "professional" }) {
  const [patient, setPatient] = useState<Patient | null>(null);
  const patientRef = useRef<Patient | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const patients = await api.listPatients();
        let activePatient = patients[0];
        if (!activePatient) {
          activePatient = await api.createPatient(variant === "professional" ? "Clinician demo" : "Guest patient");
        }
        if (cancelled) return;
        patientRef.current = activePatient;
        setPatient(activePatient);

        const existing = await api.listConversations(activePatient.id);
        const available =
          existing.length > 0
            ? existing
            : [
                await api.createConversation(
                  activePatient.id,
                  variant === "professional" ? "Clinical drug queries" : "General medical chat",
                ),
              ];
        if (cancelled) return;
        setConversations(available);
        const first = available[0];
        setActiveId(first.id);
        setMessages(await api.listMessages(first.id));
      } catch (caught) {
        if (!cancelled) setError(errorMessage(caught));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [variant]);

  useEffect(() => {
    const element = scrollRef.current;
    if (element) element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
  }, [messages, streamingText]);

  const selectConversation = async (id: string) => {
    if (id === activeId) return;
    abortRef.current?.abort();
    setStreamingText("");
    setIsStreaming(false);
    setActiveId(id);
    setError(null);
    try {
      setMessages(await api.listMessages(id));
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  const newConversation = async () => {
    if (!patientRef.current) return;
    try {
      const conversation = await api.createConversation(patientRef.current.id, "New medical chat");
      setConversations((previous) => [conversation, ...previous]);
      setActiveId(conversation.id);
      setMessages([]);
      setError(null);
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  const deleteConversation = async (id: string) => {
    if (deletingId) return;
    if (!window.confirm("Delete this chat? Its messages and any clinician review will be removed permanently.")) return;

    const wasActive = id === activeId;
    if (wasActive) {
      abortRef.current?.abort();
      setIsStreaming(false);
      setStreamingText("");
    }
    setDeletingId(id);
    setError(null);
    try {
      await api.deleteConversation(id);
      const remaining = conversations.filter((item) => item.id !== id);
      setConversations(remaining);
      if (wasActive) {
        const next = remaining[0];
        if (next) {
          setActiveId(next.id);
          setMessages(await api.listMessages(next.id));
        } else if (patientRef.current) {
          // Keep the demo usable: always have one open chat after a deletion.
          const fresh = await api.createConversation(patientRef.current.id, "New medical chat");
          setConversations([fresh]);
          setActiveId(fresh.id);
          setMessages([]);
        } else {
          setActiveId(null);
          setMessages([]);
        }
      }
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setDeletingId(null);
    }
  };

  const sendMessage = async (text: string) => {
    if (!activeId || isStreaming) return;
    const conversationId = activeId;
    setError(null);
    const optimistic: ConversationMessage = {
      id: `local-${Date.now()}`,
      conversation_id: conversationId,
      role: "user",
      content: text,
      status: null,
      created_at: new Date().toISOString(),
      metadata: {},
    };
    setMessages((previous) => [...previous, optimistic]);
    setIsStreaming(true);
    setStreamingText("");

    const controller = new AbortController();
    abortRef.current = controller;
    let finalResponse: ChatResponse | null = null;

    try {
      for await (const event of api.streamMessage(conversationId, text, controller.signal)) {
        if (event.type === "token") {
          setStreamingText((previous) => previous + event.token);
        } else if (event.type === "response") {
          finalResponse = event.response;
        } else if (event.type === "error") {
          throw new Error(event.detail);
        }
      }
      if (finalResponse && activeId === conversationId) {
        setMessages(await api.listMessages(conversationId));
      }
    } catch (caught) {
      if (!controller.signal.aborted) setError(errorMessage(caught));
    } finally {
      setStreamingText("");
      setIsStreaming(false);
    }
  };

  const activeTitle = conversations.find((item) => item.id === activeId)?.title ?? "New chat";
  const starters = variant === "professional" ? PROFESSIONAL_STARTERS : PATIENT_STARTERS;

  return (
    <div className="flex h-full min-h-0">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={newConversation}
        onDelete={deleteConversation}
        deletingId={deletingId}
        loading={loading}
        variant={variant}
        className="hidden md:flex"
      />

      <section className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="flex shrink-0 items-center gap-2 border-b bg-background/70 px-4 py-3">
          {variant === "professional" ? (
            <Stethoscope className="h-4 w-4 text-primary" aria-hidden />
          ) : (
            <MessageSquareText className="h-4 w-4 text-primary" aria-hidden />
          )}
          <h2 className="truncate text-sm font-semibold">{activeTitle}</h2>
          <span className="ml-auto text-xs text-muted-foreground">{patient?.name ?? "Local demo profile"}</span>
        </div>

        {error ? (
          <div className="flex shrink-0 items-center gap-2 border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
            <span className="flex-1">{error}</span>
            <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => setError(null)} aria-label="Dismiss error">
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : null}

        <div ref={scrollRef} className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
          <div className="mx-auto max-w-3xl space-y-5">
            {loading ? (
              <p className="py-10 text-center text-sm text-muted-foreground">Loading your chat…</p>
            ) : messages.length === 0 && !isStreaming ? (
              <div className="py-8 text-center">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-primary">
                  <Sparkles className="h-6 w-6" aria-hidden />
                </div>
                <h3 className="text-lg font-semibold">
                  {variant === "professional" ? "Clinical drug assistant" : "What would you like to know?"}
                </h3>
                <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
                  {variant === "professional"
                    ? "Ask about mechanisms, interactions, or treatment references. Answers include medical sources where available."
                    : "Ask a question about a medicine or a health topic. Answers are educational and show their sources."}
                </p>
                <div className="mt-6 grid gap-2 text-left sm:grid-cols-1">
                  {starters.map((starter) => (
                    <button
                      key={starter}
                      type="button"
                      onClick={() => sendMessage(starter)}
                      className="rounded-lg border bg-card px-4 py-3 text-left text-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
                    >
                      {starter}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    role={message.role}
                    content={message.content}
                    status={message.status}
                    metadata={message.metadata}
                  />
                ))}
                {isStreaming ? <MessageBubble role="assistant" content="" streaming streamingText={streamingText} /> : null}
              </>
            )}
          </div>
        </div>

        <Composer
          onSend={sendMessage}
          onStop={() => abortRef.current?.abort()}
          isStreaming={isStreaming}
          disabled={loading || !activeId}
          placeholder={
            variant === "professional" ? "Ask a drug or pharmacology question…" : "Ask a health or medicine question…"
          }
        />
      </section>
    </div>
  );
}

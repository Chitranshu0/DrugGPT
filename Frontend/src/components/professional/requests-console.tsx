"use client";

import { AlertCircle, CheckCircle2, ClipboardList, Inbox, Plus, RefreshCw, Search, Send, ShieldCheck, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MedicationReview, NewRequestInput, ReviewDetail, Transcript } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn, formatDate, shortId } from "@/lib/utils";

type Filter = "pending" | "approved" | "rejected" | "all";
const FILTERS: Filter[] = ["pending", "approved", "rejected", "all"];
const REVIEWER_KEY = "druggpt.reviewer";

const errorMessage = (error: unknown) => (error instanceof Error ? error.message : "Something went wrong.");

export function RequestsConsole() {
  const [reviews, setReviews] = useState<MedicationReview[]>([]);
  const [filter, setFilter] = useState<Filter>("pending");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [contexts, setContexts] = useState<Record<string, Record<string, unknown>>>({});
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [reviewerName, setReviewerName] = useState("");
  const [guidance, setGuidance] = useState("");
  const [note, setNote] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(REVIEWER_KEY);
    if (saved) setReviewerName(saved);
  }, []);

  const loadReviews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await api.listReviews(filter);
      setReviews(items);
      setSelectedId((current) => (current && items.some((item) => item.id === current) ? current : (items[0]?.id ?? null)));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void loadReviews();
  }, [loadReviews]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setTranscript(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setError(null);
      try {
        const loadedDetail = await api.getReview(selectedId);
        const loadedTranscript = await api.getTranscript(loadedDetail.conversation_id);
        if (cancelled) return;
        setDetail(loadedDetail);
        setContexts((previous) => ({ ...previous, [loadedDetail.id]: loadedDetail.context ?? {} }));
        setTranscript(loadedTranscript);
        setGuidance(loadedDetail.status === "pending" ? loadedDetail.draft_guidance : (loadedDetail.approved_guidance ?? ""));
        setNote(loadedDetail.reviewer_note ?? "");
        setReply("");
      } catch (caught) {
        if (!cancelled) setError(errorMessage(caught));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const decide = async (decision: "approved" | "rejected") => {
    if (!detail) return;
    if (!reviewerName.trim()) {
      setError("Enter your clinician name first.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await api.decideReview(
        detail.id,
        decision,
        reviewerName.trim(),
        decision === "approved" ? guidance : null,
        note || null,
      );
      window.localStorage.setItem(REVIEWER_KEY, reviewerName.trim());
      setNotice(`Review ${updated.status}.`);
      await loadReviews();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const sendReply = async () => {
    if (!detail || !reply.trim() || !reviewerName.trim()) {
      setError("Enter your name and a message before sending.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.clinicianReply(detail.conversation_id, reply.trim(), reviewerName.trim(), detail.id);
      window.localStorage.setItem(REVIEWER_KEY, reviewerName.trim());
      setNotice("Reply sent. It is now visible in the conversation.");
      setReply("");
      const [loadedDetail, loadedTranscript] = await Promise.all([
        api.getReview(detail.id),
        api.getTranscript(detail.conversation_id),
      ]);
      setDetail(loadedDetail);
      setTranscript(loadedTranscript);
      await loadReviews();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const visible = reviews.filter((review) => {
    const term = search.trim().toLowerCase();
    if (!term) return true;
    const context = contexts[review.id];
    return [review.id, review.status, review.draft_guidance, JSON.stringify(context ?? {})]
      .join(" ")
      .toLowerCase()
      .includes(term);
  });

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <ClipboardList className="h-4 w-4 text-primary" aria-hidden />
          User requests
        </div>
        <Badge variant="secondary">{reviews.length}</Badge>
        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={() => void loadReviews()} aria-label="Refresh requests">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button size="sm" onClick={() => setShowNew(true)}>
            <Plus className="h-3.5 w-3.5" />
            New request
          </Button>
        </div>
      </div>

      {(error || notice) && (
        <div className="shrink-0 px-4 pt-2">
          {error ? (
            <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
              <span className="flex-1">{error}</span>
              <button type="button" onClick={() => setError(null)} aria-label="Dismiss error">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-md border border-emerald-300/40 bg-emerald-50 px-3 py-2 text-xs text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
              <CheckCircle2 className="h-4 w-4" aria-hidden />
              {notice}
            </div>
          )}
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <div className="flex w-full shrink-0 flex-col border-b md:w-80 md:border-b-0 md:border-r">
          <div className="space-y-2 border-b p-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden />
              <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search requests" className="h-9 pl-8 text-xs" />
            </div>
            <div className="flex gap-1">
              {FILTERS.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setFilter(item)}
                  className={cn(
                    "flex-1 rounded-md px-2 py-1.5 text-[11px] font-medium capitalize transition-colors",
                    filter === item ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground hover:bg-accent",
                  )}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="scrollbar-thin min-h-0 flex-1 space-y-1.5 overflow-y-auto p-2">
            {loading ? (
              <p className="p-3 text-xs text-muted-foreground">Loading requests…</p>
            ) : visible.length === 0 ? (
              <div className="flex flex-col items-center gap-2 p-6 text-center text-xs text-muted-foreground">
                <Inbox className="h-6 w-6" aria-hidden />
                <p>No {filter === "all" ? "" : filter} requests right now.</p>
              </div>
            ) : (
              visible.map((review) => (
                <button
                  key={review.id}
                  type="button"
                  onClick={() => setSelectedId(review.id)}
                  className={cn(
                    "w-full rounded-lg border p-3 text-left transition-colors",
                    selectedId === review.id ? "border-primary bg-primary/5" : "bg-card hover:bg-accent/50",
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-muted-foreground">{shortId(review.id)}</span>
                    <StatusBadge status={review.status} />
                    <span className="ml-auto text-[10px] text-muted-foreground">{formatDate(review.created_at)}</span>
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs leading-relaxed">{review.draft_guidance}</p>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">
          {!detail ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Select a request to review it.</div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-semibold">Request {shortId(detail.id)}</h3>
                <StatusBadge status={detail.status} />
                <span className="text-xs text-muted-foreground">{formatDate(detail.created_at)}</span>
              </div>

              {detail.context ? (
                <section className="rounded-lg border bg-card p-4">
                  <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Request context</h4>
                  <dl className="grid gap-3 sm:grid-cols-2">
                    {Object.entries(detail.context).map(([key, value]) => (
                      <div key={key}>
                        <dt className="text-[11px] font-medium capitalize text-muted-foreground">{key}</dt>
                        <dd className="mt-0.5 text-sm">{String(value ?? "—")}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ) : null}

              <section className="rounded-lg border border-amber-300/50 bg-amber-50/60 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
                <div className="mb-2 flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-amber-700 dark:text-amber-400" aria-hidden />
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-300">
                    Internal draft — do not share until approved
                  </h4>
                </div>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{detail.draft_guidance}</p>
              </section>

              <section className="space-y-3 rounded-lg border bg-card p-4">
                <h4 className="text-sm font-semibold">Reviewer</h4>
                <Input
                  value={reviewerName}
                  onChange={(event) => setReviewerName(event.target.value)}
                  placeholder="Your name (e.g. Dr. Smith)"
                  className="max-w-sm"
                />

                {detail.status === "pending" ? (
                  <>
                    <div>
                      <label className="mb-1.5 block text-xs font-medium" htmlFor="approved-guidance">
                        Patient-facing guidance
                      </label>
                      <Textarea id="approved-guidance" value={guidance} onChange={(event) => setGuidance(event.target.value)} rows={4} />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-medium" htmlFor="review-note">
                        Review note (optional)
                      </label>
                      <Textarea id="review-note" value={note} onChange={(event) => setNote(event.target.value)} rows={2} />
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={() => void decide("approved")} disabled={busy}>
                        <CheckCircle2 className="h-4 w-4" aria-hidden />
                        Approve &amp; send
                      </Button>
                      <Button variant="outline" onClick={() => void decide("rejected")} disabled={busy}>
                        Reject
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="space-y-2 text-sm">
                    <p>
                      <span className="text-muted-foreground">Decision: </span>
                      <StatusBadge status={detail.status} />
                    </p>
                    {detail.reviewer_name ? (
                      <p>
                        <span className="text-muted-foreground">Reviewed by: </span>
                        {detail.reviewer_name}
                      </p>
                    ) : null}
                    {detail.approved_guidance ? <p className="whitespace-pre-wrap">{detail.approved_guidance}</p> : null}
                    {detail.reviewer_note ? (
                      <p className="text-xs text-muted-foreground">Note: {detail.reviewer_note}</p>
                    ) : null}
                  </div>
                )}
              </section>

              <section className="rounded-lg border bg-card p-4">
                <h4 className="mb-3 text-sm font-semibold">Conversation transcript</h4>
                {transcript?.messages.length ? (
                  <div className="space-y-3">
                    {transcript.messages.map((message) => (
                      <div key={message.id} className="rounded-md bg-secondary/60 p-3 text-sm">
                        <div className="mb-1 flex items-center gap-2">
                          <Badge variant={message.role === "user" ? "secondary" : message.role === "clinician" ? "info" : "outline"}>
                            {message.role}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground">{formatDate(message.created_at)}</span>
                        </div>
                        <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No transcript available for this request.</p>
                )}
              </section>

              <section className="space-y-2 rounded-lg border bg-card p-4">
                <h4 className="text-sm font-semibold">Reply to the user as a clinician</h4>
                <Textarea value={reply} onChange={(event) => setReply(event.target.value)} rows={3} placeholder="Write your message…" />
                <Button onClick={() => void sendReply()} disabled={busy || !reply.trim()}>
                  <Send className="h-4 w-4" aria-hidden />
                  Send reply
                </Button>
              </section>
            </div>
          )}
        </div>
      </div>

      {showNew ? (
        <NewRequestDialog
          onClose={() => setShowNew(false)}
          onCreated={async (created) => {
            setShowNew(false);
            setNotice(created ? "New request added to the queue." : "Request sent — no clinician review was needed.");
            await loadReviews();
            if (created) setSelectedId(created.id);
          }}
        />
      ) : null}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variant = status === "pending" ? "warning" : status === "approved" ? "success" : status === "rejected" ? "destructive" : "secondary";
  return <Badge variant={variant}>{status}</Badge>;
}

function NewRequestDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (review: MedicationReview | null) => void;
}) {
  const [form, setForm] = useState<NewRequestInput>({ topic: "", medicine: "", question: "", urgency: "routine" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!form.question.trim()) {
      setError("Describe the request.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await api.createRequest(form);
      onCreated(result.review);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-lg rounded-xl border bg-card p-5 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">New user request</h3>
          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={onClose} aria-label="Close dialog">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium" htmlFor="req-topic">Topic</label>
            <Input id="req-topic" value={form.topic} onChange={(event) => setForm({ ...form, topic: event.target.value })} placeholder="e.g. Medicine interaction" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium" htmlFor="req-medicine">Medicine (optional)</label>
            <Input id="req-medicine" value={form.medicine} onChange={(event) => setForm({ ...form, medicine: event.target.value })} placeholder="e.g. Aspirin" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium" htmlFor="req-question">Question</label>
            <Textarea id="req-question" value={form.question} onChange={(event) => setForm({ ...form, question: event.target.value })} rows={4} placeholder="What does the user need reviewed?" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium" htmlFor="req-urgency">Urgency</label>
            <select
              id="req-urgency"
              value={form.urgency}
              onChange={(event) => setForm({ ...form, urgency: event.target.value as NewRequestInput["urgency"] })}
              className="flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="routine">Routine</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
          {error ? <p className="text-xs text-destructive">{error}</p> : null}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => void submit()} disabled={busy}>{busy ? "Submitting…" : "Submit request"}</Button>
        </div>
      </div>
    </div>
  );
}

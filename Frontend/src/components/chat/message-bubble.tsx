import { AlertTriangle, Info, ShieldCheck, Stethoscope } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Badge } from "@/components/ui/badge";
import { SourceList } from "@/components/chat/source-list";
import type { AnswerMode, ChatStatus, SourceCitation } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  role: string;
  content: string;
  status?: string | null;
  metadata?: Record<string, unknown>;
  streaming?: boolean;
  streamingText?: string;
}

export function MessageBubble({ role, content, status, metadata, streaming, streamingText }: MessageBubbleProps) {
  if (role === "user") {
    return (
      <div className="flex justify-end gap-2">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-sm">
          <Markdown>{content}</Markdown>
        </div>
      </div>
    );
  }

  const isClinician = role === "clinician";
  const reviewer = typeof metadata?.reviewer_name === "string" ? metadata.reviewer_name : null;
  const answerMode = metadata?.answer_mode as AnswerMode | undefined;
  const sources: SourceCitation[] = Array.isArray(metadata?.sources) ? (metadata.sources as SourceCitation[]) : [];
  const text = streaming ? streamingText || "▋" : content;

  return (
    <div className="flex justify-start gap-2.5">
      <div
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isClinician ? "bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300" : "bg-secondary text-primary",
        )}
      >
        {isClinician ? <Stethoscope className="h-4 w-4" aria-hidden /> : <span className="text-sm font-bold">💊</span>}
      </div>
      <div className="max-w-[85%] min-w-0 rounded-2xl rounded-tl-sm border bg-card px-4 py-3 text-sm leading-relaxed shadow-sm">
        {isClinician ? (
          <div className="mb-1.5 flex items-center gap-2">
            <span className="font-semibold text-sky-700 dark:text-sky-300">Dr. {reviewer ?? "Clinician"}</span>
            <Badge variant="info">Clinician reply</Badge>
          </div>
        ) : null}
        <Markdown>{text}</Markdown>
        {!streaming && <StatusNotice status={status as ChatStatus | undefined} answerMode={answerMode} />}
        {!streaming && <SourceList sources={sources} />}
      </div>
    </div>
  );
}

function Markdown({ children }: { children: string }) {
  return (
    <div className="space-y-2 break-words [&>p]:mb-2 [&>ul]:list-disc [&>ul]:pl-5 [&>ol]:list-decimal [&>ol]:pl-5 [&_strong]:font-semibold">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}

function StatusNotice({ status, answerMode }: { status?: ChatStatus; answerMode?: AnswerMode }) {
  if (status === "emergency_guidance") {
    return (
      <div className="mt-3 flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-xs font-medium text-destructive">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>Emergency guidance — call your local emergency number now if this is happening to you.</span>
      </div>
    );
  }
  if (status === "review_pending") {
    return (
      <div className="mt-3 flex items-start gap-2 rounded-lg border border-sky-300/50 bg-sky-50 p-3 text-xs text-sky-900 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>A clinician is reviewing this request. Their reply will appear here.</span>
      </div>
    );
  }
  if (answerMode === "clarification") {
    return (
      <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-300/50 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>Follow-up question — a little more detail will help.</span>
      </div>
    );
  }
  if (answerMode === "general_education") {
    return <p className="mt-2 text-xs text-muted-foreground">General educational information — not a diagnosis or prescription.</p>;
  }
  if (status === "out_of_scope" || status === "safety_refusal") {
    return <p className="mt-2 text-xs text-muted-foreground">This topic is outside the scope of this education assistant.</p>;
  }
  return null;
}

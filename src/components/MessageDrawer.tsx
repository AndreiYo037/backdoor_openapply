import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, Copy, ExternalLink, Loader2, Mail, RefreshCw } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { draftMessage, logSent } from "@/services/api";
import type { Contact, JobData } from "@/services/api";

type Tone = "professional" | "casual";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  contact: Contact | null;
  job: JobData | null;
  jobId: string | null;
  cvText: string;
  onSent: (messageId: string) => void;
}

export default function MessageDrawer({
  open,
  onOpenChange,
  contact,
  job,
  jobId,
  cvText,
  onSent,
}: Props) {
  const [tone, setTone] = useState<Tone>("professional");
  const [draft, setDraft] = useState("");
  const [copied, setCopied] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const draftMutation = useMutation({
    mutationFn: () =>
      draftMessage({
        cvText,
        contactId: contact!.id,
        jobId: jobId!,
        tone,
      }),
    onSuccess: (data) => setDraft(data.draft),
  });

  const sentMutation = useMutation({
    mutationFn: () => logSent(contact!.id, jobId!),
    onSuccess: (data) => onSent(data.messageId),
  });

  // Load draft whenever the drawer opens or tone changes
  useEffect(() => {
    if (open && contact && jobId) {
      draftMutation.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, tone, retryCount]);

  function handleCopy() {
    navigator.clipboard.writeText(draft).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      sentMutation.mutate();
      onOpenChange(false);
    });
  }

  function handleLinkedIn() {
    const url = contact?.linkedinUrl;
    if (url) window.open(url, "_blank", "noopener,noreferrer");
    sentMutation.mutate();
    onOpenChange(false);
  }

  function handleGmail() {
    const subject = encodeURIComponent(`Re: ${job?.title ?? "Role"} at ${job?.company ?? contact?.company ?? ""}`);
    const body = encodeURIComponent(draft);
    window.open(`mailto:${contact!.email}?subject=${subject}&body=${body}`, "_blank");
    sentMutation.mutate();
    onOpenChange(false);
  }

  function handleRegenerate() {
    if (retryCount < 1) {
      setRetryCount((n) => n + 1);
    }
  }

  const loading = draftMutation.isPending;
  const hasError = draftMutation.isError;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="glass border-border/50 w-full sm:max-w-md flex flex-col gap-0 p-0 overflow-hidden"
      >
        <SheetHeader className="px-5 pt-5 pb-4 border-b border-border/30">
          <SheetTitle className="text-foreground text-base font-semibold">
            {contact?.name ?? "Draft message"}
          </SheetTitle>
          <p className="text-xs text-muted-foreground -mt-1">
            {contact?.title} · {contact?.company}
          </p>
        </SheetHeader>

        <div className="flex-1 flex flex-col gap-4 px-5 py-4 overflow-y-auto">
          {/* Tone toggle */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-secondary/40 w-fit">
            {(["professional", "casual"] as Tone[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTone(t)}
                className={`px-3 py-1 rounded-md text-xs font-medium capitalize transition-colors ${
                  tone === t
                    ? "bg-primary/20 text-primary border border-primary/30"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Draft area */}
          {loading ? (
            <div className="flex-1 flex items-center justify-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Drafting…
            </div>
          ) : hasError ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center">
              <p className="text-sm text-destructive">Failed to generate draft.</p>
              <button
                type="button"
                onClick={() => draftMutation.mutate()}
                className="text-xs text-primary hover:underline"
              >
                Try again
              </button>
            </div>
          ) : (
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={10}
              className="flex-1 w-full bg-secondary/20 border border-border/30 rounded-xl p-3 text-sm text-foreground resize-none outline-none focus:border-primary/40 transition-colors"
            />
          )}

          {/* Regenerate */}
          {!loading && !hasError && retryCount < 1 && (
            <button
              type="button"
              onClick={handleRegenerate}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mx-auto"
            >
              <RefreshCw className="w-3 h-3" /> Try a different angle
            </button>
          )}
        </div>

        {/* Action row */}
        <div className="px-5 py-4 border-t border-border/30 flex flex-col gap-2">
          <button
            type="button"
            onClick={handleCopy}
            disabled={!draft || loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-40 hover:bg-primary/90 transition-colors"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? "Copied!" : "Copy message"}
          </button>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleLinkedIn}
              disabled={!draft || loading}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border border-border/50 text-sm text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors disabled:opacity-40"
            >
              <ExternalLink className="w-3.5 h-3.5" /> LinkedIn InMail
            </button>
            {contact?.email && (
              <button
                type="button"
                onClick={handleGmail}
                disabled={!draft || loading}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border border-border/50 text-sm text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors disabled:opacity-40"
              >
                <Mail className="w-3.5 h-3.5" /> Gmail
              </button>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, Loader2, MessageCircle } from "lucide-react";
import { logReply } from "@/services/api";

interface Props {
  messageId: string;
  contactName: string;
  company: string;
  sentAt: string;
}

export default function SentCard({ messageId, contactName, company, sentAt }: Props) {
  const [replied, setReplied] = useState(false);

  const replyMutation = useMutation({
    mutationFn: () => logReply(messageId),
    onSuccess: () => setReplied(true),
  });

  const date = new Date(sentAt).toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
  });

  return (
    <div
      className={`rounded-xl p-4 border flex items-center gap-4 transition-colors ${
        replied
          ? "border-emerald-500/30 bg-emerald-500/5"
          : "border-border/30 bg-secondary/20"
      }`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground truncate">{contactName}</span>
          <span className="text-xs text-muted-foreground shrink-0">{company}</span>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          {replied ? (
            <span className="text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Replied
            </span>
          ) : (
            `Sent ${date}`
          )}
        </p>
      </div>

      {!replied && (
        <button
          type="button"
          onClick={() => replyMutation.mutate()}
          disabled={replyMutation.isPending}
          className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-medium hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
        >
          {replyMutation.isPending ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <MessageCircle className="w-3 h-3" />
          )}
          Got a reply
        </button>
      )}
    </div>
  );
}

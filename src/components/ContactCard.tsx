import { ExternalLink, Mail, MessageSquare } from "lucide-react";
import type { Contact } from "@/services/api";

interface Props {
  contact: Contact;
  onDraftMessage: (contact: Contact) => void;
}

export default function ContactCard({ contact, onDraftMessage }: Props) {
  return (
    <div className="glass glass-hover rounded-xl p-4 flex flex-col gap-3 slide-up">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="font-semibold text-foreground text-sm truncate">{contact.name}</h3>
            <span
              className={`shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                contact.relevance === "HIGH"
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-muted-foreground/30 bg-muted/30 text-muted-foreground"
              }`}
            >
              {contact.relevance}
            </span>
          </div>
          <p className="text-xs text-muted-foreground truncate">{contact.title}</p>
          <p className="text-xs text-muted-foreground/70 truncate">{contact.company}</p>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <a
          href={contact.linkedinUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
        >
          <ExternalLink className="w-3 h-3" /> LinkedIn
        </a>
        {contact.email && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Mail className="w-3 h-3" />
            <span className="truncate max-w-[160px]">{contact.email}</span>
          </span>
        )}
      </div>

      <button
        onClick={() => onDraftMessage(contact)}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-primary/10 border border-primary/20 text-primary text-sm font-medium hover:bg-primary/20 transition-colors"
      >
        <MessageSquare className="w-4 h-4" />
        Draft Message
      </button>
    </div>
  );
}

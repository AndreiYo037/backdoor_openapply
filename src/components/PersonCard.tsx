import { ExternalLink, Linkedin, Globe, Mail, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export interface Person {
  id: string;
  name: string;
  title: string;
  company: string;
  avatarUrl?: string;
  linkedinUrl?: string;
  websiteUrl?: string;
  email?: string;
  relevance: number;
  tags: string[];
}

const PersonCard = ({ person }: { person: Person }) => {
  const handleColdMessage = () => {
    toast.success(`Cold message queued for ${person.name}`, {
      description: "Will be sent via LinkedIn automation.",
    });
  };

  return (
    <div className="glass glass-hover rounded-xl p-4 animate-slide-up">
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/30 to-accent/20 flex items-center justify-center text-primary font-bold text-lg shrink-0 border border-primary/20">
          {person.name.charAt(0)}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-foreground truncate">{person.name}</h4>
          <p className="text-sm text-muted-foreground truncate">{person.title}</p>
          <p className="text-xs text-primary/80 font-medium">{person.company}</p>
        </div>
        <div className="flex items-center gap-0.5 bg-primary/10 text-primary text-xs font-mono px-2 py-1 rounded-md">
          {person.relevance}%
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mt-3">
        {person.tags.map((tag) => (
          <span key={tag} className="text-xs bg-secondary text-secondary-foreground px-2 py-0.5 rounded-md">
            {tag}
          </span>
        ))}
      </div>

      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border/50">
        <div className="flex gap-2 flex-1">
          {person.linkedinUrl && (
            <a href={person.linkedinUrl} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors">
              <Linkedin className="w-3.5 h-3.5" /> LinkedIn
            </a>
          )}
          {person.websiteUrl && (
            <a href={person.websiteUrl} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors">
              <Globe className="w-3.5 h-3.5" /> Website
            </a>
          )}
          {person.email && (
            <a href={`mailto:${person.email}`}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors">
              <Mail className="w-3.5 h-3.5" /> Email
            </a>
          )}
        </div>
        {person.linkedinUrl && (
          <Button
            size="sm"
            variant="ghost"
            onClick={handleColdMessage}
            className="h-7 px-2 text-xs gap-1 text-primary hover:bg-primary/15 hover:text-primary"
          >
            <Send className="w-3 h-3" />
            Cold Message
          </Button>
        )}
      </div>
    </div>
  );
};

export default PersonCard;

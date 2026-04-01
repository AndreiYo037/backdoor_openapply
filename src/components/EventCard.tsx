import { Calendar, MapPin, Users, ExternalLink } from "lucide-react";

export interface EventData {
  id: string;
  title: string;
  date: string;
  location: string;
  type: string;
  attendees?: number;
  url?: string;
  description: string;
}

const EventCard = ({ event }: { event: EventData }) => {
  const typeColors: Record<string, string> = {
    meetup: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    conference: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    workshop: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    networking: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  };

  return (
    <div className="glass glass-hover rounded-xl p-4 animate-slide-up">
      <div className="flex items-start justify-between mb-2">
        <span className={`text-xs px-2 py-0.5 rounded-md border ${typeColors[event.type] || typeColors.networking}`}>
          {event.type}
        </span>
        {event.url && (
          <a href={event.url} target="_blank" rel="noopener noreferrer"
            className="text-muted-foreground hover:text-primary transition-colors">
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>

      <h4 className="font-semibold text-foreground mb-2 line-clamp-2">{event.title}</h4>
      <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{event.description}</p>

      <div className="space-y-1.5 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Calendar className="w-3.5 h-3.5 text-primary/60" />
          <span>{event.date}</span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <MapPin className="w-3.5 h-3.5 text-primary/60" />
          <span>{event.location}</span>
        </div>
        {event.attendees && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Users className="w-3.5 h-3.5 text-primary/60" />
            <span>{event.attendees} expected</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default EventCard;

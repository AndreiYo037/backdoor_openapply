import { Users, UserCheck, CalendarDays } from "lucide-react";
import PersonCard, { Person } from "./PersonCard";
import ProfileCompareCard, { ProfileData } from "./ProfileCompareCard";
import EventCard, { EventData } from "./EventCard";

interface ResultsSectionProps {
  people: Person[];
  profiles: ProfileData[];
  events: EventData[];
}

const ResultsSection = ({ people, profiles, events }: ResultsSectionProps) => {
  return (
    <div className="w-full max-w-7xl mx-auto mt-12 space-y-10 animate-fade-in">
      {/* Relevant People */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
            <Users className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Relevant People</h2>
            <p className="text-xs text-muted-foreground">Key contacts at target companies</p>
          </div>
          <span className="ml-auto text-xs font-mono text-primary bg-primary/10 px-2 py-1 rounded-md">
            {people.length} found
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {people.map((person) => (
            <PersonCard key={person.id} person={person} />
          ))}
        </div>
      </section>

      {/* Similar Profiles */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 rounded-lg bg-accent/10 border border-accent/20">
            <UserCheck className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Similar Profiles</h2>
            <p className="text-xs text-muted-foreground">People in the same or similar roles for CV comparison</p>
          </div>
          <span className="ml-auto text-xs font-mono text-accent bg-accent/10 px-2 py-1 rounded-md">
            {profiles.length} found
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {profiles.map((profile) => (
            <ProfileCompareCard key={profile.id} profile={profile} />
          ))}
        </div>
      </section>

      {/* Nearby Events */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 rounded-lg bg-violet-500/10 border border-violet-500/20">
            <CalendarDays className="w-5 h-5 text-violet-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Nearby Events</h2>
            <p className="text-xs text-muted-foreground">Organic networking opportunities</p>
          </div>
          <span className="ml-auto text-xs font-mono text-violet-400 bg-violet-500/10 px-2 py-1 rounded-md">
            {events.length} upcoming
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      </section>
    </div>
  );
};

export default ResultsSection;

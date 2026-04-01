import { useState } from "react";
import { Users, UserCheck, CalendarDays, Send } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import PersonCard, { Person } from "./PersonCard";
import ProfileCompareCard, { ProfileData } from "./ProfileCompareCard";
import EventCard, { EventData } from "./EventCard";
import { toast } from "sonner";

interface ResultsSectionProps {
  people: Person[];
  profiles: ProfileData[];
  events: EventData[];
}

const ResultsSection = ({ people, profiles, events }: ResultsSectionProps) => {
  const handleMassSend = (type: "people" | "profiles") => {
    const count = type === "people" ? people.length : profiles.length;
    toast.success(`Queued cold messages to ${count} ${type}`, {
      description: "LinkedIn messages will be sent sequentially to avoid rate limits.",
    });
  };

  return (
    <div className="w-full max-w-5xl mx-auto mt-8 animate-fade-in">
      <Tabs defaultValue="people" className="w-full">
        <TabsList className="w-full bg-card/60 backdrop-blur-xl border border-border/50 h-12 p-1 rounded-xl">
          <TabsTrigger value="people" className="flex-1 gap-2 data-[state=active]:bg-primary/15 data-[state=active]:text-primary rounded-lg">
            <Users className="w-4 h-4" />
            People
            <span className="text-xs font-mono bg-primary/10 px-1.5 py-0.5 rounded">{people.length}</span>
          </TabsTrigger>
          <TabsTrigger value="profiles" className="flex-1 gap-2 data-[state=active]:bg-primary/15 data-[state=active]:text-primary rounded-lg">
            <UserCheck className="w-4 h-4" />
            Profiles
            <span className="text-xs font-mono bg-primary/10 px-1.5 py-0.5 rounded">{profiles.length}</span>
          </TabsTrigger>
          <TabsTrigger value="events" className="flex-1 gap-2 data-[state=active]:bg-primary/15 data-[state=active]:text-primary rounded-lg">
            <CalendarDays className="w-4 h-4" />
            Events
            <span className="text-xs font-mono bg-primary/10 px-1.5 py-0.5 rounded">{events.length}</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="people">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Key contacts at target companies</p>
            <Button
              size="sm"
              onClick={() => handleMassSend("people")}
              className="gap-1.5 bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25"
            >
              <Send className="w-3.5 h-3.5" />
              Message All ({people.length})
            </Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {people.map((person) => (
              <PersonCard key={person.id} person={person} />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="profiles">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">People in similar roles for CV comparison</p>
            <Button
              size="sm"
              onClick={() => handleMassSend("profiles")}
              className="gap-1.5 bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25"
            >
              <Send className="w-3.5 h-3.5" />
              Message All ({profiles.length})
            </Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {profiles.map((profile) => (
              <ProfileCompareCard key={profile.id} profile={profile} />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="events">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Organic networking opportunities</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {events.map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ResultsSection;

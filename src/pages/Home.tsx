import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Zap, Users, Send } from "lucide-react";
import TopNav from "@/components/TopNav";
import JobInput from "@/components/JobInput";
import ContactCard from "@/components/ContactCard";
import LinkedInFallbackCard from "@/components/LinkedInFallbackCard";
import CVUploadPrompt from "@/components/CVUploadPrompt";
import MessageDrawer from "@/components/MessageDrawer";
import SentCard from "@/components/SentCard";
import { useCV } from "@/hooks/useCV";
import { parseJob, searchPeople } from "@/services/api";
import type { Contact, JobData, SentMessage } from "@/services/api";
import heroBg from "@/assets/hero-bg.jpg";

// Stable job ID for the current session (replaced by real backend ID once /parse returns one)
function makeJobId(job: JobData) {
  return `${job.company.toLowerCase().replace(/\s+/g, "-")}-${job.title.toLowerCase().replace(/\s+/g, "-")}`;
}

export default function Home() {
  const { cvText, hasCV, storeCV } = useCV();

  // Core loop state
  const [job, setJob] = useState<JobData | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [linkedinFallbackUrl, setLinkedinFallbackUrl] = useState<string | null>(null);

  // CV prompt
  const [cvPromptOpen, setCVPromptOpen] = useState(false);
  const [pendingContact, setPendingContact] = useState<Contact | null>(null);

  // Message drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);

  // Sent messages
  const [sentMessages, setSentMessages] = useState<SentMessage[]>([]);

  // ── Parse job URL / text ──────────────────────────────────────────────────
  const parseMutation = useMutation({
    mutationFn: (input: string) => parseJob(input),
    onSuccess: (jobData) => {
      setJob(jobData);
      setContacts([]);
      setLinkedinFallbackUrl(null);
      searchMutation.mutate({ company: jobData.company, role: jobData.title });
    },
  });

  // ── Search people via Apollo ──────────────────────────────────────────────
  const searchMutation = useMutation({
    mutationFn: ({ company, role }: { company: string; role: string }) =>
      searchPeople(company, role),
    onSuccess: (result) => {
      setContacts(result.contacts.slice(0, 8));
      setLinkedinFallbackUrl(result.linkedinFallbackUrl ?? null);
    },
  });

  const isSearching = parseMutation.isPending || searchMutation.isPending;
  const hasResults = contacts.length > 0 || linkedinFallbackUrl !== null;
  const searchError = parseMutation.error ?? searchMutation.error;

  // ── Draft message flow ────────────────────────────────────────────────────
  function handleDraftMessage(contact: Contact) {
    if (!hasCV) {
      setPendingContact(contact);
      setCVPromptOpen(true);
    } else {
      openDrawer(contact);
    }
  }

  function handleCVDone(text: string) {
    storeCV(text);
    setCVPromptOpen(false);
    if (pendingContact) openDrawer(pendingContact);
    setPendingContact(null);
  }

  function handleCVSkip() {
    setCVPromptOpen(false);
    if (pendingContact) openDrawer(pendingContact);
    setPendingContact(null);
  }

  function openDrawer(contact: Contact) {
    setSelectedContact(contact);
    setDrawerOpen(true);
  }

  // ── Log sent ─────────────────────────────────────────────────────────────
  function handleSent(messageId: string) {
    if (!selectedContact || !job) return;
    setSentMessages((prev) => [
      {
        messageId,
        contactId: selectedContact.id,
        jobId: makeJobId(job),
        sentAt: new Date().toISOString(),
        replied: false,
      },
      ...prev,
    ]);
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img
            src={heroBg}
            alt=""
            className="w-full h-full object-cover opacity-20"
            width={1920}
            height={1080}
          />
          <div className="absolute inset-0 bg-gradient-to-b from-background/40 via-background/80 to-background" />
        </div>

        <div className="relative z-10 pb-16">
          <TopNav />

          {/* Headline */}
          <div className="text-center max-w-3xl mx-auto mb-10 px-6">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight leading-tight">
              Input a job.{" "}
              <span className="text-primary text-glow">Get the right person.</span>
              <br />
              Send the message.
            </h1>
            <p className="text-lg text-muted-foreground max-w-xl mx-auto">
              Skip the black hole. Find the hiring manager or recruiter at any SG company and send a cold message that gets replies.
            </p>
          </div>

          {/* Job input */}
          <JobInput onSubmit={(input) => parseMutation.mutate(input)} isLoading={isSearching} />

          {/* Error */}
          {searchError && (
            <p className="text-center text-sm text-destructive mt-4">
              {searchError instanceof Error ? searchError.message : "Something went wrong. Try again."}
            </p>
          )}

          {/* Feature pills — only before first search */}
          {!hasResults && !isSearching && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto mt-12 px-6">
              {[
                {
                  icon: Users,
                  title: "Find the right people",
                  desc: "Recruiters, hiring managers, and team leads at SG companies — ranked by relevance",
                },
                {
                  icon: Zap,
                  title: "Claude drafts your message",
                  desc: "Personalised InMail under 180 words. Specific, not generic. Based on your CV.",
                },
                {
                  icon: Send,
                  title: "Send in under a minute",
                  desc: "Copy to clipboard + LinkedIn deep link. No account needed.",
                },
              ].map(({ icon: Icon, title, desc }) => (
                <div key={title} className="glass rounded-xl p-4 text-center">
                  <div className="inline-flex p-2 rounded-lg bg-primary/10 border border-primary/20 mb-3">
                    <Icon className="w-5 h-5 text-primary" />
                  </div>
                  <h3 className="font-semibold text-foreground text-sm mb-1">{title}</h3>
                  <p className="text-xs text-muted-foreground">{desc}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      {(hasResults || isSearching) && (
        <div className="max-w-3xl mx-auto px-6 pb-16">
          {/* Job header */}
          {job && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-foreground">
                {job.title}{" "}
                <span className="text-muted-foreground font-normal">at {job.company}</span>
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {contacts.length} contact{contacts.length !== 1 ? "s" : ""} found
              </p>
            </div>
          )}

          {/* Loading skeleton */}
          {isSearching && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="glass rounded-xl p-4 h-36 animate-pulse bg-secondary/20"
                />
              ))}
            </div>
          )}

          {/* Contact cards */}
          {!isSearching && contacts.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {contacts.map((contact) => (
                <ContactCard
                  key={contact.id}
                  contact={contact}
                  onDraftMessage={handleDraftMessage}
                />
              ))}
            </div>
          )}

          {/* LinkedIn fallback */}
          {!isSearching && linkedinFallbackUrl && (
            <div className="mt-4">
              <LinkedInFallbackCard searchUrl={linkedinFallbackUrl} />
            </div>
          )}
        </div>
      )}

      {/* Sent messages */}
      {sentMessages.length > 0 && (
        <div className="max-w-3xl mx-auto px-6 pb-16">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Sent
          </h2>
          <div className="flex flex-col gap-2">
            {sentMessages.map((msg) => {
              const contact = contacts.find((c) => c.id === msg.contactId);
              return (
                <SentCard
                  key={msg.messageId}
                  messageId={msg.messageId}
                  contactName={contact?.name ?? "Contact"}
                  company={contact?.company ?? job?.company ?? ""}
                  sentAt={msg.sentAt}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* CV upload prompt */}
      <CVUploadPrompt
        open={cvPromptOpen}
        onDone={handleCVDone}
        onSkip={handleCVSkip}
      />

      {/* Message drawer */}
      <MessageDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        contact={selectedContact}
        job={job}
        jobId={job ? makeJobId(job) : null}
        cvText={cvText}
        onSent={handleSent}
      />
    </div>
  );
}

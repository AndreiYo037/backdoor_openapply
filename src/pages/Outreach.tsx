import { useState } from "react";
import { loadPipelineResult } from "@/lib/pipelineState";
import { generateMessages } from "@/services/pipelineApi";

type DraftMap = Record<string, { email: string; linkedin: string }>;

export default function Outreach() {
  const result = loadPipelineResult();
  const [drafts, setDrafts] = useState<DraftMap>({});

  if (!result) return <div className="p-8">Run dashboard first.</div>;

  async function handleGenerate(contactId: string) {
    const internship = result.internships[0];
    const messages = await generateMessages({
      user_id: result.user.id,
      contact_id: contactId,
      internship_id: internship.id,
    });
    setDrafts((prev) => ({ ...prev, [contactId]: messages }));
  }

  return (
    <div className="min-h-screen p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Outreach</h1>
      <div className="space-y-4">
        {result.contacts.map((item) => {
          const draft = drafts[item.contact.id];
          return (
            <div key={item.contact.id} className="glass rounded p-4">
              <p className="font-semibold">{item.contact.name}</p>
              <button className="underline text-sm my-2" onClick={() => void handleGenerate(item.contact.id)}>
                Generate messages
              </button>
              {draft && (
                <div className="space-y-2 text-sm">
                  <textarea className="w-full p-2 h-40 bg-secondary rounded" value={draft.email} readOnly />
                  <textarea className="w-full p-2 h-28 bg-secondary rounded" value={draft.linkedin} readOnly />
                  <div className="flex gap-4">
                    <button className="underline" onClick={() => navigator.clipboard.writeText(draft.email)}>Copy Email</button>
                    <button className="underline" onClick={() => navigator.clipboard.writeText(draft.linkedin)}>Copy LinkedIn</button>
                    <a className="underline" href="https://mail.google.com/mail/u/0/#drafts" target="_blank" rel="noreferrer">Open Gmail</a>
                    <a className="underline" href={item.contact.linkedin_url} target="_blank" rel="noreferrer">Open LinkedIn</a>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

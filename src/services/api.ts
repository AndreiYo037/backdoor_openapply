const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:3000";

async function apiFetch<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { message?: string }).message ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Types ──────────────────────────────────────────────────────────────────

export interface JobData {
  title: string;
  company: string;
  description: string;
}

export interface Contact {
  id: string;
  name: string;
  title: string;
  company: string;
  linkedinUrl: string;
  email?: string;
  relevance: "HIGH" | "MED";
}

export interface PeopleResult {
  contacts: Contact[];
  linkedinFallbackUrl?: string; // present when contacts.length < 3
}

export interface DraftParams {
  cvText: string;
  contactId: string;
  jobId: string;
  tone: "professional" | "casual";
}

export interface SentMessage {
  messageId: string;
  contactId: string;
  jobId: string;
  sentAt: string;
  replied: boolean;
}

// ─── Endpoints ──────────────────────────────────────────────────────────────

export function parseJob(input: string): Promise<JobData> {
  return apiFetch("/api/job/parse", {
    method: "POST",
    body: JSON.stringify({ input }),
  });
}

export function searchPeople(company: string, role: string): Promise<PeopleResult> {
  return apiFetch("/api/people/search", {
    method: "POST",
    body: JSON.stringify({ company, role }),
  });
}

export async function uploadCV(file: File): Promise<{ text: string }> {
  const form = new FormData();
  form.append("cv", file);
  const res = await fetch(`${BASE}/api/cv/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { message?: string }).message ?? `Upload error ${res.status}`);
  }
  return res.json() as Promise<{ text: string }>;
}

export function draftMessage(params: DraftParams): Promise<{ draft: string }> {
  return apiFetch("/api/message/draft", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function logSent(contactId: string, jobId: string): Promise<{ messageId: string }> {
  return apiFetch("/api/message/sent", {
    method: "POST",
    body: JSON.stringify({ contactId, jobId }),
  });
}

export function logReply(messageId: string): Promise<void> {
  return apiFetch("/api/message/reply", {
    method: "POST",
    body: JSON.stringify({ messageId }),
  });
}

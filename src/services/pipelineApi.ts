const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export type Internship = {
  id: string;
  company: string;
  role: string;
  description: string;
  requirements: string;
  application_email?: string;
  source: string;
  role_match: number;
};

export type ContactResult = {
  id: string;
  name: string;
  role: string;
  company: string;
  linkedin_url: string;
  email: string | null;
  email_confidence: string;
  scores: {
    final: number;
    role_match: number;
    affinity: number;
    reachability: number;
  };
  reason: string;
};

export type PipelineResponse = {
  user: { id: string; name: string; email: string; university: string };
  internships: Internship[];
  contacts: ContactResult[];
  cv_text: string;
};

export type ContactsResponse = {
  company: string;
  role: string;
  contacts: ContactResult[];
};

export async function runPipeline(input: {
  targetRole: string;
  cvFile: File;
  userName: string;
  userEmail: string;
  university: string;
}): Promise<PipelineResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45000);
  const form = new FormData();
  form.append("target_role", input.targetRole);
  form.append("user_name", input.userName);
  form.append("user_email", input.userEmail);
  form.append("university", input.university);
  form.append("cv", input.cvFile);
  try {
    const response = await fetch(`${API_BASE}/api/pipeline/run`, {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
    if (!response.ok) throw new Error("Pipeline failed.");
    return (await response.json()) as PipelineResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Pipeline timed out. Please try a broader role or retry.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function generateMessages(input: {
  user_id: string;
  contact_id: string;
  internship_id: string;
}): Promise<{ email: string; linkedin: string }> {
  const response = await fetch(`${API_BASE}/api/outreach/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error("Message generation failed.");
  return (await response.json()) as { email: string; linkedin: string };
}

export async function getContactsByCompanyRole(input: {
  company: string;
  role: string;
}): Promise<ContactsResponse> {
  const query = new URLSearchParams({ company: input.company, role: input.role });
  const response = await fetch(`${API_BASE}/api/contacts?${query.toString()}`);
  if (!response.ok) throw new Error("Failed to load contacts.");
  return (await response.json()) as ContactsResponse;
}

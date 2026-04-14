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
  contact: {
    id: string;
    name: string;
    role: string;
    company: string;
    linkedin_url: string;
    education: string;
    seniority: string;
  };
  score: {
    final_score: number;
    role_match: number;
    affinity: number;
    reachability_score: number;
    email_confidence: number;
  };
  email: { email: string; confidence_label: string } | null;
  strategy: string;
  why_selected: string;
};

export type PipelineResponse = {
  user: { id: string; name: string; email: string; university: string };
  internships: Internship[];
  contacts: ContactResult[];
  cv_text: string;
};

export async function runPipeline(input: {
  targetRole: string;
  cvFile: File;
  userName: string;
  userEmail: string;
  university: string;
}): Promise<PipelineResponse> {
  const form = new FormData();
  form.append("target_role", input.targetRole);
  form.append("user_name", input.userName);
  form.append("user_email", input.userEmail);
  form.append("university", input.university);
  form.append("cv", input.cvFile);
  const response = await fetch(`${API_BASE}/api/pipeline/run`, { method: "POST", body: form });
  if (!response.ok) throw new Error("Pipeline failed.");
  return (await response.json()) as PipelineResponse;
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

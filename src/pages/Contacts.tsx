import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { loadPipelineResult, savePipelineResult } from "@/lib/pipelineState";
import { getContactsByCompanyRole, type ContactResult } from "@/services/pipelineApi";

function normalizeContact(item: unknown): ContactResult | null {
  if (!item || typeof item !== "object") return null;
  const row = item as Record<string, unknown>;

  // New API shape
  if (
    typeof row.id === "string" &&
    typeof row.name === "string" &&
    typeof row.role === "string" &&
    typeof row.company === "string" &&
    typeof row.linkedin_url === "string"
  ) {
    const scores = (row.scores ?? {}) as Record<string, unknown>;
    return {
      id: row.id,
      name: row.name,
      role: row.role,
      company: row.company,
      linkedin_url: row.linkedin_url,
      email: typeof row.email === "string" ? row.email : null,
      email_confidence: typeof row.email_confidence === "string" ? row.email_confidence : "NONE",
      scores: {
        final: typeof scores.final === "number" ? scores.final : 0,
        role_match: typeof scores.role_match === "number" ? scores.role_match : 0,
        affinity: typeof scores.affinity === "number" ? scores.affinity : 0,
        reachability: typeof scores.reachability === "number" ? scores.reachability : 0,
      },
      reason: typeof row.reason === "string" ? row.reason : "",
    };
  }

  // Legacy shape from earlier pipeline versions
  const contact = (row.contact ?? {}) as Record<string, unknown>;
  const score = (row.score ?? {}) as Record<string, unknown>;
  const email = (row.email ?? {}) as Record<string, unknown>;
  if (
    typeof contact.id === "string" &&
    typeof contact.name === "string" &&
    typeof contact.role === "string" &&
    typeof contact.company === "string" &&
    typeof contact.linkedin_url === "string"
  ) {
    return {
      id: contact.id,
      name: contact.name,
      role: contact.role,
      company: contact.company,
      linkedin_url: contact.linkedin_url,
      email: typeof email.email === "string" ? email.email : null,
      email_confidence: typeof email.confidence_label === "string" ? email.confidence_label : "NONE",
      scores: {
        final: typeof score.final_score === "number" ? score.final_score : 0,
        role_match: typeof score.role_match === "number" ? score.role_match : 0,
        affinity: typeof score.affinity === "number" ? score.affinity : 0,
        reachability: typeof score.reachability_score === "number" ? score.reachability_score : 0,
      },
      reason: typeof row.why_selected === "string" ? row.why_selected : "",
    };
  }

  return null;
}

export default function Contacts() {
  const result = loadPipelineResult();
  const [params] = useSearchParams();
  const company = params.get("company");
  const role = params.get("role");
  const [contacts, setContacts] = useState<ContactResult[]>(() =>
    ((result?.contacts ?? []) as unknown[]).map(normalizeContact).filter(Boolean) as ContactResult[]
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!company || !role || !result) return;
      setLoading(true);
      setError(null);
      try {
        const response = await getContactsByCompanyRole({ company, role });
        if (cancelled) return;
        const normalized = (response.contacts as unknown[])
          .map(normalizeContact)
          .filter(Boolean) as ContactResult[];
        setContacts(normalized);
        savePipelineResult({ ...result, contacts: normalized });
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load contacts.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
    // Intentionally avoid `result` as a dependency to prevent refetch loops
    // after writing updated contacts back to sessionStorage.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company, role]);

  if (!result) return <div className="p-8">Run dashboard first.</div>;
  return (
    <div className="min-h-screen p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Contacts</h1>
      {company && role && (
        <p className="text-sm text-muted-foreground mb-4">
          Showing top contacts for <strong>{company}</strong> - <strong>{role}</strong>
        </p>
      )}
      {loading && <p className="text-sm mb-4">Loading contacts...</p>}
      {error && <p className="text-sm mb-4 text-destructive">{error}</p>}
      {!loading && !error && contacts.length === 0 && (
        <p className="text-sm mb-4 text-muted-foreground">
          No contacts found for this company/role yet. Go back and run pipeline again.
        </p>
      )}
      <div className="space-y-3">
        {contacts.map((item) => (
          <div key={item.id} className="glass rounded p-4">
            <p className="font-semibold">{item.name} - {item.role}</p>
            <p className="text-sm">{item.company}</p>
            <p className="text-sm">Email: {item.email ?? "N/A"} ({item.email_confidence})</p>
            <p className="text-sm">
              Scores: role {item.scores.role_match.toFixed(2)}, affinity {item.scores.affinity.toFixed(2)},
              reachability {item.scores.reachability.toFixed(2)}
            </p>
            <p className="text-sm">Why selected: {item.reason}</p>
            <a className="underline text-sm" href={item.linkedin_url} target="_blank" rel="noreferrer">Open LinkedIn Profile</a>
          </div>
        ))}
      </div>
      <Link to="/outreach" className="inline-block mt-6 underline">Generate outreach</Link>
    </div>
  );
}

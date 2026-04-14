import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { loadPipelineResult, savePipelineResult } from "@/lib/pipelineState";
import { getContactsByCompanyRole, type ContactResult } from "@/services/pipelineApi";

export default function Contacts() {
  const result = loadPipelineResult();
  const [params] = useSearchParams();
  const company = params.get("company");
  const role = params.get("role");
  const [contacts, setContacts] = useState<ContactResult[]>(result?.contacts ?? []);
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
        setContacts(response.contacts);
        savePipelineResult({ ...result, contacts: response.contacts });
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
  }, [company, role, result]);

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

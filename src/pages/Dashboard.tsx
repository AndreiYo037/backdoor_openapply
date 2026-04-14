import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { runPipeline } from "@/services/pipelineApi";
import { savePipelineResult } from "@/lib/pipelineState";

export default function Dashboard() {
  const navigate = useNavigate();
  const [targetRole, setTargetRole] = useState("Software Engineer Intern");
  const [name, setName] = useState("Student");
  const [email, setEmail] = useState("student@example.com");
  const [university, setUniversity] = useState("National University of Singapore");
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!cvFile) return;
    setLoading(true);
    setError(null);
    try {
      const result = await runPipeline({
        targetRole,
        cvFile,
        userName: name,
        userEmail: email,
        university,
      });
      savePipelineResult(result);
      navigate("/internships");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background p-8 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      <form onSubmit={onSubmit} className="space-y-4 glass p-6 rounded-xl">
        <input className="w-full p-2 rounded bg-secondary" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
        <input className="w-full p-2 rounded bg-secondary" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input className="w-full p-2 rounded bg-secondary" value={university} onChange={(e) => setUniversity(e.target.value)} placeholder="University" />
        <input className="w-full p-2 rounded bg-secondary" value={targetRole} onChange={(e) => setTargetRole(e.target.value)} placeholder="Target role" />
        <input type="file" accept="application/pdf" onChange={(e) => setCvFile(e.target.files?.[0] ?? null)} />
        {error && <p className="text-destructive">{error}</p>}
        <button className="bg-primary text-primary-foreground px-4 py-2 rounded" disabled={!cvFile || loading}>
          {loading ? "Processing..." : "Run Discovery Pipeline"}
        </button>
      </form>
    </div>
  );
}

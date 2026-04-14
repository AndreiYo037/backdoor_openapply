import { Link } from "react-router-dom";
import { loadPipelineResult } from "@/lib/pipelineState";

export default function Internships() {
  const result = loadPipelineResult();
  if (!result) return <div className="p-8">Run dashboard first.</div>;
  return (
    <div className="min-h-screen p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Internships</h1>
      {result.internships.length === 0 ? (
        <div className="glass rounded p-4 text-sm text-muted-foreground">
          No internships were returned for this run. Try a broader target role (for example,
          "Software Engineer") and rerun the pipeline.
        </div>
      ) : (
        <div className="space-y-3">
          {result.internships.map((item) => (
            <div key={item.id} className="glass rounded p-4">
              <p className="font-semibold">{item.role}</p>
              <p className="text-sm text-muted-foreground">{item.company}</p>
              <p className="text-sm">Match: {(item.role_match * 100).toFixed(1)}%</p>
              <Link
                to={`/contacts?company=${encodeURIComponent(item.company)}&role=${encodeURIComponent(item.role)}`}
                className="inline-block mt-3 underline text-sm"
              >
                View top contacts
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

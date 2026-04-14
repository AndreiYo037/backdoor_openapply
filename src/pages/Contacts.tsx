import { Link } from "react-router-dom";
import { loadPipelineResult } from "@/lib/pipelineState";

export default function Contacts() {
  const result = loadPipelineResult();
  if (!result) return <div className="p-8">Run dashboard first.</div>;
  return (
    <div className="min-h-screen p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Contacts</h1>
      <div className="space-y-3">
        {result.contacts.map((item) => (
          <div key={item.contact.id} className="glass rounded p-4">
            <p className="font-semibold">{item.contact.name} - {item.contact.role}</p>
            <p className="text-sm">{item.contact.company}</p>
            <p className="text-sm">Email: {item.email?.email ?? "N/A"} ({item.email?.confidence_label ?? "NONE"})</p>
            <p className="text-sm">Why selected: {item.why_selected}</p>
            <a className="underline text-sm" href={item.contact.linkedin_url} target="_blank" rel="noreferrer">Open LinkedIn Search</a>
          </div>
        ))}
      </div>
      <Link to="/outreach" className="inline-block mt-6 underline">Generate outreach</Link>
    </div>
  );
}

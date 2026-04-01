import { useState } from "react";
import { Rocket, ExternalLink, CheckCircle, Clock, Zap, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

interface JobListing {
  id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  status: "pending" | "applied" | "backdoor";
  postedDate: string;
}

const mockJobs: JobListing[] = [
  { id: "1", title: "Senior Frontend Engineer", company: "Stripe", location: "San Francisco, CA", url: "#", status: "pending", postedDate: "2 days ago" },
  { id: "2", title: "Staff Software Engineer", company: "Plaid", location: "New York, NY", url: "#", status: "pending", postedDate: "1 day ago" },
  { id: "3", title: "Frontend Tech Lead", company: "Square", location: "Remote", url: "#", status: "applied", postedDate: "3 days ago" },
  { id: "4", title: "Senior React Developer", company: "Coinbase", location: "Remote", url: "#", status: "pending", postedDate: "5 hours ago" },
  { id: "5", title: "Software Engineer III", company: "Adyen", location: "London, UK", url: "#", status: "pending", postedDate: "1 day ago" },
  { id: "6", title: "Frontend Engineer", company: "Revolut", location: "London, UK", url: "#", status: "backdoor", postedDate: "4 days ago" },
];

const MassApply = () => {
  const [jobs, setJobs] = useState<JobListing[]>(mockJobs);
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const navigate = useNavigate();

  const toggleSelect = (id: string) => {
    setSelectedJobs((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleMassApply = () => {
    const count = selectedJobs.size;
    if (!count) {
      toast.error("Select at least one job");
      return;
    }
    setJobs((prev) =>
      prev.map((j) => (selectedJobs.has(j.id) ? { ...j, status: "applied" as const } : j))
    );
    setSelectedJobs(new Set());
    toast.success(`Auto-applying to ${count} jobs...`, {
      description: "Applications will be submitted with your saved profile.",
    });
  };

  const handleBackdoor = (job: JobListing) => {
    navigate(`/?backdoor=${encodeURIComponent(job.url)}&company=${encodeURIComponent(job.company)}`);
    toast.info(`Finding backdoor into ${job.company}...`);
  };

  const statusIcon = (status: string) => {
    if (status === "applied") return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    if (status === "backdoor") return <Zap className="w-4 h-4 text-primary" />;
    return <Clock className="w-4 h-4 text-muted-foreground" />;
  };

  const statusLabel = (status: string) => {
    if (status === "applied") return "Applied";
    if (status === "backdoor") return "Backdoored";
    return "Pending";
  };

  return (
    <div className="min-h-screen bg-background px-6 py-12">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-10">
          <div className="inline-flex p-3 rounded-xl bg-primary/10 border border-primary/20 mb-4">
            <Rocket className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Mass Apply</h1>
          <p className="text-muted-foreground">Autonomous job applications — select and let the bot handle the rest</p>
        </div>

        {/* Actions bar */}
        <div className="flex items-center justify-between mb-6">
          <div className="text-sm text-muted-foreground">
            {selectedJobs.size > 0 ? (
              <span className="text-primary font-medium">{selectedJobs.size} selected</span>
            ) : (
              `${jobs.length} jobs found`
            )}
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                setSelectedJobs(
                  selectedJobs.size === jobs.filter((j) => j.status === "pending").length
                    ? new Set()
                    : new Set(jobs.filter((j) => j.status === "pending").map((j) => j.id))
                )
              }
              className="border-border text-muted-foreground"
            >
              {selectedJobs.size > 0 ? "Deselect All" : "Select All Pending"}
            </Button>
            <Button
              size="sm"
              onClick={handleMassApply}
              disabled={selectedJobs.size === 0}
              className="bg-primary text-primary-foreground hover:bg-primary/90 glow-primary gap-1.5"
            >
              <Rocket className="w-3.5 h-3.5" />
              Auto-Apply ({selectedJobs.size})
            </Button>
          </div>
        </div>

        {/* Job list */}
        <div className="space-y-3">
          {jobs.map((job) => (
            <div
              key={job.id}
              className={`glass rounded-xl p-4 flex items-center gap-4 transition-all ${
                selectedJobs.has(job.id) ? "border-primary/50 glow-primary" : ""
              }`}
            >
              {job.status === "pending" && (
                <input
                  type="checkbox"
                  checked={selectedJobs.has(job.id)}
                  onChange={() => toggleSelect(job.id)}
                  className="w-4 h-4 rounded border-border accent-primary"
                />
              )}
              {job.status !== "pending" && <div className="w-4" />}

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold text-foreground truncate">{job.title}</h4>
                  <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
                <p className="text-sm text-muted-foreground">{job.company} · {job.location}</p>
                <p className="text-xs text-muted-foreground/60">{job.postedDate}</p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <span className="flex items-center gap-1 text-xs">
                  {statusIcon(job.status)}
                  <span className="text-muted-foreground">{statusLabel(job.status)}</span>
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleBackdoor(job)}
                  className="h-8 gap-1 text-xs text-primary hover:bg-primary/15 hover:text-primary"
                >
                  <Zap className="w-3.5 h-3.5" />
                  Backdoor This
                  <ArrowRight className="w-3 h-3" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MassApply;

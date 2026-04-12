import { useState } from "react";
import { Link2, Briefcase, ChevronDown, ChevronUp, Loader2 } from "lucide-react";

interface Props {
  onSubmit: (input: string) => void;
  isLoading: boolean;
}

const JOB_URL_PATTERN = /^https?:\/\/(www\.)?(linkedin\.com|mycareersfuture\.gov\.sg|glassdoor\.com|careers\.|jobs\.)/i;

function isJobUrl(val: string): boolean {
  return JOB_URL_PATTERN.test(val.trim());
}

export default function JobInput({ onSubmit, isLoading }: Props) {
  const [urlValue, setUrlValue] = useState("");
  const [showFallback, setShowFallback] = useState(false);
  const [titleValue, setTitleValue] = useState("");
  const [companyValue, setCompanyValue] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (showFallback) {
      if (!titleValue.trim() || !companyValue.trim()) return;
      onSubmit(`${titleValue.trim()} at ${companyValue.trim()}`);
    } else {
      if (!urlValue.trim()) return;
      onSubmit(urlValue.trim());
    }
  }

  const canSubmit = showFallback
    ? titleValue.trim().length > 0 && companyValue.trim().length > 0
    : urlValue.trim().length > 0;

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-2xl mx-auto px-6"
    >
      <div className="glass rounded-2xl p-4 border border-primary/20">
        {!showFallback ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-muted-foreground shrink-0">
              <Link2 className="w-4 h-4" />
            </div>
            <input
              type="url"
              value={urlValue}
              onChange={(e) => setUrlValue(e.target.value)}
              placeholder="Paste a job URL (LinkedIn, MyCareersFuture, Glassdoor…)"
              className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/60 outline-none"
              autoFocus
            />
            <button
              type="submit"
              disabled={!canSubmit || isLoading}
              className="shrink-0 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-40 hover:bg-primary/90 transition-colors flex items-center gap-2"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              Find people
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <Briefcase className="w-4 h-4 text-muted-foreground shrink-0" />
              <input
                type="text"
                value={titleValue}
                onChange={(e) => setTitleValue(e.target.value)}
                placeholder="Job title (e.g. Software Engineer)"
                className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/60 outline-none"
                autoFocus
              />
            </div>
            <div className="border-t border-border/30" />
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 shrink-0" />
              <input
                type="text"
                value={companyValue}
                onChange={(e) => setCompanyValue(e.target.value)}
                placeholder="Company name (e.g. Grab)"
                className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/60 outline-none"
              />
              <button
                type="submit"
                disabled={!canSubmit || isLoading}
                className="shrink-0 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-40 hover:bg-primary/90 transition-colors flex items-center gap-2"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Find people
              </button>
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={() => setShowFallback((v) => !v)}
        className="flex items-center gap-1 mx-auto mt-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {showFallback ? (
          <>
            <ChevronUp className="w-3 h-3" /> Paste a URL instead
          </>
        ) : (
          <>
            <ChevronDown className="w-3 h-3" /> No URL? Type job title + company
          </>
        )}
      </button>
    </form>
  );
}

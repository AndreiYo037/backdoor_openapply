import { AlertTriangle, ExternalLink } from "lucide-react";

interface Props {
  searchUrl: string;
}

export default function LinkedInFallbackCard({ searchUrl }: Props) {
  return (
    <div className="rounded-xl p-4 border border-amber-500/30 bg-amber-500/5 flex flex-col gap-3">
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-sm text-amber-200/80">
          We found fewer contacts than usual for this company. Try searching LinkedIn directly.
        </p>
      </div>
      <a
        href={searchUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 text-sm font-medium hover:bg-amber-500/20 transition-colors"
      >
        <ExternalLink className="w-4 h-4" />
        Search LinkedIn
      </a>
    </div>
  );
}

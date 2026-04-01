import { useState } from "react";
import { Search, Link, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SearchBarProps {
  onSearch: (query: string, type: "search" | "url") => void;
  isLoading?: boolean;
}

const SearchBar = ({ onSearch, isLoading }: SearchBarProps) => {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"search" | "url">("search");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) onSearch(query.trim(), mode);
  };

  const isUrl = query.startsWith("http") || query.includes("linkedin.com") || query.includes("indeed.com");

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div className="flex gap-2 mb-3">
        <button
          type="button"
          onClick={() => setMode("search")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
            mode === "search"
              ? "bg-primary/15 text-primary border border-primary/30"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Search className="w-3.5 h-3.5" />
          Search Jobs
        </button>
        <button
          type="button"
          onClick={() => setMode("url")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
            mode === "url"
              ? "bg-primary/15 text-primary border border-primary/30"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Link className="w-3.5 h-3.5" />
          Paste URL
        </button>
      </div>

      <div className="relative group">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/20 via-accent/20 to-primary/20 rounded-xl opacity-0 group-focus-within:opacity-100 transition-opacity blur" />
        <div className="relative flex items-center bg-card border border-border rounded-xl overflow-hidden focus-within:border-primary/50 transition-colors">
          {mode === "search" ? (
            <Search className="w-5 h-5 text-muted-foreground ml-4 shrink-0" />
          ) : (
            <Link className="w-5 h-5 text-muted-foreground ml-4 shrink-0" />
          )}
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (e.target.value.startsWith("http")) setMode("url");
            }}
            placeholder={
              mode === "search"
                ? "Search for a job title, company, or keywords..."
                : "Paste a job listing URL (LinkedIn, Indeed, etc.)..."
            }
            className="flex-1 bg-transparent px-3 py-4 text-foreground placeholder:text-muted-foreground focus:outline-none text-base"
          />
          <Button
            type="submit"
            disabled={!query.trim() || isLoading}
            className="m-2 bg-primary text-primary-foreground hover:bg-primary/90 glow-primary rounded-lg px-5"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                Analyze
                <ArrowRight className="w-4 h-4 ml-1" />
              </>
            )}
          </Button>
        </div>
      </div>

      {isUrl && mode === "search" && (
        <p className="text-xs text-muted-foreground mt-2 ml-1">
          Looks like a URL — switch to{" "}
          <button type="button" onClick={() => setMode("url")} className="text-primary underline">
            Paste URL
          </button>{" "}
          mode?
        </p>
      )}
    </form>
  );
};

export default SearchBar;

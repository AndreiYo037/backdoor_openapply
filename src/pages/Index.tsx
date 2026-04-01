import { useState } from "react";
import { Network, Zap, Shield, Eye } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import ResultsSection from "@/components/ResultsSection";
import NavLink from "@/components/NavLink";
import { mockPeople, mockProfiles, mockEvents } from "@/data/mockData";
import heroBg from "@/assets/hero-bg.jpg";
import { Search, FileText, Rocket } from "lucide-react";

const Index = () => {
  const [hasResults, setHasResults] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = (query: string, type: "search" | "url") => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setHasResults(true);
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img src={heroBg} alt="" className="w-full h-full object-cover opacity-20" width={1920} height={1080} />
          <div className="absolute inset-0 bg-gradient-to-b from-background/40 via-background/80 to-background" />
        </div>

        <div className="relative z-10 px-6 pt-8 pb-16">
          {/* Nav */}
          <nav className="flex items-center justify-between max-w-7xl mx-auto mb-16">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 glow-primary">
                <Network className="w-5 h-5 text-primary" />
              </div>
              <span className="font-bold text-lg text-foreground tracking-tight">
                backdoor<span className="text-primary">network</span>
              </span>
            </div>
            <div className="flex items-center gap-1">
              <NavLink to="/" icon={Search} label="Search" />
              <NavLink to="/cv-optimize" icon={FileText} label="CV Optimize" />
              <NavLink to="/mass-apply" icon={Rocket} label="Mass Apply" />
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="flex items-center gap-1 text-primary text-xs font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-glow" />
                BETA
              </span>
            </div>
          </nav>

          {/* Hero Content */}
          <div className="text-center max-w-3xl mx-auto mb-10">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight leading-tight">
              Find the <span className="text-primary text-glow">backdoor</span>
              <br />into your dream job
            </h1>
            <p className="text-lg text-muted-foreground max-w-xl mx-auto">
              Skip the application black hole. Discover the right people, compare profiles, and find networking events — all from a single search.
            </p>
          </div>

          {/* Search */}
          <SearchBar onSearch={handleSearch} isLoading={isLoading} />

          {/* Features */}
          {!hasResults && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto mt-12">
              {[
                { icon: Eye, title: "Identify Key People", desc: "Find hiring managers, recruiters, and team members at target companies" },
                { icon: Shield, title: "Compare Profiles", desc: "See who holds similar roles to benchmark your experience" },
                { icon: Zap, title: "Find Events", desc: "Discover networking events to make organic connections" },
              ].map(({ icon: Icon, title, desc }) => (
                <div key={title} className="glass rounded-xl p-4 text-center">
                  <div className="inline-flex p-2 rounded-lg bg-primary/10 border border-primary/20 mb-3">
                    <Icon className="w-5 h-5 text-primary" />
                  </div>
                  <h3 className="font-semibold text-foreground text-sm mb-1">{title}</h3>
                  <p className="text-xs text-muted-foreground">{desc}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      {hasResults && (
        <div className="px-6 pb-16">
          <ResultsSection people={mockPeople} profiles={mockProfiles} events={mockEvents} />
        </div>
      )}
    </div>
  );
};

export default Index;

import { Network } from "lucide-react";

const TopNav = () => (
  <nav className="flex items-center justify-between max-w-7xl mx-auto mb-10 px-6 pt-8">
    <div className="flex items-center gap-2">
      <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 glow-primary">
        <Network className="w-5 h-5 text-primary" />
      </div>
      <span className="font-bold text-lg text-foreground tracking-tight">
        backdoor<span className="text-primary">network</span>
      </span>
    </div>
    <div className="flex items-center gap-2 text-sm">
      <span className="flex items-center gap-1 text-primary text-xs font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-glow" />
        BETA
      </span>
    </div>
  </nav>
);

export default TopNav;

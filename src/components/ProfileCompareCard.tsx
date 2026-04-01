import { Briefcase, MapPin, GraduationCap, TrendingUp } from "lucide-react";

export interface ProfileData {
  id: string;
  name: string;
  currentTitle: string;
  company: string;
  location: string;
  experience: string;
  education: string;
  skills: string[];
  matchScore: number;
}

const ProfileCompareCard = ({ profile }: { profile: ProfileData }) => {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
    if (score >= 60) return "text-amber-400 bg-amber-400/10 border-amber-400/20";
    return "text-red-400 bg-red-400/10 border-red-400/20";
  };

  return (
    <div className="glass glass-hover rounded-xl p-4 animate-slide-up">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent/30 to-primary/20 flex items-center justify-center text-primary font-bold shrink-0 border border-primary/20">
            {profile.name.charAt(0)}
          </div>
          <div>
            <h4 className="font-semibold text-foreground">{profile.name}</h4>
            <p className="text-sm text-muted-foreground">{profile.currentTitle}</p>
          </div>
        </div>
        <span className={`text-xs font-mono px-2 py-1 rounded-md border ${getScoreColor(profile.matchScore)}`}>
          {profile.matchScore}% match
        </span>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Briefcase className="w-3.5 h-3.5 text-primary/60" />
          <span>{profile.company} · {profile.experience}</span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <MapPin className="w-3.5 h-3.5 text-primary/60" />
          <span>{profile.location}</span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <GraduationCap className="w-3.5 h-3.5 text-primary/60" />
          <span>{profile.education}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border/50">
        {profile.skills.slice(0, 5).map((skill) => (
          <span key={skill} className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-md">
            {skill}
          </span>
        ))}
        {profile.skills.length > 5 && (
          <span className="text-xs text-muted-foreground">+{profile.skills.length - 5}</span>
        )}
      </div>
    </div>
  );
};

export default ProfileCompareCard;

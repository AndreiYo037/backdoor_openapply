import { useState } from "react";
import { Upload, FileText, Sparkles, CheckCircle, AlertTriangle, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

const CVOptimize = () => {
  const [file, setFile] = useState<File | null>(null);
  const [jobUrl, setJobUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<null | {
    score: number;
    missingKeywords: string[];
    matchedKeywords: string[];
    suggestions: string[];
  }>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      toast.success(`Uploaded: ${f.name}`);
    }
  };

  const handleAnalyze = () => {
    if (!file) {
      toast.error("Please upload your CV first");
      return;
    }
    setIsAnalyzing(true);
    setTimeout(() => {
      setResults({
        score: 68,
        matchedKeywords: ["React", "TypeScript", "REST APIs", "Agile", "Git"],
        missingKeywords: ["GraphQL", "System Design", "CI/CD", "Kubernetes", "Microservices", "AWS"],
        suggestions: [
          "Add a dedicated 'Technical Skills' section highlighting GraphQL and cloud technologies",
          "Include specific metrics: team size managed, performance improvements, uptime percentages",
          "Mention CI/CD pipeline experience — even side projects count",
          "Add 'System Design' examples from your architecture decisions",
          "Tailor your summary to mention payment infrastructure experience",
        ],
      });
      setIsAnalyzing(false);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-background">
      <TopNav />
      <div className="max-w-4xl mx-auto px-6 pb-12">
        <div className="text-center mb-10">
          <div className="inline-flex p-3 rounded-xl bg-primary/10 border border-primary/20 mb-4">
            <FileText className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground mb-2">CV Optimizer</h1>
          <p className="text-muted-foreground">Upload your CV and match it against target job keywords</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Upload CV */}
          <div className="glass rounded-xl p-6">
            <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
              <Upload className="w-4 h-4 text-primary" /> Upload CV
            </h3>
            <label className="flex flex-col items-center justify-center border-2 border-dashed border-border/50 hover:border-primary/50 rounded-xl p-8 cursor-pointer transition-colors">
              <input type="file" accept=".pdf,.doc,.docx" onChange={handleFileChange} className="hidden" />
              {file ? (
                <>
                  <FileText className="w-10 h-10 text-primary mb-2" />
                  <span className="text-sm text-foreground font-medium">{file.name}</span>
                  <span className="text-xs text-muted-foreground mt-1">Click to replace</span>
                </>
              ) : (
                <>
                  <Upload className="w-10 h-10 text-muted-foreground mb-2" />
                  <span className="text-sm text-muted-foreground">Drop your CV here or click to browse</span>
                  <span className="text-xs text-muted-foreground mt-1">PDF, DOC, DOCX</span>
                </>
              )}
            </label>
          </div>

          {/* Job URL */}
          <div className="glass rounded-xl p-6">
            <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" /> Target Job
            </h3>
            <Input
              placeholder="Paste job listing URL..."
              value={jobUrl}
              onChange={(e) => setJobUrl(e.target.value)}
              className="mb-4 bg-secondary/50 border-border"
            />
            <p className="text-xs text-muted-foreground mb-4">Or paste keywords manually to compare against</p>
            <Button
              onClick={handleAnalyze}
              disabled={!file || isAnalyzing}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90 glow-primary"
            >
              {isAnalyzing ? (
                <>
                  <Sparkles className="w-4 h-4 animate-spin mr-2" /> Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" /> Optimize CV
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Results */}
        {results && (
          <div className="space-y-6 animate-fade-in">
            {/* Score */}
            <div className="glass rounded-xl p-6 text-center">
              <p className="text-sm text-muted-foreground mb-2">Keyword Match Score</p>
              <div className="text-5xl font-bold text-primary text-glow mb-2">{results.score}%</div>
              <p className="text-sm text-muted-foreground">
                {results.score >= 80 ? "Great match!" : results.score >= 60 ? "Good, but room to improve" : "Needs significant optimization"}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Matched */}
              <div className="glass rounded-xl p-6">
                <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" /> Matched Keywords
                </h3>
                <div className="flex flex-wrap gap-2">
                  {results.matchedKeywords.map((kw) => (
                    <span key={kw} className="text-xs bg-emerald-400/10 text-emerald-400 border border-emerald-400/20 px-2 py-1 rounded-md">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>

              {/* Missing */}
              <div className="glass rounded-xl p-6">
                <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" /> Missing Keywords
                </h3>
                <div className="flex flex-wrap gap-2">
                  {results.missingKeywords.map((kw) => (
                    <span key={kw} className="text-xs bg-amber-400/10 text-amber-400 border border-amber-400/20 px-2 py-1 rounded-md">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Suggestions */}
            <div className="glass rounded-xl p-6">
              <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-primary" /> Optimization Suggestions
              </h3>
              <ul className="space-y-3">
                {results.suggestions.map((s, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-muted-foreground">
                    <span className="text-xs font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded mt-0.5 shrink-0">{i + 1}</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CVOptimize;

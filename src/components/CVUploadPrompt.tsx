import { useRef, useState } from "react";
import { FileText, Loader2, Upload, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { uploadCV } from "@/services/api";

interface Props {
  open: boolean;
  onDone: (cvText: string) => void;
  onSkip: () => void;
}

export default function CVUploadPrompt({ open, onDone, onSkip }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.type !== "application/pdf") {
      setError("Please upload a PDF file.");
      return;
    }
    setError(null);
    setFile(f);
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const { text } = await uploadCV(file);
      onDone(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Try again.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onSkip(); }}>
      <DialogContent className="glass border-border/50 max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-foreground">Add your CV</DialogTitle>
          <DialogDescription className="text-muted-foreground text-sm">
            Claude uses your CV to personalise the cold message. Upload once — it's remembered for this session.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 mt-2">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="flex flex-col items-center gap-2 rounded-xl border-2 border-dashed border-border/50 hover:border-primary/40 p-6 transition-colors group"
          >
            {file ? (
              <>
                <FileText className="w-8 h-8 text-primary" />
                <span className="text-sm text-foreground font-medium">{file.name}</span>
                <span className="text-xs text-muted-foreground">Click to change</span>
              </>
            ) : (
              <>
                <Upload className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
                <span className="text-sm text-muted-foreground">Click to upload PDF</span>
              </>
            )}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleFileChange}
          />

          {error && (
            <p className="text-xs text-destructive flex items-center gap-1">
              <X className="w-3 h-3" /> {error}
            </p>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleUpload}
              disabled={!file || uploading}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-40 hover:bg-primary/90 transition-colors"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              Use this CV
            </button>
            <button
              type="button"
              onClick={onSkip}
              className="px-4 py-2 rounded-lg border border-border/50 text-muted-foreground text-sm hover:text-foreground hover:border-border transition-colors"
            >
              Skip
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

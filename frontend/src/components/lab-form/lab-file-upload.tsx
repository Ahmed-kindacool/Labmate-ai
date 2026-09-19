import * as React from "react";
import { AlertCircle, FileText, Upload, X } from "lucide-react";

import { cn } from "@/lib/utils";

// Mirrors backend/app/validation/lab_file.py (ACCEPTED_LAB_MIME_TYPES,
// MAX_LAB_FILE_SIZE_BYTES) so the UI can reject bad files instantly instead
// of waiting on a round trip. The backend re-validates regardless — this is
// UX only, not the source of truth.
const ACCEPTED_LAB_MIME_TYPES = new Set([
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

const ACCEPTED_EXTENSIONS = ".pdf,.doc,.docx";

const MAX_LAB_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB — PROJECT_SPEC.md §2

function validateLabFileClientSide(file: File): string | null {
  // Same order and copy as validate_lab_file() on the backend: type before
  // size, identical messages, so a client-caught error and a server-caught
  // error look the same to the user.
  if (!ACCEPTED_LAB_MIME_TYPES.has(file.type)) {
    return "Unsupported file type. Please upload a PDF, DOC, or DOCX file.";
  }
  if (file.size > MAX_LAB_FILE_SIZE_BYTES) {
    return "File is too large. Maximum size is 10MB.";
  }
  return null;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export interface LabFileUploadProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  error?: string | null;
  onErrorChange?: (error: string | null) => void;
  disabled?: boolean;
}

/**
 * Phase 2 (Dev A scope): drag-and-drop upload, file name display,
 * type/size validation UX, error messages. Wiring this into the full
 * student-info form and the POST /api/v1/labs/generate submit is a
 * separate "Together" step per API_CONTRACT.md.
 */
export function LabFileUpload({
  file,
  onFileChange,
  error,
  onErrorChange,
  disabled = false,
}: LabFileUploadProps) {
  const [isDragging, setIsDragging] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleFile = React.useCallback(
    (candidate: File | undefined) => {
      if (!candidate) return;
      const validationError = validateLabFileClientSide(candidate);
      if (validationError) {
        onFileChange(null);
        onErrorChange?.(validationError);
        return;
      }
      onErrorChange?.(null);
      onFileChange(candidate);
    },
    [onFileChange, onErrorChange]
  );

  const handleRemove = () => {
    onFileChange(null);
    onErrorChange?.(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="grid gap-2">
      <label htmlFor="lab-file-input" className="text-sm font-medium leading-none">
        Lab file
      </label>

      {file ? (
        <div className="flex items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm">
          <div className="flex min-w-0 items-center gap-2">
            <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <div className="min-w-0">
              <p className="truncate font-medium">{file.name}</p>
              <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRemove}
            disabled={disabled}
            className="rounded-md p-1 text-muted-foreground outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
            aria-label={`Remove ${file.name}`}
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      ) : (
        <div
          role="button"
          tabIndex={disabled ? -1 : 0}
          aria-disabled={disabled}
          aria-describedby={error ? "lab-file-error" : undefined}
          onClick={() => !disabled && inputRef.current?.click()}
          onKeyDown={(event) => {
            if (disabled) return;
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragOver={(event) => {
            event.preventDefault();
            if (!disabled) setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setIsDragging(false);
            if (disabled) return;
            handleFile(event.dataTransfer.files?.[0]);
          }}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed px-6 py-8 text-center transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            isDragging ? "border-primary bg-accent" : "border-input hover:bg-accent/50",
            error && "border-destructive",
            disabled && "pointer-events-none opacity-50"
          )}
        >
          <Upload className="size-5 text-muted-foreground" aria-hidden="true" />
          <p className="text-sm">
            <span className="font-medium text-primary">Click to upload</span> or drag and drop
          </p>
          <p className="text-xs text-muted-foreground">PDF, DOC, or DOCX — up to 10MB</p>
        </div>
      )}

      <input
        ref={inputRef}
        id="lab-file-input"
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        className="sr-only"
        disabled={disabled}
        onChange={(event) => handleFile(event.target.files?.[0])}
      />

      {error && (
        <p id="lab-file-error" role="alert" className="flex items-center gap-1.5 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  );
}

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

export interface GenerationErrorProps {
  /** Always a real message: either the backend's own GenerateErrorResponse
   * message (backend/app/schemas/generate.py), or the one client-authored
   * message used when the request never reached the server at all. */
  message: string;
  onRetry: () => void;
}

/**
 * Shown when generation fails. `message` is never invented here — it's the
 * backend's own copy where one exists (same contract-driven approach as the
 * attendance module: written once server-side, shown verbatim), or the one
 * explicit network-failure string when there was no server response at all.
 */
export function GenerationError({ message, onRetry }: GenerationErrorProps) {
  return (
    <div
      role="alert"
      className="grid gap-3 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-5 text-center"
    >
      <div className="flex flex-col items-center gap-2">
        <AlertTriangle className="size-5 text-destructive" aria-hidden="true" />
        <p className="text-sm font-medium text-foreground">Report generation failed</p>
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
      <Button type="button" variant="outline" onClick={onRetry} className="mx-auto">
        Try again
      </Button>
    </div>
  );
}

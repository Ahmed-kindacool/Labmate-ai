import { AlertOctagon, Clock, Loader2, Terminal, XCircle } from "lucide-react";
import type { ComponentType } from "react";

// Matches the real Pydantic model in backend/app/execution/__init__.py
// (ExecutionResult: output, success, error) as implemented by Dev C's
// PythonExecutor — NOT the richer status/stdout/stderr/exitCode shape
// sketched in docs/AI_AND_GENERATION.md and currently sitting in
// types/lab.ts's `ExecutionResult`, which the real implementation doesn't
// return. Named differently here on purpose so it isn't mistaken for that
// stale type; frontend/src/types/lab.ts still needs reconciling with the
// real backend, separately from this component.
export interface ExecutionOutcome {
  output: string;
  success: boolean;
  error?: string | null;
}

export type ExecutionUiState = "running" | "done";

export interface ExecutionOutputProps {
  state: ExecutionUiState;
  result?: ExecutionOutcome;
  /** Optional label for which task this ran, e.g. "task1.py". */
  taskLabel?: string;
}

/**
 * The backend currently returns a single freeform `error` label rather than
 * a strict status enum (today: "Runtime Error", or a Docker-image message).
 * This maps that label to a category for icon/copy purposes without
 * asserting a category the backend didn't actually report — anything that
 * doesn't match a known keyword still renders, just as a generic failure.
 */
function categorizeError(error: string | null | undefined): {
  label: string;
  Icon: ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
} {
  const normalized = (error ?? "").toLowerCase();
  if (normalized.includes("timeout")) {
    return { label: error ?? "Timed out", Icon: Clock };
  }
  if (normalized.includes("compile")) {
    return { label: error ?? "Compile error", Icon: AlertOctagon };
  }
  return { label: error ?? "Execution failed", Icon: XCircle };
}

/**
 * Phase 4 (Dev A scope): running/success/runtime-error/compile-error/timeout
 * states and output display. Per docs/AI_AND_GENERATION.md's anti-
 * fabrication rule, this only ever renders `result.output` /
 * `result.error` as given — it never invents or guesses at output.
 */
export function ExecutionOutput({ state, result, taskLabel }: ExecutionOutputProps) {
  if (state === "running") {
    return (
      <div className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        <span>Running{taskLabel ? ` ${taskLabel}` : " code"}…</span>
      </div>
    );
  }

  if (!result) return null;

  if (result.success) {
    return (
      <div className="grid gap-2">
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <Terminal className="size-3.5" aria-hidden="true" />
          <span>Output</span>
        </div>
        <pre className="overflow-x-auto rounded-md bg-muted px-3 py-2 text-xs">
          <code>{result.output || "(no output)"}</code>
        </pre>
      </div>
    );
  }

  const { label, Icon } = categorizeError(result.error);

  return (
    <div
      role="alert"
      className="grid gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-3"
    >
      <div className="flex items-center gap-1.5 text-xs font-medium text-destructive">
        <Icon className="size-3.5" aria-hidden="true" />
        <span>{label}</span>
      </div>
      {result.output && (
        <pre className="overflow-x-auto rounded-md bg-background px-3 py-2 text-xs text-muted-foreground">
          <code>{result.output}</code>
        </pre>
      )}
    </div>
  );
}

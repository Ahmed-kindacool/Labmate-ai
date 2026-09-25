import { Clock, Loader2, Terminal, XCircle } from "lucide-react";

import type { ExecutionResult } from "@/types/lab";

// Historical note: an earlier version of this file matched a competing
// {output, success, error} shape from a since-reverted backend
// implementation (see docs/DOCX_GENERATION.md / PROJECT_HANDOFF.md's
// Phase 5 merge-conflict incident). The real, current backend contract
// is ExecutionResult from types/lab.ts (status/stdout/stderr/exit_code) --
// this component now renders that shape directly, with no translation.

export type ExecutionUiState = "running" | "done";

export interface ExecutionOutputProps {
  state: ExecutionUiState;
  result?: ExecutionResult;
  /** Optional label for which task this ran, e.g. "task1.py". */
  taskLabel?: string;
}

const STATUS_COPY: Record<ExecutionResult["status"], string> = {
  success: "Ran successfully",
  failed: "Runtime error",
  timeout: "Timed out",
  unsupported: "Execution not supported for this language",
};

/**
 * Phase 4 (Dev A scope) + Phase 8 wiring: running/success/failed/timeout/
 * unsupported states and output display. Per AI_AND_GENERATION.md's
 * anti-fabrication rule, this only ever renders `result.stdout` /
 * `result.stderr` as given -- it never invents or guesses at output.
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

  if (result.status === "success") {
    return (
      <div className="grid gap-2">
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <Terminal className="size-3.5" aria-hidden="true" />
          <span>Output</span>
        </div>
        <pre className="overflow-x-auto rounded-md bg-muted px-3 py-2 text-xs">
          <code>{result.stdout || "(no output)"}</code>
        </pre>
      </div>
    );
  }

  if (result.status === "unsupported") {
    return (
      <div className="flex items-center gap-1.5 rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
        <Terminal className="size-3.5 shrink-0" aria-hidden="true" />
        <span>{STATUS_COPY.unsupported}</span>
      </div>
    );
  }

  const Icon = result.status === "timeout" ? Clock : XCircle;

  return (
    <div
      role="alert"
      className="grid gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-3"
    >
      <div className="flex items-center gap-1.5 text-xs font-medium text-destructive">
        <Icon className="size-3.5" aria-hidden="true" />
        <span>{STATUS_COPY[result.status]}</span>
      </div>
      {result.stderr && (
        <pre className="overflow-x-auto rounded-md bg-background px-3 py-2 text-xs text-muted-foreground">
          <code>{result.stderr}</code>
        </pre>
      )}
    </div>
  );
}

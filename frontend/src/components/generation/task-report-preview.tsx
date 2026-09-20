import { CheckCircle2, XCircle } from "lucide-react";

import type { GeneratedTaskSolution } from "@/types/lab";
import type { ExecutionOutcome } from "./execution-output";

export interface TaskReportPreviewProps {
  task: GeneratedTaskSolution;
  /** Omit when this task hasn't been executed yet — renders a plain
   * "not yet executed" placeholder rather than an empty/fake terminal. */
  execution?: ExecutionOutcome;
}

// Mirrors backend/app/screenshots/__init__.py's generate_terminal_screenshot
// HTML/CSS token-for-token (#1e1e1e window, red/yellow/green traffic-light
// dots, Courier New, 2000-char truncation) so this preview looks like the
// actual screenshot that gets embedded in the DOCX, not an approximation of
// it. That function renders whatever `output` string it's given regardless
// of success/failure — this does the same for visual fidelity, and only
// adds the pass/fail badge above the window as extra, non-visual info.
const TERMINAL_OUTPUT_CHAR_LIMIT = 2000;

function truncateForTerminal(output: string): string {
  return output.length > TERMINAL_OUTPUT_CHAR_LIMIT
    ? `${output.slice(0, TERMINAL_OUTPUT_CHAR_LIMIT)}\n...[Output Truncated]`
    : output;
}

function TerminalWindow({ output }: { output: string }) {
  return (
    <div
      className="overflow-hidden rounded-lg shadow-lg"
      style={{ backgroundColor: "#1e1e1e", fontFamily: "'Courier New', Courier, monospace" }}
    >
      <div className="flex gap-2 px-3 py-2.5" style={{ backgroundColor: "#2d2d2d" }}>
        <span className="size-3 rounded-full" style={{ backgroundColor: "#ff5f56" }} />
        <span className="size-3 rounded-full" style={{ backgroundColor: "#ffbd2e" }} />
        <span className="size-3 rounded-full" style={{ backgroundColor: "#27c93f" }} />
      </div>
      <pre
        className="whitespace-pre-wrap break-words px-4 py-4 text-sm leading-relaxed"
        style={{ color: "#d4d4d4" }}
      >
        <code>{truncateForTerminal(output)}</code>
      </pre>
    </div>
  );
}

export function TaskReportPreview({ task, execution }: TaskReportPreviewProps) {
  return (
    <section className="grid gap-3 border-b pb-6 last:border-b-0 last:pb-0">
      <div>
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {task.filename}
        </p>
        <h3 className="text-sm font-semibold text-foreground">{task.description}</h3>
      </div>

      <pre className="overflow-x-auto rounded-md bg-muted px-3 py-2 text-xs">
        <code>{task.code}</code>
      </pre>

      <p className="text-sm text-muted-foreground">{task.explanation}</p>

      {execution ? (
        <div className="grid gap-1.5">
          <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            {execution.success ? (
              <CheckCircle2 className="size-3.5 text-primary" aria-hidden="true" />
            ) : (
              <XCircle className="size-3.5 text-destructive" aria-hidden="true" />
            )}
            <span>{execution.success ? "Ran successfully" : (execution.error ?? "Execution failed")}</span>
          </div>
          <TerminalWindow output={execution.output} />
        </div>
      ) : (
        <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
          Not yet executed — no output to preview.
        </p>
      )}
    </section>
  );
}

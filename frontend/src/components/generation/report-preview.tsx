import { TaskReportPreview } from "./task-report-preview";
import type { ExecutionResult, GeneratedLab } from "@/types/lab";

export interface ReportPreviewProps {
  lab: GeneratedLab;
  /** Keyed by GeneratedTaskSolution.id. A task with no entry here renders
   * as "not yet executed" — see TaskReportPreview. */
  executions?: Record<string, ExecutionResult>;
}

/**
 * Phase 5 (Dev A scope): a preview of what the generated report will
 * actually contain once python-docx assembles it (Phase 7) — question, code
 * block, and a terminal-style output block matching Dev C's real screenshot
 * renderer. This is deliberately separate from SolutionList (Phase 3): that
 * one is an interactive review/browse UI (collapsible cards); this one is a
 * static, page-like preview of the final document layout.
 */
export function ReportPreview({ lab, executions }: ReportPreviewProps) {
  return (
    <article className="grid gap-6 rounded-lg border bg-card px-6 py-8 shadow-sm">
      <header className="grid gap-2 border-b pb-4">
        <h2 className="text-lg font-semibold text-foreground">{lab.lab_title}</h2>
        {lab.objectives.length > 0 && (
          <ul className="list-disc pl-5 text-sm text-muted-foreground">
            {lab.objectives.map((objective) => (
              <li key={objective}>{objective}</li>
            ))}
          </ul>
        )}
      </header>

      <div className="grid gap-6">
        {lab.tasks.map((task) => (
          <TaskReportPreview key={task.id} task={task} execution={executions?.[task.id]} />
        ))}
      </div>

      {lab.conclusion && (
        <footer className="border-t pt-4">
          <p className="text-sm text-muted-foreground">{lab.conclusion}</p>
        </footer>
      )}
    </article>
  );
}

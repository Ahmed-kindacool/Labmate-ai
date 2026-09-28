import { ReportPage } from "./report-page";
import { ReportTitlePage } from "./report-title-page";
import { TaskReportPreview } from "./task-report-preview";
import type { StudentInfo } from "@/types/api";
import type { ExecutionResult, GeneratedLab } from "@/types/lab";

export interface ReportPreviewProps {
  lab: GeneratedLab;
  /** Keyed by GeneratedTaskSolution.id. */
  executions?: Record<string, ExecutionResult>;
  /** GenerateSuccessResponse.screenshots as-is: task id -> base64 PNG, or
   * null when no screenshot was captured at all. */
  screenshots?: Record<string, string> | null;
  /** The student info the report was actually generated from. Without it
   * there's no cover page to show. */
  student?: StudentInfo;
}

/**
 * A preview of the generated .docx: the university's cover page, then the
 * task sections, laid out as white US Letter "pages" with the real
 * template margins (see ReportPage). Content and order mirror what
 * DocxGenerator writes -- the cover fields per university, then each
 * task's heading, description, code and output -- and deliberately leave
 * out what it doesn't write (the AI's objectives, per-task explanations
 * and conclusion never reach the document).
 *
 * Distinct from SolutionList (Phase 3), the interactive collapsible
 * review UI; this is the static document preview.
 *
 * Not simulated: page headers/footers and where pages break -- see
 * ReportPage.
 */
export function ReportPreview({ lab, executions, screenshots, student }: ReportPreviewProps) {
  const university = student && student.university !== "" ? student.university : undefined;

  return (
    <div className="grid gap-4">
      {student && <ReportTitlePage student={student} labTitle={lab.lab_title} />}

      {lab.tasks.length > 0 && (
        <ReportPage university={university} className="grid gap-6">
          {lab.tasks.map((task, index) => (
            <TaskReportPreview
              key={task.id}
              task={task}
              index={index + 1}
              execution={executions?.[task.id]}
              screenshot={screenshots?.[task.id]}
            />
          ))}
        </ReportPage>
      )}
    </div>
  );
}

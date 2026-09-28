import type { ExecutionResult, GeneratedTaskSolution } from "@/types/lab";

export interface TaskReportPreviewProps {
  task: GeneratedTaskSolution;
  /** 1-based position of this task in the report ("Task 1: ..."). */
  index: number;
  /** The task's real ExecutionResult, if it ran. */
  execution?: ExecutionResult;
  /** The real captured terminal screenshot for this task: a base64-encoded
   * PNG, exactly as GenerateSuccessResponse.screenshots carries it. */
  screenshot?: string;
}

// Mirrors DocxGenerator._build_sequential_content
// (backend/app/documents/docx_generator.py), section by section, so the
// preview shows what the generated document will contain:
//
//   "Task N: <filename>"           bold heading
//   <description>                  plain paragraph
//   "Implementation:"              bold label
//   <code>                         dark IDE block (1x1 table, #1E1E1E fill,
//                                  #D4D4D4 monospace text) -- or
//                                  "(No code provided)" for empty code
//   "Execution Output:"            bold label
//   <output>                       the real screenshot image if one was
//                                  captured; else a dark IDE block with
//                                  stdout (success) / stderr (failed,
//                                  timeout); else
//                                  "(No execution output available)"
//
// The document does not include the AI's per-task explanation, so neither
// does this preview.
const IDE_BACKGROUND = "#1E1E1E";
const IDE_TEXT = "#D4D4D4";
const IDE_FONT = "Consolas, 'Courier New', monospace";

function IdeBlock({ text }: { text: string }) {
  return (
    <div className="w-full" style={{ backgroundColor: IDE_BACKGROUND }}>
      <pre
        className="px-2 py-1.5 text-[11px] leading-snug whitespace-pre-wrap break-words"
        style={{ color: IDE_TEXT, fontFamily: IDE_FONT }}
      >
        <code>{text}</code>
      </pre>
    </div>
  );
}

// Same rule as DocxGenerator._write_task_output's text fallback: only
// success / failed / timeout results have text to show. An "unsupported"
// result (e.g. no Docker) falls through to the plain "no output" line, the
// same as the document does.
function fallbackOutputText(execution: ExecutionResult | undefined): string | null {
  if (!execution || execution.status === "unsupported") return null;
  const text = execution.status === "success" ? execution.stdout : execution.stderr;
  return text.trim() || "(no terminal output)";
}

export function TaskReportPreview({ task, index, execution, screenshot }: TaskReportPreviewProps) {
  const outputText = fallbackOutputText(execution);

  return (
    <section className="grid gap-2 text-[13px] leading-relaxed">
      <h3 className="text-[15px] font-bold">
        Task {index}: {task.filename}
      </h3>

      {task.description && <p>{task.description}</p>}

      <p className="font-bold">Implementation:</p>
      {task.code.trim() ? <IdeBlock text={task.code} /> : <p>(No code provided)</p>}

      <p className="font-bold">Execution Output:</p>
      {screenshot ? (
        <img
          src={`data:image/png;base64,${screenshot}`}
          alt={`Terminal output of ${task.filename}`}
          className="w-[92%]"
        />
      ) : outputText !== null ? (
        <IdeBlock text={outputText} />
      ) : (
        <p>(No execution output available)</p>
      )}
    </section>
  );
}

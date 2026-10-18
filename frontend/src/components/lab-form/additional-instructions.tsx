import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// Mirrors MAX_ADDITIONAL_INSTRUCTIONS_CHARS in
// backend/app/validation/additional_instructions.py (the backend re-validates;
// this only gives instant feedback).
export const MAX_ADDITIONAL_INSTRUCTIONS_CHARS = 2000;

// One-click starting points. Each is appended as its own line, so several can
// be combined and the student can edit the wording freely afterwards.
const SUGGESTIONS = [
  { label: "Introduction", text: "Add an Introduction section explaining the purpose and background of this lab." },
  { label: "Viva questions", text: "Add 5 viva questions with short answers about the concepts used in this lab." },
  { label: "Comparison table", text: "Add a comparison table of the approaches or concepts used in this lab." },
  { label: "Discussion", text: "Add a Discussion section analysing the results and what was learned." },
  { label: "References", text: "Add a References section listing the sources for the concepts used." },
] as const;

export interface AdditionalInstructionsProps {
  value: string;
  onChange: (value: string) => void;
  /** From GenerateErrorResponse.field_errors["additional_instructions"]. */
  errors?: string[];
  disabled?: boolean;
}

/**
 * Optional free-text box: "anything else you'd like in the report?". Sent to
 * the AI as the student's own requests, in addition to what the lab manual
 * asks for (extra sections, tables, code, a different emphasis...).
 */
export function AdditionalInstructions({
  value,
  onChange,
  errors,
  disabled = false,
}: AdditionalInstructionsProps) {
  const remaining = MAX_ADDITIONAL_INSTRUCTIONS_CHARS - value.length;
  const overLimit = remaining < 0;
  const hasError = overLimit || Boolean(errors?.length);

  const addSuggestion = (text: string) => {
    if (value.includes(text)) return;
    onChange(value.trim() ? `${value.trimEnd()}\n${text}` : text);
  };

  return (
    <div className="grid gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <Label htmlFor="additional-instructions">
          Anything else you&apos;d like in the report?{" "}
          <span className="font-normal text-muted-foreground">(optional)</span>
        </Label>
        <span
          className={overLimit ? "text-xs text-destructive" : "text-xs text-muted-foreground"}
          aria-live="polite"
        >
          {value.length} / {MAX_ADDITIONAL_INSTRUCTIONS_CHARS}
        </span>
      </div>

      <Textarea
        id="additional-instructions"
        value={value}
        disabled={disabled}
        placeholder="e.g. Add an introduction, include a table comparing the two approaches, and write a short discussion of the results."
        aria-invalid={hasError ? true : undefined}
        aria-describedby="additional-instructions-help"
        onChange={(event) => onChange(event.target.value)}
      />

      <p id="additional-instructions-help" className="text-xs text-muted-foreground">
        These are added on top of what your lab manual asks for. They can add sections, tables or
        extra code, but can&apos;t change the report&apos;s fonts or layout.
      </p>

      {hasError && (
        <p role="alert" className="text-xs text-destructive">
          {overLimit
            ? `Too long by ${-remaining} characters.`
            : errors?.join(" ")}
        </p>
      )}

      <div className="flex flex-wrap gap-2" aria-label="Quick suggestions">
        {SUGGESTIONS.map(({ label, text }) => (
          <button
            key={label}
            type="button"
            disabled={disabled}
            onClick={() => addSuggestion(text)}
            className="rounded-full border border-input px-3 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-50"
          >
            + {label}
          </button>
        ))}
      </div>
    </div>
  );
}

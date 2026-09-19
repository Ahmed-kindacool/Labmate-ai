import { Check, Circle, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

// Step copy and order taken verbatim from docs/TEMPLATES_AND_UI.md "Progress":
//   ✓ Lab uploaded
//   ✓ Lab analyzed
//   → Generating solution
//   ○ Running code
//   ○ Creating report
const STEPS = [
  "Lab uploaded",
  "Lab analyzed",
  "Generating solution",
  "Running code",
  "Creating report",
] as const;

export type GenerationStepStatus = "done" | "active" | "pending";

export interface GenerationProgressProps {
  /** Index (0-based) of the step currently in progress. Steps before it are
   * done, steps after it are pending. */
  currentStep: number;
  className?: string;
}

export function GenerationProgress({ currentStep, className }: GenerationProgressProps) {
  return (
    <ol className={cn("grid gap-3", className)} aria-label="Report generation progress">
      {STEPS.map((label, index) => {
        const status: GenerationStepStatus =
          index < currentStep ? "done" : index === currentStep ? "active" : "pending";

        return (
          <li key={label} className="flex items-center gap-3 text-sm">
            <span
              aria-hidden="true"
              className={cn(
                "flex size-5 shrink-0 items-center justify-center rounded-full",
                status === "done" && "bg-primary text-primary-foreground",
                status === "active" && "text-primary",
                status === "pending" && "text-muted-foreground"
              )}
            >
              {status === "done" && <Check className="size-3.5" />}
              {status === "active" && <Loader2 className="size-4 animate-spin" />}
              {status === "pending" && <Circle className="size-3.5" />}
            </span>
            <span
              className={cn(
                status === "done" && "text-foreground",
                status === "active" && "font-medium text-foreground",
                status === "pending" && "text-muted-foreground"
              )}
            >
              {label}
              <span className="sr-only">
                {" — "}
                {status === "done" && "complete"}
                {status === "active" && "in progress"}
                {status === "pending" && "not started"}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

import * as React from "react";
import { ChevronDown, Code2 } from "lucide-react";

import { cn } from "@/lib/utils";
import type { GeneratedTaskSolution } from "@/types/lab";

export interface TaskSolutionCardProps {
  task: GeneratedTaskSolution;
  defaultOpen?: boolean;
}

/**
 * One task from a GeneratedLab (see backend/app/schemas/lab.py ->
 * GeneratedTaskSolution): the original question, collapsed by default, that
 * expands to show the generated code + explanation. Execution
 * output/screenshots aren't part of this shape yet (Phase 4/5, Dev C) — this
 * only renders what the AI service is contracted to return.
 */
export function TaskSolutionCard({ task, defaultOpen = false }: TaskSolutionCardProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);
  const contentId = `task-solution-${task.id}`;

  return (
    <div className="rounded-lg border">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        aria-controls={contentId}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <div className="min-w-0">
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {task.filename}
          </p>
          <p className="text-sm font-medium text-foreground">{task.description}</p>
        </div>
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground transition-transform",
            isOpen && "rotate-180"
          )}
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div id={contentId} className="grid gap-3 border-t px-4 py-4">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Code2 className="size-3.5" aria-hidden="true" />
            <span className="capitalize">{task.language}</span>
          </div>
          <pre className="overflow-x-auto rounded-md bg-muted px-3 py-2 text-xs">
            <code>{task.code}</code>
          </pre>
          <p className="text-sm text-muted-foreground">{task.explanation}</p>
        </div>
      )}
    </div>
  );
}

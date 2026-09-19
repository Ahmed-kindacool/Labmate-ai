import { TaskSolutionCard } from "./task-solution-card";
import type { GeneratedLab } from "@/types/lab";

export interface SolutionListProps {
  lab: GeneratedLab;
}

export function SolutionList({ lab }: SolutionListProps) {
  return (
    <div className="grid gap-4">
      <div>
        <h2 className="text-base font-semibold text-foreground">{lab.labTitle}</h2>
        {lab.objectives.length > 0 && (
          <ul className="mt-2 list-disc pl-5 text-sm text-muted-foreground">
            {lab.objectives.map((objective) => (
              <li key={objective}>{objective}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid gap-2">
        {lab.tasks.map((task, index) => (
          // First task open by default so there's something to see without
          // an extra click; the rest stay collapsed to keep a multi-task lab
          // scannable.
          <TaskSolutionCard key={task.id} task={task} defaultOpen={index === 0} />
        ))}
      </div>

      {lab.conclusion && (
        <p className="rounded-md bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
          {lab.conclusion}
        </p>
      )}
    </div>
  );
}

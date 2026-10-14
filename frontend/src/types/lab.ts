export interface LabTask {
  id: string;
  description: string;
  language?: string;
}

export interface ParsedLab {
  title?: string;
  rawText: string;
  tasks: LabTask[];
}

export interface GeneratedTaskSolution {
  id: string;
  description: string;
  language: string;
  filename: string;
  code: string;
  explanation: string;
}

export interface LabStep {
  title: string;
  details: string;
  location: string;
  issue: string;
}

export interface LabTable {
  title: string;
  headers: string[];
  rows: string[][];
}

export interface GeneratedLab {
  // snake_case to match backend/app/schemas/lab.py's GeneratedLab exactly
  // (Phase 8: this is now a real wire type, not a sketch -- the naming
  // mismatch flagged since Phase 3/5 in docs/API_CONTRACT.md is resolved
  // by matching the backend 1:1 rather than translating at a boundary).
  lab_title: string;
  objectives: string[];
  tasks: GeneratedTaskSolution[];
  conclusion: string;
  // Project / documentation assignments (optional; older responses omit them).
  steps?: LabStep[];
  tables?: LabTable[];
  screenshots?: string[];
  code_as_text?: boolean;
}

export type ExecutionStatus = "success" | "failed" | "timeout" | "unsupported";

export interface ExecutionResult {
  status: ExecutionStatus;
  stdout: string;
  stderr: string;
  exit_code?: number | null;
}

// Matches backend/app/schemas/generate.py's TaskExecutionResult: one
// ExecutionResult tagged with the GeneratedTaskSolution.id it belongs to.
export interface TaskExecutionResult {
  task_id: string;
  result: ExecutionResult;
}

export type University = "air" | "bahria" | "nust";

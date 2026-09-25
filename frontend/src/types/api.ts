import type { ExecutionStatus, GeneratedLab, TaskExecutionResult, University } from "./lab";

export interface StudentInfo {
  name: string;
  // snake_case throughout: these are sent as literal multipart form-field
  // names to POST /api/v1/labs/generate (backend/app/schemas/student.py),
  // so keeping StudentInfo's own field names identical to the wire format
  // means building that FormData is a direct field-by-field copy -- see
  // lib/generate-api.ts -- with no separate camelCase/snake_case mapping
  // layer to keep in sync.
  roll_number: string;
  university: University | "";
  class_section: string;
  instructor_name: string;
  course: string;
}

// Sent as multipart/form-data to POST /api/v1/labs/generate: every
// StudentInfo field above (university must be a real University, not "")
// as a form field, plus a "lab_file" file field.
export type GenerateRequestFields = Omit<StudentInfo, "university"> & {
  university: University;
};

export interface GenerateSuccessResponse {
  status: "success";
  // As of Phase 7, a base64 data: URI containing the whole generated
  // .docx -- see docs/DOCX_GENERATION.md "Why download_url is a data
  // URI". Usable directly as <a href={download_url} download="...">.
  download_url: string;
  generated_lab: GeneratedLab;
  execution_results: TaskExecutionResult[];
  // null when no task produced code to execute, or screenshot capture
  // failed entirely (see backend GenerationService._capture_screenshots)
  // -- never fabricated, per AI_AND_GENERATION.md.
  screenshots: Record<string, string> | null;
}

export interface GenerateErrorResponse {
  status: "error";
  code:
    | "INVALID_INPUT"
    | "UNSUPPORTED_FILE"
    | "FILE_TOO_LARGE"
    | "LAB_READ_FAILED"
    | "AI_GENERATION_FAILED"
    | "EXECUTION_FAILED"
    | "REPORT_GENERATION_FAILED";
  message: string;
  // Present only for INVALID_INPUT -- lets the frontend highlight specific
  // fields instead of showing one generic error banner.
  field_errors?: Record<string, string[]>;
}

export type GenerateResponse = GenerateSuccessResponse | GenerateErrorResponse;

export type { ExecutionStatus };

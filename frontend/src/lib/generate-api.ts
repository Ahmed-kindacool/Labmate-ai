import type { GenerateResponse, StudentInfo } from "@/types/api";

// Same-origin in production (served together); overridable for local dev
// where Vite (5173) and FastAPI (8000) run as separate origins -- see
// docs/TEAM_SPLIT_PHASE1_ONWARD.md's `npm run dev` / `uvicorn` setup and
// backend/app/core/config.py's `frontend_origin` CORS setting.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * Thrown when the request never reached the server at all (offline, DNS
 * failure, CORS rejection, backend not running) or the server's response
 * couldn't even be parsed as JSON -- i.e. there is no backend-authored
 * `GenerateErrorResponse.message` to show. `GenerationError`'s own doc
 * comment already anticipates exactly this: "the one explicit
 * network-failure string when there was no server response at all."
 */
export class GenerateRequestError extends Error {}

function buildFormData(student: StudentInfo, labFile: File): FormData {
  if (!student.university) {
    // Guarded by the UI (Generate is disabled until a university is
    // picked) -- this is a defensive check, not the primary validation
    // path, same convention as TemplateRegistry.get_template's own
    // defensive ValueError->AppError handling on the backend.
    throw new Error("A university must be selected before generating a report.");
  }

  const formData = new FormData();
  formData.append("name", student.name);
  formData.append("roll_number", student.roll_number);
  formData.append("university", student.university);
  formData.append("class_section", student.class_section);
  formData.append("instructor_name", student.instructor_name);
  formData.append("course", student.course);
  formData.append("lab_file", labFile);
  return formData;
}

/**
 * Calls POST /api/v1/labs/generate and returns the parsed response as-is
 * -- both `{status: "success", ...}` and `{status: "error", ...}` are
 * normal, successful HTTP responses per docs/API_CONTRACT.md (the route
 * returns 200 either way; only genuinely unexpected server failures are
 * a non-2xx/unparseable response). The caller (App.tsx) is responsible
 * for branching on `.status`.
 */
export async function generateLabReport(
  student: StudentInfo,
  labFile: File
): Promise<GenerateResponse> {
  const formData = buildFormData(student, labFile);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/labs/generate`, {
      method: "POST",
      body: formData,
    });
  } catch (cause) {
    throw new GenerateRequestError(
      "Could not reach the server. Check your connection and try again.",
      { cause }
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch (cause) {
    throw new GenerateRequestError(
      "The server returned an unexpected response. Please try again.",
      { cause }
    );
  }

  // The shape is trusted here -- it's the backend's own Pydantic-validated
  // contract (GenerateSuccessResponse | GenerateErrorResponse), not
  // arbitrary external data.
  return body as GenerateResponse;
}

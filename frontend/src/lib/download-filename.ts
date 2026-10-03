import type { StudentInfo } from "@/types/api";

/**
 * Real data only: the university the report was actually generated for,
 * plus the AI's real lab_title, slugified. Falls back to a generic name
 * only when one of those is genuinely unavailable.
 */
export function buildDownloadFilename(
  student: StudentInfo | null,
  labTitle: string | undefined
): string {
  const slug = (labTitle ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  const university = student?.university || "report";
  return `${university}-${slug || "lab-report"}.docx`;
}

import { describe, expect, it } from "vitest";

import { buildDownloadFilename } from "@/lib/download-filename";
import type { StudentInfo } from "@/types/api";

const student: StudentInfo = {
  name: "Haziq",
  roll_number: "242242",
  university: "air",
  class_section: "BSCS-6A",
  instructor_name: "Sir Ali",
  course: "Algorithms",
};

describe("buildDownloadFilename", () => {
  it("builds a slug from the real university and lab title", () => {
    expect(buildDownloadFilename(student, "Lab 03 - Sorting Algorithms")).toBe(
      "air-lab-03-sorting-algorithms.docx"
    );
  });

  it("matches the real fake-AI dev server's lab_title", () => {
    // Verified against an actual response from
    // backend/scripts/dev_server_with_fake_ai.py, not invented.
    expect(buildDownloadFilename(student, "Lab: Fake-AI Dev Server")).toBe(
      "air-lab-fake-ai-dev-server.docx"
    );
  });

  it("falls back to a generic slug when labTitle is empty", () => {
    expect(buildDownloadFilename(student, "")).toBe("air-lab-report.docx");
  });

  it("falls back to a generic slug when labTitle is undefined", () => {
    expect(buildDownloadFilename(student, undefined)).toBe("air-lab-report.docx");
  });

  it("falls back to 'report' when there is no student", () => {
    expect(buildDownloadFilename(null, "Something")).toBe("report-something.docx");
  });

  it("strips characters that aren't safe/expected in a filename", () => {
    expect(buildDownloadFilename(student, "Lab #4: Pointers & Arrays!")).toBe(
      "air-lab-4-pointers-arrays.docx"
    );
  });
});

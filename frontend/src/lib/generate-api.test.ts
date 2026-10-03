import { afterEach, describe, expect, it, vi } from "vitest";

import { GenerateRequestError, generateLabReport } from "@/lib/generate-api";
import type { StudentInfo } from "@/types/api";

const student: StudentInfo = {
  name: "Haziq",
  roll_number: "242242",
  university: "air",
  class_section: "BSCS-6A",
  instructor_name: "Sir Ali",
  course: "Algorithms",
};

function fakeFile(): File {
  return new File(["dummy"], "lab.pdf", { type: "application/pdf" });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("generateLabReport", () => {
  it("sends the six StudentInfo fields plus lab_file as multipart form data", async () => {
    let capturedBody: FormData | undefined;
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      capturedBody = init?.body as FormData;
      return new Response(JSON.stringify({ status: "success" }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await generateLabReport(student, fakeFile());

    expect(capturedBody).toBeInstanceOf(FormData);
    expect(capturedBody!.get("name")).toBe("Haziq");
    expect(capturedBody!.get("roll_number")).toBe("242242");
    expect(capturedBody!.get("university")).toBe("air");
    expect(capturedBody!.get("class_section")).toBe("BSCS-6A");
    expect(capturedBody!.get("instructor_name")).toBe("Sir Ali");
    expect(capturedBody!.get("course")).toBe("Algorithms");
    expect((capturedBody!.get("lab_file") as File).name).toBe("lab.pdf");
  });

  it("posts to /api/v1/labs/generate", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      expect(url).toContain("/api/v1/labs/generate");
      return new Response(JSON.stringify({ status: "success" }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await generateLabReport(student, fakeFile());
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("returns a real success response shape as-is (captured from the fake-AI dev server)", async () => {
    // Captured with: curl -X POST http://localhost:8000/api/v1/labs/generate
    // against backend/scripts/dev_server_with_fake_ai.py, with no Docker
    // or Chromium available -- so this is also the genuinely honest
    // "unsupported" execution / null-screenshots shape, not a fabricated
    // happy path.
    const realResponse = {
      status: "success",
      download_url: "data:application/vnd...;base64,UEsD...",
      generated_lab: {
        lab_title: "Lab: Fake-AI Dev Server",
        objectives: ["Exercise the real pipeline without a real AI provider."],
        tasks: [
          {
            id: "task-1",
            description: "Print a greeting message.",
            language: "python",
            filename: "hello.py",
            code: "print('Hello from Labmate AI!')",
            explanation: "A minimal real task, used to exercise real code execution.",
          },
        ],
        conclusion: "This report was generated with a fake AI step and every other stage real.",
      },
      execution_results: [
        {
          task_id: "task-1",
          result: {
            status: "unsupported",
            stdout: "",
            stderr: "Code execution is currently disabled on this server.",
            exit_code: null,
          },
        },
      ],
      screenshots: null,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(realResponse), { status: 200 }))
    );

    const result = await generateLabReport(student, fakeFile());
    expect(result).toEqual(realResponse);
  });

  it("returns a real validation error response as-is", async () => {
    // Captured from: curl -X POST .../generate -F "name=" -F "lab_file=@sample.pdf"
    const realErrorResponse = {
      status: "error",
      code: "INVALID_INPUT",
      message: "Please fix the highlighted fields.",
      field_errors: {
        name: ["Value error, Name is required"],
        roll_number: ["Input should be a valid string"],
        university: ["Input should be 'air', 'bahria' or 'nust'"],
        class_section: ["Input should be a valid string"],
        instructor_name: ["Input should be a valid string"],
        course: ["Input should be a valid string"],
      },
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(realErrorResponse), { status: 400 }))
    );

    const result = await generateLabReport(student, fakeFile());
    expect(result).toEqual(realErrorResponse);
  });

  it("throws GenerateRequestError when the network request itself fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      })
    );

    await expect(generateLabReport(student, fakeFile())).rejects.toBeInstanceOf(
      GenerateRequestError
    );
  });

  it("throws GenerateRequestError when the response body isn't valid JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html>not json</html>", { status: 200 }))
    );

    await expect(generateLabReport(student, fakeFile())).rejects.toBeInstanceOf(
      GenerateRequestError
    );
  });

  it("throws a plain Error (not GenerateRequestError) if no university is selected", async () => {
    // Defensive-only path -- the UI disables Generate before this can
    // happen -- so this deliberately never reaches fetch at all.
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      generateLabReport({ ...student, university: "" }, fakeFile())
    ).rejects.toThrow("A university must be selected");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

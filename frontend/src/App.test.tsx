import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";

// A minimal, valid PDF-ish File -- LabFileUpload only checks MIME type and
// size client-side (backend/app/validation/lab_file.py is the real
// authority), so content doesn't need to be a real PDF for these tests.
function makeLabFile(): File {
  return new File(["%PDF-1.4 fake content"], "lab.pdf", { type: "application/pdf" });
}

async function fillStudentInfoOnly(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/full name/i), "Haziq");
  await user.type(screen.getByLabelText(/roll number/i), "242242");
  await user.type(screen.getByLabelText(/class \/ section/i), "BSCS-6A");
  await user.type(screen.getByLabelText(/instructor name/i), "Sir Ali");
  await user.type(screen.getByLabelText(/^course$/i), "Algorithms");
  await user.click(screen.getByRole("radio", { name: /air university/i }));
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await fillStudentInfoOnly(user);
  await user.upload(screen.getByLabelText(/lab file/i), makeLabFile());
}

// Real response shape, captured from backend/scripts/dev_server_with_fake_ai.py
// (no Docker/Chromium in that environment either -- this is the genuine
// "unsupported"/null-screenshots path, not an invented happy path).
const REAL_SUCCESS_RESPONSE = {
  status: "success" as const,
  download_url: "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,UEsD",
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
        status: "unsupported" as const,
        stdout: "",
        stderr: "Code execution is currently disabled on this server.",
        exit_code: null,
      },
    },
  ],
  screenshots: null,
};

// Captured from: curl -X POST .../generate -F "name=" -F "lab_file=@sample.pdf"
const REAL_VALIDATION_ERROR = {
  status: "error" as const,
  code: "INVALID_INPUT" as const,
  message: "Please fix the highlighted fields.",
  field_errors: {
    name: ["Value error, Name is required"],
  },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("disables Generate until the form and file are complete", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByRole("button", { name: /generate lab report/i })).toBeDisabled();

    await fillValidForm(user);

    expect(screen.getByRole("button", { name: /generate lab report/i })).toBeEnabled();
  });

  it("shows a client-side error and blocks generation for an unsupported file type", async () => {
    const user = userEvent.setup();
    render(<App />);
    await fillStudentInfoOnly(user);

    // Real-world note: userEvent.upload() on an <input accept="..."> filters
    // to matching types, same as a real OS file picker -- so it can't
    // exercise the rejection path at all. Drag-and-drop bypasses `accept`
    // entirely (both in real browsers and in LabFileUpload's own onDrop
    // handler), which is the actual way an unsupported file reaches the
    // client-side validator mirroring backend/app/validation/lab_file.py.
    const dropzone = screen.getByRole("button", { name: /click to upload/i });
    const rejectedFile = new File(["x"], "notes.exe", { type: "application/x-msdownload" });
    fireEvent.drop(dropzone, { dataTransfer: { files: [rejectedFile] } });

    expect(await screen.findByText(/unsupported file type/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generate lab report/i })).toBeDisabled();
  });

  it("submits real form data, shows loading state, then the real success UI", async () => {
    // A deferred promise, so the loading state can actually be observed
    // before the response resolves -- an immediately-resolving mock would
    // let React run straight through to "done" before any assertion runs.
    let resolveFetch!: (response: Response) => void;
    const fetchMock = vi.fn(
      () => new Promise<Response>((resolve) => { resolveFetch = resolve; })
    );
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<App />);
    await fillValidForm(user);

    await user.click(screen.getByRole("button", { name: /generate lab report/i }));

    // Loading state: spinner text visible, form locked.
    expect(await screen.findByRole("button", { name: /generating/i })).toBeDisabled();
    expect(screen.getByLabelText(/full name/i)).toBeDisabled();

    resolveFetch(new Response(JSON.stringify(REAL_SUCCESS_RESPONSE), { status: 200 }));

    // Real success state, driven by the real response above.
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/your report is ready/i);
    });

    const downloadLink = screen.getByRole("link", { name: /download report/i });
    expect(downloadLink).toHaveAttribute("href", REAL_SUCCESS_RESPONSE.download_url);
    // Built from the real submitted university + the real lab_title.
    expect(downloadLink).toHaveAttribute("download", "air-lab-fake-ai-dev-server.docx");

    // Report preview renders the real generated task, and the real
    // "unsupported" execution result's honest fallback text -- never a
    // fabricated success.
    expect(screen.getByText(/print a greeting message/i)).toBeInTheDocument();
    expect(screen.getByText(/no execution output available/i)).toBeInTheDocument();

    // Form stays locked while a result is showing (Phase 8 fix).
    expect(screen.getByLabelText(/full name/i)).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("shows the real backend validation error, highlighting the right field", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(REAL_VALIDATION_ERROR), { status: 400 }))
    );

    const user = userEvent.setup();
    render(<App />);
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /generate lab report/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/please fix the highlighted fields/i);
    });
    // The backend's own per-field message, shown verbatim next to the field.
    expect(screen.getByText(/name is required/i)).toBeInTheDocument();

    // Not locked on error -- the student should be able to fix the field
    // and resubmit without starting over.
    expect(screen.getByLabelText(/full name/i)).toBeEnabled();
  });

  it("shows a network-failure message distinct from a backend error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      })
    );

    const user = userEvent.setup();
    render(<App />);
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /generate lab report/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/could not reach the server/i);
    });
  });

  it("'Start over' after a success clears the form, file, and result back to the initial state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(REAL_SUCCESS_RESPONSE), { status: 200 }))
    );

    const user = userEvent.setup();
    render(<App />);
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /generate lab report/i }));
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/your report is ready/i);
    });

    await user.click(screen.getByRole("button", { name: /start over/i }));

    // The bug this test guards: "Start over" previously left studentInfo
    // untouched, so the form kept showing the previous submission's data.
    expect(screen.getByLabelText(/full name/i)).toHaveValue("");
    expect(screen.getByLabelText(/roll number/i)).toHaveValue("");
    expect(
      within(screen.getByRole("radiogroup", { name: /university/i })).getByRole("radio", {
        name: /air university/i,
      })
    ).toHaveAttribute("aria-checked", "false");
    expect(screen.queryByText(/your report is ready/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generate lab report/i })).toBeDisabled();
  });
});

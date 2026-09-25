import * as React from "react";
import { Download, FileUp, Sparkles } from "lucide-react";

import { SiteHeader } from "@/components/site-header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LabFileUpload, StudentInfoForm } from "@/components/lab-form";
import { GenerationError, GenerationProgress, ReportPreview } from "@/components/generation";
import { GenerateRequestError, generateLabReport } from "@/lib/generate-api";
import type { GenerateSuccessResponse, StudentInfo } from "@/types/api";

const GENERATION_STEP_COUNT = 5; // must match STEPS.length in generation-progress.tsx

// The backend does one request/response (no SSE/polling for sub-step
// progress yet -- flagged as a follow-up in docs/DOCX_GENERATION.md), so
// there's no real signal for which of the 5 named steps the server is on
// while the request is in flight. This advances an estimate every ~900ms,
// capped at index 3 ("Running code") so it never claims "Creating report"
// finished before the real response actually arrives -- an honest
// approximation, not a fabricated completion signal.
const ESTIMATED_STEP_CAP = 3;
const ESTIMATED_STEP_INTERVAL_MS = 900;

const steps = [
  {
    icon: FileUp,
    title: "1. Student details & lab upload",
    description:
      "Fill in your student and course info, then upload your lab as PDF, DOC, or DOCX.",
  },
  {
    icon: Sparkles,
    title: "2. AI generates your solution",
    description:
      "AI reads the lab, identifies the tasks, and writes explanations and code where needed.",
  },
  {
    icon: Download,
    title: "3. Download your report",
    description:
      "Code is executed for real output, then everything is placed into your university's report template.",
  },
];

type UploadState = "idle" | "ready" | "generating" | "done" | "error";

const EMPTY_STUDENT_INFO: StudentInfo = {
  name: "",
  roll_number: "",
  university: "",
  class_section: "",
  instructor_name: "",
  course: "",
};

function isStudentInfoComplete(info: StudentInfo): boolean {
  return (
    info.name.trim() !== "" &&
    info.roll_number.trim() !== "" &&
    info.university !== "" &&
    info.class_section.trim() !== "" &&
    info.instructor_name.trim() !== "" &&
    info.course.trim() !== ""
  );
}

function App() {
  const [studentInfo, setStudentInfo] = React.useState<StudentInfo>(EMPTY_STUDENT_INFO);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string[]> | undefined>();
  const [file, setFile] = React.useState<File | null>(null);
  const [fileError, setFileError] = React.useState<string | null>(null);
  const [uploadState, setUploadState] = React.useState<UploadState>("idle");
  const [currentStep, setCurrentStep] = React.useState(0);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<GenerateSuccessResponse | null>(null);

  const canGenerate =
    file !== null && isStudentInfoComplete(studentInfo) && uploadState !== "generating";

  const handleFileChange = (nextFile: File | null) => {
    setFile(nextFile);
    if (uploadState !== "generating") {
      setUploadState(nextFile ? "ready" : "idle");
    }
  };

  const handleGenerate = async () => {
    if (!file || !isStudentInfoComplete(studentInfo) || uploadState === "generating") return;

    setUploadState("generating");
    setErrorMessage(null);
    setFieldErrors(undefined);
    setResult(null);
    setCurrentStep(0);

    const interval = window.setInterval(() => {
      setCurrentStep((step) => (step < ESTIMATED_STEP_CAP ? step + 1 : step));
    }, ESTIMATED_STEP_INTERVAL_MS);

    try {
      const response = await generateLabReport(studentInfo, file);
      window.clearInterval(interval);

      if (response.status === "success") {
        setCurrentStep(GENERATION_STEP_COUNT);
        setResult(response);
        setUploadState("done");
      } else {
        setErrorMessage(response.message);
        setFieldErrors(response.field_errors);
        setUploadState("error");
      }
    } catch (error) {
      window.clearInterval(interval);
      setErrorMessage(
        error instanceof GenerateRequestError
          ? error.message
          : "Something went wrong while generating your report. Please try again."
      );
      setUploadState("error");
    }
  };

  const handleReset = () => {
    setFile(null);
    setFileError(null);
    setUploadState("idle");
    setCurrentStep(0);
    setErrorMessage(null);
    setFieldErrors(undefined);
    setResult(null);
  };

  const executionsByTaskId = React.useMemo(() => {
    if (!result) return undefined;
    return Object.fromEntries(
      result.execution_results.map(({ task_id, result: executionResult }) => [
        task_id,
        executionResult,
      ])
    );
  }, [result]);

  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-10">
        <div className="grid gap-4 sm:grid-cols-3">
          {steps.map(({ icon: Icon, title, description }) => (
            <Card key={title} className="border-muted-foreground/10">
              <CardHeader className="gap-2">
                <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
                <CardTitle className="text-base">{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Generate a report</CardTitle>
            <CardDescription>
              Fill in your details, upload your lab, and we&apos;ll generate a
              formatted report with real code, real output, and your
              university&apos;s branding.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6">
            <StudentInfoForm
              value={studentInfo}
              onChange={setStudentInfo}
              fieldErrors={fieldErrors}
              disabled={uploadState === "generating"}
            />

            <LabFileUpload
              file={file}
              onFileChange={handleFileChange}
              error={fileError}
              onErrorChange={setFileError}
              disabled={uploadState === "generating"}
            />

            {(uploadState === "generating" || uploadState === "done") && (
              <GenerationProgress currentStep={currentStep} />
            )}

            {uploadState === "error" && errorMessage && (
              <GenerationError message={errorMessage} onRetry={handleGenerate} />
            )}

            {uploadState === "done" && result && (
              <div className="grid gap-3">
                <Button asChild>
                  <a href={result.download_url} download="lab-report.docx">
                    <Download className="size-4" aria-hidden="true" />
                    Download report
                  </a>
                </Button>
                <ReportPreview lab={result.generated_lab} executions={executionsByTaskId} />
              </div>
            )}

            <div className="flex gap-3">
              {uploadState !== "done" && (
                <Button onClick={handleGenerate} disabled={!canGenerate}>
                  {uploadState === "generating" ? "Generating…" : "Generate Lab Report"}
                </Button>
              )}
              {(file || uploadState === "done" || uploadState === "error") && (
                <Button variant="outline" onClick={handleReset}>
                  Start over
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </main>

      <footer className="border-t py-6 text-center text-xs text-muted-foreground">
        Air University · Bahria University · NUST
      </footer>
    </div>
  );
}

export default App;

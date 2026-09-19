import * as React from "react";
import { FileUp, Sparkles, Download } from "lucide-react";

import { SiteHeader } from "@/components/site-header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LabFileUpload } from "@/components/lab-form";
import { GenerationProgress } from "@/components/generation";

const GENERATION_STEP_COUNT = 5; // must match STEPS.length in generation-progress.tsx

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

type UploadState = "idle" | "ready" | "generating" | "done";

function App() {
  const [file, setFile] = React.useState<File | null>(null);
  const [fileError, setFileError] = React.useState<string | null>(null);
  const [uploadState, setUploadState] = React.useState<UploadState>("idle");
  const [currentStep, setCurrentStep] = React.useState(0);

  const handleFileChange = (nextFile: File | null) => {
    setFile(nextFile);
    setUploadState(nextFile ? "ready" : "idle");
  };

  // Phase 2 scope stops at the upload + progress UI. This just drives
  // GenerationProgress locally so the states are reviewable; swapping it for
  // a real POST /api/v1/labs/generate call (with SSE/polling for step
  // updates) is the "Together" wiring step for a later phase.
  const handleGenerate = () => {
    if (!file || uploadState !== "ready") return;
    setUploadState("generating");
    setCurrentStep(0);

    let step = 0;
    const interval = window.setInterval(() => {
      step += 1;
      setCurrentStep(step);
      if (step >= GENERATION_STEP_COUNT) {
        window.clearInterval(interval);
        setUploadState("done");
      }
    }, 700);
  };

  const handleReset = () => {
    setFile(null);
    setFileError(null);
    setUploadState("idle");
    setCurrentStep(0);
  };

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
              The student info form and university selector are still Phase 1
              work in progress. Lab upload and generation progress (Phase 2)
              are wired up below.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6">
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

            <div className="flex gap-3">
              <Button
                onClick={handleGenerate}
                disabled={uploadState !== "ready"}
              >
                Generate Lab Report
              </Button>
              {file && (
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

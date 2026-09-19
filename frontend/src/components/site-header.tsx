import { FileText } from "lucide-react";

import { ThemeToggle } from "@/components/ui/theme-toggle";

export function SiteHeader() {
  return (
    <header className="border-b bg-background">
      <div className="mx-auto flex max-w-3xl items-start justify-between gap-4 px-6 py-8 sm:py-10">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-foreground">
            <FileText className="size-5" aria-hidden="true" />
            <span className="text-lg font-semibold tracking-tight">LabMate AI</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Upload your lab, let AI work through the tasks, and download a
            formatted report — no sign-up required.
          </p>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}

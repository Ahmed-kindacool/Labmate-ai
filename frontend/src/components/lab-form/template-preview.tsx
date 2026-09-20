import type { University } from "@/types/lab";

const UNIVERSITY_LABELS: Record<University, string> = {
  air: "Air University",
  bahria: "Bahria University",
  nust: "NUST",
};

export interface TemplatePreviewProps {
  university: University | "";
}

/**
 * backend/app/templates_registry/ is still a Phase 2 stub — get_template()
 * only returns a university -> template_dir path, no actual
 * logo/header/formatting/footer data yet (that's the still-outstanding
 * Phase 6 backend work). This intentionally stays generic instead of
 * mocking up a specific layout that doesn't exist, echoing the one design
 * decision that IS already settled (domain/university.py's own comment):
 * one shared report structure, only the university branding changes.
 */
export function TemplatePreview({ university }: TemplatePreviewProps) {
  if (!university) {
    return (
      <p className="rounded-md border border-dashed px-3 py-4 text-center text-sm text-muted-foreground">
        Select a university to preview its report template.
      </p>
    );
  }

  const label = UNIVERSITY_LABELS[university];

  return (
    <div className="grid gap-1 rounded-md border bg-muted/30 px-4 py-4 text-sm">
      <p className="font-medium text-foreground">{label} template</p>
      <p className="text-muted-foreground">
        Your report will use {label}&apos;s logo and header/footer styling. The report
        content itself is identical across universities — only the branding changes.
      </p>
    </div>
  );
}

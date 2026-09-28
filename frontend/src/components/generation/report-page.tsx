import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { University } from "@/types/lab";

// Margins read from the real backend/templates_registry/templates/*/
// template.docx files (python-docx section margins, in inches). Air uses 1in
// all round; Bahria and NUST share 1in left/right but 0.94in top and 0.31in
// bottom. Page width is US Letter (8.5in), so each margin becomes a % of
// page width -- CSS padding percentages resolve against width, which keeps
// the proportions right at any preview size.
const PAGE_WIDTH_IN = 8.5;

const MARGINS_IN: Record<University, { top: number; bottom: number; side: number }> = {
  air: { top: 1, bottom: 1, side: 1 },
  bahria: { top: 0.94, bottom: 0.31, side: 1 },
  nust: { top: 0.94, bottom: 0.31, side: 1 },
};

const pct = (inches: number) => `${((inches / PAGE_WIDTH_IN) * 100).toFixed(2)}%`;

function pageStyle(university: University | undefined): CSSProperties {
  const m = MARGINS_IN[university ?? "air"];
  return { padding: `${pct(m.top)} ${pct(m.side)} ${pct(m.bottom)}` };
}

export interface ReportPageProps {
  university?: University;
  /** Force a full US Letter (8.5x11) page shape -- used for the cover page.
   * Content pages instead grow with their content. */
  fixedLetterShape?: boolean;
  className?: string;
  children: ReactNode;
}

/**
 * A sheet of "paper" in the report preview. Always white with dark text
 * regardless of the app's light/dark theme, because the real .docx is
 * always white paper -- theme tokens like text-muted-foreground would go
 * near-invisible on white in dark mode.
 *
 * Bahria and NUST templates draw a black page border in the real document
 * (visible in a rendered copy of the generated report); Air doesn't.
 *
 * Pagination is deliberately NOT simulated: where Word breaks content
 * across pages depends on fonts and rendered heights this preview can't
 * know, so content flows on one continuous page instead of guessing at
 * break points.
 */
export function ReportPage({
  university,
  fixedLetterShape = false,
  className,
  children,
}: ReportPageProps) {
  const hasPageBorder = university === "bahria" || university === "nust";

  return (
    <div
      style={pageStyle(university)}
      className={cn(
        "w-full bg-white text-neutral-900 shadow-sm",
        hasPageBorder ? "border-2 border-neutral-900" : "border border-neutral-300",
        fixedLetterShape && "aspect-[8.5/11]",
        className
      )}
    >
      {children}
    </div>
  );
}

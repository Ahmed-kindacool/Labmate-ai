import { ReportPage } from "./report-page";
import { cn } from "@/lib/utils";
import type { StudentInfo } from "@/types/api";
import type { University } from "@/types/lab";

// Wording and field order come straight from the three real cover pages in
// backend/templates_registry/templates/{air,bahria,nust}/template.docx, as
// filled by DocxGenerator (checked by generating a real report per
// university and reading the result):
//
//   Air     logo / course / lab title / Name / Roll Number / Submitted To
//   Bahria  crest / BAHRIA UNIVERSITY / department / course / lab title /
//           Name / Enrollment / SUBMITTED TO: / instructor
//   NUST    seal / department / course / lab title / Name / Enrollment /
//           Date / Instructor
//
// The covers really do differ per university (the shared part is the task
// layout after the cover) -- this mirrors each one rather than flattening
// them into a single generic cover.
//
// The NUST template also prints a bare "Time:" label with no placeholder
// behind it, so it always renders blank in the real document. It's left out
// here rather than showing an empty label the student could never fill.

// DocxGenerator falls back to this exact string for {{DEPARTMENT_TITLE}}
// when no lab_metadata is supplied, and GenerationService never supplies
// any -- so today every Bahria/NUST report says this regardless of the
// student's actual department. Mirrored as-is because the preview must
// match what the document will say.
const DEPARTMENT_TITLE = "Department of Computing";

type Emphasis = "institution" | "heading" | "title" | "field" | "label" | "plain";

interface CoverLine {
  text: string;
  emphasis: Emphasis;
}

const EMPHASIS_CLASS: Record<Emphasis, string> = {
  institution: "text-xl font-bold underline underline-offset-4",
  heading: "text-base font-bold",
  title: "text-sm font-bold",
  field: "text-sm font-semibold",
  label: "pt-3 text-xs font-bold",
  plain: "text-xs",
};

// Same format as DocxGenerator's datetime.date.today().strftime('%B %d, %Y')
// (zero-padded day, e.g. "September 05, 2026").
function formatCoverDate(date: Date): string {
  return date.toLocaleDateString("en-US", { month: "long", day: "2-digit", year: "numeric" });
}

function buildCoverLines(
  university: University,
  student: StudentInfo,
  labTitle: string,
  date: string
): CoverLine[] {
  switch (university) {
    case "air":
      return [
        { text: student.course, emphasis: "heading" },
        { text: labTitle, emphasis: "title" },
        { text: `Name: ${student.name}`, emphasis: "field" },
        { text: `Roll Number: ${student.roll_number}`, emphasis: "field" },
        { text: `Submitted To: ${student.instructor_name}`, emphasis: "field" },
      ];
    case "bahria":
      return [
        { text: "BAHRIA UNIVERSITY", emphasis: "institution" },
        { text: DEPARTMENT_TITLE, emphasis: "title" },
        { text: student.course, emphasis: "title" },
        { text: labTitle, emphasis: "title" },
        { text: `Name: ${student.name}`, emphasis: "field" },
        { text: `Enrollment: ${student.roll_number}`, emphasis: "field" },
        { text: "SUBMITTED TO:", emphasis: "label" },
        { text: student.instructor_name, emphasis: "plain" },
      ];
    case "nust":
      return [
        { text: DEPARTMENT_TITLE, emphasis: "title" },
        { text: student.course, emphasis: "title" },
        { text: labTitle, emphasis: "title" },
        { text: `Name: ${student.name}`, emphasis: "field" },
        { text: `Enrollment: ${student.roll_number}`, emphasis: "field" },
        { text: `Date: ${date}`, emphasis: "field" },
        { text: `Instructor: ${student.instructor_name}`, emphasis: "field" },
      ];
  }
}

export interface ReportTitlePageProps {
  student: StudentInfo;
  labTitle: string;
}

export function ReportTitlePage({ student, labTitle }: ReportTitlePageProps) {
  // The upload flow only reaches a report once the form was complete, but
  // StudentInfo.university is typed University | "" -- nothing to show a
  // cover for without a real university.
  if (student.university === "") return null;

  const { university } = student;
  const lines = buildCoverLines(university, student, labTitle, formatCoverDate(new Date()));
  const isSerif = university === "bahria" || university === "nust";

  return (
    <ReportPage university={university} fixedLetterShape>
      <div
        className={cn(
          "flex h-full flex-col items-center justify-center gap-2.5 text-center",
          isSerif && "font-serif"
        )}
      >
        <img
          src={`/logos/${university}.png`}
          alt=""
          aria-hidden="true"
          // Hide rather than show a broken-image icon if a logo file is
          // ever missing.
          onError={(event) => {
            event.currentTarget.style.display = "none";
          }}
          className="mb-4 h-28 max-w-[60%] object-contain"
        />
        {lines.map((line, index) => (
          <p key={`${index}-${line.text}`} className={EMPHASIS_CLASS[line.emphasis]}>
            {line.text}
          </p>
        ))}
      </div>
    </ReportPage>
  );
}

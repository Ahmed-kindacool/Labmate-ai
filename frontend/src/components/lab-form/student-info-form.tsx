import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { UniversitySelector } from "./university-selector";
import type { StudentInfo } from "@/types/api";

export interface StudentInfoFormProps {
  value: StudentInfo;
  onChange: (value: StudentInfo) => void;
  /** Keyed by StudentInfo field name, from GenerateErrorResponse.field_errors
   * (backend/app/schemas/generate.py) -- shown under the matching field
   * instead of one generic banner. */
  fieldErrors?: Record<string, string[]>;
  disabled?: boolean;
}

interface TextFieldConfig {
  name: keyof Omit<StudentInfo, "university">;
  label: string;
  placeholder: string;
  autoComplete?: string;
}

// Order and labels match backend/app/schemas/student.py's StudentInfo
// fields exactly (see types/api.ts's note on why the field names
// themselves are already identical to the wire format).
const TEXT_FIELDS: TextFieldConfig[] = [
  { name: "name", label: "Full Name", placeholder: "Ahmed Ali Khan", autoComplete: "name" },
  { name: "roll_number", label: "Roll Number", placeholder: "211-CS-101" },
  { name: "class_section", label: "Class / Section", placeholder: "BS-AI 5A" },
  { name: "instructor_name", label: "Instructor Name", placeholder: "Dr. Farah Naz" },
  { name: "course", label: "Course", placeholder: "Artificial Intelligence" },
];

export function StudentInfoForm({
  value,
  onChange,
  fieldErrors,
  disabled = false,
}: StudentInfoFormProps) {
  return (
    <div className="grid gap-5">
      <div className="grid gap-4 sm:grid-cols-2">
        {TEXT_FIELDS.map((field) => {
          const errors = fieldErrors?.[field.name];
          const fieldId = `student-${field.name}`;
          const errorId = `${fieldId}-error`;

          return (
            <div key={field.name} className="grid gap-1.5">
              <Label htmlFor={fieldId}>{field.label}</Label>
              <Input
                id={fieldId}
                value={value[field.name]}
                placeholder={field.placeholder}
                autoComplete={field.autoComplete}
                disabled={disabled}
                aria-invalid={errors ? true : undefined}
                aria-describedby={errors ? errorId : undefined}
                onChange={(event) =>
                  onChange({ ...value, [field.name]: event.target.value })
                }
              />
              {errors?.map((error) => (
                <p key={error} id={errorId} className="text-xs text-destructive">
                  {error}
                </p>
              ))}
            </div>
          );
        })}
      </div>

      <div className="grid gap-1.5">
        <UniversitySelector
          value={value.university}
          onChange={(university) => onChange({ ...value, university })}
          disabled={disabled}
        />
        {fieldErrors?.university?.map((error) => (
          <p key={error} className="text-xs text-destructive">
            {error}
          </p>
        ))}
      </div>
    </div>
  );
}

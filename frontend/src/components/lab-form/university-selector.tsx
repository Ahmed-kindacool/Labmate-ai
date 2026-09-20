import * as React from "react";
import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import type { University } from "@/types/lab";

// Matches backend/app/domain/university.py's University enum values exactly
// (air/bahria/nust) and the real logo files now at
// frontend/public/logos/{air,bahria,nust}.png.
interface UniversityOption {
  value: University;
  label: string;
  shortLabel: string;
  logoSrc: string;
}

const UNIVERSITIES: UniversityOption[] = [
  { value: "air", label: "Air University", shortLabel: "AU", logoSrc: "/logos/air.png" },
  { value: "bahria", label: "Bahria University", shortLabel: "BU", logoSrc: "/logos/bahria.png" },
  { value: "nust", label: "NUST", shortLabel: "NU", logoSrc: "/logos/nust.png" },
];

export interface UniversitySelectorProps {
  value: University | "";
  onChange: (value: University) => void;
  disabled?: boolean;
}

function UniversityLogo({ uni, isSelected }: { uni: UniversityOption; isSelected: boolean }) {
  const [failed, setFailed] = React.useState(false);

  if (failed) {
    // Falls back to the monogram badge if a logo file is ever missing or
    // fails to load, rather than showing a broken image icon.
    return (
      <span
        aria-hidden="true"
        className={cn(
          "flex size-10 items-center justify-center rounded-full text-sm font-semibold",
          isSelected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
        )}
      >
        {uni.shortLabel}
      </span>
    );
  }

  return (
    <img
      src={uni.logoSrc}
      alt=""
      aria-hidden="true"
      onError={() => setFailed(true)}
      className="size-10 rounded-full object-contain"
    />
  );
}

export function UniversitySelector({
  value,
  onChange,
  disabled = false,
}: UniversitySelectorProps) {
  return (
    <div className="grid gap-2">
      <span className="text-sm font-medium leading-none">University</span>
      <div role="radiogroup" aria-label="University" className="grid gap-3 sm:grid-cols-3">
        {UNIVERSITIES.map((uni) => {
          const isSelected = value === uni.value;
          return (
            <button
              key={uni.value}
              type="button"
              role="radio"
              aria-checked={isSelected}
              disabled={disabled}
              onClick={() => onChange(uni.value)}
              className={cn(
                "relative flex flex-col items-center gap-2 rounded-lg border px-4 py-5 text-center outline-none transition-colors",
                "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                isSelected ? "border-primary bg-primary/5" : "border-input hover:bg-accent/50",
                disabled && "pointer-events-none opacity-50"
              )}
            >
              {isSelected && (
                <span className="absolute top-2 right-2 flex size-4 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Check className="size-3" aria-hidden="true" />
                </span>
              )}
              <UniversityLogo uni={uni} isSelected={isSelected} />
              <span className="text-sm font-medium text-foreground">{uni.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

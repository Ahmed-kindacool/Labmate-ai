import * as React from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  AdditionalInstructions,
  MAX_ADDITIONAL_INSTRUCTIONS_CHARS,
} from "@/components/lab-form/additional-instructions";

// Controlled wrapper so typing and the chips behave like they do in App.
function Harness({ initial = "", disabled = false, errors }: { initial?: string; disabled?: boolean; errors?: string[] }) {
  const [value, setValue] = React.useState(initial);
  return <AdditionalInstructions value={value} onChange={setValue} disabled={disabled} errors={errors} />;
}

describe("AdditionalInstructions", () => {
  it("is clearly optional and shows a live character counter", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.getByText(/\(optional\)/i)).toBeInTheDocument();
    expect(screen.getByText(`0 / ${MAX_ADDITIONAL_INSTRUCTIONS_CHARS}`)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/anything else/i), "Add a table");
    expect(screen.getByText(`11 / ${MAX_ADDITIONAL_INSTRUCTIONS_CHARS}`)).toBeInTheDocument();
  });

  it("a suggestion chip fills the box; several chips stack on separate lines; the same chip never duplicates", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const box = screen.getByLabelText(/anything else/i) as HTMLTextAreaElement;

    await user.click(screen.getByRole("button", { name: /\+ introduction/i }));
    expect(box.value).toMatch(/^Add an Introduction section/);

    await user.click(screen.getByRole("button", { name: /\+ viva questions/i }));
    expect(box.value.split("\n")).toHaveLength(2);

    await user.click(screen.getByRole("button", { name: /\+ introduction/i }));
    expect(box.value.split("\n")).toHaveLength(2); // not added twice
  });

  it("keeps what the student already typed when a chip is added", async () => {
    const user = userEvent.setup();
    render(<Harness initial="Use Python 3 only." />);
    await user.click(screen.getByRole("button", { name: /\+ references/i }));
    const box = screen.getByLabelText(/anything else/i) as HTMLTextAreaElement;
    expect(box.value.startsWith("Use Python 3 only.\n")).toBe(true);
  });

  it("warns when over the limit", () => {
    render(<Harness initial={"x".repeat(MAX_ADDITIONAL_INSTRUCTIONS_CHARS + 5)} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/too long by 5 characters/i);
    expect(screen.getByLabelText(/anything else/i)).toHaveAttribute("aria-invalid", "true");
  });

  it("shows a backend field error", () => {
    render(<Harness errors={["Too long: 2100 characters (maximum 2000)."]} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/too long: 2100/i);
  });

  it("disables the box and the chips while the form is locked", () => {
    render(<Harness disabled />);
    expect(screen.getByLabelText(/anything else/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /\+ discussion/i })).toBeDisabled();
  });
});

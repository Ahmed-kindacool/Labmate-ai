import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SAMPLE_PDF = path.join(__dirname, "fixtures", "sample-lab.pdf");

async function fillStudentInfo(page: import("@playwright/test").Page) {
  await page.getByLabel(/full name/i).fill("Haziq");
  await page.getByLabel(/roll number/i).fill("242242");
  await page.getByLabel(/class \/ section/i).fill("BSCS-6A");
  await page.getByLabel(/instructor name/i).fill("Sir Ali");
  await page.getByLabel(/^course$/i).fill("Algorithms");
  await page.getByRole("radio", { name: /air university/i }).click();
}

test("Generate stays disabled until the form and a file are complete", async ({ page }) => {
  await page.goto("/");

  const generateButton = page.getByRole("button", { name: /generate lab report/i });
  await expect(generateButton).toBeDisabled();

  await fillStudentInfo(page);
  await expect(generateButton).toBeDisabled(); // still no file yet

  await page.getByLabel(/lab file/i).setInputFiles(SAMPLE_PDF);
  await expect(generateButton).toBeEnabled();
});

test("rejects an unsupported file type with the client-side message", async ({ page }) => {
  await page.goto("/");
  await fillStudentInfo(page);

  // setInputFiles doesn't filter by the input's accept attribute (unlike a
  // real OS file picker, which never offers this file at all) -- this
  // exercises LabFileUpload's own client-side validator directly, mirroring
  // backend/app/validation/lab_file.py.
  await page.getByLabel(/lab file/i).setInputFiles({
    name: "notes.exe",
    mimeType: "application/x-msdownload",
    buffer: Buffer.from("x"),
  });

  await expect(page.getByText(/unsupported file type/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /generate lab report/i })).toBeDisabled();
});

test("a real submission produces a real downloadable report", async ({ page }) => {
  await page.goto("/");
  await fillStudentInfo(page);
  await page.getByLabel(/lab file/i).setInputFiles(SAMPLE_PDF);

  await page.getByRole("button", { name: /generate lab report/i }).click();

  // Real request to the real (fake-AI-only) backend -- no mocked fetch
  // anywhere in this suite.
  await expect(page.getByRole("status")).toHaveText(/your report is ready/i, {
    timeout: 30_000,
  });

  // The report preview renders the real AI-less pipeline's actual task
  // output, including the honest "unsupported" execution fallback when
  // this environment has no Docker -- never a fabricated success.
  await expect(page.getByText(/no execution output available/i)).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: /download report/i }).click();
  const download = await downloadPromise;

  // Built from the real submitted university + the real AI-generated
  // lab_title (dev_server_with_fake_ai.py's own fixed title).
  expect(download.suggestedFilename()).toBe("air-lab-fake-ai-dev-server.docx");

  const downloadedPath = await download.path();
  expect(downloadedPath).not.toBeNull();
});

test("'Start over' clears the form after a real successful generation", async ({ page }) => {
  await page.goto("/");
  await fillStudentInfo(page);
  await page.getByLabel(/lab file/i).setInputFiles(SAMPLE_PDF);
  await page.getByRole("button", { name: /generate lab report/i }).click();

  await expect(page.getByRole("status")).toHaveText(/your report is ready/i, {
    timeout: 30_000,
  });

  await page.getByRole("button", { name: /start over/i }).click();

  await expect(page.getByLabel(/full name/i)).toHaveValue("");
  await expect(
    page.getByRole("radiogroup", { name: /university/i }).getByRole("radio", { name: /air university/i })
  ).toHaveAttribute("aria-checked", "false");
  await expect(page.getByRole("button", { name: /generate lab report/i })).toBeDisabled();
});

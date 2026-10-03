import { defineConfig, devices } from "@playwright/test";

// Points at a pre-installed Chromium binary when this sandbox can't reach
// Playwright's own CDN to download one (its own installer looks in
// ~/.cache/ms-playwright, not wherever this happens to live). On a normal
// dev machine, ignore this entirely: just run
// `npx playwright install chromium` once, and leave the env var unset.
const sandboxChromiumPath = process.env.PLAYWRIGHT_CHROMIUM_PATH;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        ...(sandboxChromiumPath ? { launchOptions: { executablePath: sandboxChromiumPath } } : {}),
      },
    },
  ],
  // Starts the real backend (with only the AI call faked -- see
  // backend/scripts/dev_server_with_fake_ai.py) and the real Vite dev
  // server. Every stage after that -- parsing, execution, screenshots,
  // templates, DOCX generation -- is the genuine pipeline; nothing here is
  // mocked at the HTTP layer.
  webServer: [
    {
      command:
        "cd ../backend && ([ -d .venv ] || python3 -m venv .venv) && .venv/bin/pip install -q -r requirements.txt && .venv/bin/python scripts/dev_server_with_fake_ai.py",
      url: "http://localhost:8000/api/v1/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
    },
  ],
});

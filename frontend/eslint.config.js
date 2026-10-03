import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "e2e-report", "playwright-report", "test-results"] },
  {
    // Covers both the app source and the Playwright e2e specs -- all TS,
    // all needing the TS-aware parser/rules below. Global sets differ by
    // directory, applied in the two overrides that follow.
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["src/**/*.{ts,tsx}", "e2e/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
  {
    // Test files run under Vitest/Node, not the browser.
    files: ["src/test/**/*.{ts,tsx}", "src/**/*.test.{ts,tsx}"],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },
  {
    // Playwright E2E specs run under Node, not the browser, and aren't
    // part of the Vite app build.
    files: ["e2e/**/*.{ts,tsx}"],
    languageOptions: {
      globals: globals.node,
    },
  }
);

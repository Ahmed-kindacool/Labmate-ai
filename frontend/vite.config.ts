/// <reference types="vitest/config" />
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Deliberately off: every test file imports describe/it/expect/vi
    // explicitly from "vitest" rather than relying on injected globals.
    globals: false,
    // e2e/ is a separate Playwright suite (real browser, real backend),
    // not part of this fast unit/component suite.
    exclude: ["e2e/**", "node_modules/**"],
  },
});

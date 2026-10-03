import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// @testing-library/react's auto-cleanup only registers itself if it finds
// a *global* afterEach at import time -- which never happens here, since
// `globals` is off in vite.config.ts by design. Without this, every
// test's rendered DOM would silently pile up across the rest of that
// file, causing getByRole to find duplicate/stale elements from earlier
// tests.
afterEach(() => {
  cleanup();
});

// jsdom doesn't implement matchMedia at all (a real browser does), and
// src/lib/use-theme.ts reads it on every mount. Only `.matches` is ever
// read (no listener API), so a minimal stub is enough.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}

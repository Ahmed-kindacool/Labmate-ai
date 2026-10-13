import * as React from "react";

/**
 * Turns the backend's base64 data URI into a Blob object URL.
 *
 * Browsers are unreliable with large `data:` links (Chrome caps navigation
 * size, Safari is flaky), and reports with embedded screenshots get big. A
 * Blob URL has no such limit. Falls back to the original data URI whenever
 * Blob URLs aren't available, so the link always works.
 */
export function dataUriToBlob(dataUri: string): Blob | null {
  const match = /^data:([^;,]+)?(;base64)?,(.*)$/s.exec(dataUri);
  if (!match) return null;
  const [, mime = "application/octet-stream", isBase64, payload] = match;
  try {
    if (!isBase64) return new Blob([decodeURIComponent(payload)], { type: mime });
    const binary = atob(payload);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return new Blob([bytes], { type: mime });
  } catch {
    return null;
  }
}

export function useDownloadUrl(dataUri: string | undefined): string | undefined {
  const objectUrl = React.useMemo(() => {
    if (!dataUri || typeof URL.createObjectURL !== "function") return undefined;
    const blob = dataUriToBlob(dataUri);
    return blob ? URL.createObjectURL(blob) : undefined;
  }, [dataUri]);

  React.useEffect(() => {
    if (!objectUrl) return undefined;
    return () => URL.revokeObjectURL(objectUrl);
  }, [objectUrl]);

  return objectUrl ?? dataUri;
}

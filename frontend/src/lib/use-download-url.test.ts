import { describe, expect, it } from "vitest";

import { dataUriToBlob } from "@/lib/use-download-url";

describe("dataUriToBlob", () => {
  it("decodes a base64 data URI into a Blob with the right type and bytes", async () => {
    const blob = dataUriToBlob("data:application/pdf;base64,SGVsbG8=");
    expect(blob).not.toBeNull();
    expect(blob?.type).toBe("application/pdf");
    expect(blob?.size).toBe(5);
  });

  it("returns null for something that is not a data URI", () => {
    expect(dataUriToBlob("https://example.com/x.docx")).toBeNull();
  });

  it("returns null for invalid base64 instead of throwing", () => {
    expect(dataUriToBlob("data:text/plain;base64,@@@")).toBeNull();
  });
});

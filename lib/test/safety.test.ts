import { readFile } from "node:fs/promises";
import { unzipSync, zipSync } from "fflate";
import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";

describe("ZIP safety limits", () => {
  test("rejects archives with more than 32 entries before extraction", async () => {
    const entries: Record<string, Uint8Array> = {};
    for (let i = 0; i < 33; i += 1) {
      entries[`entry-${i}.txt`] = new Uint8Array([i]);
    }
    const result = await verify(zipSync(entries));
    expect(result.valid).toBe(false);
    expect(result.failureReason).toContain("too many ZIP entries");
    expect(result.failureCode).toBe("ZIP_INVALID_OR_UNSAFE");
  });

  test("rejects nested entry names in the flat AEP profile", async () => {
    const result = await verify(
      zipSync({ "nested/entry.txt": new Uint8Array([1]) }),
    );
    expect(result.valid).toBe(false);
    expect(result.failureReason).toContain("flat, safe names");
    expect(result.failureCode).toBe("ZIP_INVALID_OR_UNSAFE");
  });
});

describe("decision-procedure boundary states", () => {
  async function baselineEntries(): Promise<Record<string, Uint8Array>> {
    const source = await readFile(
      new URL("../../test-vectors/valid/minimal-roundtrip/package.aep", import.meta.url),
    );
    return unzipSync(source);
  }

  test("rejects metadata JSON values that are not objects", async () => {
    const entries = await baselineEntries();
    entries["metadata.json"] = new TextEncoder().encode("[]\n");
    const result = await verify(zipSync(entries, { level: 0 }));
    expect(result.valid).toBe(false);
    expect(result.failureCode).toBe("METADATA_NOT_OBJECT");
  });

  test("rejects a half-present ML-DSA pair", async () => {
    const entries = await baselineEntries();
    entries["signature_pqc.sig"] = new TextEncoder().encode("bmVnYXRpdmUtY29udHJvbA==\n");
    const result = await verify(zipSync(entries, { level: 0 }));
    expect(result.valid).toBe(false);
    expect(result.failureCode).toBe("PQC_PAIR_INCOMPLETE");
  });

  test("rejects a classical-only package when policy requires ML-DSA", async () => {
    const source = await readFile(
      new URL("../../test-vectors/valid/minimal-roundtrip/package.aep", import.meta.url),
    );
    const result = await verify(source, { pqcPolicy: "required" });
    expect(result.valid).toBe(false);
    expect(result.failureCode).toBe("PQC_SIGNATURE_REQUIRED");
  });

  test("rejects an unknown PQC policy instead of silently accepting it", async () => {
    const source = await readFile(
      new URL("../../test-vectors/valid/minimal-roundtrip/package.aep", import.meta.url),
    );
    await expect(
      verify(source, { pqcPolicy: "unknown" as "if-present" }),
    ).rejects.toThrow("pqcPolicy must be");
  });
});

import { zipSync } from "fflate";
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
  });

  test("rejects nested entry names in the flat AEP profile", async () => {
    const result = await verify(
      zipSync({ "nested/entry.txt": new Uint8Array([1]) }),
    );
    expect(result.valid).toBe(false);
    expect(result.failureReason).toContain("flat, safe names");
  });
});

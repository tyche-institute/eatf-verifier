/**
 * Boundary behavioural vector conformance.
 *
 * Each directory under ../test-vectors/boundary/ ships a package.aep
 * plus an expected-boundary.json naming the VerifyOptions to verify
 * with and the BoundaryReport rows the run must produce. Several of
 * these packages verify VALID on purpose — what they freeze is the
 * boundary (advisory failures, short-circuit shadows, unsigned
 * fields, claimed-vs-computed overclaims), not the validity bit.
 */

import { readdirSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";
import { CHECK_REGISTRY } from "../src/check-registry.js";
import type { BoundaryCheck, VerifyOptions } from "../src/index.js";

const BOUNDARY_DIR = resolve("../test-vectors/boundary");

type ExpectedBoundary = {
  description: string;
  options?: VerifyOptions;
  expect: {
    valid: boolean;
    canonicalForm?: "profile" | "response-only" | null;
    metadata?: Record<string, unknown>;
    checks?: Record<string, Partial<BoundaryCheck>>;
    unsignedFieldsInclude?: string[];
    claimedSurface?: { claimed: string[]; unrecognized: string[]; notAssessed: string[] };
  };
};

const vectors = readdirSync(BOUNDARY_DIR, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .sort();

describe("boundary vectors", () => {
  test("the generated set is present", () => {
    expect(vectors.length).toBeGreaterThanOrEqual(6);
  });

  for (const name of vectors) {
    test(name, async () => {
      const expected = JSON.parse(
        readFileSync(resolve(BOUNDARY_DIR, name, "expected-boundary.json"), "utf8"),
      ) as ExpectedBoundary;
      const bytes = await readFile(resolve(BOUNDARY_DIR, name, "package.aep"));

      const result = await verify(bytes, expected.options ?? {});

      expect(result.valid).toBe(expected.expect.valid);
      // Every boundary report carries the full registry in order,
      // whatever the vector pins beyond that.
      expect(result.boundary.checks.map((c) => c.id)).toEqual(CHECK_REGISTRY.map((c) => c.id));

      if (expected.expect.canonicalForm !== undefined) {
        expect(result.boundary.canonicalForm).toBe(expected.expect.canonicalForm);
      }
      for (const [key, value] of Object.entries(expected.expect.metadata ?? {})) {
        expect(result.metadata?.[key], `metadata.${key}`).toEqual(value);
      }
      for (const [id, row] of Object.entries(expected.expect.checks ?? {})) {
        const actual = result.boundary.checks.find((c) => c.id === id);
        expect(actual, `check ${id}`).toBeDefined();
        expect(actual, `check ${id}`).toMatchObject(row);
      }
      for (const field of expected.expect.unsignedFieldsInclude ?? []) {
        expect(result.boundary.unsignedFields, `unsignedFields must list ${field}`).toContain(field);
      }
      if (expected.expect.claimedSurface !== undefined) {
        expect(result.boundary.claimedSurface).toEqual(expected.expect.claimedSurface);
      }
    });
  }
});

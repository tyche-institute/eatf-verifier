/**
 * Detached-mandate vector conformance (spec §4.5).
 *
 * Each directory under ../test-vectors/mandate/ — plus the three valid
 * conformance vectors ../test-vectors/valid/{mandated-action,
 * mandated-and-accepted, mandated-denied-action} and the gating negative
 * ../test-vectors/invalid/profile-form-policy-rewrite — ships a
 * package.aep and an expected-mandate.json naming the VerifyOptions to
 * verify with and the VerifyResult.mandate fields, boundary rows and
 * report lines the run must produce.
 *
 * Two of these packages verify VALID on purpose: scope and temporal
 * containment are appraisal outcomes, and an action outside its mandate
 * may inform but carries no mandate to compel. A third —
 * mandate-reference-only — pins the pre-§4.5 state: a deontic principal
 * named, nothing about it verified.
 */

import { readdirSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";
import { CHECK_REGISTRY } from "../src/check-registry.js";
import type { BoundaryCheck, MandateResult, VerifyOptions } from "../src/index.js";

const MANDATE_DIR = resolve("../test-vectors/mandate");
const NAMED_DIRS = [
  resolve("../test-vectors/valid/mandated-action"),
  resolve("../test-vectors/valid/mandated-and-accepted"),
  resolve("../test-vectors/valid/mandated-denied-action"),
  resolve("../test-vectors/invalid/profile-form-policy-rewrite"),
];

type ExpectedMandate = {
  description: string;
  options?: VerifyOptions;
  expect: {
    valid: boolean;
    failureReason?: string;
    canonicalForm?: "profile" | "response-only" | null;
    mandate?: Partial<MandateResult>;
    checks?: Record<string, Partial<BoundaryCheck>>;
    unsignedFieldsInclude?: string[];
    reportIncludes?: string[];
  };
};

const vectorDirs = [
  ...NAMED_DIRS,
  ...readdirSync(MANDATE_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => resolve(MANDATE_DIR, entry.name))
    .sort(),
];

describe("mandate vectors", () => {
  test("the generated set is present", () => {
    expect(vectorDirs.length).toBeGreaterThanOrEqual(13);
  });

  for (const dir of vectorDirs) {
    const name = dir.split("/").slice(-1)[0]!;
    test(name, async () => {
      const expected = JSON.parse(
        readFileSync(resolve(dir, "expected-mandate.json"), "utf8"),
      ) as ExpectedMandate;
      const bytes = await readFile(resolve(dir, "package.aep"));

      const result = await verify(bytes, expected.options ?? {});

      expect(result.valid).toBe(expected.expect.valid);
      expect(result.boundary.checks.map((c) => c.id)).toEqual(CHECK_REGISTRY.map((c) => c.id));

      if (expected.expect.failureReason !== undefined) {
        expect(result.failureReason).toBe(expected.expect.failureReason);
      }
      if (expected.expect.canonicalForm !== undefined) {
        expect(result.canonicalForm).toBe(expected.expect.canonicalForm);
      }
      if (expected.expect.mandate !== undefined) {
        expect(result.mandate, "mandate").not.toBeNull();
        expect(result.mandate).toMatchObject(expected.expect.mandate);
      }
      for (const [id, row] of Object.entries(expected.expect.checks ?? {})) {
        const actual = result.boundary.checks.find((c) => c.id === id);
        expect(actual, `check ${id}`).toBeDefined();
        expect(actual, `check ${id}`).toMatchObject(row);
      }
      for (const field of expected.expect.unsignedFieldsInclude ?? []) {
        expect(result.boundary.unsignedFields, `unsignedFields must list ${field}`).toContain(field);
      }
      for (const line of expected.expect.reportIncludes ?? []) {
        expect(result.report, `report must include: ${line}`).toContain(line);
      }
    });
  }
});

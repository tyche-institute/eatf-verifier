/**
 * Warrant behavioural vector conformance.
 *
 * Each directory under ../test-vectors/warrant/ — plus the valid
 * conformance vector ../test-vectors/valid/warranted-action/ — ships a
 * package.aep and an expected-warrant.json naming the VerifyOptions to
 * verify with and the VerifyResult.warrant fields, boundary rows, and
 * report lines the run must produce. Several of these packages verify
 * VALID on purpose: applicability and freshness are appraisal
 * outcomes, and an output whose warrant does not apply may inform but
 * carries no warrant to compel.
 */

import { readdirSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";
import { CHECK_REGISTRY } from "../src/check-registry.js";
import type { BoundaryCheck, VerifyOptions, WarrantResult } from "../src/index.js";

const WARRANT_DIR = resolve("../test-vectors/warrant");
const WARRANTED_ACTION_DIR = resolve("../test-vectors/valid/warranted-action");

type ExpectedWarrant = {
  description: string;
  options?: VerifyOptions;
  expect: {
    valid: boolean;
    failureReason?: string;
    canonicalForm?: "profile" | "response-only" | null;
    warrant?: Partial<WarrantResult>;
    checks?: Record<string, Partial<BoundaryCheck>>;
    unsignedFieldsInclude?: string[];
    reportIncludes?: string[];
  };
};

const vectorDirs = [
  WARRANTED_ACTION_DIR,
  ...readdirSync(WARRANT_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => resolve(WARRANT_DIR, entry.name))
    .sort(),
];

describe("warrant vectors", () => {
  test("the generated set is present", () => {
    expect(vectorDirs.length).toBeGreaterThanOrEqual(9);
  });

  for (const dir of vectorDirs) {
    const name = dir.split("/").slice(-1)[0]!;
    test(name, async () => {
      const expected = JSON.parse(
        readFileSync(resolve(dir, "expected-warrant.json"), "utf8"),
      ) as ExpectedWarrant;
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
      if (expected.expect.warrant !== undefined) {
        expect(result.warrant, "warrant").not.toBeNull();
        expect(result.warrant).toMatchObject(expected.expect.warrant);
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

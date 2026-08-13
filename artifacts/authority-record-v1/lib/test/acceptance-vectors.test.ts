/**
 * Accepting-authority vector conformance (spec §4.3).
 *
 * Each directory under ../test-vectors/acceptance/ ships a package.aep and
 * an expected-acceptance.json naming the VerifyResult.acceptingAuthority
 * fields, boundary rows and report lines the run must produce. All four are
 * REJECTED: they are the isolated adversaries of the two §4.3 binding-family
 * checks, one broken property each, so a failure names one check.
 *
 * The two §4.3 adversaries that do NOT reject stay under
 * ../test-vectors/voiding/ and are driven by voiding-vectors.test.ts:
 * `expired-acceptance` (temporal containment) and
 * `authority-key-substitution` (role). Those two checks are appraisal — an
 * expired acceptance is authentic and bound, and role is undecidable from
 * the package alone — and the pair of trees together is the enforced/advisory
 * line of §4.3, drawn where §4.5 draws it.
 */

import { readdirSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";
import { CHECK_REGISTRY } from "../src/check-registry.js";
import type {
  AcceptingAuthorityResult,
  BoundaryCheck,
  VerifyOptions,
} from "../src/index.js";

const ACCEPTANCE_DIR = resolve("../test-vectors/acceptance");

type ExpectedAcceptance = {
  description: string;
  options?: VerifyOptions;
  expect: {
    valid: boolean;
    failureReason?: string;
    canonicalForm?: "profile" | "response-only" | null;
    acceptingAuthority?: Partial<AcceptingAuthorityResult>;
    checks?: Record<string, Partial<BoundaryCheck>>;
    reportIncludes?: string[];
  };
};

const vectorDirs = readdirSync(ACCEPTANCE_DIR, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => resolve(ACCEPTANCE_DIR, entry.name))
  .sort();

describe("accepting-authority vectors", () => {
  test("the generated set is present", () => {
    expect(vectorDirs.length).toBeGreaterThanOrEqual(4);
  });

  test("every vector in this tree is rejected", async () => {
    for (const dir of vectorDirs) {
      const result = await verify(await readFile(resolve(dir, "package.aep")), {});
      expect(result.valid, `${dir} must be rejected`).toBe(false);
    }
  });

  for (const dir of vectorDirs) {
    const name = dir.split("/").slice(-1)[0]!;
    test(name, async () => {
      const expected = JSON.parse(
        readFileSync(resolve(dir, "expected-acceptance.json"), "utf8"),
      ) as ExpectedAcceptance;
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
      if (expected.expect.acceptingAuthority !== undefined) {
        // A rejection must not drop the evidence the run had in hand: the
        // §4.3 outcome is carried onto the failing result, not nulled.
        expect(result.acceptingAuthority, "acceptingAuthority").not.toBeNull();
        expect(result.acceptingAuthority).toMatchObject(expected.expect.acceptingAuthority);
      }
      for (const [id, row] of Object.entries(expected.expect.checks ?? {})) {
        const actual = result.boundary.checks.find((c) => c.id === id);
        expect(actual, `check ${id}`).toBeDefined();
        expect(actual, `check ${id}`).toMatchObject(row);
      }
      for (const line of expected.expect.reportIncludes ?? []) {
        expect(result.report, `report must include: ${line}`).toContain(line);
      }
    });
  }

  test("the verify-expected.txt contract agrees with the run", async () => {
    for (const dir of vectorDirs) {
      const lines = readFileSync(resolve(dir, "verify-expected.txt"), "utf8").split("\n");
      const result = await verify(await readFile(resolve(dir, "package.aep")), {});
      expect(lines[0], dir).toBe(`verify=${result.valid}`);
      expect(lines[1], dir).toBe(`diagnostic=${result.failureReason}`);
    }
  });
});

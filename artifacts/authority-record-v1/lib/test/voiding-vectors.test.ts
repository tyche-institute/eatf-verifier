/**
 * Voiding + accepting-authority behavioural vector conformance (spec §4.3,
 * §4.4).
 *
 * Each directory under ../test-vectors/voiding/ — plus the valid conformance
 * vectors ../test-vectors/valid/voided-and-authorized/ and
 * ../test-vectors/valid/co-located-authority/ — ships a package.aep
 * and an expected-voiding.json naming the VerifyOptions to verify with and
 * the VerifyResult.voidingVerdicts / acceptingAuthority fields, boundary
 * rows, and report lines the run must produce.
 *
 * Every §4.4 voiding package verifies VALID on purpose: a voiding verdict is
 * informational in this release and does not flip `valid`. The §4.3
 * accepting-authority packages split: the two binding-family checks gate, so
 * `tampered-acceptance`, `acceptance-policy-mismatch` and
 * `response-only-with-authority` are REJECTED, while `expired-acceptance`
 * (temporal containment) and `authority-key-substitution` (role) are
 * appraisal and stay accepted. That split is the point of keeping all five
 * here; the isolated single-property §4.3 negatives live under
 * ../test-vectors/acceptance/.
 *
 * Registry snapshots and authority trust lists are CALLER-SUPPLIED inputs,
 * never packaged in the .aep. The expected file carries them inline
 * (options.registrySnapshot.inline) or by key name
 * (options.authorityTrustListKeys); resolveOptions() rebuilds the real
 * VerifyOptions exactly as scripts/generate-voiding-vectors.mjs does.
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
  VoidingVerdict,
} from "../src/index.js";

const VOIDING_DIR = resolve("../test-vectors/voiding");
const VALID_DIR = resolve("../test-vectors/valid/voided-and-authorized");
const CO_LOCATED_DIR = resolve("../test-vectors/valid/co-located-authority");
const KEYS_DIR = resolve("../test-vectors/keys");

const TEXT_ENC = new TextEncoder();

type RawOptions = {
  tsaTrustList?: string[];
  supersessionList?: string[];
  registrySnapshot?: { inline: unknown; date: string };
  authorityTrustListKeys?: string[];
};

type ExpectedVoiding = {
  description: string;
  options?: RawOptions;
  expect: {
    valid: boolean;
    failureReason?: string;
    canonicalForm?: "profile" | "response-only" | null;
    voiding?: Array<Partial<VoidingVerdict> & { id: string }>;
    acceptingAuthority?: Partial<AcceptingAuthorityResult>;
    checks?: Record<string, Partial<BoundaryCheck>>;
    reportIncludes?: string[];
  };
};

function resolveOptions(raw: RawOptions | undefined): VerifyOptions {
  if (!raw) return {};
  const opts: VerifyOptions = {};
  if (raw.tsaTrustList !== undefined) opts.tsaTrustList = raw.tsaTrustList;
  if (raw.supersessionList) opts.supersessionList = raw.supersessionList;
  if (raw.registrySnapshot?.inline !== undefined) {
    opts.registrySnapshot = {
      bytes: TEXT_ENC.encode(JSON.stringify(raw.registrySnapshot.inline)),
      date: raw.registrySnapshot.date,
    };
  }
  if (raw.authorityTrustListKeys) {
    opts.authorityTrustList = raw.authorityTrustListKeys.map((k) =>
      readFileSync(resolve(KEYS_DIR, `${k}.pem`), "utf8"),
    );
  }
  return opts;
}

const vectorDirs = [
  VALID_DIR,
  CO_LOCATED_DIR,
  ...readdirSync(VOIDING_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => resolve(VOIDING_DIR, entry.name))
    .sort(),
];

describe("voiding + accepting-authority vectors", () => {
  test("the generated set is present", () => {
    expect(vectorDirs.length).toBeGreaterThanOrEqual(12);
  });

  for (const dir of vectorDirs) {
    const name = dir.split("/").slice(-1)[0]!;
    test(name, async () => {
      const expected = JSON.parse(
        readFileSync(resolve(dir, "expected-voiding.json"), "utf8"),
      ) as ExpectedVoiding;
      const bytes = await readFile(resolve(dir, "package.aep"));

      const result = await verify(bytes, resolveOptions(expected.options));

      expect(result.valid).toBe(expected.expect.valid);
      expect(result.boundary.checks.map((c) => c.id)).toEqual(CHECK_REGISTRY.map((c) => c.id));

      if (expected.expect.failureReason !== undefined) {
        expect(result.failureReason).toBe(expected.expect.failureReason);
      }
      if (expected.expect.canonicalForm !== undefined) {
        expect(result.canonicalForm).toBe(expected.expect.canonicalForm);
      }
      for (const ev of expected.expect.voiding ?? []) {
        expect(result.voidingVerdicts, "voidingVerdicts").not.toBeNull();
        const actual = result.voidingVerdicts!.find((v) => v.id === ev.id);
        expect(actual, `voiding verdict ${ev.id}`).toBeDefined();
        expect(actual, `voiding verdict ${ev.id}`).toMatchObject(ev);
      }
      if (expected.expect.acceptingAuthority !== undefined) {
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
});

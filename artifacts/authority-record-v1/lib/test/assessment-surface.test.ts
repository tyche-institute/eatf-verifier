/**
 * Registry-vs-spec two-set diff (the registry-shrink guard).
 *
 * docs/specs/assessment-surface-v1.json enumerates the normative
 * clauses of docs/specs/aep-profile-v1.md and maps each onto a
 * CHECK_REGISTRY check id or onto "no-executable-check". This suite
 * fails the build whenever either side drifts on its own:
 *
 *   - a check added to the registry without a spec clause claiming it
 *     (an assessed surface the spec never asked for), or
 *   - a check removed from the registry while the map still names it
 *     (a spec clause silently losing its executable check), or
 *   - a registry version bump without a map touch (and vice versa).
 *
 * The point is the denominator: any "share of the spec assessed"
 * figure divides by this map, which is derived from the spec surface —
 * never by the verifier's own check list.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import {
  CHECK_REGISTRY,
  CHECK_REGISTRY_VERSION,
  checkRegistryDigest,
} from "../src/check-registry.js";

type SurfaceMap = {
  version: string;
  registry_version: string;
  clauses: Array<{ clause: string; statement: string; check: string }>;
};

// vitest runs with cwd == lib/, so the spec map sits at ../docs/specs/.
const MAP_PATH = resolve("../docs/specs/assessment-surface-v1.json");
const surface = JSON.parse(readFileSync(MAP_PATH, "utf8")) as SurfaceMap;

const registryIds = new Set(CHECK_REGISTRY.map((entry) => entry.id));
const mappedIds = new Set(
  surface.clauses.map((row) => row.check).filter((check) => check !== "no-executable-check"),
);

describe("assessment-surface map vs CHECK_REGISTRY", () => {
  test("map pins the registry version it was derived against", () => {
    expect(surface.registry_version).toBe(CHECK_REGISTRY_VERSION);
  });

  test("every registry check is claimed by at least one spec clause", () => {
    const unclaimed = [...registryIds].filter((id) => !mappedIds.has(id));
    expect(unclaimed).toEqual([]);
  });

  test("every mapped check id still exists in the registry (shrink guard)", () => {
    const orphaned = [...mappedIds].filter((id) => !registryIds.has(id as never));
    expect(orphaned).toEqual([]);
  });

  test("registry clause labels match the map rows that claim them", () => {
    for (const entry of CHECK_REGISTRY) {
      const rows = surface.clauses.filter((row) => row.check === entry.id);
      expect(
        rows.some((row) => row.clause === entry.clause),
        `registry check ${entry.id} carries clause "${entry.clause}" but no map row with that clause names it`,
      ).toBe(true);
    }
  });

  test("every map row names a real clause and a non-empty statement", () => {
    for (const row of surface.clauses) {
      expect(row.clause).toMatch(/^§\d/);
      expect(row.statement.length).toBeGreaterThan(0);
    }
  });

  test("registry digest is stable and well-formed", async () => {
    const digest = await checkRegistryDigest();
    expect(digest).toMatch(/^[0-9a-f]{64}$/);
    expect(digest).toBe(await checkRegistryDigest());
  });
});

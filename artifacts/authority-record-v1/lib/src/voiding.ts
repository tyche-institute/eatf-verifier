/**
 * Typed per-output voiding predicates (docs/specs/aep-profile-v1.md §4.4),
 * a four-valued evaluator over caller-supplied inputs.
 *
 * A voiding predicate is a machine-evaluable condition carried in
 * metadata.voiding that, when it holds, voids or degrades the output. Each
 * entry is evaluated to a four-valued verdict:
 *
 *   holds        — the voiding condition did NOT fire; the output holds.
 *   voided       — the voiding condition fired; the output is voided/degraded.
 *   unknown      — a KNOWN predicate type whose caller-supplied input or a
 *                  required fact is absent; NEVER silently "holds".
 *   not-assessed — an UNKNOWN predicate type, or an attested-only predicate.
 *
 * External state is a caller-supplied input (a dated registry snapshot, a
 * supersession list) exactly like the TSA trust list — never a network
 * fetch, so verification stays offline-deterministic and every verdict is
 * explicitly relative to a named snapshot.
 *
 * THE DUAL-TIME CORE. For `registry-status` predicates the verifier
 * evaluates the SAME snapshot twice: once at the package's RFC 3161 genTime
 * (`atSigning`) and once at the caller-supplied evaluation instant of the
 * snapshot (`now`). The pair is surfaced and is NEVER collapsed to one
 * boolean. This imports the dual-time temporal-validation semantics of AdES
 * signature validation (ETSI EN 319 102-1) and eIDAS status determination
 * (ETSI TS 119 615) — where those procedures collapse the two evaluations
 * into one indication, here the DIVERGENCE between them is the reportable
 * object. The semantics are imported, not invented.
 */

import { isRecord, textAt } from "./overt.js";
import type { VoidingVerdict, VoidingVerdictValue } from "./index.js";

const TEXT_DEC = new TextDecoder();

/** Caller-supplied inputs and package facts the evaluator reads. */
export type VoidingContext = {
  /** RFC 3161 genTime extracted from the package (inspectTsa), or null. */
  genTime: Date | null;
  /** Caller-supplied dated registry snapshot (bytes + evaluation instant). */
  registrySnapshot?: { bytes: Uint8Array; date: string };
  /** Caller-supplied list of superseded artifact identifiers. */
  supersessionList?: string[];
  /** The package's TSA-trust tri-state, for `tsa-trust` predicates. */
  tsaTrusted: boolean | null;
};

type RegistrySnapshotDoc = {
  entries?: Record<string, unknown>;
};

/**
 * Evaluate every metadata.voiding predicate. Returns null when the package
 * carries no voiding array; otherwise one verdict per entry, in order.
 */
export function evaluateVoiding(
  metadata: Record<string, unknown>,
  ctx: VoidingContext,
): VoidingVerdict[] | null {
  const raw = metadata["voiding"];
  if (!Array.isArray(raw)) {
    return null;
  }

  const snapshot = parseSnapshot(ctx.registrySnapshot);

  return raw.map((entry, index) => evaluateEntry(entry, index, ctx, snapshot));
}

type ParsedSnapshot =
  | { state: "absent" }
  | { state: "unparseable" }
  | { state: "ok"; entries: Record<string, unknown>; now: Date | null };

function parseSnapshot(
  input: { bytes: Uint8Array; date: string } | undefined,
): ParsedSnapshot {
  if (!input) {
    return { state: "absent" };
  }
  let doc: RegistrySnapshotDoc;
  try {
    const parsed = JSON.parse(TEXT_DEC.decode(input.bytes)) as unknown;
    if (!isRecord(parsed)) {
      return { state: "unparseable" };
    }
    doc = parsed as RegistrySnapshotDoc;
  } catch {
    return { state: "unparseable" };
  }
  const entries = isRecord(doc.entries) ? doc.entries : {};
  const nowDate = new Date(input.date);
  const now = Number.isNaN(nowDate.getTime()) ? null : nowDate;
  return { state: "ok", entries, now };
}

function evaluateEntry(
  entry: unknown,
  index: number,
  ctx: VoidingContext,
  snapshot: ParsedSnapshot,
): VoidingVerdict {
  if (!isRecord(entry)) {
    return { id: `voiding[${index}]`, type: "", verdict: "not-assessed", reason: "malformed_entry" };
  }
  const id = textAt(entry, "id") ?? `voiding[${index}]`;
  const type = textAt(entry, "type") ?? "";
  const subject = isRecord(entry["subject"]) ? (entry["subject"] as Record<string, unknown>) : {};

  switch (type) {
    case "registry-status":
      return evaluateRegistryStatus(id, type, subject, ctx, snapshot);
    case "mandate-revocation":
      return evaluateMandateRevocation(id, type, subject, snapshot);
    case "artifact-supersession":
      return evaluateArtifactSupersession(id, type, subject, ctx);
    case "telemetry-freshness":
      return evaluateTelemetryFreshness(id, type, subject, ctx);
    case "tsa-trust":
      return evaluateTsaTrust(id, type, ctx);
    case "attested":
      return { id, type, verdict: "not-assessed", reason: "attested" };
    default:
      // Unknown predicate type: NEVER "holds".
      return { id, type, verdict: "not-assessed", reason: "unknown_type" };
  }
}

/**
 * registry-status: dual-time. Read the same snapshot at genTime and at the
 * snapshot's evaluation instant; emit both members and never collapse them.
 */
function evaluateRegistryStatus(
  id: string,
  type: string,
  subject: Record<string, unknown>,
  ctx: VoidingContext,
  snapshot: ParsedSnapshot,
): VoidingVerdict {
  if (snapshot.state === "absent") {
    return { id, type, verdict: "unknown", atSigning: "unknown", now: "unknown", reason: "input_absent" };
  }
  if (snapshot.state === "unparseable") {
    return { id, type, verdict: "unknown", atSigning: "unknown", now: "unknown", reason: "parse_failure" };
  }
  const entryId = textAt(subject, "entry_id") ?? textAt(subject, "id");
  const record = entryId !== null ? snapshot.entries[entryId] : undefined;
  const atSigning = statusAt(record, ctx.genTime);
  const now = statusAt(record, snapshot.now);
  // The `now` member is the operative current-time answer; both stay visible.
  return { id, type, verdict: now, atSigning, now };
}

/**
 * mandate-revocation: single-time as-of the snapshot instant. Distinct from
 * registry-status (no dual-time pair): a mandate is revoked or it is not.
 */
function evaluateMandateRevocation(
  id: string,
  type: string,
  subject: Record<string, unknown>,
  snapshot: ParsedSnapshot,
): VoidingVerdict {
  if (snapshot.state === "absent") {
    return { id, type, verdict: "unknown", reason: "input_absent" };
  }
  if (snapshot.state === "unparseable") {
    return { id, type, verdict: "unknown", reason: "parse_failure" };
  }
  const mandateId = textAt(subject, "mandate_id") ?? textAt(subject, "entry_id");
  const record = mandateId !== null ? snapshot.entries[mandateId] : undefined;
  return { id, type, verdict: statusAt(record, snapshot.now) };
}

/** artifact-supersession: subject.artifact_id present in the supersession list. */
function evaluateArtifactSupersession(
  id: string,
  type: string,
  subject: Record<string, unknown>,
  ctx: VoidingContext,
): VoidingVerdict {
  if (!Array.isArray(ctx.supersessionList)) {
    return { id, type, verdict: "unknown", reason: "input_absent" };
  }
  const artifactId = textAt(subject, "artifact_id");
  if (artifactId === null) {
    return { id, type, verdict: "unknown", reason: "subject_incomplete" };
  }
  return { id, type, verdict: ctx.supersessionList.includes(artifactId) ? "voided" : "holds" };
}

/**
 * telemetry-freshness: the telemetry underlying the decision was already
 * stale at signing time (genTime - sampled_at > max_age_seconds). Judged
 * against the RFC 3161 genTime, so it needs no extra caller input.
 */
function evaluateTelemetryFreshness(
  id: string,
  type: string,
  subject: Record<string, unknown>,
  ctx: VoidingContext,
): VoidingVerdict {
  const sampledText = textAt(subject, "sampled_at");
  const maxAge = subject["max_age_seconds"];
  if (sampledText === null || typeof maxAge !== "number" || !Number.isFinite(maxAge)) {
    return { id, type, verdict: "unknown", reason: "subject_incomplete" };
  }
  const sampledAt = new Date(sampledText);
  if (Number.isNaN(sampledAt.getTime())) {
    return { id, type, verdict: "unknown", reason: "subject_incomplete" };
  }
  if (ctx.genTime === null) {
    return { id, type, verdict: "unknown", reason: "input_absent" };
  }
  const ageSeconds = (ctx.genTime.getTime() - sampledAt.getTime()) / 1000;
  return { id, type, verdict: ageSeconds > maxAge ? "voided" : "holds" };
}

/** tsa-trust: the package's TSA trust tri-state maps to holds/voided/unknown. */
function evaluateTsaTrust(id: string, type: string, ctx: VoidingContext): VoidingVerdict {
  if (ctx.tsaTrusted === true) return { id, type, verdict: "holds" };
  if (ctx.tsaTrusted === false) return { id, type, verdict: "voided" };
  return { id, type, verdict: "unknown", reason: "input_absent" };
}

/**
 * Read one registry entry's status as of `instant`. Absent entry or a null
 * instant is "unknown"; a withdrawal timestamp at or before the instant is
 * "voided"; otherwise "holds" (including a forward-dated withdrawal whose
 * effective date is still in the future relative to the instant).
 */
function statusAt(record: unknown, instant: Date | null): VoidingVerdictValue {
  if (instant === null) return "unknown";
  if (record === undefined) return "unknown";
  const withdrawnText =
    textAt(record, "withdrawn_at") ?? textAt(record, "revoked_at") ?? null;
  if (withdrawnText === null) {
    return "holds";
  }
  const withdrawnAt = new Date(withdrawnText);
  if (Number.isNaN(withdrawnAt.getTime())) {
    return "unknown";
  }
  return withdrawnAt.getTime() <= instant.getTime() ? "voided" : "holds";
}

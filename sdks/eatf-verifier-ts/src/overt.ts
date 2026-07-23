const TEXT_DEC = new TextDecoder();

export type OvertReceipt = Record<string, unknown>;

export type OvertValidation = {
  receipt: OvertReceipt | null;
  error: string | null;
};

const OVERT_VERSION = "1.0.0";
const AEP_PROFILE = "urn:eatf:spec:aep:1.0";

export function parseAndValidateOvertReceipt(
  entries: Record<string, Uint8Array>,
  metadata: Record<string, unknown>,
  expectedHashHex: string,
): OvertValidation {
  const bytes = entries["overt_receipt.json"];
  if (!bytes || bytes.length === 0) {
    return { receipt: null, error: null };
  }

  let receipt: OvertReceipt;
  try {
    const parsed = JSON.parse(TEXT_DEC.decode(bytes));
    if (!isRecord(parsed)) {
      return { receipt: null, error: "receipt must be a JSON object" };
    }
    receipt = parsed;
  } catch (e) {
    return { receipt: null, error: "receipt is not valid JSON" };
  }

  if (textAt(receipt, "overt") !== OVERT_VERSION) {
    return { receipt, error: `overt must be ${OVERT_VERSION}` };
  }
  if (textAt(receipt, "profile") !== AEP_PROFILE) {
    return { receipt, error: `profile must be ${AEP_PROFILE}` };
  }
  const scope = textAt(receipt, "scope");
  if (!scope) {
    return { receipt, error: "scope is required" };
  }
  if (textAt(receipt, "content_hash") !== `sha256:${expectedHashHex.toLowerCase()}`) {
    return { receipt, error: "content_hash does not match hash.sha256" };
  }

  const textMismatch =
    compareMetadataText(metadata, ["created_at", "createdAt"], receipt, ["event", "timestamp"], "event.timestamp") ??
    compareMetadataText(metadata, ["agent_id", "agentId"], receipt, ["subject", "agent_id"], "subject.agent_id") ??
    compareMetadataText(metadata, ["tenant_id_hash", "tenantIdHash"], receipt, ["subject", "tenant_hash"], "subject.tenant_hash") ??
    compareMetadataText(metadata, ["action_type", "actionType"], receipt, ["event", "action_type"], "event.action_type") ??
    compareMetadataText(metadata, ["policy_version", "policyVersion"], receipt, ["policy", "version"], "policy.version") ??
    compareMetadataText(metadata, ["policy_decision", "policyDecision"], receipt, ["policy", "decision"], "policy.decision");
  if (textMismatch) {
    return { receipt, error: textMismatch };
  }

  const coverageMismatch = compareMetadataNumber(
    metadata,
    "policy_coverage",
    valueAt(receipt, ["policy", "coverage"]),
    "policy.coverage",
  );
  if (coverageMismatch) {
    return { receipt, error: coverageMismatch };
  }

  const signatureRefsError = validateRefs(entries, receipt, "signature_refs", true);
  if (signatureRefsError) {
    return { receipt, error: signatureRefsError };
  }
  const timestampRefsError = validateRefs(entries, receipt, "timestamp_refs", false);
  if (timestampRefsError) {
    return { receipt, error: timestampRefsError };
  }

  return { receipt, error: null };
}

function compareMetadataText(
  metadata: Record<string, unknown>,
  metadataKeys: string[],
  receipt: OvertReceipt,
  receiptPath: string[],
  label: string,
): string | null {
  const metadataValue = firstText(metadata, metadataKeys);
  if (!metadataValue) return null;
  if (textAt(receipt, ...receiptPath) !== metadataValue) {
    return `${label} does not match metadata.${metadataKeys[0]}`;
  }
  return null;
}

function compareMetadataNumber(
  metadata: Record<string, unknown>,
  metadataKey: string,
  receiptValue: unknown,
  label: string,
): string | null {
  const metadataValue = metadata[metadataKey];
  if (metadataValue === undefined || metadataValue === null) return null;
  if (typeof metadataValue !== "number" || typeof receiptValue !== "number") {
    return `${label} does not match metadata.${metadataKey}`;
  }
  if (Math.abs(metadataValue - receiptValue) > 1e-9) {
    return `${label} does not match metadata.${metadataKey}`;
  }
  return null;
}

function validateRefs(
  entries: Record<string, Uint8Array>,
  receipt: OvertReceipt,
  key: "signature_refs" | "timestamp_refs",
  requireNonEmpty: boolean,
): string | null {
  const refs = valueAt(receipt, ["witness", key]);
  if (!Array.isArray(refs)) {
    return `witness.${key} must be an array`;
  }
  if (requireNonEmpty && refs.length === 0) {
    return `witness.${key} must name at least one file`;
  }
  for (const ref of refs) {
    if (typeof ref !== "string" || ref.trim() === "") {
      return `witness.${key} contains a non-text ref`;
    }
    if (ref.includes("/") || ref.includes("\\")) {
      return `witness.${key} must use flat package filenames`;
    }
    const entry = entries[ref];
    if (!entry) {
      return `witness.${key} references missing file ${ref}`;
    }
    if (entry.length === 0) {
      return `witness.${key} references empty file ${ref}`;
    }
  }
  return null;
}

function valueAt(value: unknown, path: string[]): unknown {
  let current = value;
  for (const segment of path) {
    if (!isRecord(current) || !(segment in current)) return undefined;
    current = current[segment];
  }
  return current;
}

function textAt(value: unknown, ...path: string[]): string | null {
  const found = valueAt(value, path);
  if (typeof found !== "string" || found.trim() === "") {
    return null;
  }
  return found;
}

function firstText(record: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim() !== "") {
      return value;
    }
  }
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

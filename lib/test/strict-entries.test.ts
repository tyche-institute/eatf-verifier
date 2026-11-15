import { readFile } from "node:fs/promises";
import { unzipSync, zipSync } from "fflate";
import { describe, expect, test } from "vitest";

import type { VerifyOptions } from "../src/index.js";
import { verify } from "../src/verifier.js";

// One reading of public_key.pem, metadata.json and the base64 signature
// entries in both verifiers. lib-python/tests/test_strict_entries.py runs the
// same cases against the Python verifier; both ports must report the same
// first-failure code for each.

const TEXT_ENC = new TextEncoder();
const TEXT_DEC = new TextDecoder();

// Current profile form, so metadata.json is bound by the signature; it also
// carries a marked overt_receipt.sig.
async function baseEntries(): Promise<Record<string, Uint8Array>> {
  const source = await readFile(
    new URL("../../test-vectors/valid/minimal-roundtrip/package.aep", import.meta.url),
  );
  return unzipSync(source);
}

async function signerPem(): Promise<string> {
  // dev-rsa-4096.pem is the key that signed minimal-roundtrip.
  return readFile(new URL("../../test-vectors/keys/dev-rsa-4096.pem", import.meta.url), "utf8");
}

async function verifyReplacing(
  replace: (entries: Record<string, Uint8Array>) => void | Promise<void>,
  options: VerifyOptions = {},
): Promise<[boolean, string | null]> {
  const entries = await baseEntries();
  await replace(entries);
  const result = await verify(zipSync(entries, { level: 0 }), options);
  return [result.valid, result.failureCode];
}

function text(entries: Record<string, Uint8Array>, name: string): string {
  return TEXT_DEC.decode(entries[name]!);
}

function pemBody(pem: string): string {
  return pem
    .split(/\r?\n/)
    .filter((line) => line && !line.startsWith("-----"))
    .join("");
}

function pemOf(label: string, body: string, eol = "\n", width = 64): string {
  const lines = body.match(new RegExp(`.{1,${width}}`, "g"))!;
  return `-----BEGIN ${label}-----${eol}${lines.join(eol)}${eol}-----END ${label}-----${eol}`;
}

function concat(...parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, part) => n + part.length, 0));
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

function nested(depth: number): string {
  // A member holding depth - 1 arrays inside the top-level object.
  return `${"[".repeat(depth - 1)}${"]".repeat(depth - 1)}`;
}

describe("public_key.pem", () => {
  test("the base package verifies", async () => {
    expect(await verifyReplacing(() => {})).toEqual([true, null]);
  });

  test("accepts CRLF line endings and other line widths", async () => {
    const result = await verifyReplacing((e) => {
      e["public_key.pem"] = TEXT_ENC.encode(pemOf("PUBLIC KEY", pemBody(text(e, "public_key.pem")), "\r\n", 76));
    });
    expect(result).toEqual([true, null]);
  });

  test("rejects two PEM blocks", async () => {
    const result = await verifyReplacing((e) => {
      const pem = text(e, "public_key.pem");
      e["public_key.pem"] = TEXT_ENC.encode(pem + pem);
    });
    expect(result).toEqual([false, "RSA_VERIFY_ERROR"]);
  });

  test("rejects the PKCS#1 RSA PUBLIC KEY label", async () => {
    const result = await verifyReplacing((e) => {
      e["public_key.pem"] = TEXT_ENC.encode(pemOf("RSA PUBLIC KEY", pemBody(text(e, "public_key.pem"))));
    });
    expect(result).toEqual([false, "RSA_VERIFY_ERROR"]);
  });

  test("rejects bytes after the SubjectPublicKeyInfo", async () => {
    const result = await verifyReplacing((e) => {
      const der = Buffer.from(pemBody(text(e, "public_key.pem")), "base64");
      const body = Buffer.concat([der, Buffer.from([0x05, 0x00])]).toString("base64");
      e["public_key.pem"] = TEXT_ENC.encode(pemOf("PUBLIC KEY", body));
    });
    expect(result).toEqual([false, "RSA_VERIFY_ERROR"]);
  });

  test("a signer pin matches on the DER, whatever its line layout", async () => {
    const pin = pemOf("PUBLIC KEY", pemBody(await signerPem()), "\r\n", 76);
    expect(await verifyReplacing(() => {}, { trustedSignerPems: [pin] })).toEqual([true, null]);
  });

  test("a signer pin of two PEM blocks matches nothing", async () => {
    const pem = await signerPem();
    const result = await verifyReplacing(() => {}, { trustedSignerPems: [pem + pem] });
    expect(result).toEqual([false, "SIGNER_NOT_TRUSTED"]);
  });
});

describe("metadata.json", () => {
  test("rejects a repeated member name, even when the last value is the signed one", async () => {
    const result = await verifyReplacing((e) => {
      e["metadata.json"] = TEXT_ENC.encode(
        text(e, "metadata.json").replace(/^\{/, '{"schema":"urn:example:other",'),
      );
    });
    expect(result).toEqual([false, "METADATA_INVALID_JSON"]);
  });

  test("rejects a repeated member name written with an escape", async () => {
    const result = await verifyReplacing((e) => {
      e["metadata.json"] = TEXT_ENC.encode(
        text(e, "metadata.json").replace(/^\{/, '{"sch\\u0065ma":"urn:example:other",'),
      );
    });
    expect(result).toEqual([false, "METADATA_INVALID_JSON"]);
  });

  test("allows one name in two different objects", async () => {
    const result = await verifyReplacing((e) => {
      e["metadata.json"] = TEXT_ENC.encode(
        text(e, "metadata.json").replace(/^\{/, '{"x":{"schema":1},'),
      );
    });
    expect(result).toEqual([false, "CANONICAL_FORM_MISMATCH"]);
  });

  test("rejects a UTF-8 byte order mark", async () => {
    const result = await verifyReplacing((e) => {
      e["metadata.json"] = concat(new Uint8Array([0xef, 0xbb, 0xbf]), e["metadata.json"]!);
    });
    expect(result).toEqual([false, "METADATA_INVALID_JSON"]);
  });

  test("rejects bytes that are not UTF-8", async () => {
    const result = await verifyReplacing((e) => {
      e["metadata.json"] = concat(TEXT_ENC.encode('{"x":"'), new Uint8Array([0xff]), TEXT_ENC.encode('"}'));
    });
    expect(result).toEqual([false, "METADATA_INVALID_JSON"]);
  });

  test("rejects a NaN literal", async () => {
    const result = await verifyReplacing((e) => {
      e["metadata.json"] = TEXT_ENC.encode('{"x":NaN}');
    });
    expect(result).toEqual([false, "METADATA_INVALID_JSON"]);
  });

  test("allows 64 nested levels and rejects 65", async () => {
    const at = (depth: number) =>
      verifyReplacing((e) => {
        e["metadata.json"] = TEXT_ENC.encode(`{"x":${nested(depth)}}`);
      });
    expect(await at(64)).toEqual([false, "CANONICAL_FORM_MISMATCH"]);
    expect(await at(65)).toEqual([false, "METADATA_INVALID_JSON"]);
  });
});

describe("signature entries", () => {
  test("accept CRLF-wrapped base64", async () => {
    const result = await verifyReplacing((e) => {
      const sig = text(e, "signature.sig").trim();
      e["signature.sig"] = TEXT_ENC.encode(sig.match(/.{1,64}/g)!.join("\r\n") + "\r\n");
    });
    expect(result).toEqual([true, null]);
  });

  test("signature.sig rejects missing padding", async () => {
    const result = await verifyReplacing((e) => {
      e["signature.sig"] = TEXT_ENC.encode(text(e, "signature.sig").trim().replace(/=+$/, ""));
    });
    expect(result).toEqual([false, "RSA_SIGNATURE_ENCODING"]);
  });

  test("signature.sig rejects a NUL byte inside the base64", async () => {
    const result = await verifyReplacing((e) => {
      const sig = text(e, "signature.sig");
      e["signature.sig"] = concat(TEXT_ENC.encode(sig.slice(0, 100)), new Uint8Array([0]), TEXT_ENC.encode(sig.slice(100)));
    });
    expect(result).toEqual([false, "RSA_SIGNATURE_ENCODING"]);
  });

  test("overt_receipt.sig rejects a NUL byte inside the base64", async () => {
    const result = await verifyReplacing((e) => {
      const sig = text(e, "overt_receipt.sig");
      e["overt_receipt.sig"] = concat(TEXT_ENC.encode(sig.slice(0, 100)), new Uint8Array([0]), TEXT_ENC.encode(sig.slice(100)));
    });
    expect(result).toEqual([false, "OVERT_SIGNATURE_ERROR"]);
  });
});

test("an unreadable timestamp.tsr is reported as such, not as missing", async () => {
  const source = await readFile(
    new URL("../../test-vectors/invalid/bad-timestamp/package.aep", import.meta.url),
  );
  const result = await verify(source);
  expect(result.failureCode).toBe("TSA_MISSING_OR_INVALID");
  expect(result.failureReason).toBe(
    "timestamp.tsr is empty or not a readable RFC 3161 TimeStampResp or token.",
  );
});

import { describe, expect, test } from "vitest";

import { jcs } from "../src/canonical.js";

const decode = (bytes: Uint8Array): string => new TextDecoder().decode(bytes);

describe("RFC 8785 cross-language canonicalization contract", () => {
  test("uses ECMAScript number serialization at the RFC boundaries", () => {
    expect(decode(jcs([333333333.33333329, 4.5, 2e-3, 1e-27]))).toBe(
      "[333333333.3333333,4.5,0.002,1e-27]",
    );
  });

  test("sorts object names by UTF-16 code units", () => {
    const value = {
      "€": "euro",
      "\r": "cr",
      "דּ": "hebrew",
      "1": "one",
      "😀": "emoji",
      "\u0080": "control",
      "ö": "o-umlaut",
    };
    expect(decode(jcs(value))).toBe(
      "{\"\\r\":\"cr\",\"1\":\"one\",\"\u0080\":\"control\",\"ö\":\"o-umlaut\",\"€\":\"euro\",\"😀\":\"emoji\",\"דּ\":\"hebrew\"}",
    );
  });

  test("rejects values outside the shared I-JSON domain", () => {
    expect(() => jcs({ unsafe: 9007199254740992 })).toThrow(/safe range/);
    expect(() => jcs({ surrogate: "\ud800" })).toThrow(/surrogate/);
    expect(() => jcs({ invalid: undefined })).toThrow(/undefined/);
  });
});

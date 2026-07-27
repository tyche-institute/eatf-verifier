// Runs the JCS boundary corpus through the third-party `canonicalize` package.
// Text in, text out: JSON.parse then canonicalize, which is the path the
// package's own CLI documents. Any coercion performed by JSON.parse is part of
// what a caller of this library actually gets, and is reported as such.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import canonicalize from 'canonicalize';

const here = dirname(fileURLToPath(import.meta.url));
const oracle = JSON.parse(readFileSync(join(here, 'oracle.json'), 'utf8'));

const rows = oracle.cases.map((c) => {
  let parsed;
  try {
    parsed = JSON.parse(c.input);
  } catch (e) {
    return { id: c.id, outcome: 'error', stage: 'parse', error: e.constructor.name };
  }
  // Report what the host parser produced for the numeric leaf, if any, so the
  // Python side can compare it against an exact parse. We do NOT decide
  // "coerced" here: JSON.stringify normalises formatting (-0 -> 0, escapes ->
  // characters) in ways that are not value changes.
  const leaf = parsed && typeof parsed === 'object' ? parsed.a : undefined;
  const numeric = typeof leaf === 'number';
  const host_number = numeric ? (Number.isFinite(leaf) ? leaf.toString() : String(leaf)) : null;
  let out;
  try {
    out = canonicalize(parsed);
  } catch (e) {
    return { id: c.id, outcome: 'error', stage: 'canonicalize', error: e.constructor.name, host_number };
  }
  if (out === undefined) {
    return { id: c.id, outcome: 'error', stage: 'canonicalize', error: 'undefined-return', host_number };
  }
  return {
    id: c.id,
    outcome: 'output',
    bytes_hex: Buffer.from(out, 'utf8').toString('hex'),
    text: out,
    host_number,
  };
});

process.stdout.write(JSON.stringify({ implementation: 'js', rows }, null, 2) + '\n');

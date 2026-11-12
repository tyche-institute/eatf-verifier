#!/usr/bin/env node
// Guard deletion for the TypeScript port, done on the syntax tree with the
// toolkit's own TypeScript compiler.
//
//   node delete-ts.mjs <guard> <source.ts> <output.ts>
//
// Every `return fail(...)` whose code argument (a string literal, or both
// branches of a conditional) belongs to the guard becomes `{}`. For 1-zip, the
// `throw` statements inside the guard's own line range become `{}` as well.
// `// @ts-nocheck` is prepended, as StrykerJS does for its own mutants. The
// script prints one JSON line naming the replaced statements by original line.

import { readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../..");
const require = createRequire(import.meta.url);
const ts = require(resolve(repoRoot, "lib/node_modules/typescript"));

const [guard, sourcePath, outputPath] = process.argv.slice(2);
if (!guard || !sourcePath || !outputPath) {
  process.stderr.write("usage: delete-ts.mjs <guard> <source.ts> <output.ts>\n");
  process.exit(2);
}
const regions = JSON.parse(await readFile(resolve(here, "guard-regions.json"), "utf8"));
if (!(guard in regions.guards)) throw new Error(`unknown guard ${guard}`);
const codes = new Set(regions.guards[guard].codes);
const ranges = regions.files.typescript["lib/src/verifier.ts"].regions
  .filter(([, , name]) => name === guard)
  .map(([from, to]) => [from, to]);

const text = await readFile(sourcePath, "utf8");
const source = ts.createSourceFile(sourcePath, text, ts.ScriptTarget.ES2022, true, ts.ScriptKind.TS);
const lineOf = (pos) => source.getLineAndCharacterOfPosition(pos).line + 1;
const inGuardRange = (node) => {
  const line = lineOf(node.getStart(source));
  return ranges.some(([from, to]) => line >= from && line <= to);
};

function codesOf(node) {
  if (!node) return null;
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return [node.text];
  if (ts.isParenthesizedExpression(node)) return codesOf(node.expression);
  if (ts.isConditionalExpression(node)) {
    const a = codesOf(node.whenTrue);
    const b = codesOf(node.whenFalse);
    return a && b ? [...a, ...b] : null;
  }
  return null;
}

const targets = [];
function visit(node) {
  if (
    ts.isReturnStatement(node) &&
    node.expression &&
    ts.isCallExpression(node.expression) &&
    ts.isIdentifier(node.expression.expression) &&
    node.expression.expression.text === "fail"
  ) {
    const found = codesOf(node.expression.arguments[1]);
    if (found === null) throw new Error(`fail() without a literal code at line ${lineOf(node.getStart(source))}`);
    const mine = found.filter((code) => codes.has(code));
    if (mine.length === found.length) targets.push(node);
    else if (mine.length > 0) throw new Error(`fail() mixes guards at line ${lineOf(node.getStart(source))}`);
  }
  if (guard === "1-zip" && ts.isThrowStatement(node) && inGuardRange(node)) targets.push(node);
  ts.forEachChild(node, visit);
}
visit(source);

let output = text;
for (const node of [...targets].sort((a, b) => b.getStart(source) - a.getStart(source))) {
  output = output.slice(0, node.getStart(source)) + "{}" + output.slice(node.getEnd());
}
await writeFile(outputPath, `// @ts-nocheck\n${output}`);
process.stdout.write(JSON.stringify({
  guard,
  replaced: targets.map((node) => ({
    line: lineOf(node.getStart(source)),
    kind: ts.isThrowStatement(node) ? "throw" : "return fail",
  })).sort((a, b) => a.line - b.line),
}) + "\n");

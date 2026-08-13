/**
 * v0.1: browser-only re-export.
 *
 * The default `@eatf/verifier` entry is isomorphic (works in Node 20+
 * and the browser). This subpath is identical at runtime but lets a
 * frontend bundler statically know that no Node-only side effects
 * exist, which improves tree-shaking and produces a smaller bundle.
 */

export * from "./index.js";

#!/bin/sh
# Build command for StrykerJS. Stryker 9.6.1 runs the build command before it
# links node_modules into its sandbox, so the toolkit's compiler and type
# packages are not there yet. This links them from the original checkout,
# named by EATF_REPO_ROOT, and then runs the toolkit's own build.
set -eu
: "${EATF_REPO_ROOT:?EATF_REPO_ROOT must name the original checkout}"
ln -sfn "$EATF_REPO_ROOT/node_modules" node_modules
ln -sfn "$EATF_REPO_ROOT/lib/node_modules" lib/node_modules
npm run build

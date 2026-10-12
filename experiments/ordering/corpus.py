"""The corpus both ordering scripts run over, taken from the experiments' oracles.

The figures in DESIGN.md are about every case of the decision-path and
path-shadowing corpora. The path-shadowing packages are not committed: they
exist only after that experiment has been run. Collecting "every case we can
reach" therefore analysed the 21 decision-path packages alone on a fresh
clone, rewrote the deposited results without the four path-shadowing rows, and
exited 0.

The case ids now come from each experiment's oracle. A declared case without a
package is an error, not a smaller corpus. Directories an oracle does not
declare are not read. Callers load the corpus before writing anything, so an
incomplete corpus leaves the deposited results as they were.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# (source, oracle declaring the case ids, directory holding <id>/package.aep,
#  command that produces those packages). The decision-path packages are
# committed, so they are restored rather than regenerated: the generator is
# deterministic for one zlib, not across zlib builds.
SOURCES = (
    ("decision-path", "experiments/decision-path/oracle.json",
     "experiments/decision-path/generated/corpus",
     "git checkout -- experiments/decision-path/generated/corpus"),
    ("path-shadowing", "experiments/path-shadowing/oracle.json",
     "experiments/path-shadowing/generated",
     "python experiments/path-shadowing/run_experiment.py"),
)


class IncompleteCorpus(Exception):
    """A source corpus lacks a package its oracle declares."""


def load_corpus() -> list[tuple[str, bytes, str]]:
    """(case id, package bytes, source experiment) for every case the oracles
    declare, in id order within each source."""
    out: list[tuple[str, bytes, str]] = []
    problems: list[str] = []
    declared = 0
    for source, oracle, root, command in SOURCES:
        cases = json.loads((REPO_ROOT / oracle).read_text(encoding="utf-8"))["cases"]
        ids = sorted(case["id"] for case in cases)
        declared += len(ids)
        if not ids:
            problems.append(f"{source}: {oracle} declares no cases")
            continue
        missing = [i for i in ids if not (REPO_ROOT / root / i / "package.aep").is_file()]
        if missing:
            problems.append(
                f"{source}: {oracle} declares {len(ids)} cases, "
                f"{len(ids) - len(missing)} have a package under {root}/\n"
                f"  missing: {', '.join(missing)}\n"
                f"  run: {command}")
            continue
        out.extend((i, (REPO_ROOT / root / i / "package.aep").read_bytes(), source)
                   for i in ids)
    if problems:
        raise IncompleteCorpus(
            "corpus incomplete\n" + "\n".join(problems) + "\n"
            f"The ordering figures are over all {declared} declared cases; "
            "no results were written.")
    return out

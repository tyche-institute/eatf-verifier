"""Check that the built conference ZIP is intact and independently runnable."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
ARCHIVE = ROOT / "dist" / f"eatf-pqc-hybrid-lab-v{VERSION}.zip"
REQUIRED_ENTRIES = {
    "README.md",
    "QUICKSTART.md",
    "EXPECTED-TRANSCRIPT.md",
    "run_lab.py",
    "run.sh",
    "SHA256SUMS",
    "packages/manifest.json",
}


def replay(extracted: Path, environment: dict[str, str]) -> None:
    completed = subprocess.run(
        [sys.executable, str(extracted / "run_lab.py")],
        cwd=extracted,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Portable lab runner failed:\n{completed.stdout}\n{completed.stderr}"
        )
    if "Cross-language policy mismatches: 0" not in completed.stdout:
        raise RuntimeError(f"Unexpected portable runner output:\n{completed.stdout}")


def main() -> int:
    if not ARCHIVE.is_file():
        raise RuntimeError(f"Missing {ARCHIVE}; run npm run build:conference-assets")

    with tempfile.TemporaryDirectory(prefix="eatf-conference-bundle-") as temp:
        extracted = Path(temp)
        with zipfile.ZipFile(ARCHIVE) as bundle:
            names = set(bundle.namelist())
            missing = REQUIRED_ENTRIES - names
            if missing:
                raise RuntimeError(f"Conference bundle is missing: {sorted(missing)}")
            bundle.extractall(extracted)

        for line in (extracted / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            expected, relative_name = line.split(maxsplit=1)
            artifact = extracted / relative_name.lstrip("* ")
            observed = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if observed != expected:
                raise RuntimeError(f"SHA-256 mismatch for {artifact.name}")

        environment = os.environ.copy()
        environment["EATF_REPO_ROOT"] = str(ROOT)
        replay(extracted, environment)

        path_environment = os.environ.copy()
        path_environment.pop("EATF_REPO_ROOT", None)
        path_environment["PATH"] = f"{ROOT / 'bin'}{os.pathsep}{path_environment['PATH']}"
        replay(extracted, path_environment)

    print("Conference bundle passed integrity and portable-runner checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

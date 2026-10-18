"""Download, authenticate, extract, and replay the published v0.6.1, v0.7.0 and v0.7.1 labs.

v0.6.1 backs docs/pqc-hybrid-lab-five-minute-fallback.md; v0.7.1 is the current release.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ("0.6.1", "0.7.0", "0.7.1")
REQUIRED_ENTRIES = {
    "README.md",
    "QUICKSTART.md",
    "EXPECTED-TRANSCRIPT.md",
    "run_lab.py",
    "run.sh",
    "SHA256SUMS",
    "packages/manifest.json",
}


def download(url: str, version: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": f"eatf-release-audit/{version}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def check_internal_digests(extracted: Path) -> None:
    for line in (extracted / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, relative_name = line.split(maxsplit=1)
        artifact = extracted / relative_name.lstrip("* ")
        observed = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if observed != expected:
            raise RuntimeError(f"SHA-256 mismatch for {artifact.name}")


def replay(extracted: Path) -> None:
    environment = os.environ.copy()
    environment["EATF_REPO_ROOT"] = str(ROOT)
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
            f"Published lab runner failed:\n{completed.stdout}\n{completed.stderr}"
        )
    if "Cross-language policy mismatches: 0" not in completed.stdout:
        raise RuntimeError(f"Unexpected published runner output:\n{completed.stdout}")


def check_release(version: str) -> None:
    archive_name = f"eatf-pqc-hybrid-lab-v{version}.zip"
    release_base = (
        f"https://github.com/tyche-institute/eatf-verifier/releases/download/v{version}"
    )
    archive_url = f"{release_base}/{archive_name}"
    checksum_line = download(f"{archive_url}.sha256", version).decode("utf-8").strip()
    expected, published_name = checksum_line.split(maxsplit=1)
    if published_name.lstrip("* ") != archive_name:
        raise RuntimeError(f"Unexpected release checksum filename: {published_name}")

    archive_bytes = download(archive_url, version)
    observed = hashlib.sha256(archive_bytes).hexdigest()
    if observed != expected:
        raise RuntimeError(f"Published ZIP SHA-256 mismatch: {observed} != {expected}")

    with tempfile.TemporaryDirectory(prefix="eatf-published-bundle-") as temp:
        temp_path = Path(temp)
        archive = temp_path / archive_name
        archive.write_bytes(archive_bytes)
        extracted = temp_path / "extracted"
        extracted.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            missing = REQUIRED_ENTRIES - names
            if missing:
                raise RuntimeError(f"Published bundle is missing: {sorted(missing)}")
            bundle.extractall(extracted)
        check_internal_digests(extracted)
        replay(extracted)

    print(
        f"Published {archive_name} passed external SHA-256, internal digest, "
        "and portable-runner checks."
    )


def main() -> int:
    for version in VERSIONS:
        check_release(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

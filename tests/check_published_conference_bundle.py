"""Download, authenticate, extract, and replay the published v0.6.1 lab."""

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
VERSION = "0.6.1"
ARCHIVE_NAME = f"eatf-pqc-hybrid-lab-v{VERSION}.zip"
RELEASE_BASE = (
    f"https://github.com/tyche-institute/eatf-verifier/releases/download/v{VERSION}"
)
ARCHIVE_URL = f"{RELEASE_BASE}/{ARCHIVE_NAME}"
CHECKSUM_URL = f"{ARCHIVE_URL}.sha256"
REQUIRED_ENTRIES = {
    "README.md",
    "QUICKSTART.md",
    "EXPECTED-TRANSCRIPT.md",
    "run_lab.py",
    "run.sh",
    "SHA256SUMS",
    "packages/manifest.json",
}


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "eatf-release-audit/0.6.1"})
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


def main() -> int:
    checksum_line = download(CHECKSUM_URL).decode("utf-8").strip()
    expected, published_name = checksum_line.split(maxsplit=1)
    if published_name.lstrip("* ") != ARCHIVE_NAME:
        raise RuntimeError(f"Unexpected release checksum filename: {published_name}")

    archive_bytes = download(ARCHIVE_URL)
    observed = hashlib.sha256(archive_bytes).hexdigest()
    if observed != expected:
        raise RuntimeError(f"Published ZIP SHA-256 mismatch: {observed} != {expected}")

    with tempfile.TemporaryDirectory(prefix="eatf-published-bundle-") as temp:
        temp_path = Path(temp)
        archive = temp_path / ARCHIVE_NAME
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
        f"Published {ARCHIVE_NAME} passed external SHA-256, internal digest, "
        "and portable-runner checks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

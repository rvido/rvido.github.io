#!/usr/bin/env python3
"""Generate build-meta.json for the portfolio footer."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def get_semver(version_file: Path) -> str:
    try:
        version = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return ""

    if not version:
        return ""

    return version if version.startswith("v") else f"v{version}"


def get_short_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        short_hash = result.stdout.strip()
        if short_hash:
            return short_hash
    except (OSError, subprocess.CalledProcessError):
        pass

    return "local"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate build-meta.json")
    parser.add_argument("output", nargs="?", default="build-meta.json", help="Output JSON path")
    parser.add_argument("--version", default="", help="Semantic version override (e.g. v1.2.3)")
    parser.add_argument("--version-file", default="VERSION", help="Path to VERSION file")
    args = parser.parse_args()

    output_path = Path(args.output)
    version = args.version.strip() or get_semver(Path(args.version_file))
    if version and not version.startswith("v"):
        version = f"v{version}"

    payload = {
        "version": version,
        "shortHash": get_short_hash(),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }

    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote build meta to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
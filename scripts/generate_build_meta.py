#!/usr/bin/env python3
"""Generate build-meta.json for the portfolio footer."""

from __future__ import annotations

import json
import subprocess
import sys
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
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build-meta.json")
    version = get_semver(Path("VERSION"))

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
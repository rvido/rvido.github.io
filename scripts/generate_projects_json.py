#!/usr/bin/env python3
"""Generate projects.json for the portfolio site from public GitHub repositories."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

EXCLUDED_REPOS = {"rvido.github.io"}
DEFAULT_OVERRIDES_FILE = "projects.overrides.json"


def fetch_repositories(user: str) -> list[dict]:
    base_url = f"https://api.github.com/users/{urllib.parse.quote(user)}/repos"
    query = urllib.parse.urlencode(
        {
            "per_page": 100,
            "sort": "updated",
            "type": "owner",
        }
    )
    url = f"{base_url}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "rvido-portfolio-project-sync",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
            data = json.loads(payload)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API request failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API request failed: {exc.reason}") from exc

    if not isinstance(data, list):
        raise RuntimeError("GitHub API returned an unexpected response shape")

    return data


def load_overrides(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exclude": [], "overrides": {}, "order": []}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Override file must be a JSON object")

    exclude = data.get("exclude", [])
    overrides = data.get("overrides", {})
    order = data.get("order", [])

    if not isinstance(exclude, list) or not all(isinstance(x, str) for x in exclude):
        raise RuntimeError("Override file field 'exclude' must be an array of strings")
    if not isinstance(overrides, dict):
        raise RuntimeError("Override file field 'overrides' must be an object")
    if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
        raise RuntimeError("Override file field 'order' must be an array of strings")

    return {"exclude": exclude, "overrides": overrides, "order": order}


def apply_order(projects: list[dict], order: list[str]) -> list[dict]:
    if not order:
        return projects

    by_name = {p.get("name"): p for p in projects}
    ordered: list[dict] = []

    for name in order:
        project = by_name.pop(name, None)
        if project is not None:
            ordered.append(project)

    remaining = sorted(
        by_name.values(),
        key=lambda p: (-(p.get("stars") or 0), p.get("name") or ""),
    )
    ordered.extend(remaining)
    return ordered


def build_projects(repositories: list[dict], config: dict[str, Any]) -> list[dict]:
    projects: list[dict] = []
    excluded = EXCLUDED_REPOS.union(config.get("exclude", []))
    overrides = config.get("overrides", {})

    for repo in repositories:
        name = repo.get("name")

        if name in excluded:
            continue
        if repo.get("private"):
            continue
        if repo.get("fork"):
            continue

        language = (repo.get("language") or "").strip().lower()
        project = {
            "name": name or "",
            "lang": language,
            "desc": repo.get("description") or "No description provided.",
            "url": repo.get("html_url"),
            "stars": int(repo.get("stargazers_count") or 0),
            "forks": int(repo.get("forks_count") or 0),
            "tags": ["Open Source"],
            "status": "public",
        }

        manual = overrides.get(project["name"], {})
        if isinstance(manual, dict):
            for key in ("desc", "tags", "status", "lang", "url"):
                if key in manual:
                    project[key] = manual[key]

            if manual.get("hidden") is True:
                continue

        projects.append(project)

    return apply_order(projects, config.get("order", []))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate projects.json from GitHub repos")
    parser.add_argument("--user", default="rvido", help="GitHub username")
    parser.add_argument("--output", default="projects.json", help="Output JSON file path")
    parser.add_argument(
        "--overrides",
        default=DEFAULT_OVERRIDES_FILE,
        help="Manual override file path",
    )
    args = parser.parse_args()

    repositories = fetch_repositories(args.user)
    overrides = load_overrides(Path(args.overrides))
    projects = build_projects(repositories, overrides)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(projects, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(projects)} projects to {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as err:
        print(f"Error: {err}", file=sys.stderr)
        raise SystemExit(1)

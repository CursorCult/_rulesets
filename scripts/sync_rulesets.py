#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ORG = "CursorCult"
API_BASE = "https://api.github.com"
TAG_REQUIRED = "v1"
TAG_RE = re.compile(r"^v(\d+)$")


@dataclass(frozen=True)
class GitHubApiError(RuntimeError):
    status: int
    url: str
    body: str


def _token() -> str:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        raise SystemExit("Missing GITHUB_TOKEN (or GH_TOKEN) in environment.")
    return token


def _request_json(url: str, token: str) -> tuple[Any, dict[str, str]]:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "CursorCult-Rulesets-Sync")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return json.loads(raw), headers
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        raise GitHubApiError(status=e.code, url=url, body=body) from e


def _paginate(url: str, token: str) -> Iterable[Any]:
    while url:
        data, headers = _request_json(url, token)
        if not isinstance(data, list):
            raise RuntimeError(f"Expected list response for {url}, got {type(data)}")
        for item in data:
            yield item
        link = headers.get("link", "")
        next_url = None
        for part in link.split(","):
            part = part.strip()
            if not part:
                continue
            if 'rel="next"' in part:
                m = re.search(r"<([^>]+)>", part)
                if m:
                    next_url = m.group(1)
                break
        url = next_url


def repo_exists(repo: str, token: str) -> bool:
    url = f"{API_BASE}/repos/{urllib.parse.quote(ORG)}/{urllib.parse.quote(repo)}"
    try:
        data, _ = _request_json(url, token)
    except GitHubApiError as e:
        if e.status == 404:
            return False
        raise
    if not isinstance(data, dict):
        return False
    if data.get("archived") is True:
        return False
    if data.get("fork") is True:
        return False
    return True


def repo_has_required_tag(repo: str, token: str) -> bool:
    url = f"{API_BASE}/repos/{urllib.parse.quote(ORG)}/{urllib.parse.quote(repo)}/tags?per_page=100"
    for item in _paginate(url, token):
        name = item.get("name")
        if not isinstance(name, str):
            continue
        if name.strip() == TAG_REQUIRED:
            return True
    return False


def normalize_rule_name(raw: str) -> str | None:
    s = raw.strip()
    if not s or s.startswith("#"):
        return None
    if any(c.isspace() for c in s):
        return None
    if s.startswith(".") or s.startswith("_"):
        return None
    return s


def read_ruleset_file(path: Path) -> tuple[list[str], list[str]]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    rules: list[str] = []
    dropped: list[str] = []
    seen: set[str] = set()
    for line in raw_lines:
        name = normalize_rule_name(line)
        if name is None:
            continue
        if name in seen:
            continue
        seen.add(name)
        rules.append(name)
    return rules, dropped


def write_ruleset_file(path: Path, rules: list[str]) -> None:
    content = "\n".join(rules) + ("\n" if rules else "")
    path.write_text(content, encoding="utf-8")


def sync_ruleset(path: Path, token: str, check_only: bool) -> tuple[bool, list[str]]:
    rules, _ = read_ruleset_file(path)
    kept: list[str] = []
    removed: list[str] = []
    for rule in rules:
        if not repo_exists(rule, token):
            removed.append(rule)
            continue
        if not repo_has_required_tag(rule, token):
            removed.append(rule)
            continue
        kept.append(rule)

    original = path.read_text(encoding="utf-8")
    updated = "\n".join(kept) + ("\n" if kept else "")
    changed = updated != original
    if changed and not check_only:
        path.write_text(updated, encoding="utf-8")
    return changed, removed


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    token = _token()

    rulesets_dir = Path("rulesets")
    if not rulesets_dir.is_dir():
        raise SystemExit("Missing rulesets/ directory.")

    files = sorted(
        p
        for p in rulesets_dir.glob("*.txt")
        if p.is_file()
    )
    if not files:
        print("No ruleset files found (rulesets/*.txt).")
        return 0

    changed_any = False
    for path in files:
        changed, removed = sync_ruleset(path, token, check_only=check_only)
        if removed:
            print(f"{path}: removed {len(removed)} -> {', '.join(removed)}")
        if changed:
            changed_any = True
            print(f"{path}: {'would change' if check_only else 'updated'}")
        else:
            print(f"{path}: ok")

    if check_only and changed_any:
        print("rulesets invalid: run sync to apply removals")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


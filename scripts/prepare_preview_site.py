#!/usr/bin/env python3
"""Prepare an isolated static bundle for the persistent preview Worker."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


BANNER = """
<style id="newsradar-preview-style">
  .newsradar-preview-badge{position:fixed;z-index:2147483647;left:16px;bottom:16px;padding:8px 12px;border:3px solid #1a1a1a;background:#ffcc00;color:#1a1a1a;box-shadow:4px 4px 0 #1a1a1a;font:900 13px/1.2 system-ui,sans-serif;letter-spacing:0}
  .newsradar-preview-badge:focus{outline:3px solid #3366ff;outline-offset:3px}
  @media(max-width:640px){.newsradar-preview-badge{left:10px;bottom:10px;padding:6px 9px;font-size:12px}}
</style>
<a class="newsradar-preview-badge" href="/build-info.json" title="查看当前内测版本">内测环境 · PREVIEW</a>
""".strip()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def inject_banner(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    if "newsradar-preview-badge" in content:
        return
    marker = "</body>"
    content = content.replace(marker, f"{BANNER}\n{marker}", 1) if marker in content else f"{content}\n{BANNER}\n"
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--data-repo", type=Path)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    data_repo = args.data_repo.resolve() if args.data_repo else repo
    source = args.source.resolve()
    destination = args.destination.resolve()
    if not source.joinpath("index.html").is_file():
        raise SystemExit(f"missing preview entry point: {source / 'index.html'}")

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

    for html_file in destination.rglob("*.html"):
        inject_banner(html_file)

    now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    info = {
        "environment": "preview",
        "generated_at": now,
        "git_branch": git(repo, "branch", "--show-current"),
        "git_commit": git(repo, "rev-parse", "HEAD"),
        "git_commit_short": git(repo, "rev-parse", "--short=12", "HEAD"),
        "data_branch": git(data_repo, "branch", "--show-current"),
        "data_commit": git(data_repo, "rev-parse", "HEAD"),
        "data_commit_short": git(data_repo, "rev-parse", "--short=12", "HEAD"),
    }
    destination.joinpath("build-info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    destination.joinpath("_headers").write_text(
        "/*\n  X-Robots-Tag: noindex, nofollow, noarchive\n  Cache-Control: no-cache\n",
        encoding="utf-8",
    )
    destination.joinpath("robots.txt").write_text(
        "User-agent: *\nDisallow: /\n", encoding="utf-8"
    )
    print(f"[preview] prepared {destination} ({info['git_commit_short']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

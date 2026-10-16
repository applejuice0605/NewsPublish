#!/usr/bin/env python3
"""Probe candidate news sources without touching the production pipeline."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "source_pilot.json"
OUTPUT_DIR = REPO_ROOT / "TrendRadar" / "output" / "source-pilot"
NEWS_DIR = REPO_ROOT / "TrendRadar" / "output" / "news"
REQUEST_TIMEOUT_SECONDS = 10
ALLOWED_API_STATUSES = {"success", "cache"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe candidate news sources safely.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to the pilot JSON configuration.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the result without writing pilot state.",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load config: {path}") from exc

    sources = config.get("sources")
    rules = config.get("interest_rules")
    thresholds = config.get("promotion_thresholds")
    if not isinstance(sources, list) or not sources:
        raise ValueError("config sources must be a non-empty array")
    source_ids: list[str] = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("each source must be an object")
        source_id = source.get("id")
        kind = source.get("kind")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("each source needs a string id")
        if kind not in {"newsnow", "feed"}:
            raise ValueError(f"unsupported source kind for {source_id}")
        if kind == "newsnow" and not isinstance(source.get("source_id"), str):
            raise ValueError(f"newsnow source {source_id} needs source_id")
        if kind == "feed" and not isinstance(source.get("url"), str):
            raise ValueError(f"feed source {source_id} needs url")
        source_ids.append(source_id)
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("config sources must not contain duplicates")
    api_url = config.get("newsnow_api_url")
    if not isinstance(api_url, str) or not api_url.strip():
        raise ValueError("config newsnow_api_url must be a URL")
    if not isinstance(rules, list):
        raise ValueError("config interest_rules must be an array")
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("name"), str):
            raise ValueError("each interest rule needs a string name")
        keywords = rule.get("keywords")
        if not isinstance(keywords, list) or not all(
            isinstance(keyword, str) and keyword.strip() for keyword in keywords
        ):
            raise ValueError("each interest rule needs non-empty string keywords")
    required_thresholds = {
        "minimum_sample_days",
        "success_rate",
        "interest_hit_rate",
        "maximum_duplicate_rate",
    }
    if not isinstance(thresholds, dict) or not required_thresholds.issubset(thresholds):
        raise ValueError("config promotion_thresholds is incomplete")
    if not isinstance(thresholds["minimum_sample_days"], int) or thresholds[
        "minimum_sample_days"
    ] < 1:
        raise ValueError("minimum_sample_days must be a positive integer")
    for key in required_thresholds - {"minimum_sample_days"}:
        value = thresholds[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
            raise ValueError(f"{key} must be between 0 and 1")
    return config


def normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def normalize_for_keyword(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def load_official_titles(date: str) -> tuple[set[str], dict[str, Any]]:
    db_path = NEWS_DIR / f"{date}.db"
    metadata = {
        "date": date,
        "database": f"TrendRadar/output/news/{date}.db",
        "available": db_path.is_file(),
        "normalized_title_count": 0,
    }
    if not db_path.is_file():
        return set(), metadata

    titles: set[str] = set()
    try:
        uri = f"{db_path.resolve().as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            rows = connection.execute("SELECT title FROM news_items").fetchall()
        titles = {normalize_title(row[0]) for row in rows if row[0]}
        titles.discard("")
    except sqlite3.Error:
        metadata["available"] = False
        metadata["read_error"] = "sqlite_error"
    metadata["normalized_title_count"] = len(titles)
    return titles, metadata


def build_request_url(endpoint: str, source: str) -> str:
    try:
        parts = urllib.parse.urlsplit(endpoint)
    except ValueError as exc:
        raise ValueError("OMNITRENDS_API_URL is not a valid URL") from exc
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("OMNITRENDS_API_URL must be an HTTP(S) URL")
    pilot_query = f"id={urllib.parse.quote(source, safe='')}&latest"
    query = f"{parts.query}&{pilot_query}" if parts.query else pilot_query
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, query, parts.fragment)
    )


def interest_matches(title: str, rules: list[dict[str, Any]]) -> list[str]:
    searchable = normalize_for_keyword(title)
    matched: list[str] = []
    for rule in rules:
        if any(normalize_for_keyword(keyword) in searchable for keyword in rule["keywords"]):
            matched.append(rule["name"])
    return matched


def probe_source(
    endpoint: str,
    source: str,
    rules: list[dict[str, Any]],
    official_titles: set[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": source,
        "success": False,
        "api_status": None,
        "item_count": 0,
        "interest_hit_count": 0,
        "interest_hit_rate": 0.0,
        "duplicate_count": 0,
        "duplicate_rate": 0.0,
        "items": [],
    }
    try:
        request_url = build_request_url(endpoint, source)
        request = urllib.request.Request(
            request_url,
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        result["error"] = "http_error"
        result["http_status"] = exc.code
        return result
    except (urllib.error.URLError, TimeoutError):
        result["error"] = "network_error"
        return result
    except (json.JSONDecodeError, UnicodeDecodeError):
        result["error"] = "invalid_json"
        return result
    except (OSError, ValueError):
        result["error"] = "request_error"
        return result

    if not isinstance(payload, dict):
        result["error"] = "invalid_payload"
        return result
    api_status = payload.get("status")
    result["api_status"] = api_status if isinstance(api_status, str) else None
    if api_status not in ALLOWED_API_STATUSES:
        result["error"] = "invalid_status"
        return result
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        result["error"] = "invalid_items"
        return result

    extracted_items: list[dict[str, Any]] = []
    duplicate_count = 0
    interest_hit_count = 0
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        title = raw_item.get("title")
        url = raw_item.get("url", "")
        if not isinstance(title, str) or not title.strip() or not isinstance(url, str):
            continue
        title = title.strip()
        matches = interest_matches(title, rules)
        duplicate = normalize_title(title) in official_titles
        duplicate_count += int(duplicate)
        interest_hit_count += int(bool(matches))
        extracted_items.append(
            {
                "title": title,
                "url": url.strip(),
                "interest_rules": matches,
                "duplicate_in_official_news": duplicate,
            }
        )

    item_count = len(extracted_items)
    result.update(
        {
            "success": True,
            "item_count": item_count,
            "interest_hit_count": interest_hit_count,
            "interest_hit_rate": ratio(interest_hit_count, item_count),
            "duplicate_count": duplicate_count,
            "duplicate_rate": ratio(duplicate_count, item_count),
            "invalid_item_count": len(raw_items) - item_count,
            "items": extracted_items,
        }
    )
    return result


def _feed_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for child in element.iter():
        local_name = child.tag.rsplit("}", 1)[-1].lower()
        if local_name in names and child.text:
            return child.text.strip()
    return ""


def _feed_link(element: ET.Element) -> str:
    for child in element.iter():
        if child.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        href = child.attrib.get("href", "").strip()
        if href:
            return href
        if child.text:
            return child.text.strip()
    return ""


def probe_feed(
    source_id: str,
    url: str,
    rules: list[dict[str, Any]],
    official_titles: set[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": source_id,
        "success": False,
        "api_status": None,
        "item_count": 0,
        "interest_hit_count": 0,
        "interest_hit_rate": 0.0,
        "duplicate_count": 0,
        "duplicate_rate": 0.0,
        "items": [],
    }
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read()
        root = ET.fromstring(body)
    except urllib.error.HTTPError as exc:
        result.update(error="http_error", http_status=exc.code)
        return result
    except (urllib.error.URLError, TimeoutError):
        result["error"] = "network_error"
        return result
    except (ET.ParseError, OSError, ValueError):
        result["error"] = "invalid_feed"
        return result

    entries = [
        element for element in root.iter()
        if element.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}
    ]
    extracted_items: list[dict[str, Any]] = []
    duplicate_count = 0
    interest_hit_count = 0
    for entry in entries[:50]:
        title = _feed_text(entry, ("title",))
        if not title:
            continue
        matches = interest_matches(title, rules)
        duplicate = normalize_title(title) in official_titles
        duplicate_count += int(duplicate)
        interest_hit_count += int(bool(matches))
        extracted_items.append(
            {
                "title": title,
                "url": _feed_link(entry),
                "interest_rules": matches,
                "duplicate_in_official_news": duplicate,
            }
        )
    item_count = len(extracted_items)
    if not item_count:
        result["error"] = "empty_feed"
        return result
    result.update(
        success=True,
        api_status="success",
        item_count=item_count,
        interest_hit_count=interest_hit_count,
        interest_hit_rate=ratio(interest_hit_count, item_count),
        duplicate_count=duplicate_count,
        duplicate_rate=ratio(duplicate_count, item_count),
        items=extracted_items,
    )
    return result


def probe_configured_source(
    endpoint: str,
    source: dict[str, Any],
    rules: list[dict[str, Any]],
    official_titles: set[str],
) -> dict[str, Any]:
    if source["kind"] == "newsnow":
        result = probe_source(endpoint, source["source_id"], rules, official_titles)
        result["source"] = source["id"]
        result["adapter"] = "newsnow"
        return result
    result = probe_feed(source["id"], source["url"], rules, official_titles)
    result["adapter"] = "feed"
    return result


def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def load_history(current_date: str) -> list[dict[str, Any]]:
    if not OUTPUT_DIR.is_dir():
        return []
    snapshots: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_DIR.glob("????-??-??.json")):
        if path.stem == current_date:
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                snapshot = json.load(handle)
            if snapshot.get("configured") is True and isinstance(snapshot.get("sources"), list):
                snapshots.append(snapshot)
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
    return snapshots


def recommendation(
    source: str,
    snapshots: list[dict[str, Any]],
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    sample_dates: set[str] = set()
    for snapshot in snapshots:
        sample_date = snapshot.get("date")
        for source_result in snapshot.get("sources", []):
            if source_result.get("source") == source:
                observations.append(source_result)
                if isinstance(sample_date, str):
                    sample_dates.add(sample_date)
                break

    successes = sum(1 for item in observations if item.get("success") is True)
    item_count = sum(int(item.get("item_count", 0)) for item in observations)
    interest_hits = sum(int(item.get("interest_hit_count", 0)) for item in observations)
    duplicates = sum(int(item.get("duplicate_count", 0)) for item in observations)
    metrics = {
        "sample_days": len(sample_dates),
        "attempts": len(observations),
        "success_rate": ratio(successes, len(observations)),
        "item_count": item_count,
        "interest_hit_count": interest_hits,
        "interest_hit_rate": ratio(interest_hits, item_count),
        "duplicate_count": duplicates,
        "duplicate_rate": ratio(duplicates, item_count),
    }

    if metrics["sample_days"] < thresholds["minimum_sample_days"]:
        status = "observing"
        reasons = [
            f"sample_days {metrics['sample_days']} < {thresholds['minimum_sample_days']}"
        ]
    else:
        checks = {
            "success_rate": metrics["success_rate"] >= thresholds["success_rate"],
            "interest_hit_rate": metrics["interest_hit_rate"] >= thresholds["interest_hit_rate"],
            "duplicate_rate": metrics["duplicate_rate"] <= thresholds["maximum_duplicate_rate"],
        }
        status = "promote" if all(checks.values()) else "hold"
        reasons = [name for name, passed in checks.items() if not passed]
    return {"status": status, "metrics": metrics, "reasons": reasons}


def make_summary(sources: list[dict[str, Any]]) -> dict[str, Any]:
    successes = sum(1 for source in sources if source["success"])
    item_count = sum(source["item_count"] for source in sources)
    interest_hits = sum(source["interest_hit_count"] for source in sources)
    duplicates = sum(source["duplicate_count"] for source in sources)
    return {
        "source_count": len(sources),
        "successful_source_count": successes,
        "success_rate": ratio(successes, len(sources)),
        "item_count": item_count,
        "interest_hit_count": interest_hits,
        "interest_hit_rate": ratio(interest_hits, item_count),
        "duplicate_count": duplicates,
        "duplicate_rate": ratio(duplicates, item_count),
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temporary_name = handle.name
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, path)
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass


def emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
    except ValueError as exc:
        print(f"source pilot configuration error: {exc}", file=sys.stderr)
        return 2

    now = datetime.now().astimezone()
    date = now.date().isoformat()
    endpoint = os.environ.get("OMNITRENDS_API_URL", "").strip() or config[
        "newsnow_api_url"
    ].strip()
    source_ids = [source["id"] for source in config["sources"]]
    common: dict[str, Any] = {
        "schema_version": 2,
        "generated_at": now.isoformat(timespec="seconds"),
        "date": date,
        "configured": True,
        "dry_run": args.dry_run,
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "interest_method": {
            "type": "heuristic",
            "is_ai": False,
            "description": "case-insensitive Unicode-normalized keyword substring matching",
            "rules": config["interest_rules"],
        },
        "promotion_thresholds": config["promotion_thresholds"],
    }

    try:
        build_request_url(endpoint, "health-check")
    except ValueError as exc:
        print(f"source pilot endpoint error: {exc}", file=sys.stderr)
        return 2

    official_titles, official_metadata = load_official_titles(date)
    source_results = [
        probe_configured_source(endpoint, source, config["interest_rules"], official_titles)
        for source in config["sources"]
    ]
    current_snapshot = {
        **common,
        "official_news_reference": official_metadata,
        "sources": source_results,
        "summary": make_summary(source_results),
    }
    history = load_history(date) + [current_snapshot]
    current_snapshot["recommendations"] = {
        source: recommendation(source, history, config["promotion_thresholds"])
        for source in source_ids
    }
    emit(current_snapshot)
    if not args.dry_run:
        write_json_atomic(OUTPUT_DIR / f"{date}.json", current_snapshot)
        write_json_atomic(OUTPUT_DIR / "latest.json", current_snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

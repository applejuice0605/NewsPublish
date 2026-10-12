#!/usr/bin/env python3
"""
Backfill TrendRadar's cross-day dedup index from archived SQLite files.

This script preserves the daily archive databases and only populates
output/seen_items.db, which is used to suppress duplicate future pushes.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Dict, Set
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


ROOT = Path(__file__).resolve().parents[1]
TRENDRADAR_DIR = ROOT / "TrendRadar"

PLATFORM_PARAMS_TO_REMOVE: Dict[str, Set[str]] = {
    "weibo": {"band_rank", "Refer", "t"},
}

COMMON_TRACKING_PARAMS: Set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "referrer", "source", "channel",
    "_t", "timestamp", "_", "random",
    "share_token", "share_id", "share_from",
}


def normalize_url(url: str, platform_id: str = "") -> str:
    if not url:
        return url
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        params = parse_qs(parsed.query, keep_blank_values=True)
        params_to_remove = set(COMMON_TRACKING_PARAMS)
        params_to_remove.update(PLATFORM_PARAMS_TO_REMOVE.get(platform_id, set()))
        lowered_remove = {p.lower() for p in params_to_remove}
        filtered_params = {
            key: values
            for key, values in params.items()
            if key.lower() not in lowered_remove
        }
        if not filtered_params:
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, "", ""))
        sorted_params = []
        for key in sorted(filtered_params.keys()):
            for value in filtered_params[key]:
                sorted_params.append((key, value))
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(sorted_params), ""))
    except Exception:
        return url


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip()).lower()


def hash_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ensure_seen_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_items (
            item_type TEXT NOT NULL,
            scope_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            title TEXT DEFAULT '',
            url TEXT DEFAULT '',
            guid TEXT DEFAULT '',
            first_seen_date TEXT NOT NULL,
            first_seen_time TEXT NOT NULL,
            last_seen_date TEXT NOT NULL,
            last_seen_time TEXT NOT NULL,
            seen_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (item_type, scope_id, fingerprint)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_seen_lookup
        ON seen_items(item_type, scope_id, first_seen_date, first_seen_time)
    """)
    conn.commit()


def upsert_seen(
    conn: sqlite3.Connection,
    item_type: str,
    scope_id: str,
    fingerprint: str,
    title: str,
    url: str,
    guid: str,
    date: str,
    first_time: str,
    last_time: str,
    count: int,
) -> None:
    conn.execute("""
        INSERT INTO seen_items
        (item_type, scope_id, fingerprint, title, url, guid, first_seen_date, first_seen_time,
         last_seen_date, last_seen_time, seen_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(item_type, scope_id, fingerprint) DO UPDATE SET
            title = excluded.title,
            url = CASE WHEN excluded.url != '' THEN excluded.url ELSE seen_items.url END,
            guid = CASE WHEN excluded.guid != '' THEN excluded.guid ELSE seen_items.guid END,
            first_seen_date = CASE
                WHEN (excluded.first_seen_date, excluded.first_seen_time) < (seen_items.first_seen_date, seen_items.first_seen_time)
                THEN excluded.first_seen_date ELSE seen_items.first_seen_date END,
            first_seen_time = CASE
                WHEN (excluded.first_seen_date, excluded.first_seen_time) < (seen_items.first_seen_date, seen_items.first_seen_time)
                THEN excluded.first_seen_time ELSE seen_items.first_seen_time END,
            last_seen_date = CASE
                WHEN (excluded.last_seen_date, excluded.last_seen_time) > (seen_items.last_seen_date, seen_items.last_seen_time)
                THEN excluded.last_seen_date ELSE seen_items.last_seen_date END,
            last_seen_time = CASE
                WHEN (excluded.last_seen_date, excluded.last_seen_time) > (seen_items.last_seen_date, seen_items.last_seen_time)
                THEN excluded.last_seen_time ELSE seen_items.last_seen_time END,
            seen_count = seen_items.seen_count + excluded.seen_count,
            updated_at = CURRENT_TIMESTAMP
    """, (item_type, scope_id, fingerprint, title, url, guid, date, first_time, date, last_time, count))


def backfill_news(output_dir: Path, seen_conn: sqlite3.Connection) -> int:
    total = 0
    for db_path in sorted((output_dir / "news").glob("*.db")):
        date = db_path.stem
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            for row in conn.execute("""
                SELECT title, platform_id, url, first_crawl_time, last_crawl_time, crawl_count
                FROM news_items
            """):
                title = row["title"] or ""
                platform_id = row["platform_id"] or ""
                url = normalize_url(row["url"] or "", platform_id)
                first_time = row["first_crawl_time"] or ""
                last_time = row["last_crawl_time"] or first_time
                count = int(row["crawl_count"] or 1)
                if url:
                    upsert_seen(seen_conn, "hotlist_url", platform_id, hash_key(f"url:{url}"), title, url, "", date, first_time, last_time, count)
                    total += 1
                title_key = normalize_title(title)
                if title_key:
                    upsert_seen(seen_conn, "hotlist_title", platform_id, hash_key(f"title:{title_key}"), title, url, "", date, first_time, last_time, count)
                    total += 1
        finally:
            conn.close()
    return total


def backfill_rss(output_dir: Path, seen_conn: sqlite3.Connection) -> int:
    total = 0
    for db_path in sorted((output_dir / "rss").glob("*.db")):
        date = db_path.stem
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(rss_items)")}
            guid_expr = "guid" if "guid" in columns else "'' AS guid"
            for row in conn.execute(f"""
                SELECT title, feed_id, url, {guid_expr}, first_crawl_time, last_crawl_time, crawl_count
                FROM rss_items
            """):
                title = row["title"] or ""
                feed_id = row["feed_id"] or ""
                url = row["url"] or ""
                guid = row["guid"] or ""
                first_time = row["first_crawl_time"] or ""
                last_time = row["last_crawl_time"] or first_time
                count = int(row["crawl_count"] or 1)
                if guid:
                    fingerprint = hash_key(f"guid:{guid}")
                elif url:
                    fingerprint = hash_key(f"url:{url}")
                else:
                    fingerprint = hash_key(f"title:{normalize_title(title)}")
                upsert_seen(seen_conn, "rss", feed_id, fingerprint, title, url, guid, date, first_time, last_time, count)
                total += 1
        finally:
            conn.close()
    return total


def main() -> int:
    output_dir = TRENDRADAR_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    seen_path = output_dir / "seen_items.db"
    seen_conn = sqlite3.connect(seen_path)
    try:
        ensure_seen_schema(seen_conn)
        news_count = backfill_news(output_dir, seen_conn)
        rss_count = backfill_rss(output_dir, seen_conn)
        seen_conn.commit()
    finally:
        seen_conn.close()

    print(f"backfilled seen index: hotlist fingerprints={news_count}, rss items={rss_count}, db={seen_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

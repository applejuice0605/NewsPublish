#!/usr/bin/env python3
"""Generate the public TrendRadar archive page."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from html import escape


REPO_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_DIR / "docs"
REPORTS_DIR = SITE_DIR / "reports"
ARCHIVE_FILE = SITE_DIR / "archive.html"


def _report_dates() -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    if not REPORTS_DIR.exists():
        return grouped

    for path in REPORTS_DIR.rglob("*.html"):
        rel = path.relative_to(SITE_DIR)
        parts = rel.parts
        if len(parts) >= 3 and parts[0] == "reports" and _is_date(parts[1]):
            grouped[parts[1]].append(rel)
        elif len(parts) == 2 and parts[0] == "reports":
            date_key = path.stem
            if _is_date(date_key):
                grouped[date_key].append(rel)

    for paths in grouped.values():
        paths.sort(key=lambda p: str(p), reverse=True)
    return dict(sorted(grouped.items(), reverse=True))


def _is_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _page_html(grouped: dict[str, list[Path]]) -> str:
    options = "\n".join(
        f'<option value="{escape(date)}">{escape(date)}</option>' for date in grouped
    )
    cards = []
    for date, paths in grouped.items():
        latest = paths[0] if paths else ""
        links = "\n".join(
            f'<li><a href="/{escape(str(path))}">{escape(path.stem)}</a></li>'
            for path in paths[:12]
        )
        cards.append(
            f"""
            <section class="archive-card" data-date="{escape(date)}">
                <div>
                    <h2>{escape(date)}</h2>
                    <p>{len(paths)} 份报告</p>
                </div>
                <a class="primary-link" href="/{escape(str(latest))}">查看当天最新</a>
                <details>
                    <summary>展开当天所有快照</summary>
                    <ul>{links}</ul>
                </details>
            </section>
            """
        )

    cards_html = "\n".join(cards) or '<p class="empty">暂无历史报告</p>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TrendRadar 历史报告</title>
  <style>
    :root {{
      --ink: #1a1a1a;
      --paper: #fffef0;
      --red: #ff3333;
      --yellow: #ffcc00;
      --blue: #3366ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      background: var(--paper);
      background-image: radial-gradient(circle, rgba(26,26,26,.18) 1px, transparent 1px);
      background-size: 4px 4px;
      color: var(--ink);
      font-family: "Arial Black", Impact, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-weight: 900;
    }}
    .shell {{ max-width: 960px; margin: 0 auto; }}
    header {{
      background: var(--red);
      border: 4px solid var(--ink);
      box-shadow: 10px 10px 0 var(--ink);
      padding: 22px;
      margin-bottom: 24px;
    }}
    h1 {{ margin: 0 0 12px; font-size: clamp(28px, 7vw, 58px); text-transform: uppercase; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
    select, input, a.button, .primary-link {{
      background: white;
      color: var(--ink);
      border: 4px solid var(--ink);
      box-shadow: 4px 4px 0 var(--ink);
      padding: 10px 12px;
      font: inherit;
      text-decoration: none;
      min-height: 44px;
    }}
    a.button:hover, .primary-link:hover {{
      background: var(--yellow);
      transform: scale(1.04) rotate(-2deg);
    }}
    .archive-card {{
      background: white;
      border: 4px solid var(--ink);
      box-shadow: 6px 6px 0 var(--ink);
      padding: 18px;
      margin-bottom: 18px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 14px;
      align-items: start;
    }}
    h2 {{ margin: 0; font-size: 24px; }}
    p {{ margin: 8px 0 0; color: #4a4a4a; }}
    details {{ grid-column: 1 / -1; }}
    summary {{ cursor: pointer; }}
    ul {{ margin: 12px 0 0; padding-left: 22px; line-height: 1.9; }}
    li a {{ color: var(--blue); text-decoration-thickness: 3px; }}
    .empty {{ background: white; border: 4px solid var(--ink); padding: 18px; }}
    @media (max-width: 640px) {{
      body {{ padding: 14px; }}
      .archive-card {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <h1>TrendRadar Archive</h1>
      <div class="toolbar">
        <a class="button" href="/">返回首页</a>
        <label>
          选择日期
          <select id="dateSelect">
            <option value="">全部日期</option>
            {options}
          </select>
        </label>
      </div>
    </header>
    <div id="archiveList">{cards_html}</div>
  </main>
  <script>
    const select = document.getElementById('dateSelect');
    const cards = Array.from(document.querySelectorAll('.archive-card'));
    select.addEventListener('change', () => {{
      const value = select.value;
      cards.forEach(card => {{
        card.style.display = !value || card.dataset.date === value ? '' : 'none';
      }});
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    ARCHIVE_FILE.write_text(_page_html(_report_dates()), encoding="utf-8")
    print(f"[site] archive generated: {ARCHIVE_FILE}")


if __name__ == "__main__":
    main()

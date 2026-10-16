from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_daily_podcast.py"
SPEC = importlib.util.spec_from_file_location("generate_daily_podcast", MODULE_PATH)
assert SPEC and SPEC.loader
podcast = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(podcast)


class DailyPodcastTest(unittest.TestCase):
    def test_extracts_only_ai_section(self) -> None:
        parser = podcast.AISectionParser()
        parser.feed(
            '<div class="other">ignore</div><div class="ai-section">'
            '<h2>AI 热点分析</h2><div class="ai-block"><p>核心趋势内容</p></div>'
            '</div><div>ignore too</div>'
        )
        self.assertEqual(parser.text(), "AI 热点分析\n核心趋势内容")

    def test_cleans_markdown_for_tts(self) -> None:
        result = podcast.clean_script("# 标题\n1. 第一条\n- 第二条", 100)
        self.assertEqual(result, "标题\n第一条\n第二条")


if __name__ == "__main__":
    unittest.main()

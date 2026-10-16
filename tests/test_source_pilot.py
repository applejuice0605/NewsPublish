from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_source_pilot.py"
SPEC = importlib.util.spec_from_file_location("run_source_pilot", MODULE_PATH)
assert SPEC and SPEC.loader
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.body


class SourcePilotTest(unittest.TestCase):
    def test_loads_mixed_adapters(self) -> None:
        config = pilot.load_config(Path(__file__).resolve().parents[1] / "config" / "source_pilot.json")
        self.assertEqual(len(config["sources"]), 4)
        self.assertEqual({source["kind"] for source in config["sources"]}, {"newsnow", "feed"})

    def test_parses_rss_and_computes_metrics(self) -> None:
        body = b"""<?xml version='1.0'?><rss><channel>
        <item><title>New AI model released</title><link>https://example.com/1</link></item>
        <item><title>Unrelated update</title><link>https://example.com/2</link></item>
        </channel></rss>"""
        rules = [{"name": "ai", "keywords": ["AI", "model"]}]
        with patch.object(pilot.urllib.request, "urlopen", return_value=FakeResponse(body)):
            result = pilot.probe_feed("feed", "https://example.com/feed", rules, {pilot.normalize_title("Unrelated update")})
        self.assertTrue(result["success"])
        self.assertEqual(result["item_count"], 2)
        self.assertEqual(result["interest_hit_count"], 1)
        self.assertEqual(result["duplicate_count"], 1)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class PreviewSiteTests(unittest.TestCase):
    def test_prepare_preview_site_is_isolated_and_identifiable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "docs"
            destination = root / "preview"
            source.mkdir()
            source.joinpath("index.html").write_text(
                "<html><body><h1>NewsRadar</h1></body></html>", encoding="utf-8"
            )

            subprocess.run(
                [
                    "python3",
                    str(REPO / "scripts/prepare_preview_site.py"),
                    "--repo",
                    str(REPO),
                    "--source",
                    str(source),
                    "--destination",
                    str(destination),
                ],
                check=True,
            )

            original = source.joinpath("index.html").read_text(encoding="utf-8")
            preview = destination.joinpath("index.html").read_text(encoding="utf-8")
            metadata = json.loads(destination.joinpath("build-info.json").read_text())
            self.assertNotIn("newsradar-preview-badge", original)
            self.assertIn("内测环境", preview)
            self.assertEqual(metadata["environment"], "preview")
            self.assertEqual(metadata["data_commit"], metadata["git_commit"])
            self.assertIn("noindex", destination.joinpath("_headers").read_text())


if __name__ == "__main__":
    unittest.main()

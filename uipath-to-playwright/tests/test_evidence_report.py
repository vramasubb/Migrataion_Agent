from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_evidence_report import _HAS_PIL, _similarity_percent, build_html_report, build_report


@unittest.skipUnless(_HAS_PIL, "Pillow not installed")
class EvidenceReportTests(unittest.TestCase):
    def _make_png(self, directory: Path, name: str, color: tuple[int, int, int]) -> Path:
        from PIL import Image

        path = directory / name
        Image.new("RGB", (10, 10), color).save(path)
        return path

    def test_identical_images_are_100_percent_similar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = self._make_png(root, "a.png", (10, 20, 30))
            b = self._make_png(root, "b.png", (10, 20, 30))
            self.assertAlmostEqual(_similarity_percent(a, b), 100.0, places=3)

    def test_fully_different_images_are_0_percent_similar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = self._make_png(root, "a.png", (0, 0, 0))
            b = self._make_png(root, "b.png", (255, 255, 255))
            self.assertAlmostEqual(_similarity_percent(a, b), 0.0, places=3)

    def test_similarity_is_never_negative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = self._make_png(root, "a.png", (12, 34, 56))
            b = self._make_png(root, "b.png", (200, 100, 5))
            similarity = _similarity_percent(a, b)
            self.assertGreaterEqual(similarity, 0.0)
            self.assertLessEqual(similarity, 100.0)

    def test_build_report_pairs_screenshots_and_embeds_images(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before_dir = root / "before"
            after_dir = root / "after"
            before_dir.mkdir()
            after_dir.mkdir()
            self._make_png(before_dir, "01-fill.png", (10, 20, 30))
            self._make_png(after_dir, "01-fill.png", (10, 20, 30))
            report = build_report(
                test_name="Demo",
                before_dir=before_dir,
                after_dir=after_dir,
                report_root=root,
                test_passed=True,
                mapped_actions=1,
                unmatched_actions=0,
            )
            self.assertIn("PASSED", report)
            self.assertIn("1/1 activities mapped (100%)", report)
            self.assertIn("100.0% similar (PASS)", report)
            self.assertIn("before/01-fill.png", report)
            self.assertIn("after/01-fill.png", report)

    def test_html_report_shows_pass_banner_at_100_percent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before_dir = root / "before"
            after_dir = root / "after"
            before_dir.mkdir()
            after_dir.mkdir()
            self._make_png(before_dir, "01-fill.png", (10, 20, 30))
            self._make_png(after_dir, "01-fill.png", (10, 20, 30))
            html = build_html_report(
                test_name="Demo",
                before_dir=before_dir,
                after_dir=after_dir,
                test_passed=True,
                mapped_actions=1,
                unmatched_actions=0,
            )
            self.assertIn("<html lang=", html)
            self.assertIn("banner pass", html)
            self.assertIn(">100%<", html)
            self.assertIn("data:image/png;base64,", html)

    def test_html_report_flags_incomplete_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before_dir = root / "before"
            after_dir = root / "after"
            before_dir.mkdir()
            after_dir.mkdir()
            html = build_html_report(
                test_name="Demo",
                before_dir=before_dir,
                after_dir=after_dir,
                test_passed=None,
                mapped_actions=8,
                unmatched_actions=2,
            )
            self.assertIn("banner warn", html)
            self.assertIn(">80%<", html)


if __name__ == "__main__":
    unittest.main()

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tmdb_feed_generator.cli import _generate_all

ROOT = Path(__file__).resolve().parent.parent


class CliTest(unittest.TestCase):
    def args(self, out: Path, fixtures: Path) -> argparse.Namespace:
        return argparse.Namespace(clients_dir=ROOT / "clients", out=out, fixtures=fixtures)

    def test_generates_a_valid_json_file_per_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            failures = _generate_all(self.args(Path(tmp), ROOT / "tests" / "fixtures"))
            self.assertEqual(failures, 0)
            feed = json.loads((Path(tmp) / "default" / "recommendations.json").read_text(encoding="utf-8"))
            self.assertTrue(feed["hero"] and feed["rows"])

    def test_failed_run_keeps_the_previous_feed(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as empty:
            out = Path(tmp)
            _generate_all(self.args(out, ROOT / "tests" / "fixtures"))
            before = (out / "default" / "recommendations.json").read_text(encoding="utf-8")
            failures = _generate_all(self.args(out, Path(empty)))  # no fixtures: every lookup fails
            self.assertEqual(failures, 1)
            self.assertEqual((out / "default" / "recommendations.json").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timezone
from pathlib import Path

from tmdb_feed_generator.builder import EmptyFeedError, build_feed
from tmdb_feed_generator.config import load_client
from tmdb_feed_generator.fixtures import FixtureTransport
from tmdb_feed_generator.providers import PROVIDERS
from tmdb_feed_generator.tmdb import TmdbClient

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = {p.package for p in PROVIDERS.values()}


def make_feed(config_overrides=None):
    config = load_client(ROOT / "clients" / "default.json")
    client = TmdbClient(FixtureTransport(ROOT / "tests" / "fixtures"), config.language, config.region)
    return build_feed(client, config, now=datetime(2026, 1, 1, tzinfo=timezone.utc))


class BuilderTest(unittest.TestCase):
    def setUp(self):
        self.feed = make_feed()
        self.items = [i for r in self.feed["rows"] for i in r["items"]] + self.feed["hero"]

    def test_envelope(self):
        self.assertEqual(self.feed["generatedAt"], "2026-01-01T00:00:00Z")
        self.assertIn("TMDB", self.feed["attribution"])

    def test_every_item_matches_the_feed_format(self):
        for item in self.items:
            self.assertTrue(item["title"])
            self.assertIn(item["action"]["packageName"], PACKAGES)
            for key in ("imageUrl", "backdropUrl"):
                if key in item:
                    self.assertTrue(item[key].startswith("https://image.tmdb.org/t/p/"))

    def test_row_ids_are_unique_and_styles_valid(self):
        for row in self.feed["rows"]:
            self.assertIn(row["style"], {"poster", "banner"})
            ids = [i["id"] for i in row["items"]]
            self.assertEqual(len(ids), len(set(ids)))

    def test_hero_needs_backdrop_and_is_limited(self):
        self.assertLessEqual(len(self.feed["hero"]), 5)
        self.assertTrue(all("backdropUrl" in i for i in self.feed["hero"]))
        self.assertNotIn("tmdb-movie-9004", [i["id"] for i in self.feed["hero"]])  # fixture without backdrop

    def test_titles_not_streaming_on_a_configured_provider_are_dropped(self):
        # Provider rows are not checked here: TMDB already filters that discover query by provider,
        # while the offline fixtures answer it with the general list.
        checked = self.feed["hero"] + [i for r in self.feed["rows"] if r["id"].startswith("popular-") for i in r["items"]]
        self.assertNotIn("tmdb-movie-9003", [i["id"] for i in checked])

    def test_provider_follows_client_priority(self):
        by_id = {i["id"]: i for i in self.items}
        self.assertEqual(by_id["tmdb-movie-9002"]["provider"], "Globoplay")
        self.assertEqual(by_id["tmdb-movie-9001"]["provider"], "Netflix")

    def test_provider_rows_are_banners_with_backdrops(self):
        rows = {r["id"]: r for r in self.feed["rows"]}
        self.assertEqual(rows["provider-netflix"]["style"], "banner")
        self.assertTrue(all("/w780/" in i["imageUrl"] for i in rows["provider-netflix"]["items"]))

    def test_empty_result_is_an_error_not_an_empty_feed(self):
        config = load_client(ROOT / "clients" / "default.json")
        client = TmdbClient(lambda path, params: {"results": []}, config.language, config.region)
        with self.assertRaises(EmptyFeedError):
            build_feed(client, config)


if __name__ == "__main__":
    unittest.main()

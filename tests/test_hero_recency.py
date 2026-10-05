import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tmdb_feed_generator.builder import ATTRIBUTION, build_feed
from tmdb_feed_generator.config import ConfigError, load_client
from tmdb_feed_generator.fixtures import FixtureTransport
from tmdb_feed_generator.tmdb import TmdbClient

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class RecordingTransport:
    """Wraps the fixtures and remembers the parameters of every discover call."""

    def __init__(self):
        self._inner = FixtureTransport(ROOT / "tests" / "fixtures")
        self.discover_params: list[tuple[str, dict]] = []

    def __call__(self, path: str, params: dict):
        if path.startswith("/discover/"):
            self.discover_params.append((path, dict(params)))
        return self._inner(path, params)


def feed_with(max_age_days: int | None):
    config = load_client(ROOT / "clients" / "default.json")
    if max_age_days is not None:
        config = type(config)(**{**config.__dict__, "hero_max_age_days": max_age_days})
    transport = RecordingTransport()
    feed = build_feed(TmdbClient(transport, config.language, config.region), config, now=NOW)
    return feed, transport


class HeroRecencyTest(unittest.TestCase):
    def test_recent_releases_come_first_most_popular_first(self):
        feed, _ = feed_with(None)
        ids = [i["id"] for i in feed["hero"]]
        self.assertEqual(ids[:3], ["tmdb-movie-9201", "tmdb-tv-9301", "tmdb-movie-9202"])

    def test_remaining_slots_are_filled_with_the_most_popular_of_all_time(self):
        feed, _ = feed_with(None)
        ids = [i["id"] for i in feed["hero"]]
        self.assertEqual(len(ids), 5)
        self.assertEqual(ids[3], "tmdb-movie-9001")
        self.assertEqual(len(ids), len(set(ids)), "a title must not appear twice in the hero")

    def test_the_recent_query_sends_a_release_date_floor_per_media_type(self):
        _, transport = feed_with(None)
        floor = (NOW - timedelta(days=730)).date().isoformat()
        by_path = [(path, params) for path, params in transport.discover_params if "primary_release_date.gte" in params or "first_air_date.gte" in params]
        self.assertEqual({path for path, _ in by_path}, {"/discover/movie", "/discover/tv"})
        for path, params in by_path:
            key = "primary_release_date.gte" if path.endswith("movie") else "first_air_date.gte"
            self.assertEqual(params[key], floor)

    def test_zero_turns_the_preference_off(self):
        feed, transport = feed_with(0)
        self.assertTrue(all("primary_release_date.gte" not in p and "first_air_date.gte" not in p for _, p in transport.discover_params))
        self.assertEqual(feed["hero"][0]["id"], "tmdb-movie-9001")

    def test_the_age_must_be_a_sane_integer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "acme.json"
            for value in (-1, 99999, "730", True):
                path.write_text(json.dumps({"providers": ["netflix"], "heroMaxAgeDays": value}))
                with self.assertRaises(ConfigError, msg=repr(value)):
                    load_client(path)


class AttributionTest(unittest.TestCase):
    def test_uses_the_wording_tmdb_requires_and_names_justwatch(self):
        self.assertIn("uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB", ATTRIBUTION)
        self.assertIn("JustWatch", ATTRIBUTION)

    def test_every_feed_carries_it(self):
        feed, _ = feed_with(None)
        self.assertEqual(feed["attribution"], ATTRIBUTION)


if __name__ == "__main__":
    unittest.main()

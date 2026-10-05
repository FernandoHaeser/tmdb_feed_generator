import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from tmdb_feed_generator.config import ConfigError, load_client
from tmdb_feed_generator.tmdb import TmdbError, http_transport

SECRET = "0123456789abcdef0123456789abcdef"


def write_client(directory: str, name: str, content: dict) -> Path:
    path = Path(directory) / name
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


class ConfigTest(unittest.TestCase):
    def test_unknown_provider_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError):
                load_client(write_client(tmp, "acme.json", {"providers": ["netflix", "nope"]}))

    def test_client_id_comes_from_a_safe_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError):
                load_client(write_client(tmp, "../evil.json".replace("/", "_") + ".JSON", {"providers": ["netflix"]}))

    def test_bounds_are_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError):
                load_client(write_client(tmp, "acme.json", {"providers": ["netflix"], "heroCount": 99}))


class TransportTest(unittest.TestCase):
    def test_retries_then_succeeds_honoring_retry_after(self):
        limited = urllib.error.HTTPError("u", 429, "limit", {"Retry-After": "3"}, io.BytesIO(b""))
        ok = mock.MagicMock()
        ok.__enter__.return_value = io.BytesIO(b'{"results": []}')
        sleeps = []
        with mock.patch("urllib.request.urlopen", side_effect=[limited, ok]):
            result = http_transport(SECRET, sleep=sleeps.append)("/discover/movie", {})
        self.assertEqual(result, {"results": []})
        self.assertEqual(sleeps, [3.0])

    def test_errors_never_leak_the_credential(self):
        failure = urllib.error.HTTPError(f"https://x/?api_key={SECRET}", 401, "no", {}, io.BytesIO(b""))
        with mock.patch("urllib.request.urlopen", side_effect=failure):
            with self.assertRaises(TmdbError) as caught:
                http_transport(SECRET, sleep=lambda s: None)("/discover/movie", {})
        self.assertNotIn(SECRET, str(caught.exception))

    def test_v4_token_goes_in_the_header_not_the_url(self):
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"], seen["auth"] = request.full_url, request.get_header("Authorization")
            response = mock.MagicMock()
            response.__enter__.return_value = io.BytesIO(b"{}")
            return response

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            http_transport("eyJhbGciOi.v4.token")("/discover/tv", {"page": "1"})
        self.assertEqual(seen["auth"], "Bearer eyJhbGciOi.v4.token")
        self.assertNotIn("eyJ", seen["url"])


if __name__ == "__main__":
    unittest.main()

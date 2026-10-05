"""Minimal TMDB v3 client (standard library only)."""

import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Protocol

log = logging.getLogger(__name__)

API_BASE = "https://api.themoviedb.org/3"
V3_KEY_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class TmdbError(RuntimeError):
    """Raised for failed requests. Messages carry the path only, never the credentials."""


class Transport(Protocol):
    def __call__(self, path: str, params: dict[str, str]) -> dict: ...


def http_transport(token: str, timeout: float = 10.0, retries: int = 3, sleep: Callable[[float], None] = time.sleep) -> Transport:
    """Real transport. A 32-hex token is a v3 API key (sent as `api_key`); anything else is a v4 bearer token."""
    use_query_key = bool(V3_KEY_PATTERN.match(token))

    def request(path: str, params: dict[str, str]) -> dict:
        query = dict(params)
        headers = {"Accept": "application/json"}
        if use_query_key:
            query["api_key"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"
        url = f"{API_BASE}{path}?{urllib.parse.urlencode(query)}"

        for attempt in range(1, retries + 1):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == retries:
                    raise TmdbError(f"TMDB {path} failed with HTTP {error.code}") from None
                delay = float(error.headers.get("Retry-After") or 2 ** attempt)
                log.warning("TMDB %s returned %s, retrying in %.0fs", path, error.code, delay)
                sleep(min(delay, 30))
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt == retries:
                    raise TmdbError(f"TMDB {path} unreachable: {type(error).__name__}") from None
                sleep(2 ** attempt)
        raise TmdbError(f"TMDB {path} failed")  # pragma: no cover

    return request


class TmdbClient:
    def __init__(self, transport: Transport, language: str, region: str):
        self._transport = transport
        self._language = language
        self._region = region
        self._providers_cache: dict[tuple[str, int], list[dict]] = {}

    def discover(self, media_type: str, provider_ids: list[int], since: str | None = None) -> list[dict]:
        """Popular titles streaming (flatrate) on any of [provider_ids] in the region.

        [since] (YYYY-MM-DD) keeps only titles released on or after that date.
        """
        params = {
            "language": self._language,
            "watch_region": self._region,
            "with_watch_providers": "|".join(str(i) for i in provider_ids),
            "with_watch_monetization_types": "flatrate",
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "page": "1",
        }
        if since:
            params["primary_release_date.gte" if media_type == "movie" else "first_air_date.gte"] = since
        data = self._transport(f"/discover/{media_type}", params)
        return data.get("results", [])

    def watch_providers(self, media_type: str, tmdb_id: int) -> list[dict]:
        key = (media_type, tmdb_id)
        if key not in self._providers_cache:
            data = self._transport(f"/{media_type}/{tmdb_id}/watch/providers", {})
            self._providers_cache[key] = data.get("results", {}).get(self._region, {}).get("flatrate", [])
        return self._providers_cache[key]

    def list_providers(self, media_type: str) -> list[dict]:
        data = self._transport(
            f"/watch/providers/{media_type}", {"language": self._language, "watch_region": self._region}
        )
        return data.get("results", [])

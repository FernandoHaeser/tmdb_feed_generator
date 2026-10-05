"""Turns TMDB data into the feed described in docs/feed-format.md."""

import re
from datetime import datetime, timezone

from tmdb_feed_generator.config import ClientConfig
from tmdb_feed_generator.providers import Provider
from tmdb_feed_generator.tmdb import TmdbClient

IMAGE_BASE = "https://image.tmdb.org/t/p"
IMAGE_PATH = re.compile(r"^/[\w.-]+$")
MEDIA_TYPES = ("movie", "tv")
MIN_OVERVIEW = 20
MAX_DESCRIPTION = 280
ATTRIBUTION = (
    "This product uses the TMDB API but is not endorsed or certified by TMDB. "
    "Streaming availability data provided by JustWatch."
)


class EmptyFeedError(RuntimeError):
    pass


def build_feed(client: TmdbClient, config: ClientConfig, now: datetime | None = None) -> dict:
    builder = _Builder(client, config)
    feed = {
        "generatedAt": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "attribution": ATTRIBUTION,
        "hero": builder.hero(),
        "rows": builder.rows(),
    }
    if not feed["hero"] and not feed["rows"]:
        raise EmptyFeedError(f"Feed for '{config.client_id}' came out empty; refusing to publish it")
    return feed


class _Builder:
    def __init__(self, client: TmdbClient, config: ClientConfig):
        self._client = client
        self._config = config
        self._all_ids = [p.tmdb_id for p in config.providers]
        self._discovered: dict[str, list[dict]] = {
            media_type: client.discover(media_type, self._all_ids) for media_type in MEDIA_TYPES
        }

    def hero(self) -> list[dict]:
        merged = sorted(
            ((media_type, raw) for media_type in MEDIA_TYPES for raw in self._discovered[media_type]),
            key=lambda pair: pair[1].get("popularity", 0),
            reverse=True,
        )
        items = []
        for media_type, raw in merged:
            if len(items) == self._config.hero_count:
                break
            if not _image(raw.get("backdrop_path"), "w1280") or len(raw.get("overview", "")) < MIN_OVERVIEW:
                continue
            provider = self._pick_provider(media_type, raw)
            if provider:
                items.append(_item(media_type, raw, provider, image_size=None))
        return items

    def rows(self) -> list[dict]:
        rows = [self._poster_row("movie", "Filmes populares nos seus apps"),
                self._poster_row("tv", "Séries populares nos seus apps")]
        if self._config.per_provider_rows:
            rows.extend(self._provider_row(provider) for provider in self._config.providers)
        return [row for row in rows if row["items"]]

    def _poster_row(self, media_type: str, title: str) -> dict:
        items = []
        for raw in self._discovered[media_type]:
            if len(items) == self._config.row_size:
                break
            if not _image(raw.get("poster_path"), "w342"):
                continue
            provider = self._pick_provider(media_type, raw)
            if provider:
                items.append(_item(media_type, raw, provider, image_size=("poster_path", "w342")))
        return {"id": f"popular-{media_type}", "title": title, "style": "poster", "items": items}

    def _provider_row(self, provider: Provider) -> dict:
        candidates = [
            (media_type, raw)
            for media_type in MEDIA_TYPES
            for raw in self._client.discover(media_type, [provider.tmdb_id])
        ]
        candidates.sort(key=lambda pair: pair[1].get("popularity", 0), reverse=True)
        items = [
            _item(media_type, raw, provider, image_size=("backdrop_path", "w780"))
            for media_type, raw in candidates
            if _image(raw.get("backdrop_path"), "w780")
        ][: self._config.row_size]
        return {"id": f"provider-{provider.key}", "title": f"No {provider.name}", "style": "banner", "items": items}

    def _pick_provider(self, media_type: str, raw: dict) -> Provider | None:
        """First configured provider (in the client's priority order) that streams the title."""
        available = {p["provider_id"] for p in self._client.watch_providers(media_type, raw["id"])}
        return next((p for p in self._config.providers if p.tmdb_id in available), None)


def _image(path: str | None, size: str) -> str | None:
    return f"{IMAGE_BASE}/{size}{path}" if path and IMAGE_PATH.match(path) else None


def _item(media_type: str, raw: dict, provider: Provider, image_size: tuple[str, str] | None) -> dict:
    title = raw.get("title") or raw.get("name")
    date = raw.get("release_date") or raw.get("first_air_date") or ""
    kind = "Filme" if media_type == "movie" else "Série"
    item = {
        "id": f"tmdb-{media_type}-{raw['id']}",
        "title": title,
        "subtitle": f"{kind} · {date[:4]}" if date[:4].isdigit() else kind,
        "description": _shorten(raw.get("overview", "")),
        "provider": provider.name,
        "action": {"packageName": provider.package},
    }
    if image_size:
        field, size = image_size
        item["imageUrl"] = _image(raw.get(field), size)
    if _image(raw.get("backdrop_path"), "w1280"):
        item["backdropUrl"] = _image(raw["backdrop_path"], "w1280")
    return {key: value for key, value in item.items() if value}


def _shorten(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= MAX_DESCRIPTION else text[: MAX_DESCRIPTION - 1].rstrip() + "…"

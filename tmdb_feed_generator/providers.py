"""Streaming services the feed can target.

`tmdb_id` is the TMDB watch-provider id (region dependent) and `package` is the Android TV
package of the app a card opens. Both were written from memory (the ids were later confirmed against TMDB for BR; the packages were not): run `python -m tmdb_feed_generator list-providers`
and check the ids, and confirm each package on a real device before relying on it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    key: str
    name: str
    tmdb_id: int
    package: str


PROVIDERS: dict[str, Provider] = {
    p.key: p
    for p in (
        Provider("netflix", "Netflix", 8, "com.netflix.ninja"),
        Provider("prime", "Prime Video", 119, "com.amazon.amazonvideo.livingroom"),
        Provider("disney", "Disney+", 337, "com.disney.disneyplus"),
        Provider("globoplay", "Globoplay", 307, "com.globo.globotv"),
        Provider("appletv", "Apple TV+", 350, "com.apple.atve.androidtv.appletv"),
        Provider("paramount", "Paramount+", 531, "com.cbs.ott"),
        Provider("max", "HBO Max", 1899, "com.wbd.stream"),
    )
}

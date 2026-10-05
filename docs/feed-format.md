# Feed format

The generator writes `recommendations.json` for each client. Everything except `title` is optional for a consumer to render; unknown keys must be ignored so the format can grow.

```json
{
  "generatedAt": "2026-10-05T12:00:00Z",
  "attribution": "This product uses the TMDB API but is not endorsed or certified by TMDB. Streaming availability data provided by JustWatch.",
  "hero": [
    {
      "id": "tmdb-tv-108978",
      "title": "Reacher",
      "subtitle": "Série · 2022",
      "description": "Short synopsis, at most 280 characters.",
      "provider": "Prime Video",
      "backdropUrl": "https://image.tmdb.org/t/p/w1280/pF0qkRsrHkdYadPWY9AMeFZfcwk.jpg",
      "action": { "packageName": "com.amazon.amazonvideo.livingroom" }
    }
  ],
  "rows": [
    {
      "id": "popular-movie",
      "title": "Filmes populares nos seus apps",
      "style": "poster",
      "items": [ { "id": "tmdb-movie-1", "title": "…", "imageUrl": "https://image.tmdb.org/t/p/w342/….jpg", "action": { "packageName": "…" } } ]
    }
  ]
}
```

## Top level

| Key | Description |
|---|---|
| `generatedAt` | UTC timestamp of the run |
| `attribution` | Notice that apps displaying the feed must show |
| `hero` | Featured titles (large artwork), at most `heroCount` |
| `rows` | Rows of cards; rows without items are never emitted |

## Row

| Key | Description |
|---|---|
| `id` | Stable identifier (`popular-movie`, `popular-tv`, `provider-<key>`) |
| `title` | Row heading |
| `style` | `poster` (2:3 artwork) or `banner` (16:9 artwork) |
| `items` | Cards |

## Item

| Key | Description |
|---|---|
| `id` | Unique within the feed (`tmdb-<movie\|tv>-<TMDB id>`) |
| `title` | Localized title (required) |
| `subtitle` | Type and year |
| `description` | Synopsis, at most 280 characters |
| `provider` | Display name of the streaming service |
| `imageUrl` | Card artwork: poster (`w342`) in poster rows, backdrop (`w780`) in banner rows |
| `backdropUrl` | Large artwork (`w1280`) for hero use |
| `action.packageName` | Android package of the app that plays the title |
| `action.uri` | Optional deep link into that app. **This generator does not set it** (TMDB has no deep links); the format reserves it for other producers |

## Consuming the feed safely

- Fetch over HTTPS only, with a timeout and a size limit (the generated files are well under 1 MB).
- Treat every field as untrusted text; only load images from HTTPS URLs.
- Pin an action to its `packageName` (for example `Intent.setPackage` on Android) so a feed cannot open an arbitrary app.
- Hide cards whose app is not installed, and rows that end up empty.
- Show the `attribution` text.

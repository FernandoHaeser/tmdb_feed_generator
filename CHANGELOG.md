# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/) and the project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- The hero favours recent releases (`heroMaxAgeDays`, default 730; `0` disables) and falls back to the most popular titles.
- The `attribution` text uses the exact notice TMDB's terms require.
- README states the free API's no-commercial-use term and the attribution and logo rules.

### Added
- Feed generator: popular movies and series on the configured streaming services, from TMDB data.
- Per-client configuration (region, language, providers, hero and row sizes).
- TMDB client with retries, v3 key and v4 token support, and credential-safe error messages.
- Offline mode (`--fixtures`) and `list-providers` to verify provider ids per region.
- Docker stack: generator plus nginx serving only `/<client>/recommendations.json`.
- Atomic writes; a failed or empty run keeps the last good feed.

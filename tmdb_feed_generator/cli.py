import argparse
import logging
import os
import sys
import time
from pathlib import Path

from tmdb_feed_generator.builder import build_feed
from tmdb_feed_generator.config import ClientConfig, load_clients
from tmdb_feed_generator.envfile import load_env
from tmdb_feed_generator.fixtures import FixtureTransport
from tmdb_feed_generator.publish import write_feed
from tmdb_feed_generator.tmdb import TmdbClient, http_transport

log = logging.getLogger("tmdb_feed_generator")


def main(argv: list[str] | None = None) -> int:
    load_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parser().parse_args(argv)
    return args.handler(args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tmdb_feed_generator", description="Generate a feed of popular movies and series from TMDB")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--clients-dir", type=Path, default=Path(os.environ.get("FEED_CLIENTS_DIR", "clients")))
        p.add_argument("--out", type=Path, default=Path(os.environ.get("FEED_OUT", "dist")))
        p.add_argument(
            "--fixtures",
            type=Path,
            default=Path(os.environ["FEED_FIXTURES"]) if os.environ.get("FEED_FIXTURES") else None,
            help="answer from local JSON files instead of calling TMDB (env: FEED_FIXTURES)",
        )

    generate = sub.add_parser("generate", help="generate every client's feed once")
    common(generate)
    generate.set_defaults(handler=_generate)

    run = sub.add_parser("run", help="generate repeatedly (container entrypoint)")
    common(run)
    run.add_argument("--interval-hours", type=float, default=float(os.environ.get("FEED_INTERVAL_HOURS", "6")))
    run.set_defaults(handler=_run)

    providers = sub.add_parser("list-providers", help="print TMDB watch-provider ids, to verify providers.py")
    providers.add_argument("--region", default="BR")
    providers.set_defaults(handler=_list_providers)
    return parser


def _make_client(config: ClientConfig, fixtures: Path | None) -> TmdbClient:
    if fixtures:
        return TmdbClient(FixtureTransport(fixtures), config.language, config.region)
    token = os.environ.get("TMDB_TOKEN", "").strip()
    if not token:
        raise SystemExit("TMDB_TOKEN is not set (see .env.example), or pass --fixtures")
    return TmdbClient(http_transport(token), config.language, config.region)


def _generate_all(args: argparse.Namespace) -> int:
    """Returns the number of clients that failed; a failed client keeps its previous feed."""
    failures = 0
    for config in load_clients(args.clients_dir):
        try:
            feed = build_feed(_make_client(config, args.fixtures), config)
            target = write_feed(args.out, config.client_id, feed)
            log.info("%s: wrote %s (%d hero, %d rows)", config.client_id, target, len(feed["hero"]), len(feed["rows"]))
        except Exception as error:  # noqa: BLE001 - one client must not stop the others
            failures += 1
            log.error("%s: generation failed (%s: %s); keeping the previous feed", config.client_id, type(error).__name__, error)
    return failures


def _generate(args: argparse.Namespace) -> int:
    return 1 if _generate_all(args) else 0


def _run(args: argparse.Namespace) -> int:
    while True:
        _generate_all(args)
        time.sleep(args.interval_hours * 3600)


def _list_providers(args: argparse.Namespace) -> int:
    config = ClientConfig("providers", providers=(), region=args.region)
    client = _make_client(config, None)
    for media_type in ("movie", "tv"):
        print(f"# {media_type}")
        for provider in sorted(client.list_providers(media_type), key=lambda p: p["provider_name"]):
            print(f"{provider['provider_id']:>6}  {provider['provider_name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

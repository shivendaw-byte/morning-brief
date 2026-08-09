"""Resolve a podcast's real RSS feed URL from its Apple Podcasts ID."""

import sys

import requests

SHOWS = {
    "The Moth": "275699983",
    "This American Life": "201671138",
    "Acquired": "1050462261",
    "Huberman Lab": "1545953110",
}


def main() -> int:
    for name, podcast_id in SHOWS.items():
        try:
            resp = requests.get(
                f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcast",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30,
            )
            results = resp.json().get("results", [])
            feed = results[0].get("feedUrl") if results else None
            print(f"  {name:<22} -> {feed}")
        except Exception as exc:
            print(f"  {name:<22} -> ERROR {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

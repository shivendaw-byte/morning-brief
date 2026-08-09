"""Show exactly what a feed URL returns, straight from config."""

import pathlib
import sys

import feedparser
import requests
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from brief import collect  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
WANTED = {"The Moth", "On Purpose with Jay Shetty", "Odd Lots"}


def main() -> int:
    feeds = yaml.safe_load((ROOT / "config" / "feeds.yml").read_text(encoding="utf-8"))
    for show in feeds["listens"]:
        if show["name"] not in WANTED:
            continue
        url = show["url"]
        print(f"\n--- {show['name']} ---")
        print("url from yaml:", repr(url))
        resp = requests.get(url, headers=collect.HEADERS, timeout=30, allow_redirects=True)
        print("status:", resp.status_code, "| final url:", resp.url[:110])
        print("content-type:", resp.headers.get("content-type"))
        print("bytes:", len(resp.content))
        parsed = feedparser.parse(resp.content)
        print("bozo:", parsed.bozo, parsed.get("bozo_exception"))
        print("entries:", len(parsed.entries))
        if parsed.entries:
            first = parsed.entries[0]
            print("first title:", getattr(first, "title", None))
            print("first link:", getattr(first, "link", None))
        print("head:", resp.content[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Check every configured feed and job page. Run after editing config/."""

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from brief import collect  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    feeds = yaml.safe_load((ROOT / "config" / "feeds.yml").read_text(encoding="utf-8"))
    jobs = yaml.safe_load((ROOT / "config" / "jobs.yml").read_text(encoding="utf-8"))
    dead = 0

    print("== READS ==")
    for feed in feeds["reads"]:
        errors: list[str] = []
        items = collect.fetch_feed(feed["name"], feed["url"], feed.get("track", ""), errors)
        status = f"{len(items):3d} items" if items else "  DEAD   "
        dead += 0 if items else 1
        print(f"  [{status}] {feed['name']}")
        if errors:
            print(f"             {errors[0][:150]}")

    print("\n== LISTENS ==")
    for show in feeds["listens"]:
        errors = []
        items = collect.fetch_feed(show["name"], show["url"], "listen", errors)
        newest = items[0].title[:60] if items else "-"
        status = f"{len(items):3d} eps" if items else " DEAD  "
        dead += 0 if items else 1
        print(f"  [{status}] {show['name']:<28} newest: {newest}")
        if errors:
            print(f"             {errors[0][:150]}")

    print("\n== JOB PAGES ==")
    snapshots: dict = {}
    errors = []
    changes = collect.collect_job_changes(jobs["targets"], snapshots, errors)
    ok = {c.url for c in changes}
    for target in jobs["targets"]:
        reachable = target["url"] in ok
        chars = len(snapshots.get(target["url"], {}).get("text", ""))
        dead += 0 if reachable else 1
        print(f"  [{'OK ' if reachable else 'DEAD'}] {target['label']:<45} {chars:>6} chars")
    for err in errors:
        print(f"         {err[:170]}")

    print(f"\n{dead} unreachable source(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

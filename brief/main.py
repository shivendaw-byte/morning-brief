"""Entry point. Runs once, sends one email, exits.

Design rule: an email goes out every morning no matter what. Feed failures,
scraper failures and model failures all degrade the brief - none of them
cancel it. Only a mail-transport failure is allowed to fail the run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import zoneinfo

import yaml

from brief import collect, curate, mailer, pick, render

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
ET = zoneinfo.ZoneInfo("America/New_York")
MAX_SEEN = 4000


def _load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: pathlib.Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="ignore the once-per-day guard")
    parser.add_argument("--dry-run", action="store_true", help="write the brief to disk instead of emailing")
    args = parser.parse_args()

    now_et = dt.datetime.now(ET)
    today = now_et.date()
    date_label = now_et.strftime("%A, %B %d").replace(" 0", " ")

    last_run = _load_json(STATE / "last_run.json", {})
    if not args.force and last_run.get("sent_on") == today.isoformat():
        print(f"Already sent for {today}. Exiting cleanly.")
        return 0

    feeds_cfg = yaml.safe_load((ROOT / "config" / "feeds.yml").read_text(encoding="utf-8"))
    jobs_cfg = yaml.safe_load((ROOT / "config" / "jobs.yml").read_text(encoding="utf-8"))

    seen = _load_json(STATE / "seen_articles.json", [])
    snapshots = _load_json(STATE / "job_snapshots.json", {})

    # Everything that identifies the reader - their profile and their contacts -
    # arrives as a secret, never as a committed file, so this repo can be public
    # without exposing them or the people they know. Both fall back to local
    # gitignored files when running on this machine.
    profile = os.environ.get("BRIEF_PROFILE", "")
    if not profile:
        profile_path = ROOT / "config" / "profile.md"
        profile = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
    if not profile:
        print("No BRIEF_PROFILE set - the brief will be generic.", file=sys.stderr)

    network = []
    if os.environ.get("BRIEF_NETWORK"):
        try:
            network = json.loads(os.environ["BRIEF_NETWORK"])
        except Exception as exc:
            print(f"BRIEF_NETWORK unparseable, ignoring: {exc}", file=sys.stderr)
    else:
        network = _load_json(ROOT / "config" / "network.json", [])

    bundle = collect.Bundle()
    bundle.items = collect.collect_reads(feeds_cfg["reads"], set(seen), bundle.errors)
    episode, angle = collect.collect_episode(feeds_cfg["listens"], now_et.weekday(), bundle.errors)

    job_targets = list(jobs_cfg.get("targets", []))
    for i, query in enumerate(jobs_cfg.get("news_queries", [])):
        bundle.items += collect.fetch_feed(f"Recruiting news {i + 1}", query, "recruiting", bundle.errors)
    bundle.job_changes = collect.collect_job_changes(job_targets, snapshots, bundle.errors)

    print(f"{len(bundle.items)} candidate items | "
          f"{len([c for c in bundle.job_changes if not c.first_seen])} page diffs | "
          f"{len(bundle.errors)} source errors")

    notes: list[str] = []
    if bundle.errors:
        notes.append(f"{len(bundle.errors)} source(s) unreachable")
        for err in bundle.errors:
            print("  source error:", err, file=sys.stderr)

    try:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        brief = curate.curate(
            bundle, episode, angle, now_et,
            jobs_cfg.get("priority_programs", []), network, profile,
        )
        subject = f"Morning Brief — {date_label} — {brief.get('subject', '').strip()}".rstrip(" —")
        text_body = render.render_text(brief, date_label, notes)
        html_body = render.render_html(brief, date_label, notes)
        chosen = {r.get("url") for r in brief.get("reads", []) if r.get("url")}
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        print("Curation failed:", reason, file=sys.stderr)
        notes.append("Unedited: ranked automatically, no model available.")
        # Rank-only brief first. It keeps the 3-reads/1-listen shape and reads
        # like the real thing minus the judgment; the raw dump is the last resort.
        try:
            brief = pick.select(bundle, episode, now_et)
            subject = f"Morning Brief — {date_label} — {brief.get('subject', '').strip()}".rstrip(" —")
            text_body = render.render_text(brief, date_label, notes)
            html_body = render.render_html(brief, date_label, notes)
        except Exception as pick_exc:
            print("Rank-only fallback failed:", pick_exc, file=sys.stderr)
            subject = f"Morning Brief — {date_label} — [raw, curation failed]"
            text_body, html_body = render.render_raw_fallback(bundle, episode, date_label, reason)
        chosen = set()

    if args.dry_run:
        out = ROOT / "out"
        out.mkdir(exist_ok=True)
        (out / "brief.html").write_text(html_body, encoding="utf-8")
        (out / "brief.txt").write_text(f"Subject: {subject}\n\n{text_body}", encoding="utf-8")
        print(f"Dry run. Wrote {out / 'brief.html'}")
        return 0

    mailer.send(subject, text_body, html_body)
    print("Sent:", subject)

    # Only mark an article seen once it has actually been shipped to him, so a
    # failed run never silently burns a story.
    seen = ([collect.Item("", url, "", "").key for url in chosen] + seen)[:MAX_SEEN]
    _save_json(STATE / "seen_articles.json", seen)
    _save_json(STATE / "job_snapshots.json", snapshots)
    _save_json(STATE / "last_run.json", {"sent_on": today.isoformat(), "subject": subject})
    return 0


if __name__ == "__main__":
    sys.exit(main())

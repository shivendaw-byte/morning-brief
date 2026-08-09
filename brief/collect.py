"""Fetch RSS items and detect changes on internship application pages."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import re
from dataclasses import dataclass, field

import feedparser
import requests

# Several podcast CDNs (omny, feedburner) and careers sites reject non-browser
# agents outright, so we present as a normal browser rather than a bot.
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
LOOKBACK_HOURS = 30  # "what happened since yesterday's brief"


@dataclass
class Item:
    title: str
    url: str
    source: str
    track: str
    published: dt.datetime | None = None
    summary: str = ""

    @property
    def key(self) -> str:
        return hashlib.sha1(self.url.encode("utf-8", "ignore")).hexdigest()[:16]


@dataclass
class JobChange:
    firm: str
    label: str
    url: str
    priority: str
    added_text: str = ""
    first_seen: bool = False


@dataclass
class Bundle:
    items: list[Item] = field(default_factory=list)
    episodes: list[Item] = field(default_factory=list)
    job_changes: list[JobChange] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _published(entry) -> dt.datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            return dt.datetime(*parsed[:6], tzinfo=dt.timezone.utc)
    return None


def _entry_link(entry, feed_link: str) -> str:
    """Several podcast feeds ship no <link> on items - fall back rather than drop."""
    direct = getattr(entry, "link", "") or ""
    if direct.startswith("http"):
        return direct
    guid = getattr(entry, "id", "") or ""
    if guid.startswith("http"):
        return guid
    for enclosure in getattr(entry, "enclosures", []) or []:
        href = enclosure.get("href", "")
        if href.startswith("http"):
            return href
    return feed_link


def fetch_feed(name: str, url: str, track: str, errors: list[str]) -> list[Item]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:  # a dead feed must never kill the brief
        errors.append(f"feed '{name}': {type(exc).__name__}: {exc}")
        return []

    feed_link = getattr(parsed.feed, "link", "") or ""
    items = []
    for entry in parsed.entries[:40]:
        title = _clean(getattr(entry, "title", ""))
        link = _entry_link(entry, feed_link)
        if not link or not title:
            continue
        items.append(
            Item(
                title=title,
                url=link,
                source=name,
                track=track,
                published=_published(entry),
                summary=_clean(getattr(entry, "summary", ""))[:600],
            )
        )
    return items


def collect_reads(feeds: list[dict], seen: set[str], errors: list[str]) -> list[Item]:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=LOOKBACK_HOURS)
    fresh: list[Item] = []
    for feed in feeds:
        for item in fetch_feed(feed["name"], feed["url"], feed.get("track", "business"), errors):
            if item.key in seen:
                continue
            # Keep undated items: some feeds omit timestamps entirely.
            if item.published and item.published < cutoff:
                continue
            fresh.append(item)
    return fresh


def collect_episode(listens: list[dict], weekday: int, errors: list[str]) -> tuple[Item | None, str]:
    """Return the newest episode from whichever show owns today's slot."""
    slot = [show for show in listens if weekday in show.get("day", [])]
    if not slot:
        slot = listens[:1]

    for show in slot:
        items = fetch_feed(show["name"], show["url"], "listen", errors)
        if items:
            newest = max(items, key=lambda i: i.published or dt.datetime.min.replace(tzinfo=dt.timezone.utc))
            return newest, (show.get("angle") or "").strip()
    return None, ""


def _visible_text(html_doc: str) -> str:
    body = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html_doc)
    body = re.sub(r"(?s)<!--.*?-->", " ", body)
    body = re.sub(r"<[^>]+>", "\n", body)
    body = html.unescape(body)
    lines = [ln.strip() for ln in body.splitlines()]
    return "\n".join(ln for ln in lines if len(ln) > 2)


def collect_job_changes(targets: list[dict], snapshots: dict, errors: list[str]) -> list[JobChange]:
    changes: list[JobChange] = []
    for target in targets:
        url = target["url"]
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            text = _visible_text(resp.text)
        except Exception as exc:
            errors.append(f"job page '{target['label']}': {type(exc).__name__}: {exc}")
            continue

        digest = hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()
        previous = snapshots.get(url)
        snapshots[url] = {"hash": digest, "text": text[:20000]}

        if previous is None:
            changes.append(JobChange(target["firm"], target["label"], url, target.get("priority", "tier2"), first_seen=True))
            continue
        if previous.get("hash") == digest:
            continue

        old_lines = set(previous.get("text", "").splitlines())
        added = [ln for ln in text.splitlines() if ln not in old_lines]
        if not added:
            continue
        changes.append(
            JobChange(
                firm=target["firm"],
                label=target["label"],
                url=url,
                priority=target.get("priority", "tier2"),
                added_text="\n".join(added[:120])[:6000],
            )
        )
    return changes

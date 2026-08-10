"""Choose the brief without a model.

Used when the Anthropic API is unavailable - no key, no credit, an outage. It
returns the same dict shape curate.curate() does, so render.py is unchanged and
the 3-reads/1-listen contract still holds.

What this cannot do is write the "Use it" line. Deciding how a story lands in a
case interview is judgment, not ranking, so those fields come back empty and the
renderer omits them rather than printing something invented. A quieter brief is
the honest failure mode; a fabricated one is not.
"""

from __future__ import annotations

import datetime as dt
import re

# Reads 1 and 2 come from these; read 3 alternates between the two below.
PRIMARY = ("deals", "business")
ROTATING = ("tech", "policy")

TRACK_WEIGHT = {"deals": 3.0, "business": 3.0, "tech": 2.0, "policy": 2.0, "recruiting": 0.5}

# Publications whose house style is the deep-dive the reader is short on.
PREFERRED = (
    "wsj.com", "economist.com", "ft.com", "bloomberg.com",
    "stratechery.com", "reuters.com", "hbr.org",
)


def _age_hours(item, now: dt.datetime) -> float:
    if not item.published:
        return 48.0
    return max(0.0, (now - item.published).total_seconds() / 3600.0)


def score(item, now: dt.datetime) -> float:
    """Higher is better. Track first, then freshness, then source."""
    value = TRACK_WEIGHT.get(item.track, 1.0)
    value -= _age_hours(item, now) / 24.0
    if any(domain in item.url for domain in PREFERRED):
        value += 0.75
    if item.summary:
        value += 0.25
    return value


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (title or "").lower()).strip()


def _dedupe(items):
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out = []
    for item in items:
        title = _norm(item.title)
        if item.url in seen_urls or (title and title in seen_titles):
            continue
        seen_urls.add(item.url)
        seen_titles.add(title)
        out.append(item)
    return out


def shortlist(items, now: dt.datetime, limit: int = 110):
    """Best-first, deduped. Also used to trim what gets sent to the model."""
    return _dedupe(sorted(items, key=lambda i: -score(i, now)))[:limit]


MIN_SENTENCE = 40  # "U.S." is a sentence break to a regex, so keep taking parts.


def _first_sentence(text: str, cap: int = 220) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    sentence = ""
    for part in parts:
        sentence = f"{sentence} {part}".strip()
        if len(sentence) >= MIN_SENTENCE:
            break
    if len(sentence) > cap:
        sentence = sentence[:cap].rsplit(" ", 1)[0] + "..."
    return sentence


def _as_read(item) -> dict:
    return {
        "title": item.title,
        "source": item.source,
        "minutes": 4,
        "what": _first_sentence(item.summary),
        "use_it": "",  # deliberately empty - see module docstring
        "url": item.url,
    }


def select(bundle, episode, now: dt.datetime) -> dict:
    """Build a brief dict from ranked items alone."""
    ranked = shortlist(bundle.items, now, limit=200)
    reads: list = []

    def take(candidates, count: int) -> None:
        """Append up to `count`, never twice from one publication."""
        used = {i.source for i in reads}
        for item in candidates:
            if item in reads or item.source in used:
                continue
            reads.append(item)
            used.add(item.source)
            count -= 1
            if count <= 0:
                return

    take([i for i in ranked if i.track in PRIMARY], 2)

    # Read 3 alternates day to day, exactly as the editorial rules ask.
    wanted = ROTATING[now.timetuple().tm_yday % 2]
    take([i for i in ranked if i.track == wanted], 1)
    if len(reads) < 3:
        take([i for i in ranked if i.track in ROTATING], 1)
    if len(reads) < 3:
        take(ranked, 3 - len(reads))
    # Only if the haul is genuinely thin do we allow a repeated publication.
    for item in ranked:
        if len(reads) >= 3:
            break
        if item not in reads:
            reads.append(item)

    listen = {}
    if episode:
        listen = {
            "show": episode.source,
            "title": episode.title,
            "runtime": "",
            "what": _first_sentence(episode.summary, 300),
            "use_it": "",
            "url": episode.url,
        }

    lead = reads[0].title if reads else "no candidates today"
    return {
        "subject": f"[unedited] {lead[:60]}",
        "reads": [_as_read(i) for i in reads],
        "listen": listen,
        "jobs": [],
        "one_line": (
            "Picked by ranking, not editing - the Anthropic API was unavailable, "
            "so there are no 'Use it' lines today."
        ),
    }

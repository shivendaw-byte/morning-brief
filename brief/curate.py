"""Hand the raw haul to Claude and get back a finished brief.

Nothing in this file identifies the reader. The whole personal profile - who
they are, what they are recruiting for, which programs they track - arrives at
runtime from the BRIEF_PROFILE secret, so this repo can be public without
exposing anything about them.
"""

from __future__ import annotations

import json
import os
import re

GENERIC_PROFILE = """The reader is a university student recruiting for management consulting who does
not have a business background. No further detail was supplied, so keep the brief general: pick
widely useful business stories and write the "Use it" lines against standard case archetypes
(profitability, market entry, M&A, pricing)."""

SYSTEM = """You are the editor of a private daily Morning Brief. You write it once a day and the reader reads nothing else.

## WHO YOU ARE WRITING FOR

{profile}

## THE PROBLEM YOU SOLVE

They are building business acumen from scratch and deliberately avoid news apps and social media because they fall into addiction loops. This email is their entire information diet. It must be COMPLETE IN ITSELF - they should never need to open a homepage, a feed, or X. Never tell them to "follow" or "check" anything.

## VOLUME - HARD LIMIT

Exactly 3 reads and exactly 1 listen. Never more. If you found ten good things, pick three. Bloat is the failure mode that kills the habit; a thin brief they actually read beats a rich one they skip.

## CHOOSING THE 3 READS

Priority order:
1. Company & industry deep-dives - how a specific business makes money, unit economics, competitive position, margin structure, why a strategy is working or failing.
2. Deals, M&A & strategy moves - acquisitions, divestitures, spin-offs, restructurings, major pivots.

Reads 1 and 2 come from those two categories. Read 3 alternates between AI/frontier tech and international economics & policy (trade, tariffs, IMF/World Bank/Fed, industrial policy).

Prefer the Wall Street Journal when the story is comparable - it is the single most recommended daily habit in consulting recruiting, especially the macro drop and the op-ed page. Vary industries across the week. The reader has university library access, so paywalls are fine.

## THE LISTEN

Frame the episode as something to drop into a slot they already have - a walk, a lift, a commute - not as extra homework. A three-hour episode is a feature for someone who walks without a phone.

## WRITING EACH ITEM

- "what": one sentence on what it actually says. Concrete, with the number or the name in it. No throat-clearing, no "this article explores".
- "use_it": one sentence on how they deploy it - name the case type, the firm, or the kind of interview question. The right register: "Market-entry case: this is your outside-knowledge drop on tariff exposure." / "Ask a BCG DC contact how the healthcare practice is reading this."

Define any business or finance term a first-year non-business student wouldn't know, inline, in four words or fewer - e.g. "EBITDA (earnings before financing/accounting costs)". No separate glossary.

## INTERNSHIP TRACKER

You are given diffs from consulting firms' application pages. Most changes are noise - cookie banners, rotating testimonials, layout shuffles. Report ONLY genuine recruiting events: a new posting, an opened application, a stated deadline, a new program. If a diff is noise, drop it silently. An empty jobs list is the correct and common answer. Never invent a deadline. If you are not sure a posting is real, say what changed and let them judge, rather than asserting.

## TONE

Direct and peer-level. They are sharp and time-constrained. No hype, no emoji, no exclamation marks, no "dive in", no "in today's fast-moving world", no sign-off. If a story is overhyped, say so. If it was a slow news day, say "slow news day" and use an evergreen deep-dive rather than padding.

Return ONLY a JSON object, no prose around it:
{{
  "subject": "5-9 word hook, no date - the harness adds it",
  "reads": [{{"title": "", "source": "", "url": "", "minutes": 5, "what": "", "use_it": ""}}],
  "listen": {{"title": "", "show": "", "url": "", "runtime": "", "what": "", "use_it": ""}},
  "jobs": [{{"firm": "", "headline": "", "detail": "", "url": "", "urgency": "act now|this week|note"}}],
  "one_line": "One sentence: the sharpest fact they could drop in conversation, or a specific networking prompt tied to a read."
}}"""


def build_system(profile: str) -> str:
    return SYSTEM.format(profile=(profile or "").strip() or GENERIC_PROFILE)


def _payload(bundle, episode, angle, today, programs, network) -> str:
    lines = [f"Today is {today:%A, %B %d, %Y}."]

    lines.append("\n## CANDIDATE READS (last ~30h)\n")
    for item in bundle.items[:110]:
        stamp = item.published.strftime("%m-%d %H:%M") if item.published else "undated"
        lines.append(f"- [{item.track}] {item.title}\n  {item.source} | {stamp} | {item.url}")
        if item.summary:
            lines.append(f"  summary: {item.summary[:300]}")

    lines.append("\n## TODAY'S LISTEN SLOT\n")
    if episode:
        lines.append(f"Show: {episode.source}\nEpisode: {episode.title}\nURL: {episode.url}")
        if episode.published:
            lines.append(f"Published: {episode.published:%Y-%m-%d}")
        if episode.summary:
            lines.append(f"Description: {episode.summary[:900]}")
        if angle:
            lines.append(f"EDITORIAL ANGLE FOR THIS SHOW: {angle}")
    else:
        lines.append("Podcast feed unavailable. Recommend a specific back-catalog episode you are confident exists and mark it [from the archive].")

    if network:
        lines.append(
            "\n## THE READER'S ACTUAL CONNECTIONS AT TARGET FIRMS\n"
            "Use these to make the one_line concrete: name a real person when a story lands in "
            "their firm or practice. Only ever refer to them as written here. Do not invent "
            "anyone, do not guess an office or a practice area that is not in the title, and do "
            "not suggest contacting more than one person in a day.\n"
        )
        by_firm: dict[str, list[str]] = {}
        for person in network:
            by_firm.setdefault(person.get("firm", "?"), []).append(
                f"{person.get('name', '')} ({person.get('title', '')})"
            )
        for firm, people in sorted(by_firm.items()):
            lines.append(f"- {firm} ({len(people)}): " + "; ".join(people[:25]))

    if programs:
        lines.append("\n## PRIORITY PROGRAMS - flag ANY mention of these, even a rumour or a date\n")
        for program in programs:
            lines.append(f"- {program}")

    lines.append("\n## INTERNSHIP PAGE DIFFS\n")
    if not bundle.job_changes:
        lines.append("No application pages changed. Return an empty jobs list.")
    for change in bundle.job_changes:
        if change.first_seen:
            lines.append(f"- {change.label} ({change.firm}): first snapshot taken, no diff yet. Do not report.")
            continue
        lines.append(f"- {change.label} ({change.firm}, {change.priority}) {change.url}\n  NEW TEXT:\n{change.added_text}\n")

    return "\n".join(lines)


def curate(bundle, episode, angle, today, programs=(), network=(), profile="") -> dict:
    """Returns the finished brief, or raises so main.py can fall back to raw."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=os.environ.get("BRIEF_MODEL", "claude-sonnet-5"),
        max_tokens=4000,
        system=build_system(profile),
        messages=[{"role": "user", "content": _payload(bundle, episode, angle, today, programs, network)}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError(f"no JSON in model output: {text[:400]}")
    return json.loads(match.group(0))

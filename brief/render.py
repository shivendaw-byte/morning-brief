"""Turn the curated brief into plain-text and HTML email bodies."""

from __future__ import annotations

import html
import os

# Your library's EZproxy prefix, e.g. "https://proxy.library.example.edu/login?url=".
# Left unset, paywalled items simply render without a proxy link.
PROXY = os.environ.get("BRIEF_PROXY", "")
PAYWALLED = ("wsj.com", "ft.com", "economist.com", "bloomberg.com", "barrons.com")

URGENCY_COLOR = {"act now": "#b3261e", "this week": "#8a6100", "note": "#4a4a4a"}


def _proxy(url: str) -> str | None:
    if not PROXY:
        return None
    return PROXY + url if any(domain in url for domain in PAYWALLED) else None


def render_text(brief: dict, date_label: str, notes: list[str]) -> str:
    out = [f"MORNING BRIEF - {date_label}", ""]

    jobs = brief.get("jobs") or []
    if jobs:
        out.append("APPLICATION TRACKER")
        out.append("")
        for job in jobs:
            out.append(f"[{job.get('urgency', 'note').upper()}] {job.get('firm', '')} - {job.get('headline', '')}")
            if job.get("detail"):
                out.append(f"  {job['detail']}")
            if job.get("url"):
                out.append(f"  {job['url']}")
            out.append("")

    out.append("TODAY'S 3 READS")
    out.append("")
    for i, read in enumerate(brief.get("reads", []), 1):
        out.append(f"{i}. {read.get('title', '')}")
        out.append(f"   {read.get('source', '')} | ~{read.get('minutes', 5)} min")
        if read.get("what"):
            out.append(f"   {read['what']}")
        if read.get("use_it"):
            out.append(f"   -> Use it: {read['use_it']}")
        out.append(f"   {read.get('url', '')}")
        proxied = _proxy(read.get("url", ""))
        if proxied:
            out.append(f"   Library access: {proxied}")
        out.append("")

    listen = brief.get("listen") or {}
    if listen:
        out.append("LISTEN")
        out.append("")
        runtime = f"  ({listen['runtime']})" if listen.get("runtime") else ""
        out.append(f"{listen.get('show', '')} - {listen.get('title', '')}{runtime}")
        if listen.get("what"):
            out.append(f"   {listen['what']}")
        if listen.get("use_it"):
            out.append(f"   -> Use it: {listen['use_it']}")
        out.append(f"   {listen.get('url', '')}")
        out.append("")

    if brief.get("one_line"):
        out.append("ONE LINE")
        out.append("")
        out.append(brief["one_line"])
        out.append("")

    if notes:
        out.append("-" * 40)
        out.append("Build notes: " + " | ".join(notes))

    return "\n".join(out)


def _esc(value) -> str:
    return html.escape(str(value or ""))


def render_html(brief: dict, date_label: str, notes: list[str]) -> str:
    css_head = (
        "font-size:13px;letter-spacing:.09em;text-transform:uppercase;color:#6b6b6b;"
        "border-bottom:1px solid #e0e0e0;padding-bottom:6px;margin:0 0 18px;"
    )
    parts = [
        '<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
        'font-size:15px;line-height:1.55;color:#1a1a1a;max-width:640px;">',
        f'<p style="font-size:12px;color:#8a8a8a;margin:0 0 22px;letter-spacing:.06em;">{_esc(date_label).upper()}</p>',
    ]

    jobs = brief.get("jobs") or []
    if jobs:
        parts.append(f'<h3 style="{css_head}">Application Tracker</h3>')
        for job in jobs:
            urgency = (job.get("urgency") or "note").lower()
            color = URGENCY_COLOR.get(urgency, "#4a4a4a")
            parts.append(
                f'<div style="border-left:3px solid {color};padding:2px 0 2px 12px;margin:0 0 16px;">'
                f'<p style="margin:0 0 4px;"><span style="color:{color};font-size:11px;font-weight:700;'
                f'letter-spacing:.08em;">{_esc(urgency.upper())}</span><br>'
                f'<strong>{_esc(job.get("firm"))}</strong> &mdash; {_esc(job.get("headline"))}</p>'
            )
            if job.get("detail"):
                parts.append(f'<p style="margin:0 0 4px;">{_esc(job["detail"])}</p>')
            if job.get("url"):
                parts.append(f'<p style="margin:0;"><a href="{_esc(job["url"])}">Open the page &rarr;</a></p>')
            parts.append("</div>")

    parts.append(f'<h3 style="{css_head}">Today\'s 3 Reads</h3>')
    for i, read in enumerate(brief.get("reads", []), 1):
        proxied = _proxy(read.get("url", ""))
        extra = f' &nbsp;|&nbsp; <a href="{_esc(proxied)}">Library access</a>' if proxied else ""
        parts.append(
            f'<p style="margin:0 0 6px;"><strong>{i}. {_esc(read.get("title"))}</strong><br>'
            f'<span style="color:#6b6b6b;font-size:13px;">{_esc(read.get("source"))} &middot; ~{_esc(read.get("minutes", 5))} min</span></p>'
            + (f'<p style="margin:0 0 8px;">{_esc(read.get("what"))}</p>' if read.get("what") else "")
            + (f'<p style="margin:0 0 8px;border-left:3px solid #d4d4d4;padding-left:12px;">'
               f'<strong>Use it:</strong> {_esc(read.get("use_it"))}</p>' if read.get("use_it") else "")
            + f'<p style="margin:0 0 26px;"><a href="{_esc(read.get("url"))}">Read it &rarr;</a>{extra}</p>'
        )

    listen = brief.get("listen") or {}
    if listen:
        parts.append(f'<h3 style="{css_head}">Listen</h3>')
        parts.append(
            f'<p style="margin:0 0 6px;"><strong>{_esc(listen.get("show"))} &mdash; {_esc(listen.get("title"))}</strong><br>'
            f'<span style="color:#6b6b6b;font-size:13px;">{_esc(listen.get("runtime"))}</span></p>'
            + (f'<p style="margin:0 0 8px;">{_esc(listen.get("what"))}</p>' if listen.get("what") else "")
            + (f'<p style="margin:0 0 8px;border-left:3px solid #d4d4d4;padding-left:12px;">'
               f'<strong>Use it:</strong> {_esc(listen.get("use_it"))}</p>' if listen.get("use_it") else "")
            + f'<p style="margin:0 0 26px;"><a href="{_esc(listen.get("url"))}">Listen &rarr;</a></p>'
        )

    if brief.get("one_line"):
        parts.append(f'<h3 style="{css_head}">One Line</h3>')
        parts.append(f'<p style="margin:0 0 20px;">{_esc(brief["one_line"])}</p>')

    if notes:
        parts.append(
            '<p style="margin:24px 0 0;padding-top:12px;border-top:1px solid #eee;'
            f'font-size:11px;color:#9a9a9a;">{_esc(" | ".join(notes))}</p>'
        )

    parts.append("</div>")
    return "".join(parts)


def render_raw_fallback(bundle, episode, date_label: str, reason: str) -> tuple[str, str]:
    """Used when curation fails. He still gets an email - that is the whole point."""
    ranked = sorted(
        bundle.items,
        key=lambda i: (i.track not in ("deals", "business"), -(i.published.timestamp() if i.published else 0)),
    )[:12]

    text = [f"MORNING BRIEF - {date_label}  [RAW]", "",
            "Curation failed, so this is the unfiltered haul. Reason: " + reason, "",
            "TOP ITEMS", ""]
    body = ['<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;max-width:640px;">',
            f'<p style="color:#b3261e;font-size:13px;">Curation failed, so this is the unfiltered haul. Reason: {_esc(reason)}</p><ul>']
    for item in ranked:
        text.append(f"- [{item.track}] {item.title}\n  {item.source} | {item.url}")
        body.append(f'<li style="margin-bottom:10px;"><a href="{_esc(item.url)}">{_esc(item.title)}</a><br>'
                    f'<span style="color:#6b6b6b;font-size:13px;">{_esc(item.source)}</span></li>')
    body.append("</ul>")

    if episode:
        text += ["", "LISTEN", f"{episode.source} - {episode.title}", episode.url]
        body.append(f'<p><strong>Listen:</strong> <a href="{_esc(episode.url)}">{_esc(episode.source)} &mdash; {_esc(episode.title)}</a></p>')

    if bundle.job_changes:
        text += ["", "APPLICATION PAGES THAT CHANGED"]
        body.append("<p><strong>Application pages that changed:</strong></p><ul>")
        for change in bundle.job_changes:
            if change.first_seen:
                continue
            text.append(f"- {change.label} -> {change.url}")
            body.append(f'<li><a href="{_esc(change.url)}">{_esc(change.label)}</a></li>')
        body.append("</ul>")

    body.append("</div>")
    return "\n".join(text), "".join(body)

# Morning Brief

A daily 6:30am ET email: **3 reads + 1 listen + an internship application tracker**, assembled from yesterday's news so there's no reason to open a news app or a feed.

Runs entirely on GitHub Actions. Nothing needs to be open on your machine.

---

## What it does each morning

1. Pulls ~14 news feeds and 7 podcast feeds covering the last 30 hours.
2. Fetches 10 consulting career pages, diffs them against yesterday's snapshot, and flags genuine new postings or deadlines.
3. Hands the whole haul to Claude, which picks **exactly 3 reads and 1 listen** and writes a "Use it:" line for each — how to deploy it in a case, an interview, or a networking call.
4. Emails it to you over Gmail SMTP.
5. Commits the new state back to the repo so tomorrow knows what you've already seen.

Reads weight toward company/industry deep-dives and M&A. The listen rotates by weekday:

| Day | Show |
|---|---|
| Mon | Acquired |
| Tue | All-In |
| Wed | Huberman Lab — mechanism episodes, not protocol listicles |
| Thu | Odd Lots |
| Fri | The Moth, falling back to This American Life |
| Sat | On Purpose with Jay Shetty — purpose/relationships lane only |
| Sun | Acquired long-form |

---

## Setup

### 1. Push this to a GitHub repo

```bash
gh repo create morning-brief --public --source . --push
```

### 2. Add your secrets

Repo → Settings → Secrets and variables → Actions.

**Secrets** (never visible, even though this repo is public):

| Secret | Where it comes from |
|---|---|
| `GMAIL_ADDRESS` | your Gmail address |
| `GMAIL_APP_PASSWORD` | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) — requires 2-Step Verification. **Not** your normal password |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API keys |
| `BRIEF_PROFILE` | who you are, what you're recruiting for, which programs to watch. See below |
| `BRIEF_NETWORK` | optional; your contacts at target firms. See below |

**Variables** (optional): `BRIEF_TO` (defaults to `GMAIL_ADDRESS`), `BRIEF_MODEL` (defaults to `claude-sonnet-5`), `BRIEF_PROXY` (your library's EZproxy prefix, e.g. `https://proxy.library.example.edu/login?url=` — unset means no proxy links).

#### Why nothing personal is in this repo

The code is public; you are not. Write your profile to `config/profile.md` — background, target firms, cases you've run, interests, programs to watch — and push it as a secret:

```bash
gh secret set BRIEF_PROFILE < config/profile.md
```

Without it the brief still runs, just generically. `config/profile.md` is gitignored.

For contact-aware networking prompts, point `build_network.py` at a LinkedIn connections export:

```bash
python tools/build_network.py "path/to/Connections.csv"
gh secret set BRIEF_NETWORK < config/network.json
```

It keeps only people at target consulting firms, and only first name + last initial + firm + title — no emails, no URLs, no surnames. `config/network.json` is gitignored and reaches Actions **only** as a secret. Don't commit it, and don't widen what it stores: those are real people who didn't opt into being in your repo.

### 3. Test it

Actions → Morning Brief → **Run workflow**, with `dry_run` checked. That builds the brief and uploads it as an artifact without emailing. Uncheck to send for real.

---

## Cost

One Claude call a day on Sonnet, roughly 20-30k input tokens. Cents per day. GitHub Actions minutes are free on public repos.

---

## Guarantees and limits

**An email goes out every morning, no matter what.** Feed failures, scraper failures and model failures all degrade the brief — none of them cancel it. If curation fails entirely you get a `[raw]` edition with the unfiltered haul and the reason. Only a mail-transport failure fails the run.

**Timing.** Two crons fire (10:30 and 11:30 UTC) so 6:30am ET holds across daylight saving; a once-per-day guard in `main.py` means only the first one sends. GitHub's scheduler is best-effort and often runs 5–20 minutes late. If you need the email at exactly 6:30, this is the wrong platform.

**The application tracker is a safety net, not a system of record.** Verified 2026-08-09: BCG and McKinsey serve their careers sites as JavaScript applications, so plain HTTP gets a shell instead of listings, and McKinsey's edge resets the connection outright. Page-diffing works well on Bain, Cornerstone, Analysis Group, Bates White, Oliver Wyman, Deloitte and L.E.K. For BCG and McKinsey the Google News queries in `config/jobs.yml` are the actual coverage. **Check those two portals yourself during application season.**

---

## Maintenance

```bash
python tools/verify_sources.py     # which feeds and career pages are alive
python tools/render_smoke.py       # render a synthetic brief, no API key needed
python -m brief.main --dry-run --force   # full pipeline, writes out/ instead of emailing
```

Feeds rot. Run `verify_sources.py` every couple of months. To find a podcast's real feed after it moves, `tools/resolve_feed.py` looks it up from its Apple Podcasts ID.

Editorial voice lives in the `SYSTEM` prompt in `brief/curate.py` — that's the file to edit when the brief doesn't sound right.

## Layout

```
.github/workflows/morning-brief.yml   schedule, secrets, state commit
brief/collect.py                      RSS + career-page diffing
brief/curate.py                       the editorial prompt
brief/render.py                       HTML + plain text, and the raw fallback
brief/mailer.py                       Gmail SMTP
brief/main.py                         orchestration, once-per-day guard
config/feeds.yml                      news + podcast sources
config/jobs.yml                       tracked firms
state/                                seen articles, page snapshots (bot-committed)
```

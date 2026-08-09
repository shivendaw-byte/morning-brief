"""Render a synthetic brief so the happy path is exercised without an API key."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from brief import render  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

SAMPLE = {
    "subject": "Record margins and a $6bn telecom exit",
    "reads": [
        {
            "title": "The Efficiency Era Pushes S&P 500 Margins Past 13%",
            "source": "Wall Street Journal",
            "url": "https://www.wsj.com/finance/example-margins",
            "minutes": 5,
            "what": "Net margins (profit per dollar of sales) hit a record 13%, and the gains are finally broadening past big tech into industrials and consumer names.",
            "use_it": "Profitability case: this is your evidence that margin gains are coming from operating leverage, not pricing - the distinction interviewers actually listen for.",
        },
        {
            "title": "e& Sells Its Entire Vodafone Stake for $5.95bn",
            "source": "Financial Times",
            "url": "https://www.ft.com/content/example-vodafone",
            "minutes": 4,
            "what": "e& called the 16.2% stake non-core after a portfolio review and sold to Xavier Niel's Vega vehicle at a ~13% premium.",
            "use_it": "A divestiture case in miniature. Good opener with a BCG DC contact on how they read European telecom consolidation.",
        },
        {
            "title": "Tariff Volatility Is Now the Top Regulatory Risk",
            "source": "Reuters",
            "url": "https://www.reuters.com/business/example-tariffs",
            "minutes": 6,
            "what": "72% of trade professionals name US tariff volatility their biggest regulatory change, up from 41% a year ago; Hasbro alone booked $17.7M of tariff cost in H1.",
            "use_it": "Market-entry case: this is your outside-knowledge drop, with a number attached.",
        },
    ],
    "listen": {
        "title": "The Walt Disney Company",
        "show": "Acquired",
        "url": "https://www.acquired.fm/episodes/disney",
        "runtime": "4h 12m",
        "what": "How Disney turned nostalgia into the most durable IP monetisation machine ever built, across parks, film and streaming.",
        "use_it": "Sunday long-form. Gives you a full vocabulary for talking about IP economics and vertical integration.",
    },
    "jobs": [
        {
            "firm": "BCG",
            "headline": "Sophomore Summer 2027 program page went live",
            "detail": "New section listing a DC office option. No deadline stated yet.",
            "url": "https://careers.bcg.com/early-careers",
            "urgency": "act now",
        },
        {
            "firm": "Analysis Group",
            "headline": "Summer analyst posting added",
            "detail": "Boston and DC listed. Applications appear to open in September.",
            "url": "https://www.analysisgroup.com/careers/",
            "urgency": "note",
        },
    ],
    "one_line": "Ask a BCG DC contact how the TMT practice is reading European telecom consolidation now that one investor group sits across iliad, Vodafone and Millicom.",
}


def main() -> int:
    notes = ["1 source(s) unreachable"]
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    (out / "sample.html").write_text(render.render_html(SAMPLE, "Sunday, August 9", notes), encoding="utf-8")
    text = render.render_text(SAMPLE, "Sunday, August 9", notes)
    (out / "sample.txt").write_text(text, encoding="utf-8")
    print(text)
    print("\n--- wrote", out / "sample.html", "---")
    return 0


if __name__ == "__main__":
    sys.exit(main())

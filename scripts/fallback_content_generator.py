"""
Fallback Content Generator — Watchdog API-Based Fallback

Runs in GitHub Actions when Cowork fails to deliver daily content.
Generates 2-3 Substack notes + 3-5 tweets using Claude API (Sonnet).

Skips: long-form posts, animated diagrams, carousels.
These require Cowork's full context window and sequential prompting.

Usage:
    python3 scripts/fallback_content_generator.py           # Full run
    python3 scripts/fallback_content_generator.py --dry-run  # Preview only
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.output_paths import SUBSTACK_OUTPUT, COWORK_QUEUE_FILE
from config.banned_terms import validate_content
from substack.constants import NOTE_TYPE_MATRIX

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

MODEL = "claude-sonnet-4-20250514"
PORTFOLIO_CSV = ROOT / "portfolio" / "output" / "portfolio.csv"
SIGNALS_JSON = ROOT / "scanner" / "output" / "signals.json"
EQUITY_CSV = ROOT / "portfolio" / "output" / "equity_curve.csv"

NOTES_DIR = SUBSTACK_OUTPUT / "current" / "notes"
MANIFEST_PATH = SUBSTACK_OUTPUT / "current" / "daily_manifest.json"

TIME_LABEL_MAP = {
    "08:30 ET": "morning",
    "12:30 ET": "midday",
    "17:00 ET": "evening",
}

NOTE_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body>
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; color: #1a1a1a; line-height: 1.6; font-size: 16px;">
{content}
<p style="color: #6b6b6b; font-size: 13px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #e0ddd8;">Not financial advice. Informational only.</p>
</div>
</body>
</html>"""

NOTE_SYSTEM_PROMPT = """You are the content engine for Sterling Signals, a momentum trading newsletter targeting US active investors and swing traders.

VOICE: Decisive, data-first, short sentences, contractions OK. No AI filler ("let's dive in", "here's the thing", "interestingly"). Write like a sharp analyst briefing a trading desk.

BANNED TERMS (never use): HMA, RSI, MACD, KDJ, Banker, Undercurrent, UC, trailing stop, profit lock, BoS, Break of Structure, ExD, Gatekeeper, Investment Gate, conviction score, tier 1/2/3, UK ISA, GMT, BST.

APPROVED ALTERNATIVES:
- "Institutional Accumulation Divergence" (for Banker/UC)
- "Structural Pivot Confirmation" (for HMA/BoS)
- "Capital Preservation Protocol" (for trailing stop)
- "Systematic exit discipline" (for exits)
- "Cleared all gates" (for Gatekeeper)
- "Our 5-gate screening system" (for the scanner)

SIGNAL COLOURS: GREEN = buy, RED = exit, CONSIDER = watchlist.

CRITICAL: Do NOT quote specific current prices — the data may be several days old. Reference themes, positions, and system metrics instead. Lead with a specific data point or number.

OUTPUT: Write 150-280 words of flowing HTML paragraphs (no headers, no bullet lists). Use <b>$TICKER</b> for bold tickers. Use <br><br> between paragraphs. Do NOT include the outer template div or footer — just the inner content paragraphs."""

TWEET_SYSTEM_PROMPT = """You are the social media engine for Sterling Signals, a momentum trading newsletter.

VOICE: Sharp, data-driven, no fluff. Each tweet must stand alone as valuable content.

RULES:
- Each tweet MUST be ≤ 280 characters
- Use $TICKER format for stock references
- BANNED: HMA, RSI, MACD, Banker, trailing stop, conviction score, tier 1/2/3, UK ISA, GMT
- Use: "institutional accumulation", "structural pivot", "cleared all gates", "capital preservation"
- Signal colours: GREEN = buy, RED = exit
- Do NOT quote specific current prices — data may be stale
- No hashtags unless they're a ticker ($AAPL)
- No emojis except signal indicators

CATEGORIES (pick the best fit for each tweet):
- SIGNAL_ALERT: Scanner signal detected
- RECEIPT: Portfolio win showcase
- MARKET_COMMENTARY: Market conditions
- THEME_CATALYST: Breaking theme catalyst
- EDUCATIONAL: Trading methodology lessons
- SUBSTACK_TEASER: Today's note topic teaser
- ENGAGEMENT: Community question or discussion

ACCOUNTS (assign each tweet to the best-fit persona):
- variant_1 (Alex/Analyst): SIGNAL_ALERT, RECEIPT, TECHNICAL_ANALYSIS
- variant_2 (Rozalia/Teacher): EDUCATIONAL, THEME_CATALYST, SUBSTACK_TEASER
- variant_3 (James/Trader): MARKET_COMMENTARY, RECEIPT, ENGAGEMENT

Return ONLY a JSON array. Each object must have exactly these keys:
  "text": the tweet text (≤280 chars),
  "category": one of the categories above,
  "account": "variant_1" or "variant_2" or "variant_3"
"""


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════


def load_data() -> dict:
    """Load portfolio, signals, and equity data from repo files.

    Returns dict with portfolio_summary, signals_summary, equity_summary strings,
    plus raw data for manifest/tweet generation.
    Gracefully handles missing files.
    """
    data = {
        "portfolio_summary": "No portfolio data available.",
        "signals_summary": "No scanner signals available.",
        "equity_summary": "No equity curve data available.",
        "open_positions": [],
        "themes": [],
        "buy_signals": [],
        "exit_signals": [],
    }

    # Portfolio
    if PORTFOLIO_CSV.exists():
        try:
            with open(PORTFOLIO_CSV) as f:
                positions = list(csv.DictReader(f))
            open_pos = [p for p in positions if p.get("status") == "OPEN"]
            data["open_positions"] = open_pos
            if open_pos:
                lines = [
                    f"  {p['ticker']}: entry ${p.get('entry_price', '?')}, "
                    f"theme: {p.get('theme', 'N/A')}"
                    for p in open_pos
                ]
                data["portfolio_summary"] = (
                    f"{len(open_pos)} open positions:\n" + "\n".join(lines)
                )
        except Exception as e:
            print(f"  Warning: Could not load portfolio.csv: {e}")

    # Signals
    if SIGNALS_JSON.exists():
        try:
            with open(SIGNALS_JSON) as f:
                signals = json.load(f)
            themes = signals.get("themes", [])
            buys = signals.get("buy_signals", [])
            exits = signals.get("exit_signals", [])
            data["themes"] = themes
            data["buy_signals"] = buys
            data["exit_signals"] = exits

            parts = []
            if themes:
                theme_names = [
                    f"{t['name']} ({t.get('classification', '?')})"
                    for t in themes[:5]
                ]
                parts.append("Themes: " + ", ".join(theme_names))
            if buys:
                buy_tickers = [b.get("symbol", "?") for b in buys[:5]]
                parts.append(f"Buy signals: {', '.join(buy_tickers)}")
            if exits:
                exit_tickers = [e.get("symbol", "?") for e in exits[:5]]
                parts.append(f"Exit signals: {', '.join(exit_tickers)}")
            context = signals.get("market_context_summary", "")
            if context:
                parts.append(f"Market context: {context[:200]}")
            if parts:
                data["signals_summary"] = "\n".join(parts)
        except Exception as e:
            print(f"  Warning: Could not load signals.json: {e}")

    # Equity curve
    if EQUITY_CSV.exists():
        try:
            with open(EQUITY_CSV) as f:
                rows = list(csv.DictReader(f))
            if rows:
                latest = rows[-1]
                data["equity_summary"] = (
                    f"NAV: ${float(latest.get('nav', 0)):,.0f}, "
                    f"Return: {latest.get('total_return_pct', '?')}%, "
                    f"SPY: {latest.get('spy_return_pct', '?')}%, "
                    f"Alpha: {latest.get('alpha_pct', '?')}%"
                )
        except Exception as e:
            print(f"  Warning: Could not load equity_curve.csv: {e}")

    return data


def build_context_string(data: dict) -> str:
    """Build a combined context string for LLM prompts."""
    return (
        f"Portfolio:\n{data['portfolio_summary']}\n\n"
        f"Scanner:\n{data['signals_summary']}\n\n"
        f"Performance:\n{data['equity_summary']}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# NOTE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════


def get_note_slots(day: str) -> list:
    """Get today's note slots from NOTE_TYPE_MATRIX.

    Returns list of dicts with slot, type, time, time_label.
    """
    slots = NOTE_TYPE_MATRIX.get(day, [])
    result = []
    for s in slots:
        time_str = s.get("time", "08:30 ET")
        result.append({
            "slot": s["slot"],
            "type": s["type"],
            "time_et": time_str.replace(" ET", ""),
            "time_label": TIME_LABEL_MAP.get(time_str, "morning"),
        })
    return result


def extract_html_content(response_text: str) -> str:
    """Extract inner HTML content from LLM response.

    Strips any outer template wrapper if the LLM included it.
    Returns just the paragraph content.
    """
    text = response_text.strip()

    # If LLM returned full HTML doc, extract just the div content
    match = re.search(
        r'<div[^>]*style="[^"]*max-width:\s*680px[^"]*"[^>]*>(.*?)</div>\s*</body>',
        text,
        re.DOTALL,
    )
    if match:
        inner = match.group(1).strip()
        # Remove the footer if included
        inner = re.sub(
            r'<p[^>]*>Not financial advice\..*?</p>',
            '',
            inner,
            flags=re.DOTALL,
        ).strip()
        return inner

    # If LLM returned just paragraphs, use as-is
    # Strip any leading/trailing code fences
    text = re.sub(r'^```html?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def generate_note(
    client, note_type: str, day: str, context: str, date_str: str
) -> tuple:
    """Generate a single note via API call.

    Returns (html_content, cost_usd) or (None, 0) on failure.
    """
    user_prompt = (
        f"Generate a {note_type} note for {day.capitalize()}.\n\n"
        f"{context}\n\n"
        f"Write the note as inner HTML paragraphs (150-280 words). "
        f"Lead with a specific data point or number from the context."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=NOTE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        print(f"    API error for {note_type}: {e}")
        return None, 0.0

    raw = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw += block.text

    cost = (
        response.usage.input_tokens * 3.0 / 1_000_000
        + response.usage.output_tokens * 15.0 / 1_000_000
    )

    inner_html = extract_html_content(raw)
    full_html = NOTE_HTML_TEMPLATE.format(content=inner_html)

    # Validate against banned terms
    is_valid, violations = validate_content(full_html)
    if not is_valid:
        print(f"    Warning: {note_type} has banned terms: {violations[:3]}")

    return full_html, cost


def generate_notes(client, day: str, context: str, date_str: str, dry_run: bool) -> list:
    """Generate all notes for today.

    Returns list of note metadata dicts for manifests.
    """
    slots = get_note_slots(day)
    if not slots:
        print(f"  No note slots defined for {day}")
        return []

    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    notes_meta = []
    total_cost = 0.0

    for slot_info in slots:
        note_type = slot_info["type"]
        time_label = slot_info["time_label"]
        filename = f"{time_label}_{note_type.lower()}_{date_str}.html"
        filepath = NOTES_DIR / filename

        print(f"  [{slot_info['slot']}] {note_type} ({time_label})...", end=" ")

        if dry_run:
            print("SKIPPED (dry run)")
            notes_meta.append({
                "slot": slot_info["slot"],
                "type": note_type,
                "time_et": slot_info["time_et"],
                "time_label": time_label,
                "file": f"notes/{filename}",
                "filepath": filename,
            })
            continue

        html, cost = generate_note(client, note_type, day, context, date_str)
        total_cost += cost

        if html:
            filepath.write_text(html, encoding="utf-8")
            print(f"OK ({len(html)} bytes, ${cost:.4f})")
        else:
            print("FAILED")
            continue

        notes_meta.append({
            "slot": slot_info["slot"],
            "type": note_type,
            "time_et": slot_info["time_et"],
            "time_label": time_label,
            "file": f"notes/{filename}",
            "filepath": filename,
        })

    print(f"\n  Notes cost: ${total_cost:.4f}")
    return notes_meta


# ═══════════════════════════════════════════════════════════════════════════════
# TWEET GENERATION
# ═══════════════════════════════════════════════════════════════════════════════


def generate_tweets(client, day: str, context: str, date_str: str, dry_run: bool) -> int:
    """Generate 3-5 tweets and write to cowork queue.

    Returns number of tweets generated.
    """
    if dry_run:
        print("  Tweets: SKIPPED (dry run)")
        return 0

    user_prompt = (
        f"Generate 3-5 tweets for {day.capitalize()}.\n\n"
        f"{context}\n\n"
        f"Return ONLY a JSON array — no markdown fences, no explanation. "
        f"Each tweet must be ≤ 280 characters. Spread tweets across all 3 accounts."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=TWEET_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        print(f"  Tweet generation API error: {e}")
        return 0

    raw = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw += block.text

    cost = (
        response.usage.input_tokens * 3.0 / 1_000_000
        + response.usage.output_tokens * 15.0 / 1_000_000
    )

    # Parse JSON from response (strip code fences if present)
    cleaned = re.sub(r'^```json?\s*', '', raw.strip())
    cleaned = re.sub(r'\s*```$', '', cleaned)

    try:
        tweets_raw = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try extracting JSON array from response
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            try:
                tweets_raw = json.loads(match.group())
            except json.JSONDecodeError:
                print(f"  Could not parse tweet JSON from response")
                return 0
        else:
            print(f"  No JSON array found in tweet response")
            return 0

    if not isinstance(tweets_raw, list):
        print(f"  Tweet response is not a list")
        return 0

    now_iso = datetime.now(timezone.utc).isoformat()

    # Build queue items
    queue_items = []
    for i, tweet in enumerate(tweets_raw[:5], 1):
        text = tweet.get("text", "").strip()
        if not text or len(text) > 280:
            continue

        # Validate banned terms
        is_valid, violations = validate_content(text)
        if not is_valid:
            print(f"    Tweet {i} has banned terms: {violations[:2]} — skipping")
            continue

        # Extract primary ticker
        ticker_match = re.search(r'\$([A-Z]{2,5})', text)
        primary_ticker = f"${ticker_match.group(1)}" if ticker_match else None

        queue_items.append({
            "id": f"watchdog_{date_str}_{i:03d}",
            "text": text,
            "category": tweet.get("category", "MARKET_COMMENTARY"),
            "account": tweet.get("account", "variant_1"),
            "ticker": primary_ticker,
            "thread": False,
            "status": "pending",
            "created_at": now_iso,
            "source": "watchdog",
        })

    if not queue_items:
        print(f"  No valid tweets generated")
        return 0

    # Write to cowork queue (replace — watchdog owns the queue when it runs)
    COWORK_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(COWORK_QUEUE_FILE, "w") as f:
        json.dump(queue_items, f, indent=2)

    print(f"  Tweets: {len(queue_items)} written to cowork queue (${cost:.4f})")
    return len(queue_items)


# ═══════════════════════════════════════════════════════════════════════════════
# MANIFESTS
# ═══════════════════════════════════════════════════════════════════════════════


def write_manifests(
    day: str, date_str: str, notes_meta: list, tweet_count: int
) -> None:
    """Write daily_manifest.json and notes/notes_manifest.json."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Daily manifest
    manifest = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "day": day,
        "generated_at": now_iso,
        "source": "watchdog_fallback",
        "decision_reason": "Cowork missed — watchdog fallback ran",
        "post": {"category": "none", "file": None, "title": None},
        "notes": [
            {
                "slot": n["slot"],
                "type": n["type"],
                "time_et": n["time_et"],
                "time_label": n["time_label"],
                "file": n["file"],
            }
            for n in notes_meta
        ],
        "visual": {"type": "none", "file": None},
        "tweets_generated": tweet_count,
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Manifest: {MANIFEST_PATH}")

    # Notes manifest
    notes_manifest = {
        "generated_at": now_iso,
        "target_date": date_str.replace("", "-") if len(date_str) == 8 else date_str,
        "day": day,
        "notes": [
            {
                "slot": n["slot"],
                "type": n["type"],
                "time_et": n["time_et"],
                "time_label": n["time_label"],
                "filepath": n.get("filepath", ""),
            }
            for n in notes_meta
        ],
    }

    notes_manifest_path = NOTES_DIR / "notes_manifest.json"
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(notes_manifest_path, "w") as f:
        json.dump(notes_manifest, f, indent=2)
    print(f"  Notes manifest: {notes_manifest_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="Watchdog fallback content generator")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load data and print plan without making API calls",
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    day = now.strftime("%A").lower()
    date_str = now.strftime("%Y%m%d")

    print("=" * 70)
    print("  WATCHDOG FALLBACK CONTENT GENERATOR")
    print(f"  Date: {now.strftime('%Y-%m-%d')} ({day.capitalize()})")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 70)

    # Load data
    print("\n  Loading data...")
    data = load_data()
    context = build_context_string(data)

    print(f"  Portfolio: {len(data['open_positions'])} open positions")
    print(f"  Themes: {len(data['themes'])} tracked")
    print(f"  Buy signals: {len(data['buy_signals'])}")
    print(f"  Exit signals: {len(data['exit_signals'])}")

    # Note slots
    slots = get_note_slots(day)
    print(f"\n  Note slots for {day}: {len(slots)}")
    for s in slots:
        print(f"    Slot {s['slot']}: {s['type']} @ {s['time_et']}")

    if args.dry_run:
        print("\n  DRY RUN — no API calls, no file writes")
        print(f"\n  Context preview:\n{context[:500]}...")
        print("\n  Done (dry run)")
        return

    # Initialize API client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n  ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    # Generate notes
    print("\n  Generating notes...")
    notes_meta = generate_notes(client, day, context, date_str, args.dry_run)

    # Generate tweets
    print("\n  Generating tweets...")
    tweet_count = generate_tweets(client, day, context, date_str, args.dry_run)

    # Write manifests
    print("\n  Writing manifests...")
    write_manifests(day, date_str, notes_meta, tweet_count)

    # Summary
    print("\n" + "=" * 70)
    print(f"  COMPLETE: {len(notes_meta)} notes, {tweet_count} tweets")
    print(f"  Source: watchdog_fallback")
    print("=" * 70)


if __name__ == "__main__":
    main()

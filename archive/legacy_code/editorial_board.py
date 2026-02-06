#!/usr/bin/env python3
"""
Editorial Board - Plans content allocation across all 3 accounts.

Runs ONCE per day, outputs topic assignments for all 15 slots (5 per account).
This prevents same-slot collisions, ticker over-mention, and repetitive content
by coordinating at the planning stage rather than relying on post-hoc fixes.
"""

import json
import re
from typing import Optional

EDITORIAL_BOARD_PROMPT = """You are the Managing Editor for Sterling Signals, a trading newsletter with 3 Twitter accounts.
Your job is to PLAN (not write) the content for all 3 accounts for {day_name}.

THE ACCOUNTS:
1. ALEX (Main): Dry, data-driven, skeptical of hype. The system voice.
2. ROZALIA (Mentor): Warm, educational, patient with beginners. The teacher.
3. JAMES (Trader): High-energy, real-time feel, sports metaphors. The practitioner.

THE TIME SLOTS (Eastern Time):
- Slot 1 (8am): Morning prep / reflective
- Slot 2 (10am): Market open energy on weekdays / casual on weekends
- Slot 3 (12:30pm): Midday check-in, engagement questions work well
- Slot 4 (3:30pm): Power hour on weekdays / general reflection on weekends
- Slot 5 (6pm): End of day, newsletter CTAs, looking ahead

CONTENT CATEGORIES (distribute across slots):
- scanner_result: New signals WITH TICKERS AND PRICES, gate analysis
- performance: Portfolio winners with receipts (entry → current, % gain)
- theme_analysis: Hot/cold sectors WITH ALL TICKERS in the theme
- educational: Teaching moments using SPECIFIC EXAMPLES ($TICKER did X)
- engagement: Questions to followers, observations that invite replies
- watchlist: Stocks being monitored WITH PRICES and what's missing
- newsletter_cta: Drive newsletter signups (EXACTLY 2 per account)
- process: Trading discipline WITH PROOF (not vague platitudes)

{content_phase_guidance}

FINTWIT RULES (CRITICAL — enforce these in assignments):
- Every scanner_result and theme_analysis assignment MUST include tickers
- Every performance assignment MUST reference a specific winner
- NEVER assign "generic system trust" or "vague theme talk" — always include data
- Banned topics: loser-focused content, "still bleeding", "quality over quantity"

COORDINATION RULES (CRITICAL):
1. NO SAME-SLOT COLLISIONS: If Alex mentions $AMPX in slot 2, Rozalia and James must NOT mention $AMPX in slot 2
2. TICKER BUDGET: Each ticker can appear in MAX {ticker_max_per_day} slots total across ALL 3 accounts for the day
3. TOP WINNER QUOTA: {top_winner_ticker} is the biggest winner — mention it in MAX 2 slots total across all accounts
4. CATEGORY VARIETY: Each account needs at least 3 different categories across their 5 slots
5. NEWSLETTER CTA: Exactly 2 of each account's 5 slots should include the newsletter URL
6. PERSONA FIT: Assign topics that match each persona's strengths:
   - Alex: scanner_result, theme_analysis, performance (data angle)
   - Rozalia: educational, process, engagement (teaching angle)
   - James: watchlist, performance (energy angle), scanner_result (reaction angle)

{temporal_rules}

{weekend_rules}

{week_context}

TODAY'S DATA BRIEFING:
{morning_briefing}

OUTPUT FORMAT — Return ONLY this JSON, no explanation:
{{
  "Alex": {{
    "slot_1": {{"category": "...", "topic": "one-sentence instruction for the writer", "tickers": ["TICK"], "include_url": false, "attach_chart": false}},
    "slot_2": {{"category": "...", "topic": "...", "tickers": [], "include_url": true, "attach_chart": false}},
    "slot_3": {{"category": "...", "topic": "...", "tickers": [], "include_url": false, "attach_chart": false}},
    "slot_4": {{"category": "...", "topic": "...", "tickers": [], "include_url": false, "attach_chart": false}},
    "slot_5": {{"category": "...", "topic": "...", "tickers": [], "include_url": true, "attach_chart": false}}
  }},
  "Rozalia": {{
    "slot_1": {{"category": "...", "topic": "...", "tickers": [], "include_url": false, "attach_chart": false}},
    "slot_2": {{"category": "...", "topic": "...", "tickers": [], "include_url": true, "attach_chart": false}},
    "slot_3": {{"category": "...", "topic": "...", "tickers": [], "include_url": false, "attach_chart": false}},
    "slot_4": {{"category": "...", "topic": "...", "tickers": [], "include_url": false, "attach_chart": false}},
    "slot_5": {{"category": "...", "topic": "...", "tickers": [], "include_url": true, "attach_chart": false}}
  }},
  "James": {{
    "slot_1": {{"category": "...", "topic": "...", "tickers": [], "include_url": false, "attach_chart": false}},
    "slot_2": {{"category": "...", "topic": "...", "tickers": [], "include_url": true, "attach_chart": false}},
    "slot_3": {{"category": "...", "topic": "...", "tickers": [], "include_url": false, "attach_chart": false}},
    "slot_4": {{"category": "...", "topic": "...", "tickers": [], "include_url": false, "attach_chart": false}},
    "slot_5": {{"category": "...", "topic": "...", "tickers": [], "include_url": true, "attach_chart": false}}
  }}
}}
"""


def create_editorial_plan(
    client,
    morning_briefing: str,
    day_name: str,
    market_ctx,
    week_tracker: dict = None,
) -> dict:
    """
    Generate the content plan for all accounts for one day.

    Returns dict with keys 'Alex', 'Rozalia', 'James', each containing
    slot_1 through slot_5 assignments.
    """

    is_weekend = day_name in ['Saturday', 'Sunday']

    weekend_rules = ""
    if is_weekend:
        weekend_rules = """WEEKEND RULES:
- NO "power hour", "into the close", "watching the tape live" — markets are CLOSED
- Focus on reflection, education, prep for the week
- More engagement questions work well on weekends
- James can reference Friday's action but not as if it's happening now"""
    else:
        weekend_rules = """WEEKDAY RULES:
- Slot 4 is POWER HOUR (3:30pm) — James should own this energy
- Real-time market references are appropriate on weekdays
- Alex can comment on price action during market hours"""

    # Temporal rules
    temporal_map = {
        'Saturday': 'Say "Friday\'s close" or "Friday\'s scan". NEVER "yesterday" for market data (Saturday\'s yesterday is Friday, which is acceptable only on Saturday).',
        'Sunday': 'Say "Friday\'s scan" or "this weekend". NEVER "yesterday" (that\'s Saturday, not a market day).',
        'Monday': 'Say "last Friday" or "Friday\'s scan". NEVER "yesterday" (that\'s Sunday).',
        'Tuesday': 'Say "Friday\'s close" or "this week\'s scan". NEVER "yesterday" for Friday data.',
        'Wednesday': 'Say "this week\'s scan" or "earlier this week". NEVER "yesterday" for Friday data.',
        'Thursday': 'Say "this week" for scan data. NEVER "yesterday" for Friday data.',
        'Friday': 'Say "today\'s close" or "tonight\'s scan". All temporal references valid.',
    }
    temporal_rules = f"TEMPORAL RULES FOR {day_name}:\n{temporal_map.get(day_name, '')}"

    # Top winner
    top_winner = market_ctx.winners[0]['ticker'] if market_ctx.winners else 'N/A'

    # Week context from tracker
    week_context = ""
    if week_tracker:
        featured = week_tracker.get('tickers_featured', {})
        if featured:
            over = [f"${t} ({c}x)" for t, c in featured.items() if c >= 2]
            if over:
                week_context = f"ALREADY HEAVILY FEATURED THIS WEEK: {', '.join(over)} — use sparingly today."

    # Determine per-day ticker budget (tighter later in week)
    day_idx = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'].index(day_name)
    ticker_max = 3 if day_idx <= 2 else 2

    # Content phase guidance
    content_phase = getattr(market_ctx, 'content_phase', 'EARLY')
    phase_guides = {
        'EARLY': "CONTENT PHASE: EARLY — Focus on scanner results (WITH PRICES), educational, theme exploration with tickers. No fabricated performance.",
        'BUILDING': "CONTENT PHASE: BUILDING — Positions are green. Show momentum with numbers. Mix new signals with green position updates.",
        'ESTABLISHED': "CONTENT PHASE: ESTABLISHED — 25%+ winners exist. Lead with receipts. Show entry→current. Quote past calls.",
    }
    content_phase_guidance = phase_guides.get(content_phase, phase_guides['EARLY'])

    prompt = EDITORIAL_BOARD_PROMPT.format(
        day_name=day_name,
        morning_briefing=morning_briefing,
        top_winner_ticker=f"${top_winner}",
        weekend_rules=weekend_rules,
        temporal_rules=temporal_rules,
        week_context=week_context,
        ticker_max_per_day=ticker_max,
        content_phase_guidance=content_phase_guidance,
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        plan_text = response.content[0].text.strip()
        return _parse_editorial_json(plan_text)

    except Exception as e:
        print(f"  ❌ Editorial Board failed: {e}")
        return _fallback_plan(day_name, market_ctx)


def _parse_editorial_json(text: str) -> dict:
    """Extract and parse JSON from LLM response."""
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0]
    elif '```' in text:
        text = text.split('```')[1].split('```')[0]

    if '{' in text:
        start = text.index('{')
        # Find matching closing brace
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    text = text[start:i + 1]
                    break

    return json.loads(text.strip())


def _fallback_plan(day_name: str, market_ctx) -> dict:
    """Generate a simple fallback plan if LLM fails."""
    categories = ['scanner_result', 'performance', 'educational', 'engagement', 'newsletter_cta']

    plan = {}
    for persona in ['Alex', 'Rozalia', 'James']:
        plan[persona] = {}
        for slot in range(1, 6):
            cat = categories[(slot - 1) % len(categories)]
            plan[persona][f'slot_{slot}'] = {
                'category': cat,
                'topic': f'{day_name} slot {slot} content',
                'tickers': [],
                'include_url': slot in [2, 5],
            }
    return plan


def validate_editorial_plan(plan: dict) -> list:
    """Validate the editorial plan for coordination issues."""
    issues = []

    # Check same-slot collisions
    for slot_num in range(1, 6):
        slot_key = f'slot_{slot_num}'
        slot_tickers = {}
        for persona, assignments in plan.items():
            assignment = assignments.get(slot_key, {})
            for ticker in assignment.get('tickers', []):
                if ticker in slot_tickers:
                    issues.append(f"Slot {slot_num}: ${ticker} collision between {slot_tickers[ticker]} and {persona}")
                slot_tickers[ticker] = persona

    # Check ticker budget (max appearances across all 15 slots)
    ticker_total = {}
    for persona, assignments in plan.items():
        for slot_key, assignment in assignments.items():
            for ticker in assignment.get('tickers', []):
                ticker_total[ticker] = ticker_total.get(ticker, 0) + 1

    for ticker, count in ticker_total.items():
        if count > 4:
            issues.append(f"${ticker} appears in {count} slots (max 4)")

    # Check category variety per persona
    for persona, assignments in plan.items():
        categories = [a.get('category', '') for a in assignments.values()]
        unique = set(categories)
        if len(unique) < 3:
            issues.append(f"{persona}: only {len(unique)} unique categories (need 3+)")

    # Check URL count
    for persona, assignments in plan.items():
        url_count = sum(1 for a in assignments.values() if a.get('include_url'))
        if url_count != 2:
            issues.append(f"{persona}: {url_count} URL slots (should be 2)")

    return issues

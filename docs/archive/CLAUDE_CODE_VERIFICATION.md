# Claude Code Verification & Output Preview Prompt

## Context

The Sterling Signals marketing system has been updated. Before deploying, we need to verify the implementation produces correct output.

## Your Task

Generate sample outputs showing exactly what the system would produce, so we can verify correctness before deployment.

---

## 1. SAMPLE SIGNALS.JSON OUTPUT

Generate a realistic `signals.json` showing the new structure:

```
Create a sample signals.json with:
- scan_date: "2026-01-25"
- scan_stats showing the funnel (1817 → 485 → 48 → 17 → 3)
- 3 pass_signals (ASPI, CGON, VNET) with full details
- 4 consider_signals (stocks that passed gates 1-4)
- 2 watchlist_signals (strong technicals, theme pending)
- historical_winners from past signals
- 2 big_wins (past signals now +25% or more)
- 1 home_run (past signal now +50% or more)
- 1 caution_signal (open position weakening)
- 0 exit_signals (no stops hit this week)
```

---

## 2. SAMPLE PORTFOLIO.CSV

Generate a realistic `portfolio.csv` showing internal tracking:

```
Include:
- 5 open positions (mix of winners and losers)
- 3 closed positions (2 wins, 1 loss)
- All columns: ticker, status, entry_date, entry_price, exit_date, exit_price, highest_close, theme, tier, conviction, notes

Show that we track EVERYTHING internally, including:
- One position down -15% (LOSER - never public)
- One position down -3% (small loss - never public)
- One position up +8% (below threshold - maybe mention)
- One position up +22% (above threshold - highlight)
- One position up +48% (big win - celebrate)
```

---

## 3. SAMPLE WEEKLY TWEETS OUTPUT

Generate the COMPLETE list of tweets that would be produced for one week.

### Scenario A: Good Week (Beating SPY, Multiple Winners)

```
Generate all 25 tweets for a week where:
- SPY is +1.2% for the week
- Our signals average +18%
- We have 3 winners above 15%
- We have 1 big win crossing 50% threshold
- 3 new PASS signals this week
- 4 CONSIDER signals

Show each tweet with:
- Day
- Slot
- Category
- Full tweet text
- Image attachment (filename)
- Any safeguard checks that passed
```

### Scenario B: Bad Week (Underperforming SPY, Few Winners)

```
Generate what tweets would be produced when:
- SPY is +4.5% for the week
- Our signals average +2%
- We have 1 winner at +16% (just above threshold)
- We have 2 losers at -8% and -12%
- 1 new PASS signal
- 2 CONSIDER signals

Show:
- Which tweets are SKIPPED due to safeguards
- What FALLBACK content replaces them
- Verify no losing positions mentioned
- Verify no beat_spy content (underperforming)
- Verify weekly_wins uses fallback (only 1 winner)
```

### Scenario C: Terrible Week (All Losers)

```
Generate what tweets would be produced when:
- All 4 open positions are down
- No new PASS signals (0)
- 2 CONSIDER signals
- SPY is up +3%

Show:
- How the system gracefully handles no wins
- What content fills the schedule
- Verify ZERO position P&L mentioned anywhere
- Verify themes/engagement content still works
```

---

## 4. SAMPLE NEWSLETTER HTML

Generate the newsletter HTML structure for Scenario A (good week):

```
Show the complete newsletter with:
- Header/branding
- THIS WEEK'S TEAL SIGNALS section (all 3 PASS signals)
- ON OUR RADAR section (CONSIDER signals)
- THEME RANKINGS section
- WIN HIGHLIGHTS section (closed winners only)
- SCANNER STATS section
- WEEK AHEAD section

Verify:
- NO "Current Portfolio" section exists
- NO individual position P&L shown
- NO entry prices for open positions
- Winners show CLOSED P&L only
```

Generate newsletter for Scenario C (terrible week):

```
Show how the newsletter handles:
- No wins to highlight (section hidden)
- Still has valuable content (themes, signals, analysis)
- No mention of losing positions
```

---

## 5. SAMPLE SUBSTACK NOTES

Generate 5 sample Substack notes that align with the new system:

```
1. Signal alert note (new TEAL signal)
2. Theme update note (hot theme + tickers)
3. Win celebration note (big win)
4. Scanner stats note (weekly funnel)
5. Watchlist note (CONSIDER stocks)

Verify branding consistency with tweets.
```

---

## 6. SAFEGUARD VERIFICATION TABLE

Create a table showing safeguard behavior:

```
| Scenario | SPY Return | Our Return | Winners | beat_spy? | weekly_wins? | Content |
|----------|------------|------------|---------|-----------|--------------|---------|
| Great week | +1% | +25% | 5 | ✅ Yes | ✅ Yes | Full schedule |
| Good week | +2% | +12% | 3 | ✅ Yes (+10% edge) | ✅ Yes | Full schedule |
| Okay week | +3% | +6% | 2 | ❌ No (+3% edge) | ✅ Yes | Fallback for beat_spy |
| Bad week | +4% | +1% | 1 | ❌ No | ❌ No | Fallbacks for both |
| Terrible | +5% | -3% | 0 | ❌ No | ❌ No | Theme/engagement only |
```

---

## 7. CELEBRATION TRACKING VERIFICATION

Show the `celebrations.json` (or equivalent) state:

```
Before this week:
{
  "ASPI": { "25_pct": null, "50_pct": null, "100_pct": null },
  "CGON": { "25_pct": "2026-01-15", "50_pct": null, "100_pct": null },
  ...
}

After this week (ASPI crossed 50%):
{
  "ASPI": { "25_pct": "2026-01-18", "50_pct": "2026-01-25", "100_pct": null },
  "CGON": { "25_pct": "2026-01-15", "50_pct": null, "100_pct": null },
  ...
}

Verify:
- Only NEW threshold crossings generate self_quote tweets
- Previously celebrated thresholds don't repeat
```

---

## 8. CONTENT QUEUE STRUCTURE

Show the `content_queue.json` structure for the week:

```json
[
  {
    "id": "weekly_wins_20260125",
    "day": "Saturday",
    "slot": 1,
    "scheduled_date": "2026-01-25",
    "category": "weekly_wins",
    "text": "...",
    "image_path": "trades/charts/weekly_wins_20260125.png",
    "safeguards_passed": ["enough_winners", "spy_outperformance"],
    "status": "pending"
  },
  ...
]
```

Show:
- All 25 tweets in order
- Safeguard metadata
- Fallback indicators where applicable

---

## 9. ERROR HANDLING SCENARIOS

Show system behavior when things go wrong:

```
Scenario: yfinance API timeout
- Expected: Skip price-dependent content, log warning
- Fallback: Use last known prices or skip position content

Scenario: Empty portfolio.csv
- Expected: Skip weekly_wins, self_quote
- Fallback: Theme/engagement content only

Scenario: Scanner produced 0 signals
- Expected: No buy_signal tweets
- Fallback: theme_hot and consider_spotlight if available
```

---

## Output Format

Please provide all samples in a clear, structured format that allows us to:
1. Visually verify tweet content is correct
2. Confirm safeguards block inappropriate content
3. Check newsletter structure matches spec
4. Validate branding consistency
5. Ensure fallback logic works correctly

Include both the RAW data (JSON/CSV) and RENDERED examples (how it would appear to users).

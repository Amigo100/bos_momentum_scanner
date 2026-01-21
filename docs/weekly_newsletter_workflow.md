# Weekly Newsletter Workflow

This document contains the workflow for generating your weekly Substack newsletter using the BoS Momentum Scanner.

---

## Overview

```
FRIDAY EVENING (After Market Close)
│
├── Run: python scanner.py --web-search
│
│   Scanner automatically outputs:
│   ├── trades/latest_newsletter_briefing.md (scanner briefing)
│   ├── DD prompts for each PASS signal (copy from terminal)
│   ├── PROMPT 1: Market context generation (copy from terminal)
│   └── PROMPT 2: Newsletter compilation (copy from terminal)
│
SATURDAY/SUNDAY (In Claude Web Interface)
├── Step 1: Run PROMPT 1 → Get market context
├── Step 2: Run DD prompts for each PASS signal → Get DD outputs
├── Step 3: Run PROMPT 2 with all inputs → Get final newsletter
│
├── Add TradingView chart screenshots
└── Copy to Substack and publish
```

---

## Step 1: Run the Scanner

```bash
# Production scan with web search (recommended)
python scanner.py --web-search

# This generates files AND prints prompts to terminal:
#
# FILES:
#   trades/latest_newsletter_briefing.md  <- Scanner briefing
#   trades/latest_report.txt              <- Detailed technical report
#
# TERMINAL OUTPUT (copy these prompts):
#   [1] DD prompts for each PASS signal
#   [2] Market Context Generation prompt
#   [3] Newsletter Compilation prompt
```

To skip the prompts (e.g., for testing):
```bash
python scanner.py --web-search --no-prompts
```

---

## Step 2: Generate Market Context

Copy **PROMPT 1** from the scanner terminal output and paste into Claude.

The prompt will ask Claude to search for:
- S&P 500, NASDAQ, Russell 2000 weekly performance
- Fed announcements, economic data
- Sector rotation
- VIX and sentiment
- Key events for next week

**Save the output** for Step 4.

---

## Step 3: Run Due Diligence for Each PASS Signal

For each stock marked as 🟢 PASS, the scanner prints a DD prompt.

Copy each DD prompt and paste into Claude (can be same or new conversation).

**Save each DD output** for Step 4.

---

## Step 4: Compile Final Newsletter

Copy **PROMPT 2** from the scanner terminal output.

Then fill in the three sections:
1. **Market Context** - Paste output from Step 2
2. **Scanner Briefing** - Paste contents of `trades/latest_newsletter_briefing.md`
3. **DD Outputs** - Paste all DD outputs from Step 3

The prompt will generate a complete, publication-ready newsletter.

---

## Step 5: Add Charts & Publish

1. For each `[CHART: TICKER]` placeholder:
   - Open TradingView chart (Weekly timeframe)
   - Add your BoS indicator
   - Take screenshot or use "Publish Snapshot"

2. Copy newsletter to Substack editor

3. Replace chart placeholders with images

4. Preview and publish!

---

## Quick Reference

### Scanner Commands

```bash
# Full production scan (prints all prompts)
python scanner.py --web-search

# Skip prompts output
python scanner.py --web-search --no-prompts

# Cost-saving mode (skip Gatekeeper)
python scanner.py --no-momentum --web-search

# Technical only (free, no LLM)
python scanner.py --no-llm
```

### File Locations

| File | Purpose |
|------|---------|
| `trades/latest_newsletter_briefing.md` | Scanner output for newsletter |
| `trades/latest_report.txt` | Detailed technical report |
| `trades/open_positions.csv` | Current positions |

---

## No Signals This Week?

If the scanner produces no PASS signals:
- Skip the DD prompts (none will be printed)
- Market context and compilation prompts still print
- Focus newsletter on themes, portfolio updates, what to watch

---

*Updated: January 2025*

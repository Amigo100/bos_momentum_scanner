# BoS Momentum Scanner - Sterling Signals

A **fully automated weekly momentum trading scanner** for US stocks with integrated content generation for X (Twitter) and Substack newsletter publishing.

**Newsletter:** [Sterling Signals on Substack](https://sterlingsignals.substack.com)
**X/Twitter:** [@SterlingSignals](https://twitter.com/SterlingSignals)

---

## What This System Does

Every Friday after market close, the system automatically:

1. **Scans 1,800+ US stocks** using our proprietary multi-step screening process
2. **Identifies hot themes** and tracks institutional money flows
3. **Runs rigorous due diligence** on qualifying signals
4. **Generates 35 tweets** for the week (5/day) with marketing-optimized language
5. **Compiles newsletter** with full analysis ready for Substack
6. **Creates Substack Notes** for Tuesday/Thursday mid-week updates
7. **Posts to X automatically** via GitHub Actions with chart attachments

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Run full Friday pipeline (automated via GitHub Actions)
./run_friday.sh

# Or run scanner only
python scanner.py --web-search
```

---

## Weekly Workflow

| Day | Automated | Manual |
|-----|-----------|--------|
| **Friday** | Full scan, DD, tweets, newsletter, notes | - |
| **Saturday** | Tweet posting (5 posts) | Copy newsletter to Substack (~10 min) |
| **Sunday** | Tweet posting (5 posts) | - |
| **Monday** | Tweet posting (5 posts) | - |
| **Tuesday** | Tweet posting (5 posts) | Post "Portfolio Pulse" to Notes (~2 min) |
| **Wednesday** | Tweet posting (5 posts) | - |
| **Thursday** | Tweet posting (5 posts) | Post "Trade Spotlight" to Notes (~2 min) |

**Total manual time:** ~15 minutes per week

---

## System Overview

Our proprietary 5-gate system filters 1,800 stocks down to 3-5 actionable signals:

```
Universe (1,800 tickers)
        ↓
   Gate 1: Technical Breakout Confirmation
        ↓
   Gate 2: Smart Money Accumulation Signals
        ↓
   Gate 3: Theme Momentum Alignment
        ↓
   Gate 4: Quality Gatekeeper (LLM analysis)
        ↓
   Gate 5: Deep Due Diligence
        ↓
   PASS Signals (3-5 stocks/week)
```

---

## Project Files

### Core Pipeline
| File | Purpose |
|------|---------|
| `scanner.py` | Main pipeline orchestrator |
| `thematic_analyzer.py` | Theme discovery and stock mapping |
| `gatekeeper.py` | Quality gate with PASS/CAUTION/FAIL decisions |
| `portfolio_manager.py` | Trade tracking, P&L, stop management |
| `dd_automator.py` | Automated due diligence |

### Content Generation
| File | Purpose |
|------|---------|
| `tweet_generator.py` | 35 weekly tweets with marketing language rules |
| `newsletter_compiler.py` | Full HTML newsletter compilation |
| `substack_notes_generator.py` | Tuesday/Thursday mid-week notes |
| `market_analyzer.py` | Market context analysis |
| `chart_capture.py` | TradingView chart screenshots |

### Publishing
| File | Purpose |
|------|---------|
| `twitter_poster.py` | X/Twitter API posting with media |
| `.github/workflows/friday_scan.yml` | Weekly scan automation (Fridays 21:30 UTC) |
| `.github/workflows/daily_post.yml` | 5 tweets/day at scheduled times |
| `output_paths.py` | Centralized folder structure management |

---

## Output Structure

```
trades/
├── current/                    # Latest week's outputs
│   ├── newsletter.html         ← Copy to Substack Saturday
│   ├── newsletter_briefing.md
│   ├── signals.json
│   └── substack_notes/
│       ├── tuesday_note.md     ← Copy to Notes Tuesday
│       └── thursday_note.md    ← Copy to Notes Thursday
│
├── weeks/                      # Weekly archives (2026-W04, etc.)
├── charts/                     # Chart images with manifest
├── portfolio.csv               # Source of truth for trades
├── content_queue.json          # Tweet posting queue with status
└── signals.json                # Latest scan results
```

---

## Commands Reference

### Full Pipeline
```bash
# Automated Friday run
./run_friday.sh

# Manual with web search (~$2-5)
python scanner.py --web-search
```

### Scanner Options
```bash
# Technical scan only (FREE, no LLM)
python scanner.py --no-llm

# Full pipeline with web search
python scanner.py --web-search

# Limit to top N by beta
python scanner.py --web-search --top 50
```

### Content Generation
```bash
# Generate newsletter
python newsletter_compiler.py --full

# Generate tweets (with marketing language rules)
python tweet_generator.py

# Generate Substack notes
python substack_notes_generator.py

# Capture charts (requires TradingView login)
python chart_capture.py --tickers AAPL,NVDA
```

### Publishing
```bash
# Post next pending tweet
source .env && python twitter_poster.py

# Force post regardless of schedule
source .env && python twitter_poster.py --force

# Dry run (show what would post)
python twitter_poster.py --dry-run
```

### Portfolio Management
```bash
# View portfolio summary
python portfolio_manager.py --report

# Update prices
python portfolio_manager.py --update

# Export for Google Sheets
python portfolio_manager.py --export
```

---

## Environment Variables

```bash
# Required for LLM analysis
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Required for X posting (also set in GitHub Secrets)
export X_API_KEY="..."
export X_API_SECRET="..."
export X_ACCESS_TOKEN="..."
export X_ACCESS_SECRET="..."

# Optional: Email notifications
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export EMAIL_SENDER="you@gmail.com"
export EMAIL_PASSWORD="app-password"
export EMAIL_RECIPIENTS="you@gmail.com"
```

---

## Cost Estimate

| Component | Cost per Run |
|-----------|--------------|
| Scanner (themes + gating) | ~$1.00-1.50 |
| Due Diligence (per signal) | ~$0.30-0.50 |
| Market Analysis | ~$0.20-0.30 |
| Newsletter Compilation | ~$0.20-0.50 |
| Tweet Generation | ~$0.30-0.50 |
| **Total Friday Pipeline** | **~$2-5** |

Annual projection: ~$100-250/year

---

## Tweet Posting Schedule (Eastern Time)

| Slot | Time (ET) | Content Type |
|------|-----------|--------------|
| 1 | 08:00 | Pre-market / Beat SPY / Roth IRA hooks |
| 2 | 10:00 | Theme analysis / Buy signal |
| 3 | 12:30 | Position update with chart |
| 4 | 15:30 | **Power Hour reaction** (CRITICAL) |
| 5 | 18:00 | Engagement / Lessons |

---

## Documentation

| File | Purpose |
|------|---------|
| `SYSTEM_OVERVIEW.md` | **Complete marketing & automation guide** |
| `CLAUDE.md` | Full technical documentation |
| `SETUP.md` | External service setup guide |

---

## Marketing Language Guidelines

All generated content follows these rules:
- **NO revealing** specific strategy details (stop percentages, indicator names)
- **USE** approved phrases: "proprietary signals", "smart money accumulation", "theme momentum"
- **FOCUS** on following institutional money, bottleneck plays, discipline over FOMO
- **HONEST** about losses - frame positively but never hide them

See `SYSTEM_OVERVIEW.md` Section 2 for full marketing language rules.

---

## License

Private project for Sterling Signals newsletter.

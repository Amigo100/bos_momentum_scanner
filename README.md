# BoS Momentum Scanner - Sterling Signals

A **fully automated weekly momentum trading scanner** for US stocks with integrated content generation for X (Twitter) and Substack newsletter publishing.

**Newsletter:** [Sterling Signals on Substack](https://sterlingsignals.substack.com)
**X/Twitter:** [@SterlingSignals](https://twitter.com/SterlingSignals)

---

## What This System Does

Every Friday after market close, the system automatically:

1. **Scans 1,800+ US stocks** for momentum signals
2. **Identifies hot themes** (AI, Energy, Defense, etc.)
3. **Runs due diligence** on qualifying stocks
4. **Generates 35 tweets** for the week (5/day)
5. **Compiles newsletter** ready for Substack
6. **Creates Substack Notes** for Tuesday/Thursday mid-week updates
7. **Posts to X** automatically via GitHub Actions

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
| **Friday** | Full scan, DD, tweets, newsletter compilation | - |
| **Saturday** | Tweet posting (5 posts) | Copy newsletter to Substack, add charts |
| **Sunday** | Tweet posting (5 posts) | - |
| **Monday** | Tweet posting (5 posts) | - |
| **Tuesday** | Tweet posting (5 posts), Substack Note ready | Post Tuesday Note to Substack |
| **Wednesday** | Tweet posting (5 posts) | - |
| **Thursday** | Tweet posting (5 posts), Substack Note ready | Post Thursday Note to Substack |

**Only manual steps:** Substack newsletter publish (~10 min) + Tuesday/Thursday notes (~2 min each)

---

## Entry & Exit Strategy

### ENTRY (Buy Signal)
```
1. Weekly HMA Pivot BUY signal (bullish structure break)
2. Beta >= 1.5 (high momentum)
3. Banker score > 55 (institutional accumulation)
4. Hot theme confirmed (PRIME or INVESTABLE)
5. Gatekeeper PASS decision
6. Due Diligence confirms
```

### EXIT (Sell Signal)
```
PRIMARY:  20% trailing stop from highest weekly close
CAUTION:  Weekly BoS Down → tighten stop to 15%
```

---

## Pipeline Architecture

```
Universe (1,800 tickers)
        ↓
   Technical Gate (Beta >= 1.5 + HMA Pivot BUY + Banker > 55)
        ↓
   Thematic Analyzer (Theme classification + stock mapping)
        ↓
   Gatekeeper (PASS / CAUTION / FAIL decisions)
        ↓
   Due Diligence (Deal Memo for PASS signals)
        ↓
   Portfolio Update (track positions, P&L, stops)
        ↓
   Content Generation (tweets, newsletter, Substack notes)
        ↓
   Auto-Posting (X via GitHub Actions)
```

---

## Project Files

### Core Pipeline
| File | Purpose |
|------|---------|
| `scanner.py` | Main pipeline orchestrator |
| `thematic_analyzer.py` | LLM theme discovery and scoring |
| `gatekeeper.py` | LLM final quality gate |
| `portfolio_manager.py` | Trade tracking, P&L, Google Sheets export |

### Content Generation
| File | Purpose |
|------|---------|
| `tweet_generator.py` | Generate 35 weekly tweets |
| `newsletter_compiler.py` | Compile full newsletter with DD |
| `substack_notes_generator.py` | Tuesday/Thursday mid-week notes |
| `market_analyzer.py` | Market context analysis |
| `dd_automator.py` | Automated due diligence |

### Automation
| File | Purpose |
|------|---------|
| `run_friday.sh` | Full Friday pipeline script |
| `.github/workflows/friday_scan.yml` | Friday scan automation |
| `.github/workflows/post_content.yml` | Daily tweet posting |
| `output_paths.py` | Centralized folder structure |

### Utilities
| File | Purpose |
|------|---------|
| `verify_bos.py` | Debug signal calculation |
| `diagnose_bos.py` | Universe state analysis |
| `email_notifier.py` | Email notifications |
| `chart_capture.py` | TradingView chart screenshots |

---

## Output Structure

```
trades/
├── current/                    # Latest outputs (symlinked)
│   ├── newsletter_briefing.md
│   ├── newsletter.html
│   ├── tweets.json
│   └── substack_notes/
│       ├── tuesday_note.md
│       └── thursday_note.md
│
├── weeks/                      # Weekly archives
│   ├── 2026-W03/
│   ├── 2026-W04/
│   └── ...
│
├── charts/                     # Chart images
│   └── chart_manifest.json
│
├── grok_prompts/              # Daily tweet files
│   ├── latest_grok_prompts.md
│   ├── monday_prompts.md
│   └── ...
│
├── portfolio.csv              # Source of truth for trades
├── signals.json               # Latest scan results
├── analysis_log.csv           # Historical scan data
└── content_queue.json         # Tweet posting queue
```

---

## Commands Reference

### Full Pipeline
```bash
# Automated Friday run (what GitHub Actions does)
./run_friday.sh

# Manual full pipeline with web search
python scanner.py --web-search
```

### Scanner Options
```bash
# Technical scan only (FREE)
python scanner.py --no-llm

# With themes, skip gatekeeper
python scanner.py --no-momentum

# Full pipeline with web search (~$1-3)
python scanner.py --web-search

# Limit to top N by beta
python scanner.py --web-search --top 50
```

### Content Generation
```bash
# Generate newsletter
python newsletter_compiler.py --full

# Generate tweets
python tweet_generator.py

# Generate Substack notes
python substack_notes_generator.py
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
# Required
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Optional: Email notifications
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export EMAIL_SENDER="you@gmail.com"
export EMAIL_PASSWORD="app-password"
export EMAIL_RECIPIENTS="you@gmail.com"

# For X posting (GitHub Secrets)
TWITTER_API_KEY
TWITTER_API_SECRET
TWITTER_ACCESS_TOKEN
TWITTER_ACCESS_SECRET
```

---

## Cost Estimate

| Component | Cost per Run |
|-----------|--------------|
| Thematic Analyzer | ~$0.15-0.25 |
| Gatekeeper (per stock) | ~$0.10-0.20 |
| Due Diligence (per stock) | ~$0.30-0.50 |
| Market Analysis | ~$0.10 |
| Newsletter Compilation | ~$0.20 |
| **Total Friday Pipeline** | **~$2-5** |

---

## Documentation

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Full system documentation for AI context |
| `SETUP.md` | External service setup guide |
| `SYSTEM_OVERVIEW.md` | Marketing & improvement assessment |
| `docs/archive/` | Historical planning documents |

---

## License

Private project for Sterling Signals newsletter.

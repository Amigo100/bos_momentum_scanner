# BoS Momentum Scanner

A **weekly momentum trading scanner** for US stocks. Identifies high-beta stocks with bullish HMA Pivot signals and strong institutional accumulation, then confirms via LLM-powered thematic analysis.

**Designed for:** UK trader using Barclays ISA for US stocks, with 4-8 week hold periods.

---

## Quick Start

```bash
# 1. Install dependencies
pip install yfinance pandas numpy anthropic

# 2. Set API key (for LLM features)
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# 3. Run technical scan (FREE - no API calls)
python scanner.py --no-llm

# 4. Run with theme analysis (~$0.13)
python scanner.py --no-momentum

# 5. Run full pipeline (~$0.25)
python scanner.py
```

---

## Entry & Exit Strategy

### ENTRY (Buy Signal)
```
1. HMA Pivot BUY fires (lower step line changes = bullish structure)
2. Beta >= 1.5 (high momentum stock)
3. Banker score > 55 (institutional accumulation)
4. Stock is in a hot theme/sector (Thematic Analyzer)
5. → Enter Monday at market open
```

### EXIT (Sell Signal)
```
PRIMARY:  20% trailing stop from highest weekly close

CAUTION:  HMA Pivot SELL (upper step changes)
          - Do NOT automatically exit
          - Consider tightening stop to 15%
```

---

## Pipeline Overview

```
Universe (4000 tickers)
        ↓
   Technical Gate (Beta >= 1.5 + HMA Pivot BUY + Banker > 55)
        ↓
   Thematic Analyzer (Theme fit: STRONG/GOOD)
        ↓
   Momentum Assessor (TRADE / CONSIDER / SKIP)
        ↓
   Due Diligence (PROCEED / CAUTION / WAIT / PASS)
        ↓
   Trade Log + Email
```

---

## Files

```
scanner.py              # Main integrated pipeline
thematic_analyzer.py    # Theme identification & mapping
momentum_assessor.py    # Final trade decision
due_diligence.py        # Deep analysis (Opus)
run_full_pipeline.py    # Complete pipeline with DD
verify_bos.py           # Debug signal calculation
diagnose_bos.py         # Universe state analysis
email_notifier.py       # Email notifications
setup_scheduler.py      # Automated weekly runs
complete_tickers.txt    # Full ticker universe
test_tickers.txt        # Smaller test universe
CLAUDE.md               # Claude Code context
CLAUDE_CODE_WORKFLOWS.md # Copy-paste prompts
```

---

## Usage

### Basic Scans
```bash
# Technical only (FREE)
python scanner.py --no-llm

# With themes (~$0.13)
python scanner.py --no-momentum

# Full pipeline (~$0.25)
python scanner.py

# Top N by beta
python scanner.py --top 100 --no-llm
```

### Full Pipeline with Due Diligence
```bash
python run_full_pipeline.py                    # Full pipeline
python run_full_pipeline.py --top-dd 3         # DD on top 3 only
python run_full_pipeline.py --budget "£10,000" # Custom budget
python run_full_pipeline.py --skip-dd          # Skip DD step
```

### Debugging
```bash
python verify_bos.py NVDA TSLA PLTR    # Check specific tickers
python diagnose_bos.py 100              # Universe state
```

### Automation (macOS)
```bash
python setup_scheduler.py install       # Sunday 9:30 PM
python setup_scheduler.py status        # Check status
python setup_scheduler.py uninstall     # Remove
```

---

## Signal Criteria

### Gate 1: Technical Signals (Weekly)
| Criterion | Threshold | Description |
|-----------|-----------|-------------|
| Beta | >= 1.5 | High volatility vs SPY |
| HMA Pivot BUY | TRUE | Lower step line changed |
| Banker | > 55 | Institutional accumulation |

**Tier Assignment:**
- TIER 1: Banker > 70 (highest conviction)
- TIER 2: Banker > 60
- TIER 3: Banker > 55

### Gate 2: Thematic Analyzer
Identifies top 5-7 hot themes, maps stocks to themes.

| Theme Rating | Score | Action |
|--------------|-------|--------|
| PRIME | >= 7.5 | High conviction |
| INVESTABLE | 6.0-7.4 | Standard position |
| SELECTIVE | 4.5-5.9 | Cherry-pick only |
| AVOID | < 4.5 | Do not invest |

| Fit Verdict | Passes Gate? |
|-------------|--------------|
| STRONG FIT | ✓ |
| GOOD FIT | ✓ |
| MODERATE/WEAK/NO FIT | ✗ |

### Gate 3: Momentum Assessor
| Decision | Action |
|----------|--------|
| 🟢 TRADE | Enter Monday at market open |
| 🟡 CONSIDER | Smaller position or skip |
| 🔴 SKIP | Don't trade |

### Gate 4: Due Diligence
| Verdict | Action |
|---------|--------|
| PROCEED WITH CONVICTION | Full position |
| PROCEED WITH CAUTION | Reduced size |
| WAIT FOR BETTER ENTRY | Monitor only |
| PASS ON THIS ONE | Skip |

---

## Cost Comparison

| Mode | Cost/Run | Annual (Weekly) |
|------|----------|-----------------|
| `--no-llm` | $0.00 | $0.00 |
| `--no-momentum` | ~$0.13 | ~$7 |
| Full pipeline | ~$0.25 | ~$13 |
| + Due Diligence | ~$0.50 | ~$26 |

---

## Using with Claude Code

This project is optimized for use with Claude Code. The `CLAUDE.md` file provides context automatically.

### Recommended Workflow (Saves Money!)

Instead of using built-in API calls, use Claude Code for analysis:

```bash
# Step 1: Run technical scan (FREE)
python scanner.py --no-llm

# Step 2: Ask Claude Code to analyze themes
# Paste candidates into Claude Code, it does analysis for free
```

This uses your Pro subscription instead of API credits.

See `CLAUDE_CODE_WORKFLOWS.md` for ready-to-use prompts.

---

## Environment Variables

```bash
# Required for LLM features
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Optional: Email notifications
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export EMAIL_SENDER="you@gmail.com"
export EMAIL_PASSWORD="app-password"
export EMAIL_RECIPIENTS="you@gmail.com"
```

---

## Output Files

| File | Description |
|------|-------------|
| `data/signals.json` | Latest scan results |
| `data/pipeline_results.json` | Full pipeline results |
| `trades/trade_log.csv` | Trade history |
| `reports/dd_TICKER_*.md` | Due diligence reports |
| `logs/scan_*.log` | Execution logs |

---

## Example Output

```
╔══════════════════════════════════════════════════════════════════════╗
║             BoS MOMENTUM SCANNER - WEEKLY TIMEFRAME                  ║
╚══════════════════════════════════════════════════════════════════════╝

  ✅ ENTRY CANDIDATES (HMA Pivot BUY):
  ──────────────────────────────────────────────────────────────────────
  TIER   SYMBOL     PRICE    BETA   THEME
  ──────────────────────────────────────────────────────────────────────
  TIER1  PLTR    $ 188.71    2.45   AI Data Center Infrastructure
  TIER1  RKLB    $  70.65    2.89   Defense & Aerospace
  ──────────────────────────────────────────────────────────────────────

  SUMMARY: 2 entry candidates
    🟢 Enter Monday at market open: PLTR, RKLB
```

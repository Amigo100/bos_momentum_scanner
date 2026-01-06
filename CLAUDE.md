# CLAUDE.md - BoS Momentum Scanner

> **Claude Code reads this file automatically.** It provides context about the project structure, commands, and how to help the user effectively.

---

## CRITICAL: LLM Usage in This Project

This project has **two sources of LLM calls**:

### 1. Built-in API Calls (Uses User's API Credits) ⚠️
```python
# In thematic_analyzer.py and momentum_assessor.py
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.messages.create(...)  # COSTS USER MONEY
```

### 2. Claude Code Analysis (FREE with Pro Plan) ✅
When the user asks YOU (Claude Code) to analyze stocks, themes, or debug - this is FREE.

**RECOMMENDED WORKFLOW:**
```bash
# Step 1: Run technical scan (FREE)
python scanner.py --no-llm

# Step 2: Ask Claude Code to do theme analysis (FREE)
# User pastes candidates, you analyze using web search
```

---

## Project Overview

A **weekly momentum trading scanner** for US stocks.

**Strategy:**
- **Entry:** HMA Pivot BUY + Beta ≥1.5 + Banker ≥55 + Theme confirmation
- **Exit:** 20% trailing stop from highest weekly close
- **Timeframe:** Weekly (signals change Friday close only)

---

## File Structure

```
bos_momentum_scanner/
├── scanner.py              # Main pipeline - START HERE
├── thematic_analyzer.py    # LLM theme analysis (uses API)
├── momentum_assessor.py    # LLM trade decisions (uses API)
├── due_diligence.py        # Deep analysis with Opus (uses API)
├── due_diligence_prompts.py # DD prompt templates
├── verify_bos.py           # Debug signals for specific tickers
├── diagnose_bos.py         # Analyze universe state
├── email_notifier.py       # Email notifications
├── setup_scheduler.py      # Automated weekly runs (macOS)
├── run_full_pipeline.py    # Complete pipeline with DD step
├── complete_tickers.txt    # Ticker universe
├── requirements.txt        # Python dependencies
├── CLAUDE.md               # This file
├── CLAUDE_CODE_WORKFLOWS.md # Copy-paste prompts
├── data/                   # Signals output
├── trades/                 # Trade logs
├── logs/                   # Execution logs
└── reports/                # Due diligence reports
```

---

## Key Commands

### Technical Scan (FREE - No API)
```bash
python scanner.py --no-llm                 # All tickers
python scanner.py --no-llm --top 50        # Top 50 by beta
```

### With Theme Analysis (~$1.00 API cost with Opus 4.5)
```bash
python scanner.py --no-momentum            # Themes only
```

### Full Pipeline (~$2.00 API cost with Opus 4.5)
```bash
python scanner.py                          # Everything
```

### Full Pipeline + Due Diligence
```bash
python run_full_pipeline.py                # Scanner → Themes → DD
python run_full_pipeline.py --top-dd 3     # DD on top 3 only
```

### Debugging
```bash
python verify_bos.py NVDA TSLA PLTR        # Check specific tickers
python diagnose_bos.py 100                 # Universe state
```

---

## Signal Logic

### HMA Pivot BoS (scanner.py lines 325-430)
```
HMA = Hull Moving Average of HL2
Length: 21 periods (weekly)
Pivot: k=1

BUY:  Lower step line changed → New bullish structure
SELL: Upper step line changed → New bearish structure
```

### Beta (scanner.py lines 223-237)
```
beta = cov(stock, SPY) / var(SPY)
Threshold: >= 1.5
```

### Banker (scanner.py lines 240-270)
```
Formula: ((price / 20-day VWAP) - 1) * 100 + 50
TIER 1: > 70 (strong accumulation)
TIER 2: > 60 (moderate)
TIER 3: > 55 (entry level)
```

### Theme Classification (thematic_analyzer.py)
```
PRIME:      Score >= 7.5 (high conviction)
INVESTABLE: Score 6.0-7.4 (good opportunity)
SELECTIVE:  Score 4.5-5.9 (mixed)
AVOID:      Score < 4.5

Types: BOTTLENECK > CONTRARIAN > TREND (preference order)
```

---

## Pipeline Flow

```
┌────────────────────────────────────────────┐
│ 1. LOAD TICKERS (complete_tickers.txt)     │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 2. DOWNLOAD DATA (yfinance, 1yr daily)     │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 3. TECHNICAL GATE                          │
│    Beta >= 1.5 AND BoS UP AND Banker >= 55 │
│    Output: ~10-30 candidates               │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 4. THEMATIC ANALYZER (LLM)                 │
│    Identify themes → Map stocks → Score    │
│    Gate: PRIME/INVESTABLE + STRONG/GOOD    │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 5. MOMENTUM ASSESSOR (LLM)                 │
│    TRADE / CONSIDER / SKIP                 │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 6. DUE DILIGENCE (LLM - Opus)              │
│    Deep analysis on TRADE candidates       │
│    PROCEED / CAUTION / WAIT / PASS         │
└────────────────────────────────────────────┘
```

---

## Environment Variables

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Optional: Email
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export EMAIL_SENDER="you@gmail.com"
export EMAIL_PASSWORD="app-password"
export EMAIL_RECIPIENTS="you@gmail.com"
```

---

## When Helping the User

### For Debugging/Analysis
- Run commands directly and explain output
- Use `verify_bos.py` to trace signal calculations
- Check data quality with yfinance directly

### For Theme Analysis (Save User Money)
Instead of running `python scanner.py` (which uses API):
1. Run `python scanner.py --no-llm` for technical candidates
2. YOU do the theme analysis using web search
3. This uses Claude Code (free) instead of API (paid)

### For Code Changes
- Read the relevant file first
- Make targeted edits
- Test with `--no-llm` flag to avoid API costs
- Verify with `python -m py_compile filename.py`

---

## Quick Reference

| Signal | Meaning |
|--------|---------|
| 🟢 HMA Pivot BUY | Entry candidate |
| 🔴 HMA Pivot SELL | Tighten stop (don't exit) |
| TIER 1 | Banker > 70 |
| TIER 2 | Banker > 60 |
| TIER 3 | Banker > 55 |

| DD Verdict | Action |
|------------|--------|
| PROCEED WITH CONVICTION | Full position |
| PROCEED WITH CAUTION | Reduced size |
| WAIT FOR BETTER ENTRY | Monitor only |
| PASS ON THIS ONE | Skip |

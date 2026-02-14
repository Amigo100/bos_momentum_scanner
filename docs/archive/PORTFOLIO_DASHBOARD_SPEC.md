# Portfolio Dashboard & Automation Specification

## Overview

This document outlines an improved portfolio tracking system with:
1. **Live Web Dashboard** - Real-time prices, charts, performance
2. **Smart Grok Prompts** - Dynamic P&L data in tweets
3. **Automated Alerts** - Stop warnings, daily summaries

---

## Architecture Options

### Option A: Streamlit Dashboard (Recommended for Solo Use)
**Pros:** Python-native, easy to build, free hosting on Streamlit Cloud
**Cons:** Requires running locally or cloud deployment

```
portfolio.csv → Streamlit App → Live Dashboard
                     ↓
              yfinance API (real-time prices)
                     ↓
              Auto-refresh every 5 min
```

**Features:**
- Real-time P&L for all positions
- Visual stop-loss proximity indicators
- Theme performance breakdown
- One-click Grok prompt generation with LIVE data
- Historical performance charts

### Option B: Google Sheets + Apps Script (Current + Enhanced)
**Pros:** Already familiar, automatic GOOGLEFINANCE updates
**Cons:** Manual export, limited interactivity

**Enhancements:**
- Apps Script for automated daily email summaries
- Conditional formatting for stop alerts
- Embedded charts

### Option C: Notion Database + API
**Pros:** Beautiful UI, mobile-friendly, shareable
**Cons:** Requires Notion API integration, subscription for advanced features

---

## Recommended Implementation: Streamlit Dashboard

### File Structure
```
bos_momentum_scanner/
├── dashboard/
│   ├── app.py              # Main Streamlit app
│   ├── components/
│   │   ├── portfolio.py    # Portfolio table component
│   │   ├── charts.py       # Performance charts
│   │   ├── alerts.py       # Stop alert component
│   │   └── grok.py         # Grok prompt generator
│   └── requirements.txt    # Dashboard dependencies
```

### Dashboard Features

#### 1. Portfolio Overview
```
┌─────────────────────────────────────────────────────────────┐
│  STERLING SIGNALS PORTFOLIO                    Updated: Now │
├─────────────────────────────────────────────────────────────┤
│  Total P&L: +$4,542.00 (+12.3%)                            │
│  Open Positions: 6  │  Win Rate: 83%  │  Avg Hold: 12 days │
├─────────────────────────────────────────────────────────────┤
│  Ticker │ Entry │ Current │ P&L    │ Stop   │ Theme       │
│  ────────────────────────────────────────────────────────── │
│  RCAT   │ $8.50 │ $13.11  │ +54.2% │ 🟢 OK  │ Drones      │
│  IBKR   │ $65   │ $70.24  │ +8.1%  │ 🟢 OK  │ Financials  │
│  FIX    │ $1027 │ $1072   │ +4.4%  │ 🟢 OK  │ Grid        │
│  TLN    │ $392  │ $381    │ -2.8%  │ 🟡 17% │ Nuclear     │
│  VNET   │ $10.4 │ $11.23  │ +8.0%  │ 🟢 OK  │ Data Center │
│  CGON   │ $54   │ $54.28  │ +0.7%  │ 🟢 OK  │ Healthcare  │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Stop Alert Panel
```
┌─────────────────────────────────────────┐
│  ⚠️ STOP ALERTS                         │
├─────────────────────────────────────────┤
│  TLN: 17.7% from stop ($313.96)         │
│  Action: Tighten to 15% if BoS Down     │
└─────────────────────────────────────────┘
```

#### 3. One-Click Grok Generator
```
┌─────────────────────────────────────────────────────────────┐
│  📱 GROK PROMPT GENERATOR                                   │
├─────────────────────────────────────────────────────────────┤
│  Select Position: [RCAT ▼]                                  │
│                                                             │
│  Generated Prompt:                                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ PORTFOLIO UPDATE:                                       ││
│  │ RCAT: +54.2% | Entry: $8.50 | Current: $13.11          ││
│  │ Theme: Drone Technology | Tier: TIER1                   ││
│  │ Highest: $13.11 | Stop: $10.49 (20% trailing)          ││
│  │ Days Held: 15 | Status: UPTREND INTACT                  ││
│  │ ---                                                     ││
│  │ You are drafting an X post for @SterlingSignals...     ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  [📋 Copy to Clipboard]  [🔄 Refresh Prices]               │
└─────────────────────────────────────────────────────────────┘
```

---

## Enhanced Grok Prompts

### Current Issue
Prompts are generated once during scanner run with static P&L data.

### Solution
Generate prompts dynamically with LIVE data:

```python
def generate_position_prompt(ticker: str) -> str:
    """Generate Grok prompt with live P&L data."""
    # Fetch current price
    current = yf.Ticker(ticker).info.get('regularMarketPrice', 0)

    # Load position from portfolio
    position = get_position(ticker)

    # Calculate live P&L
    pnl_pct = ((current / position.entry_price) - 1) * 100

    return f"""PORTFOLIO UPDATE:
{ticker}: {pnl_pct:+.1f}% | Entry: ${position.entry_price:.2f} | Current: ${current:.2f}
Theme: {position.theme} | Tier: {position.tier}
Highest: ${position.highest_close:.2f} | Stop: ${position.stop_level:.2f}
Days Held: {position.days_held} | Status: {'UPTREND' if current > position.entry_price else 'WATCH'}

---

You are drafting an X post for @SterlingSignals.
..."""
```

### Prompt Categories with Live Data

| Category | Data Source | Refresh |
|----------|-------------|---------|
| Position Update | Live price via yfinance | Real-time |
| Scanner Stats | Latest scan results | Weekly |
| Theme Hot | Themes from briefing | Weekly |
| Market Pulse | Live index data | Real-time |
| Trading Lesson | Static lessons | N/A |

---

## Automated Reporting

### Daily Email Summary (via email_notifier.py)

```
Subject: Sterling Signals Daily Update - Jan 13, 2026

PORTFOLIO SUMMARY
─────────────────
Total P&L: +$4,542 (+12.3%)
Best:  RCAT +54.2%
Worst: TLN -2.8%

STOP ALERTS
─────────────────
⚠️ TLN: 17.7% from stop - watch closely

THEMES TODAY
─────────────────
Power Grid: +2.3% sector move
Nuclear: -1.1% pullback
```

### Weekly Performance Report
Automatically generated after each scan with:
- Week-over-week P&L change
- New entries/exits
- Theme performance breakdown
- Comparison to SPY

---

## Implementation Roadmap

### Phase 1: Enhanced Grok Prompts ✅ COMPLETE
- [x] Add live price fetching to grok_prompts_generator.py
- [x] Update portfolio.csv with current prices before generating
- [x] Include actual P&L in position update prompts
- [x] Parse themes from multiple briefing formats

### Phase 2: Streamlit Dashboard (4-6 hours)
- [ ] Create dashboard/app.py with basic portfolio view
- [ ] Add real-time price refresh
- [ ] Add stop alert indicators
- [ ] Add one-click Grok prompt generation

### Phase 3: Automated Alerts (2-3 hours)
- [ ] Daily email summary via email_notifier.py
- [ ] Stop proximity alerts (when within 5%)
- [ ] Weekly performance digest

### Phase 4: Cloud Deployment (1-2 hours)
- [ ] Deploy to Streamlit Cloud (free)
- [ ] Optional: Custom domain

---

## Dependencies

### For Streamlit Dashboard
```
streamlit>=1.29.0
plotly>=5.18.0
yfinance>=0.2.28
pandas>=2.0.0
```

### Hosting Options
1. **Streamlit Cloud** - Free, easy deployment
2. **Railway/Render** - Free tier available
3. **Local only** - Run `streamlit run dashboard/app.py`

---

## Quick Start (After Implementation)

```bash
# Run dashboard locally
streamlit run dashboard/app.py

# Generate live Grok prompts
python grok_prompts_generator.py --live

# Send daily summary email
python email_notifier.py --daily-summary
```

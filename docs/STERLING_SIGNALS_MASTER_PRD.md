# STERLING SIGNALS — MASTER PRODUCT REQUIREMENTS DOCUMENT

> **Purpose:** Single authoritative reference for the entire Sterling Signals ecosystem — stock scanning & selection, Substack content generation, and automated tweet posting. Consult this document before making ANY changes in Claude Code.
>
> **Version:** 1.0 (Consolidated)
> **Created:** 2026-02-14
> **Source documents:** `SCANNER_PIPELINE_REFERENCE.md` (v1), `sterling_signals_substack_prd.docx` (v3.0), `STERLING_SIGNALS_TWEET_SYSTEM_PRD_v4.md` (v4.0)
>
> **Rule:** If a component is listed under "DO NOT CHANGE", a full re-backtest (924 tickers, 2018–2025) is required before altering it.

---

## TABLE OF CONTENTS

### Part A — System Overview & Philosophy
1. [What Sterling Signals Is](#a1-what-sterling-signals-is)
2. [End-to-End Pipeline](#a2-end-to-end-pipeline)
3. [Core Principles](#a3-core-principles)

### Part B — Scanner Pipeline (Stock Scanning & Selection)
4. [Technical Screening (Sterling Grid)](#b4-technical-screening-sterling-grid)
5. [Thematic Analysis (Gate 1)](#b5-thematic-analysis-gate-1)
6. [Investment Gate (Gate 2)](#b6-investment-gate-gate-2)
7. [Deep Due Diligence (Gate 3)](#b7-deep-due-diligence-gate-3)
8. [Portfolio Tracking](#b8-portfolio-tracking)
9. [Scanner Output Generation](#b9-scanner-output-generation)
10. [Daily Scanner (Separate Pipeline)](#b10-daily-scanner-separate-pipeline)
11. [Backtest Validation](#b11-backtest-validation)

### Part C — Substack Content Generation
12. [Substack System Overview](#c12-substack-system-overview)
13. [Content Calendar & Post Definitions](#c13-content-calendar--post-definitions)
14. [Post Specifications](#c14-post-specifications)
15. [Visual Design System](#c15-visual-design-system)
16. [Substack Technical Specifications](#c16-substack-technical-specifications)
17. [Substack Module Structure](#c17-substack-module-structure)
18. [Substack Implementation Plan](#c18-substack-implementation-plan)

### Part D — Automated Tweet System
19. [Tweet System Overview & Philosophy](#d19-tweet-system-overview--philosophy)
20. [Tweet Architecture](#d20-tweet-architecture)
21. [Tweet Pipeline: Step-by-Step](#d21-tweet-pipeline-step-by-step)
22. [Tweet Categories & Decision Logic](#d22-tweet-categories--decision-logic)
23. [Voice, Tone & Style](#d23-voice-tone--style)
24. [Multi-Account Strategy — Three Personas](#d24-multi-account-strategy--three-personas)
25. [Slot Collision Prevention](#d25-slot-collision-prevention)
26. [Tweet Scheduling & Frequency](#d26-tweet-scheduling--frequency)
27. [Charts & Visual Content (Tweets)](#d27-charts--visual-content-tweets)
28. [Content Freshness & Anti-Repetition](#d28-content-freshness--anti-repetition)
29. [Tweet Validation Pipeline](#d29-tweet-validation-pipeline)
30. [Weekend & Off-Hours Behavior](#d30-weekend--off-hours-behavior)
31. [Priority Rules & Signal Urgency](#d31-priority-rules--signal-urgency)

### Part E — Shared Systems & Rules
32. [Marketing & Safety Rules](#e32-marketing--safety-rules)
33. [Data Accuracy & Anti-Fabrication](#e33-data-accuracy--anti-fabrication)
34. [Critical System Invariants](#e34-critical-system-invariants)
35. [File Locations (All Systems)](#e35-file-locations-all-systems)
36. [Configuration Reference (All Systems)](#e36-configuration-reference-all-systems)
37. [Environment Variables & Secrets](#e37-environment-variables--secrets)
38. [Cost Controls](#e38-cost-controls)
39. [Command-Line Usage](#e39-command-line-usage)
40. [Testing & Verification](#e40-testing--verification)
41. [Acceptance Criteria (All Systems)](#e41-acceptance-criteria-all-systems)
42. [Known Limitations & Future Work](#e42-known-limitations--future-work)

---

# PART A — SYSTEM OVERVIEW & PHILOSOPHY

---

## A1. What Sterling Signals Is

Sterling Signals is a weekly momentum scanner for US-listed growth stocks under $25. It combines technical signals (Sterling Grid indicators) with LLM-powered fundamental analysis to identify high-conviction opportunities, then distributes insights via a Substack newsletter (2–3 posts/week) and automated X/Twitter content (7–10 tweets/day across 3 accounts).

**Validated performance:** V1–V4 backtesting across 924 tickers, 7+ years (2018–2025): **+633% at 10×10 sizing, 79% win rate, −7.2% max drawdown.**

The system has three major subsystems that share data but operate independently:

| Subsystem | Purpose | Cadence |
|-----------|---------|---------|
| **Scanner Pipeline** | Scan universe → technical filter → LLM gates → portfolio updates | Weekly (Friday) |
| **Substack Content** | Generate 2–3 polished HTML posts from scanner data | Saturday / Tuesday / Thursday |
| **Tweet System** | Generate & post 7–10 tweets across 3 accounts from live market data | Every 2–3 hours |

---

## A2. End-to-End Pipeline

```
FRIDAY NIGHT
Scanner runs → signals.json + portfolio.csv + equity_curve.csv
                    │
                    ├──→ market_analyzer.py → market_analysis.md
                    │
                    ├──→ Substack Content System (Saturday / Tuesday / Thursday)
                    │         └──→ 2–3 HTML posts per week
                    │
                    └──→ Tweet System (every 2–3 hours, 7 days/week)
                              └──→ 7–10 tweets/day across 3 X accounts
```

**Scanner pipeline flow:**

```
Technical Screening ──→ Thematic Analysis ──→ Investment Gate ──→ Deep Due Diligence ──→ Portfolio Updates ──→ Output Generation
(Sterling Grid)         (Gate 1: Sonnet)      (Gate 2: Sonnet)    (Gate 3: Opus)          (DD-PASS only)       (signals.json,
 5 conditions on                                                   Can VETO Gate 2                               newsletter,
 same weekly bar)                                                                                                email, Sheets)
```

---

## A3. Core Principles

**Winners only.** Every piece of public content celebrates strength: gains, breakouts, momentum, receipts. Losses are never mentioned. If a position is down, don't mention it — find the one that's up. Pullbacks are framed as opportunities, not damage.

**Specificity breeds credibility.** "$AMPX at $12.44 cleared all gates" beats "scanner found 2 signals" every time. Every data-dependent piece of content contains at least one $TICKER with a price.

**Receipts culture.** Show entry prices, current prices, percentage gains. Reference past calls.

**Proprietary methodology stays private.** Internal indicator names, formulas, scoring mechanics, and gate internals are never exposed in public content.

**React to the market.** Content reflects current conditions. A Monday morning tweet could not have been written on Friday.

**Three voices, one system.** The tweet system uses three distinct personas. The Substack system has its own unified editorial voice. Both draw from the same data.

---

# PART B — SCANNER PIPELINE (Stock Scanning & Selection)

---

## B4. Technical Screening (Sterling Grid)

### B4.1 Entry Signal — ALL 5 conditions must fire on the SAME weekly bar

**Files:** `core/sterling_indicators.py` (backtest-validated), `core/scanner.py` (production integration)

| # | Condition | Formula | Notes |
|---|-----------|---------|-------|
| 1 | **HMA(21) slope rising** | `HMA[i] > HMA[i-1]` | Applied to HL2 on weekly bars. HMA = `WMA(2×WMA(n/2) − WMA(n), √n)` where n=21 |
| 2 | **RSI(14) > 50** | Wilder's smoothing: `ewm(alpha=1/14, adjust=False)` | Practically redundant (100% met when HMA bullish). Kept as safety filter. |
| 3 | **MACD(12,26,9) cross-up** | `(MACD > Signal) AND (MACD.shift(1) <= Signal.shift(1))` | **SINGLE BAR EVENT.** Must cross THIS bar, not within last 3 bars. |
| 4 | **UC rising above** | `UC > UC.shift(1) AND UC > 0` | UC = `clip(1.5 × (RSI(10) − 50), 0, 20)`. RSI-derived, **NOT** VWAP. |
| 5 | **Price < $25** | Simple filter | Backtest universe constraint. |

**Weekly resampling:** Daily OHLCV → Weekly (Friday close) via `resample('W-FRI')`

**Data source:** yfinance (1 year daily data, resampled to weekly)

**Ticker universe:** `complete_tickers.txt` (1–6 character alphanumeric symbols)

> ⚠️ **CRITICAL CORRECTION:** Production scanner's "Banker" uses VWAP formula `((Close/VWAP_20)−1)×100+50`. This is DIFFERENT from backtest UC. Scanner needs updating to use RSI-derived UC for consistency with backtest.

### B4.2 Exit Signals — FIRST to fire triggers exit

**Files:** `core/sterling_indicators.py` → `generate_exit_signal()` and `check_profit_lock()`

**Mechanism 1 — ExD (Compound Trend Reversal):**
HMA(21) slope falling AND UC falling, both on same weekly bar. Catches true trend end vs normal pullback noise.

**Mechanism 2 — Tiered Profit Lock (based on CURRENT return, NOT peak):**

| Current Return from Entry | Trail % from Peak | Lock Level |
|--------------------------|-------------------|------------|
| ≥ +200% | 15% | Exit if price drops 15% from highest weekly close |
| ≥ +100% (but < +200%) | 20% | Exit if price drops 20% from peak |
| ≥ +50% (but < +100%) | 25% | Exit if price drops 25% from peak |
| < +50% | No lock | Only ExD can trigger exit |

> ⚠️ **Tiers DEGRADE on pullbacks.** A stock at +250% (15% trail) that pulls back to +90% current return → tier loosens to 20% trail. Below +50% current return → lock deactivates entirely. This is intentional — gives stocks room to recover.

**Why no fixed stop loss:** Backtest showed fixed −30% stops triggered on 48% of trades; 48% of those recovered. Average opportunity cost: +127% per stopped trade. One stopped trade would have returned +1,104%.

### B4.3 Indicator Calculations (Exact Formulas)

**HMA(21):**
```python
half = 10, sqrt_n = 4
HMA = WMA(2 × WMA(HL2, 10) − WMA(HL2, 21), 4)
slope_rising = HMA[i] > HMA[i-1]
```

**RSI(14):**
```python
avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
RSI = 100 − 100 / (1 + avg_gain / avg_loss)
```

**MACD(12,26,9):**
```python
MACD_line = EMA(close, 12) − EMA(close, 26)
Signal_line = EMA(MACD_line, 9)
cross_up = (MACD > Signal) AND (MACD.shift(1) <= Signal.shift(1))
```

**Undercurrent (UC):**
```python
length = round(50 / 5.0)  # = 10 (weekly divisor)
RSI_10 = RSI(close, 10)   # Wilder's smoothing
UC = clip(1.5 × (RSI_10 − 50), 0, 20)
```

UC behavior lookup:
- RSI(10) ≤ 50.0 → UC = 0.0 (bearish/neutral)
- RSI(10) = 55.0 → UC = 7.5 (mild bullish)
- RSI(10) = 60.0 → UC = 15.0 (strong bullish)
- RSI(10) ≥ 63.3 → UC = 20.0 (maximum)

### B4.4 Position Sizing (Conviction-Tiered)

**File:** `core/sterling_indicators.py` → `calculate_position_size()`

**Recommended configuration:** 15% × 6 positions with conviction tiers

| Gate Verdict | Conviction Score | Position Size | Max Slots |
|-------------|-----------------|--------------|-----------|
| STRONG BUY | 8–10 | 20% of equity | 2 |
| STRONG BUY | 7 | 15% of equity | 3 |
| SPEC BUY | 4–6 | 8% of equity | 2 |

**Risk limits:** Maximum deployment 90% (10% cash minimum), maximum 6 concurrent positions, sector concentration cap of 3 positions per sector.

**Gear-shift protocol:** After 6 months or 15 completed trades, evaluate:
- Gear UP if: win rate >65%, avg winner >+50%, no trade lost >−30%, drawdown <−15%
- Gear DOWN if: win rate <50%, avg loser worse than −25%, drawdown >−20%
- PAUSE if: 3+ consecutive losses, drawdown >−25%, market regime shift

---

## B5. Thematic Analysis (Gate 1)

### Purpose

Identify top investable themes in current market, then map stocks to themes and score fit quality.

**File:** `core/thematic_analyzer.py`
**Model:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)
**Cost:** ~$0.30–0.80 per run (with web search), ~$0.15 without

### B5.1 Step 1 — Theme Identification

Outputs 5–10 themes ranked by composite score.

**Theme classification tiers:**

| Classification | Score | Meaning |
|---------------|-------|---------|
| PRIME | ≥ 7.5 | High conviction, strong catalysts + momentum |
| INVESTABLE | ≥ 6.0 | Good opportunity, standard sizing |
| SELECTIVE | ≥ 4.5 | Mixed signals, only best stocks in theme |
| AVOID | < 4.5 | Fading momentum or overcrowded |

**Scoring factors (0–10 each):**
1. **Catalyst Score** — Near-term events driving re-rating
2. **Momentum Score** — Price action, fund flows, search trends
3. **Crowding Score** — Inverse: lower = more crowded
4. **Runway Score** — Multi-year growth potential
5. **Capital Health Score** — Valuation regime health (**VETO if ≤ 3**)

Composite = weighted average of factors 1–4. Capital Health is veto-only (not averaged).

**Theme types:** TREND (mainstream momentum), BOTTLENECK (second-order plays), CONTRARIAN (out-of-favor with catalyst — preferred for asymmetry).

**Valuation regime classification:**
- **OPTIONALITY** — Pre-revenue, milestone-driven
- **FUNDAMENTAL** — Revenue/earnings-driven
- **TRANSITION** — Shifting from optionality to fundamental (highest risk)

> ⚠️ **Capital Health Veto:** If Capital Health ≤ 3, theme is capped at SELECTIVE regardless of composite score. Prevents investing in late-cycle themes with deteriorating fundamentals.

### B5.2 Step 2 — Ticker-to-Theme Mapping

Maps each technically-passing stock to a theme.

**Verdict options:** STRONG FIT, GOOD FIT, WEAK FIT, NO FIT

**Scoring (0–10 each):** Theme Fit Score, Company Position Score, Stock Setup Score

**Pass criteria:**
- Verdict: STRONG FIT or GOOD FIT
- Theme classification: PRIME or INVESTABLE
- Both must be true

**Relaxed pass (for broader screening):** STRONG FIT + SELECTIVE theme allowed; GOOD FIT requires PRIME or INVESTABLE.

**Red flags checked:** Earnings within 7 days, short interest >20%, recent SEC investigations, auditor resignations.

---

## B6. Investment Gate (Gate 2)

### Purpose

Single comprehensive assessment: "Should I buy this stock on Monday?"

**File:** `core/investment_gate.py`
**Model:** Claude Sonnet 4
**Cost:** ~$0.15–0.25 per stock (single call with web search)

### B6.1 Four-Phase Analysis

**Phase 1 — Disqualifier Screen:** SEC investigations, shelf offerings, imminent earnings (within 7 days), recent dilution, management issues. Output: CLEAN / MINOR / SEVERE red flags.

**Phase 2 — Catalyst Validation:** What drives the next move? Analyst trend (BULLISH/NEUTRAL/BEARISH), short interest, earnings revision trajectory (ACCELERATING/STABLE/DECELERATING/NEGATIVE/N/A). Output: Catalyst present (yes/no), days to catalyst.

**Phase 3 — Return Validation:** Specific math to +50% return (regime-adapted), steelmanned bear case, bear rebuttal, downside floor. Output: Math to 50%, bear case, bull case.

**Phase 4 — Synthesis:** Top 3 bullish factors, top 3 risks, kill switch (what triggers early exit), 2–3 sentence reasoning. Output: Verdict + conviction + action.

### B6.2 Verdict Framework

| Verdict | Conviction | Criteria | Position Size |
|---------|-----------|----------|---------------|
| STRONG BUY | 7–10 | Clear catalyst + clean setup + math works + bear rebuttable | 15–20% |
| SPEC BUY | 4–6 | Thesis intact but execution-dependent, higher uncertainty | 8% (reduced) |
| NO GO | 1–3 | Fatal flaw, no catalyst, math doesn't work, bear > bull | 0% (skip) |

### B6.3 Regime-Aware Analysis

**OPTIONALITY regime (pre-revenue):** Focus on milestone velocity, funding, narrative expansion. Math: Milestone → narrative expansion → institutional re-rating. Risk: Can go to zero.

**FUNDAMENTAL regime (revenue/earnings-driven):** Focus on revenue growth, operating leverage, earnings revisions, multiple expansion. Math: EPS growth × multiple expansion = target. Red flag: Capex growing 3× faster than revenue. Key metric: Earnings revision trajectory.

**TRANSITION regime:** Highest risk — market changing what it values. Key question: Is revenue materializing fast enough to justify optionality-era valuation?

### B6.4 Web Search Strategy

5 targeted searches per stock:
1. Recent earnings, revenue trends, guidance
2. Upcoming catalysts (earnings dates, product launches, regulatory)
3. Short thesis and risks
4. Valuation metrics, peer comparisons
5. Insider activity, dilution history

---

## B7. Deep Due Diligence (Gate 3)

### Purpose

Final veto power + newsletter content generation. Runs ONLY on stocks that passed Investment Gate (typically 1–3 stocks).

**File:** `core/deep_dd.py`
**Model:** Claude Opus 4 (`claude-opus-4-20250514`)
**Extended thinking:** 10,000 token budget
**Cost:** ~$1–2 per stock (but only 1–3 stocks, so $2–5 total per scan)

### B7.1 Two Jobs

**Job 1 — Newsletter content production:**
- Elevator pitch (2–3 sentences)
- Why now (key catalyst with date)
- The math (path to +50%, regime-adapted)
- Bear case (steelmanned)
- Bear rebuttal
- Risk to monitor (single most important)
- Action recommendation

**Job 2 — Final portfolio gate:**
- Can VETO Investment Gate pass if deep analysis reveals issues
- Only DD-PASS stocks get added to portfolio
- Prevents false positives from automated screening

### B7.2 Research Protocol

**Phase 1 — Growth trajectory:** Regime-adapted analysis (FUNDAMENTAL: revenue acceleration, operating leverage, NRR; OPTIONALITY: milestones, funding, partnerships; TRANSITION: revenue vs expectations).

**Phase 2 — Catalyst deep dive:** Earnings dates, guidance updates, product launches, regulatory decisions, conference presentations, management equity grants.

**Phase 3 — Bear case investigation:** #1 smart short seller argument, attempt to dismantle with data, assess if fatal flaw.

**Phase 4 — Valuation & return math:** Current multiple vs 3-year average and peers, construct specific math: growth + re-rating = target, identify downside floor.

### B7.3 Output Structure

**Verdict:** STRONG BUY / SPEC BUY / NO GO

**Newsletter fields:** `elevator_pitch`, `why_now`, `the_math`, `bear_case`, `bear_rebuttal`, `risk_to_monitor`, `action_recommendation`

**Deep analysis fields:** `revenue_trajectory`, `earnings_leverage`, `catalyst_timeline`, `variant_perception`, `key_assumption`, `kill_switch`, `downside_floor`

**Fatal flaw (if NO GO):** `fatal_flaw` + `reconsider_if`

### B7.4 Integration with Pipeline

Function `apply_dd_to_stocks()` maps DD results to Stock dataclass fields (`dd_verdict`, `dd_conviction`, `dd_position_size`, `dd_elevator_pitch`, etc.).

**Portfolio update logic:** Only stocks with `dd_verdict` in ("STRONG BUY", "SPEC BUY") get added via `add_trade_to_portfolio()`.

---

## B8. Portfolio Tracking

### B8.1 Portfolio Manager

**File:** `core/portfolio_manager.py`

**Data structure:** Unified `portfolio.csv` combining open and closed positions.

**CSV fields:** `ticker`, `status` (OPEN/CLOSED/STOPPED), `entry_date`, `entry_price`, `exit_date`, `exit_price`, `highest_close`, `theme`, `tier`, `signal_type`, `conviction` (1–10), `notes`, `stop_pct`, `position_size_pct`, `position_dollars`, `sizing_gear`

**Calculated fields (computed on load, not stored):** `current_price`, `pnl_pct`, `pnl_usd`, `stop_level`, `days_held`, `distance_to_stop_pct`, `stop_alert` (true if within 5% of stop)

**Key functions:**
- `add_trade_to_portfolio(stock)` — Maps conviction → position size tier, records entry, status = OPEN
- `flag_exit(symbol, exit_price, reason)` — Marks for exit, status = CLOSED or STOPPED
- `update_prices()` — Fetches live prices via yfinance, recalculates P&L, triggers stop alerts
- `export_for_google_sheets()` — Creates CSV with GOOGLEFINANCE formulas for live tracking

### B8.2 Equity Curve Tracking

**File:** `equity_curve.csv` (compounding NAV over time)

**Fields:** `date`, `nav`, `cash`, `invested`, `total_deployed`, `open_count`, `total_return_pct`, `spy_value`, `spy_return_pct`, `alpha_pct`, `qqq_value`, `qqq_return_pct`, `alpha_vs_qqq_pct`

**Update frequency:** After each scanner run (weekly)

**Compounding logic:** Starting capital £5,000 per position. Closed trade profits reinvested. NAV = cash + sum(current value of open positions). Benchmark: SPY and QQQ from inception date.

### B8.3 Performance Metrics

**Function:** `get_performance_summary()`

**Closed trades:** Win rate, average winner/loser, profit factor, max drawdown (from equity curve).

**Open positions:** Current P&L distribution, days held distribution, stop alerts (within 5% of stop).

---

## B9. Scanner Output Generation

### B9.1 signals.json

**File:** `scanner/output/signals.json` (current week) + `scanner/output/archive/YYYY-WNN/signals.json` (archive)

**Key sections:**

```json
{
  "timestamp": "...",
  "timeframe": "WEEKLY",
  "entry_criteria": "Sterling Grid: HMA slope↑ + RSI>50 + MACD cross-up + UC rising + Price<$25 + Theme + Investment Gate PASS",
  "exit_criteria": "ExD compound exit (HMA falling + UC falling) OR tiered profit lock (+200%→15%, +100%→20%, +50%→25%)",
  "stats": { "tickers_loaded", "price_under_cap", "buy_signal", "technical_signals", "theme_confirmed", "final_trade", "final_consider" },
  "themes": [ { "name", "rank", "classification", "theme_type", "composite_score", "thesis_summary", "key_catalysts", "valuation_regime" } ],
  "pass_signals": [ { "symbol", "tier", "price", "indicators...", "theme...", "gate...", "dd...", "position sizing...", "action" } ],
  "consider_signals": [ ... ],
  "sell_signals": [ { "symbol", "price", "reason", "entry_price", "highest_close", "pnl_pct" } ],
  "assessed_signals": [ ... ],
  "historical_winners": [], "big_wins": [], "home_runs": []
}
```

**Consumed by:** `tweet_generator.py`, `substack_content_generator.py`, `newsletter_compiler.py`

### B9.2 newsletter_briefing.md

**File:** `scanner/output/current/newsletter_briefing.md` (current) + `scanner/output/archive/YYYY-WNN/newsletter_briefing.md` (archive)

**Sections:** Market Context (placeholder), Hot Themes This Week, Signal Candidates (PASS and CONSIDER), Portfolio Update, Compounding Equity, Due Diligence placeholders.

**Privacy rules:**
- Entry prices for OPEN positions are **PRIVATE** (not shown in newsletter)
- Only show: ticker, theme, current P&L%, days held, stop distance
- Entry prices shown ONLY for closed trades or positions >25% gain

### B9.3 Email Notification

**Function:** `send_notification()` in `core/scanner.py`

Triggers on: new PASS signals, new CONSIDER signals, exit signals (ExD or profit lock).

**SMTP config:** Via environment variables (`EMAIL_SENDER`, `EMAIL_PASSWORD`, `EMAIL_RECIPIENTS`).

### B9.4 Google Sheets Export

**File:** `portfolio/output/portfolio_google_sheets.csv`

Adds `GOOGLEFINANCE` formulas for live current_price, pnl_pct, pnl_usd, stop_level, distance_to_stop with conditional formatting for stop alerts.

---

## B10. Daily Scanner (Separate Pipeline)

Lightweight daily scanner for intraday BoS signals. **Completely separate from weekly pipeline.**

**File:** `core/daily_scanner.py`

**Key differences from weekly:**
- HMA/BoS computed on DAILY bars (no weekly resample)
- NO thematic analysis, NO Investment Gate, NO Deep DD
- Max 5 new signals per day (ranked by Banker score)
- Separate portfolio: `portfolio/output/daily_portfolio.csv`
- Uses LEGACY indicators from `core/legacy_indicators.py` (HMA Pivot BoS + Banker)

**Legacy indicators (preserved for daily scanner only):**
- `calculate_banker()` — VWAP-based: `((Close/VWAP_20)−1)×100+50`
- `calculate_hma()` — Standard HMA on daily bars
- `find_pivots()` — Pivot high/low detection
- `calculate_bos()` — HMA Pivot BoS method (NOT Sterling Grid slope method)

> ⚠️ Weekly scanner uses Sterling Grid indicators from `core/sterling_indicators.py`. Daily scanner uses legacy indicators from `core/legacy_indicators.py`. Do NOT mix.

---

## B11. Backtest Validation

**Source files:** `src/indicators.py`, `src/v2_signals.py`, `src/v3_exits.py`

**Validation method:** Line-by-line comparison of `core/sterling_indicators.py` vs backtest source. Exact formula matching for HMA, RSI, MACD, UC. Signal generation and profit lock logic verified identical.

**Key corrections made during validation:**
1. UC is RSI-derived, NOT VWAP (scanner needs updating)
2. MACD cross-up is single bar, NOT 3-bar lookback
3. Profit lock tiers based on CURRENT return, NOT peak (tiers degrade)

### Results (V4, 10×10 sizing, 2018–2025)

| Metric | Value |
|--------|-------|
| Total return | +633% |
| Win rate | 79% (CI: 71%–88%) |
| Avg return per trade | +85.8% (CI: +57.7% to +118.7%) |
| Profit factor | 15.9 |
| Max drawdown | −7.2% |
| Trades | 82 over 7 years (~12/year) |
| Avg hold | 24 weeks median, 56 weeks mean |

### Walk-Forward Validation

4/4 out-of-sample windows profitable (100%): 2022 +7.4%, 2023 +92.1%, 2024 +63.6%, 2025 +53.1%. Average OOS: +54.1% per year.

### Concentration Risk

Top 5 trades = 81% of total P&L. RIOT alone = 33% of total P&L. 63% of P&L from crypto (40%) + clean energy (23%). System depends on capturing rare 500%+ moves. If these themes cool, returns will be below expectations.

### Forward Expectations (15×6 sizing)

25–40% CAGR, −12 to −22% max drawdown, moderate psychological tolerance required.

---

# PART C — SUBSTACK CONTENT GENERATION

---

## C12. Substack System Overview

Sterling Signals publishes a momentum trading newsletter on Substack. The content generation system takes weekly scanner output (signals, themes, portfolio data, market analysis) and produces 2–3 polished, visually engaging Substack posts per week. Each post serves a distinct purpose, uses the same underlying data, but is independently valuable to readers.

> *This system covers Substack post generation only. Tweet/X content generation is a separate system and must not share code paths, templates, or CLI entrypoints with this system.*

### Current Pain Points

- Monolithic 1,300-line `substack_content_generator.py` mixes data loading, LLM prompting, HTML generation, sanitization, and CLI orchestration
- `newsletter_compiler.py` duplicates ~60% of the same logic
- `substack_notes_generator.py` outputs plain text, not visual HTML — inconsistent with post format
- `dd_post_generator.py` uses a completely different design system (dark theme) from main posts (light theme)
- Visual element injection is fragile: marker-based ([SCAN_FUNNEL], [THEME_SCORES]) depends on LLM outputting exact tokens
- No shared HTML component library — same table/card/badge styles copy-pasted across 4 files
- Sanitization and banned-term checking duplicated in every generator

### Target Architecture

| Layer | Responsibility |
|-------|---------------|
| **Data Layer** | Load signals.json, portfolio.csv, equity_curve.csv, market_analysis.md into shared ContentContext dataclass. Single source of truth. |
| **Prompt Layer** | Post-type-specific prompt builders. Each returns a structured prompt string. No data loading logic. |
| **LLM Layer** | Single function: send prompt, get markdown back. Handles retries, cost tracking, fallback. |
| **Visual Layer** | Shared HTML component library (cards, tables, funnels, badges, charts). Deterministic — no LLM involved. |
| **Safety Layer** | Single sanitize-and-validate pipeline: banned terms, negative P&L scrub, marketing vocabulary check. |
| **Output Layer** | Markdown → HTML conversion, template wrapping, dual-write to current/ + weekly archive. |
| **CLI Layer** | Single entrypoint: `python -m content.substack` with --saturday, --tuesday, --thursday, --all flags. |

---

## C13. Content Calendar & Post Definitions

Each week, the system produces exactly 2–3 posts depending on whether the scanner found GREEN signals. The content calendar branches on a single boolean: did the scanner produce any PASS signals?

### Scenario A: GREEN Signals Exist (pass_count > 0)

| Day | Post Type | Focus | Word Count |
|-----|-----------|-------|------------|
| **Saturday** | Weekly Recap | Market + scan + signals + themes | 1,200–1,500 words |
| **Tuesday** | Theme Deep Dive | Top PRIME theme analysis | 800–1,200 words |
| **Thursday** | Signal Deep Dive (DD) | Narrative on top GREEN signal | 800–1,200 words |

### Scenario B: No GREEN Signals (pass_count = 0)

| Day | Post Type | Focus | Word Count |
|-----|-----------|-------|------------|
| **Saturday** | Weekly Recap | Market + scan + themes + selectivity | 1,200–1,500 words |
| **Tuesday** | Theme Deep Dive | Top PRIME theme analysis | 800–1,200 words |
| **Thursday** | Portfolio Spotlight | Performance, winners, benchmarks | 800–1,200 words |

> *Key principle: each post must stand alone. A reader who only sees the Tuesday post should get a complete, valuable experience without needing Saturday's recap.*

---

## C14. Post Specifications

### C14.1 Saturday: Weekly Recap

**Filename:** `saturday_weekly_recap.html`

**Purpose:** The flagship weekly post. Covers everything that happened this week in one comprehensive overview.

**Required Sections (in order):**
1. Title & subtitle (auto-generated from week number + hook)
2. Market Context — 3–4 paragraphs of market data (from market_analyzer output)
3. Scanner Results — scan funnel visual + commentary on selectivity
4. Theme Analysis — PRIME/INVESTABLE theme cards with scores and catalysts
5. Signals OR Selectivity — GREEN signal summaries if any, or "why we passed" narrative
6. Performance Snapshot — winners table + benchmark comparison (SPY, NASDAQ)
7. Looking Ahead — catalysts for next week
8. Footer — disclaimer + subscribe CTA

**Required Visual Elements:**
- Scan funnel bar chart (Universe → Technical Gates → Theme Confirmed → GREEN Signals)
- Theme score cards (name, classification badge, composite score, catalyst/momentum progress bars)
- Winners table (ticker, theme, P&L%) — only positions above 15% threshold
- Performance comparison table (Portfolio vs SPY vs NASDAQ)
- Stock chart images where available (from chart_manifest.json)

### C14.2 Tuesday: Theme Deep Dive

**Filename:** `tuesday_theme_deep_dive.html`

**Purpose:** Educational content that explains the #1 PRIME theme in depth. Should read like a sector research note, not a data dump. Readers learn something valuable even if they don't trade.

**Required Sections (in order):**
1. Title (Theme Watch: [Theme Name])
2. Opening hook — why this theme matters RIGHT NOW (specific catalyst)
3. Investment thesis — accessible explanation of the theme dynamics
4. Scoring breakdown — theme card visual + sub-score analysis
5. Key catalysts — specific upcoming events, dates, data points
6. Risks to thesis — balanced but not bearish
7. What we're watching — triggers for next week
8. Footer — disclaimer + subscribe CTA

**Required Visual Elements:**
- Theme score card (large format with all sub-scores: catalyst, momentum, crowding, runway)
- Historical trend indicator if theme appeared in prior weeks (rising/falling/stable)
- Optional: comparison table of related stocks in the theme

### C14.3 Thursday (Signals): Signal Deep Dive

**Filename:** `thursday_dd_[TICKER].html`

**Purpose:** Narrative investment memo for the top GREEN signal. Tells the story of why this stock cleared all gates. Only generated when pass_count > 0.

**Required Sections (in order):**
1. Title (Deep Dive: $TICKER)
2. Opening hook — compelling reason this stock caught attention
3. The Thesis — why this is a GREEN signal (synthesize all DD data)
4. The Math — return potential with specific numbers
5. The Bear Case — honest assessment + why still bullish
6. Risk to Monitor — the single biggest risk
7. Our View — confident summary
8. Footer — disclaimer + subscribe CTA

**Required Visual Elements:**
- Signal header card (ticker, price, theme, conviction badge, classification)
- Stock chart image (from chart_manifest)
- Bull/bear comparison card
- Key stats grid (price, theme, conviction, classification)

### C14.4 Thursday (No Signals): Portfolio Spotlight

**Filename:** `thursday_portfolio_spotlight.html`

**Purpose:** Performance-focused post showcasing winning positions and benchmark outperformance. Reinforces the system's discipline.

**Required Sections (in order):**
1. Title (Portfolio Spotlight: [Hook])
2. Portfolio summary — how we're performing vs benchmarks
3. Top winners — spotlight 3–5 positions with themes
4. Performance vs benchmarks — SPY and NASDAQ comparison table
5. System discipline — why patience and selectivity matter
6. Looking ahead — themes and setups for next week
7. Footer — disclaimer + subscribe CTA

**Required Visual Elements:**
- Winners table (ticker, theme, P&L%) — only 15%+ positions
- Performance comparison table (Portfolio vs SPY vs NASDAQ with alpha)
- Equity curve chart (if portfolio_visual integration available)

---

## C15. Visual Design System

All posts use a single, consistent visual language. The design must work when screenshotted and pasted into Substack's editor as images — therefore all visual elements are rendered as self-contained HTML with inline styles.

### C15.1 Design Theme

The default production theme is light (white background, dark text) matching Substack's native appearance. The dark theme from dd_post_generator.py and portfolio_visual.py is reserved for standalone social media screenshots (X/Twitter), not Substack posts.

| Element | Light Theme (Substack) | Dark Theme (Social Only) |
|---------|----------------------|------------------------|
| **Background** | #FFFFFF | #111827 |
| **Text** | #333333 | #F9FAFB |
| **Accent (GREEN signal)** | #16A34A | #22C55E / #2DD4BF |
| **Accent (badges)** | PRIME: #22C55E, INVESTABLE: #F59E0B | Same |
| **Card background** | #F9FAFB, border #E5E7EB | #1F2937, border #374151 |
| **Max width** | 680px | 900px |

### C15.2 Shared HTML Components

These components must be extracted into a single shared module (`content/html_components.py`) and used by all post generators.

| Component | Description | Used In |
|-----------|-------------|---------|
| `scan_funnel()` | Horizontal bar chart: Universe → Technical → Theme → GREEN | Saturday recap |
| `theme_card()` | Score card with name, badge, composite score, sub-score progress bars, thesis excerpt | Saturday, Tuesday |
| `winners_table()` | Table: ticker, theme, P&L%. Only 15%+ positions. Entry price shown only if 25%+. | Saturday, Thursday portfolio |
| `performance_table()` | Comparison: Portfolio vs SPY vs NASDAQ with alpha calculation | Saturday, Thursday portfolio |
| `signal_badge()` | GREEN SIGNAL / ON OUR RADAR badge with appropriate color | Thursday DD, Saturday |
| `stat_grid()` | 2×2 or 3×2 grid of stat boxes (price, theme, conviction, classification) | Thursday DD |
| `bull_bear_card()` | Two-column card: bullish factors (green) vs bear case (amber) | Thursday DD |
| `callout_box()` | Highlighted blockquote with left border accent for key insights | All posts |
| `chart_embed()` | Chart image with caption, sourced from chart_manifest.json base64 or file path | Saturday, Thursday DD |

---

## C16. Substack Technical Specifications

### C16.1 Data Flow

1. Scanner runs Friday night → produces signals.json (themes, buy_signals, assessed_signals, stats)
2. market_analyzer.py runs → produces market_analysis.md (via Claude + web search)
3. Portfolio manager updates → portfolio.csv, equity_curve.csv with latest prices
4. Chart capture runs → chart_manifest.json with base64-encoded stock charts
5. `content/substack.py --all` invoked → loads all data into ContentContext
6. Calendar logic determines which 2–3 posts to generate
7. For each post: build prompt → call LLM → inject visuals → sanitize → validate → save HTML

### C16.2 ContentContext Dataclass

Single source of truth for all generators. Populated once by data_loader.py:

| Field | Type | Source |
|-------|------|--------|
| `signals` | Dict | signals.json (full raw data) |
| `themes` | List[Dict] | signals["themes"] — scored and classified |
| `buy_signals` | List[Dict] | Filtered to PASS/TRADE decisions only |
| `assessed_signals` | List[Dict] | All assessed signals incl. failures |
| `market_analysis` | str | market_analysis.md content |
| `portfolio_stats` | Dict | equity_curve.csv latest row |
| `historical_winners` | List[Dict] | Open positions with 15%+ gain |
| `theme_history` | Dict | Last 4 weeks of theme scores for trend |
| `chart_manifest` | Dict | Ticker → chart file path mapping |
| `scan_stats` | Dict | Scanner statistics (counts at each gate) |
| `week_number` | int | ISO week number |
| `pass_count` | int | len(buy_signals) — drives calendar branching |

### C16.3 LLM Configuration

| Parameter | Value |
|-----------|-------|
| **Model** | claude-sonnet-4-20250514 (Sonnet 4) |
| **Max tokens** | 4,000 per post |
| **Web search** | Enabled for market_analyzer.py only. Disabled for post generation. |
| **Cost budget** | ~$0.05–$0.15 per post. Target <$0.50/week for 3 posts. |
| **Fallback** | If LLM fails, generate data-only post using template (no prose, just visuals + data). |

### C16.4 Output Paths

Every generated file is dual-written:
- **Current:** `substack/output/current/substack_posts/[filename].html` — always the latest version
- **Archive:** `scanner/output/archive/YYYY-WNN/substack_posts/[filename].html` — permanent weekly record

---

## C17. Substack Module Structure

The refactored `content/` directory:

| File | Status | Responsibility |
|------|--------|---------------|
| `content/__init__.py` | | |
| `content/substack.py` | NEW | CLI entrypoint. Replaces substack_content_generator.py CLI and newsletter_compiler.py CLI. |
| `content/data_loader.py` | NEW | All data loading. Builds ContentContext. |
| `content/prompts.py` | NEW | All LLM prompt builders (system prompt + per-post-type user prompts). |
| `content/llm.py` | NEW | Single generate_post() function. Handles API call, cost tracking, retries, fallback. |
| `content/html_components.py` | NEW | Shared visual HTML components. |
| `content/html_template.py` | NEW | Light-theme HTML wrapper + markdown-to-HTML converter. |
| `content/safety.py` | NEW | Sanitization pipeline: sanitize_text(), scrub_llm_output(), validate_post_content(). |
| `content/calendar.py` | NEW | Content calendar logic: determine_content_calendar(). |
| `content/market_analyzer.py` | KEEP | Standalone market analysis with web search. |
| `content/portfolio_visual.py` | KEEP | Dark-theme portfolio dashboard for social screenshots. |
| `content/morning_briefing.py` | KEEP | Data assembly for Editorial Board. |

**Files to Deprecate:**
- `newsletter_compiler.py` → Merged into substack.py + data_loader.py + html_template.py
- `substack_content_generator.py` → Broken apart into modules above
- `dd_post_generator.py` → DD generation folded into prompts.py + html_components.py
- `substack_notes_generator.py` → Upgrade to HTML or deprecate in favor of 3-post system

---

## C18. Substack Implementation Plan

**Phase 1: Extract Shared Components** — Create html_components.py, safety.py, html_template.py. Update existing generators to import from new modules (no behavior change). Test: diff against known-good outputs.

**Phase 2: Unify Data Loading** — Create data_loader.py with single `build_content_context()` function. Merge duplicate load functions. Test: verify all data sources load correctly with missing files gracefully handled.

**Phase 3: Refactor Generators** — Create prompts.py, llm.py, calendar.py. Wire into existing substack_content_generator.py (verify parity). Test: full --all run, compare outputs.

**Phase 4: New CLI Entrypoint** — Create content/substack.py. Deprecate old entrypoints with import redirects (backward compat for 2 weeks). Update calling scripts / Makefile / cron. Test: end-to-end scanner → market analysis → substack --all → 3 HTML files.

**Phase 5: Deprecate Old Files** — Remove old files. Archive in git tag. Update README.

---

# PART D — AUTOMATED TWEET SYSTEM

---

## D19. Tweet System Overview & Philosophy

### What this system does

Generates and posts 7–10 tweets per day across 3 X/Twitter accounts, using live market data gathered every 2–3 hours to create contextual, timely content that reads like three distinct real traders' feeds — not a scheduling tool. Each account has its own persona, posting schedule, and content emphasis.

### What this system replaced

The old batch system generated ~35 tweets every Friday using that Friday's scanner data, then posted them mechanically throughout the week. Zero market awareness, high repetition, robotic tone. The three accounts received trivially reworded versions of the same content.

### Style guide deference rule

**This PRD is authoritative.** `FINTWIT_STYLE_GUIDE.md` contains useful examples and patterns but was originally written for the older batch system. Where the style guide conflicts with this PRD — particularly around category names, scheduling logic, or tone rules — this PRD wins.

### What feeds INTO this system (do not modify)

- `friday_scan.yml` → runs the scanner every Friday, produces `signals.json` and updates `portfolio.csv`
- The scanner pipeline (scanner.py, portfolio_tracker.py, etc.) is completely separate and must not be modified

---

## D20. Tweet Architecture

```
EVERY 2–3 HOURS (via GitHub Actions cron — 5 weekday slots + 2 weekend)

┌──────────────────────────────────────────────────────────┐
│ Step 1: GATHER CONTEXT (Grok 4 Fast via xAI Responses API) │
│   Inputs:  portfolio.csv, signals.json, tracked themes     │
│   Queries: X Search + Web Search                           │
│   Output:  twitter/output/live_context.json                        │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Step 2: GENERATE TWEETS (Claude Sonnet 4.5)               │
│   Decides category + assigns different tickers per account │
│   Produces: 3 account variants                            │
│   Validates: 14-step pipeline per variant                 │
│   Output:  Appends to twitter/output/live_content_queue.json      │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Step 3: GENERATE CHARTS (Chart-IMG REST API)              │
│   1200×675 TradingView chart PNGs                         │
│   Output: twitter/output/charts/live_{TICKER}_{timestamp}.png     │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Step 4: POST TWEETS (Tweepy v1.1 media + v2 text)        │
│   Posts to X with media, marks queue items as "posted"    │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Step 5: COMMIT STATE (git add/commit/push)                │
│   State persists between runs via repo                    │
└──────────────────────────────────────────────────────────┘
```

---

## D21. Tweet Pipeline: Step-by-Step

### Step 1: Context Gathering (`content/live_context_gatherer.py`)

**Model:** `grok-4-fast-non-reasoning` via xAI Responses API
**Endpoint:** `https://api.x.ai/v1/responses`
**Tools:** `web_search` + `x_search` (server-side agent tools)
**Cost:** ~$0.01–0.02 per call

The gatherer assesses:
1. **Market snapshot:** SPY/QQQ/VIX direction, overall mood (risk-on/off/mixed)
2. **Portfolio movers:** Which positions are moving today? By how much?
3. **Theme activity:** Are tracked themes in the news?
4. **FinTwit buzz:** Trending tickers and topics on X
5. **News events:** Earnings, macro data, policy announcements
6. **Tweet opportunities:** Based on all above, what kind of tweet should we post?

Output: `twitter/output/live_context.json` with `gathered_at` timestamp.

**Staleness threshold:** If >4 hours old, generator flags `context_stale: true` and avoids MARKET_REACTION tweets.

### Step 2: Tweet Generation (`content/live_tweet_generator.py`)

**Model:** `claude-sonnet-4-5-20250929` (Claude Sonnet 4.5)
**Cost:** ~$0.02–0.05 per call (3 variants in one call)

Single API call:
1. Reads all inputs: live_context.json, portfolio.csv, signals.json, FINTWIT_STYLE_GUIDE.md, this PRD
2. Decides the category based on what's happening now
3. Assigns different tickers/angles per account
4. Generates 3 variants (one per persona)
5. Outputs structured JSON: text, category, primary_ticker, chart_recommended, account

Each variant passes 14-step validation. Invalid tweets regenerated up to 2 times. Valid tweets appended to `twitter/output/live_content_queue.json` with status `"pending"`.

### Step 3: Chart Generation (`content/chart_generator.py`)

**API:** chart-img.com REST API (Pro tier, $7/month)
**Resolution:** 1200×675 pixels (16:9, Twitter-optimal)
**Default interval:** 1W (weekly chart)

Finds pending items with `chart_recommended: true` and `chart_path: null`, generates PNGs, saves to `twitter/output/charts/`. **Chart failures never block posting.**

### Step 4: Tweet Posting (`distribution/twitter_poster.py`)

**API:** Twitter/X API v1.1 (media upload) + v2 (tweet posting) via Tweepy.

Multi-account variant mapping: `main` → `variant_1`, `account2` → `variant_2`, `account3` → `variant_3`

### Step 5: State Commit

GitHub Actions workflow commits updated queue and context files back to the repo.

---

## D22. Tweet Categories & Decision Logic

The system doesn't follow a schedule of categories. It **observes market conditions and decides** what to post.

### Live Categories

**MARKET_REACTION** — Trigger: Significant market move (SPY ±1%, sector rotation, breaking news). Required: $TICKER, price movement, why it matters. Chart: Recommended. Freshness: Requires live context (<4h).

**RECEIPT** — Trigger: Portfolio position showing notable gain (>5% from entry or milestone). Required: $TICKER, entry price, current price, % gain. Chart: Always. Freshness: Works with any context.

**SIGNAL_ALERT** — Trigger: New buy signal from scanner or recent entry (within 7 days). Required: $TICKER, entry price, brief thesis. Chart: Always. Priority: HIGH before Monday open.

**DIP_OPPORTUNITY** — Trigger: Market pullback creating buying opportunity. Required: Market context, $TICKER, opportunity framing. Chart: Recommended. Freshness: Requires live context.

**THEME_MOMENTUM** — Trigger: Broad theme strength across multiple positions. Required: Theme name, 3+ $TICKERs with current prices. Validation: Must use portfolio holdings grouped by theme with entry/current/gain.

### Shared Categories

**EDUCATIONAL** — Trigger: Midday/after-hours slots. Required: Concrete example with $TICKER + price, clear lesson. Limit: Max 3/week. Critical: Must receive accurate portfolio stats, must NEVER fabricate negative portfolio claims.

**ENGAGEMENT** — Trigger: Milestone, weekend, low-news periods. Required: Trading-adjacent, community-focused.

**NEWSLETTER_CTA** — Max 1/day, usually after-hours or weekend. Lead with value, reference specific content.

**WATCHLIST** — Trigger: CONSIDER signals from scanner only. Critical: If no CONSIDER signals, skip — never substitute PASS signals.

**TECHNICAL_ANALYSIS** — Trigger: Open positions with clear price levels. Required: $TICKER, support/resistance, invalidation criteria. Chart: Conditional (text-only acceptable if no chart exists).

### Decision priority (what to post when)

1. **New signals exist (< 48h old)?** → SIGNAL_ALERT
2. **Portfolio position up >5% today?** → RECEIPT
3. **Market dropping >1%?** → DIP_OPPORTUNITY
4. **Market up and portfolio leading?** → MARKET_REACTION
5. **Theme showing broad strength?** → THEME_MOMENTUM
6. **None of the above?** → EDUCATIONAL, ENGAGEMENT, or NEWSLETTER_CTA

### Category balance targets (per week, across all accounts)

| Category | Target | Min | Max |
|----------|--------|-----|-----|
| RECEIPT / PERFORMANCE | 25% | 15% | 35% |
| SIGNAL_ALERT | 15% | 10% | 25% |
| MARKET_REACTION | 15% | 5% | 25% |
| THEME_MOMENTUM | 10% | 5% | 20% |
| DIP_OPPORTUNITY | 5% | 0% | 15% |
| TECHNICAL_ANALYSIS | 10% | 5% | 15% |
| EDUCATIONAL | 8% | 5% | 12% |
| ENGAGEMENT | 5% | 3% | 10% |
| NEWSLETTER_CTA | 5% | 3% | 7% |
| WATCHLIST | 5% | 0% | 10% |

---

## D23. Voice, Tone & Style

### Universal rules (all three accounts)

- **Lead with $TICKER and price.** Never reference a stock without its ticker symbol and a number.
- **Short, punchy sentences.** Line breaks between thoughts. Let data breathe.
- **Active voice.** "$WCC ripping +4%" not "A gain of 4% was observed in WCC"
- **No emoji overuse.** 👇 for chart references, 🔥 occasionally. Never more than 1–2 per tweet.
- **Minimal disclaimers.** IMO, NFA, DYOR — sparingly, at the end.
- **Under 280 characters.** Hard limit. Shorter is better.
- **Numbers stand alone.** Percentages and prices on their own lines where possible.
- **Sound like a trader, not an AI.** Use natural FinTwit language.
- **Winners only in framing.** Even when discussing risk or pullbacks, frame as opportunity.

### FinTwit language patterns (use naturally across all accounts)

**Technical levels:**
- "Break above $X = game on" / "Break below $X = setup invalidated"
- "Gold zone support holding" / "Just a gold retest"
- "Silver resistance" / "Cleared the purple"
- "Blue diamonds" (buy signals) / "Pink diamonds" (sell signals) / "Triple blue diamonds" (strong confirmation)
- "Easy invalidation on a close below $X"
- "Bears are wrong unless this breaks"

**Receipts and proof:**
- "Happy [X]% to those who celebrate!"
- "For those who followed..."
- "$TICKER from $X to $Y" (clean receipt format)
- "One proper swing can change your life"

**Hooks and CTAs:**
- "Probably want to save this post" / "Save these tickers and thank me later"
- "Will keep updating..." / "Will update when I see..."
- "Guess which one's my favorite" / "Revisit this post soonish"

**Framing:**
- "If you missed [X]... [Y] might be next"
- "Trade the theme that you have, not the theme that you want"
- "When in doubt, zoom out"
- "Maybe I'm right. Maybe I'm wrong. NFA!"

**Market commentary:**
- "Showing strength on a red day" / "Green while indices are red"
- "Copper/[theme] catching a bid" / "That tells you everything you need to know"

### Content structure patterns

**Signal Announcement:** `$TICKER at $PRICE — [context] / [Brief thesis] / [Chart attached / Will update]`

**Performance Receipt:** `$MOD from $184 to $215 (+17%) / $WCC from $281 to $315 (+12%)`

**Theme → Ticker List:** `[Theme statement] / [Ticker list with prices] / [Hook/CTA]`

**Technical Update:** `$TICKER [observation] / [Specific level] / [Invalidation] / [Chart / Will update]`

**Dip Commentary:** `[Market observation] / [Why it's opportunity] / [Specific tickers/themes]`

---

## D24. Multi-Account Strategy — Three Personas

| Account | Persona | Archetype | Tone | Focus |
|---------|---------|-----------|------|-------|
| **Main** (variant_1) | Alex / "The System" | Analyst | Authoritative, precise, data-driven, confident | Scanner results, signal announcements, system performance, receipts, theme rankings |
| **Account 2** (variant_2) | Rozalia / "The Mentor" | Teacher | Conversational, approachable, encouraging, wise | Educational, trading psychology, dip commentary, theme context |
| **Account 3** (variant_3) | James / "The Trader" | Practitioner | Direct, casual, punchy, action-oriented | Real-time market color, quick takes, momentum plays, level calls |

### Persona voice guides

**Alex (Main):** Leads with data, follows with interpretation. Most likely to include theme rankings and multi-ticker lists. References specific technical levels precisely. Uses "Chart attached 👇" or "Save this list". Avoids slang, excessive emojis, hype.

**Rozalia (Account 2):** Explains the WHY behind trades. Uses FinTwit wisdom phrases: "One proper swing can change your life", "When in doubt, zoom out". Encourages independent thinking: "Make your own decision. NFA". More likely to frame dips as opportunity with context.

**James (Account 3):** Quick, punchy — often 1–3 lines. Real-time energy during market hours. Shortest, most direct phrasing. Casual technical references: "Bears are wrong unless this breaks". Less hedging, more conviction.

### How variants are generated

Single Claude Sonnet call generates all 3 simultaneously:
- Different primary tickers per account (where data allows)
- Different voice, sentence structure, framing per persona
- Different opening hooks — no two share the same first line
- NFA disclaimer on at most 1 of 3
- Cross-variant dedup: <70% text similarity
- If only one ticker available, accounts share ticker but use genuinely different angles

### Posting stagger

- Main (Alex): posts at cron trigger time
- Account 2 (Rozalia): offset by +10 minutes
- Account 3 (James): offset by +20 minutes

---

## D25. Slot Collision Prevention

### Rules

**Rule 1: Different primary tickers per slot (preferred).** Each account's variant within a single time slot should focus on a different primary ticker.

**Rule 2: Different category/angle when ticker must overlap.** When data is limited, accounts may share a ticker ONLY IF each uses a genuinely different category OR angle, and text similarity <70%.

**Rule 3: Stagger same-ticker mentions across time.** If Account 1 posts about $TICKER at 10:00am, Accounts 2 & 3 should avoid until next slot minimum.

**Rule 4: Theme diversification across accounts.** When posting THEME_MOMENTUM, each account emphasizes a different theme when possible.

### Implementation

The `_prepare_slot_data()` function should:
1. Gather all available tickers with postable content
2. Rank by priority (new signals > big movers > theme strength)
3. Assign top 3 different tickers to 3 accounts
4. If only 1–2 tickers available, assign different categories/angles
5. Record `primary_ticker` per variant for dedup checking
6. Never assign same primary_ticker to 2+ variants unless forced AND each uses different category

---

## D26. Tweet Scheduling & Frequency

### Weekday schedule (Monday–Friday)

| Slot | ET Time | UTC Cron | Purpose | Best Categories |
|------|---------|----------|---------|-----------------|
| 1 | 07:30 | `30 12` | Pre-market scan | SIGNAL_ALERT, WATCHLIST |
| 2 | 10:00 | `0 15` | Morning movers | MARKET_REACTION, RECEIPT |
| 3 | 12:30 | `30 17` | Midday | THEME_MOMENTUM, EDUCATIONAL, DIP_OPPORTUNITY |
| 4 | 15:30 | `30 20` | Power hour | MARKET_REACTION, RECEIPT |
| 5 | 18:00 | `0 23` | After-hours wrap | EDUCATIONAL, ENGAGEMENT, NEWSLETTER_CTA |

### Weekend schedule (Saturday–Sunday)

| Slot | ET Time | UTC Cron | Purpose | Best Categories |
|------|---------|----------|---------|-----------------|
| W1 | 10:00 | `0 15` | Weekend morning | RECEIPT (weekly recap), EDUCATIONAL |
| W2 | 16:00 | `0 21` | Weekend afternoon | ENGAGEMENT, NEWSLETTER_CTA, SIGNAL_ALERT (Sunday pre-Monday) |

### Volume

- **Hard cap:** `MAX_TWEETS_PER_DAY = 12` across all accounts, `WEEKEND_MAX_TWEETS = 4`
- **Cron note:** UTC times assume EST (UTC−5). Adjust by −1hr when EDT starts (~March).

---

## D27. Charts & Visual Content (Tweets)

### When charts are required

| Category | Chart | Why |
|----------|-------|-----|
| SIGNAL_ALERT | **Always** | Entry level and pattern |
| RECEIPT | **Always** | Entry vs current — the proof |
| TECHNICAL_ANALYSIS | **If available** | Text-only acceptable if no chart file |
| MARKET_REACTION | Recommended | Visual context |
| THEME_MOMENTUM | Optional | Nice for primary ticker |
| DIP_OPPORTUNITY | Recommended | Shows the dip |
| EDUCATIONAL | If referencing setup | Depends on content |
| ENGAGEMENT | No | Text-focused |
| NEWSLETTER_CTA | No | CTA, no chart |

### Specifications

- **API:** chart-img.com v2 Advanced Chart (Pro, $7/month)
- **Resolution:** 1200×675 px (16:9, Twitter-optimal)
- **Default interval:** 1W — override to 1D or 4H per ticker
- **Format:** PNG, saved to `twitter/output/charts/`
- **Failure:** Text-only fallback. Charts never block posting.

---

## D28. Content Freshness & Anti-Repetition

### Anti-repetition rules

| Rule | Enforcement |
|------|-------------|
| Same ticker cooldown | Max 3/day across all accounts, min 3h between same-ticker on same account |
| Category variety | No consecutive same category on same account |
| Cross-variant dedup | <70% similarity between accounts in same slot |
| Slot collision | Different primary_ticker per account per slot |
| Queue dedup | <80% similarity to last 48h tweets |
| Different openings | Each variant starts differently |
| Phrase rotation | Power phrases rotated, not repeated within 48h |
| EDUCATIONAL cap | Max 3/week |

### Dynamic content markers

1. Reference today's price action: "$WCC up 2.5% today"
2. Reference market mood: "Markets mixed but infrastructure holding green"
3. Reference news events: "Infrastructure bill passed the House"
4. Reference FinTwit buzz: "Everyone's talking about copper today"
5. Reference SPY/QQQ: "SPY down −1.2% but our portfolio green"
6. Reference time of day: "Power hour" / "Into the close" / "After the bell"

---

## D29. Tweet Validation Pipeline

Every tweet passes 14-step validation. Failures trigger regeneration (max 2 retries).

| Step | Check | Fail Action |
|------|-------|-------------|
| 1 | Character count ≤ 280 | Truncate or regenerate |
| 2 | $TICKER present with price (data-dependent categories) | Regenerate |
| 3 | Banned phrases (78 terms + 24 phrases) | Regenerate |
| 4 | Loser focus (loss/decline language) | Regenerate |
| 5 | Internal terminology (Sterling Signals, 5-gate, etc.) | Replace or regenerate |
| 6 | Category alignment — content matches declared category | Reclassify or regenerate |
| 7 | Chart flag — SIGNAL_ALERT/RECEIPT get chart_recommended=true | Auto-fix |
| 8 | Cross-variant dedup — <70% between accounts | Regenerate most similar |
| **8.5** | **Slot collision — same primary_ticker on 2+ variants** | **Regenerate duplicate with different ticker** |
| 9 | Queue dedup — <80% vs last 48h | Regenerate |
| 10 | Ticker accuracy — primary_ticker in portfolio/signals | Regenerate |
| 11 | Meta-language detection — LLM refusals, placeholders | Regenerate |
| 12 | Portfolio fabrication — false claims about gains/losses | Regenerate |
| 13 | Data exhaustion — _prepare_slot_data() returns None | Skip slot |
| 14 | Winner framing — no dwelling on losses, negative framing | Regenerate |

---

## D30. Weekend & Off-Hours Behavior

- **Weekend max:** 4 tweets/day across all accounts
- **Allowed:** EDUCATIONAL, ENGAGEMENT, NEWSLETTER_CTA, RECEIPT, SIGNAL_ALERT (Sunday only)
- **Blocked:** MARKET_REACTION, DIP_OPPORTUNITY (markets closed)
- **Saturday AM:** Weekly receipt/recap. **Saturday PM:** Educational.
- **Sunday AM:** Engagement. **Sunday PM:** SIGNAL_ALERT for Monday (highest priority).
- **Holidays:** Context gatherer returns empty intraday data → natural steer to EDUCATIONAL/ENGAGEMENT.

---

## D31. Priority Rules & Signal Urgency

### New signal priority (CRITICAL)

1. **Sunday evening (Slot W2):** SIGNAL_ALERT top priority — followers need tickers before Monday open
2. **Monday pre-market (Slot 1):** Reinforce with chart
3. **Monday morning (Slot 2):** If moving, switch to RECEIPT/MARKET_REACTION

### Concurrent priorities

1. SIGNAL_ALERT (actionable, time-sensitive)
2. RECEIPT (proof, engagement driver)
3. MARKET_REACTION (context)

---

# PART E — SHARED SYSTEMS & RULES

---

## E32. Marketing & Safety Rules

These rules are non-negotiable and enforced across ALL public content — Substack, tweets, and email.

### E32.1 Signal Branding

| Internal Term | Public Term |
|--------------|-------------|
| PASS signal | "GREEN signal" |
| CONSIDER signal | "On our radar" |
| SKIP signal | (never mentioned) |
| STOPPED | "Systematic exit" or "exit discipline" |
| System description | "Proprietary 5-gate screening system" |

**Buy signals:** "GREEN signal" only. Never TEAL, PASS, VIOLET, AMBER, purple.

### E32.2 Winner-Only Policy

- NEVER mention losing positions or display negative P&L in any public content
- NEVER display a number with a minus sign + percent (e.g., −5.2%)
- Only showcase positions above 15% gain threshold
- Entry prices shown only for positions with 25%+ gains
- If portfolio is down overall, focus on methodology and patience

### E32.3 Banned Terminology

The complete banned list lives in `config/banned_terms.py` (single source of truth).

**Never use in public content:**

- **Internal indicator names:** HMA, Hull Moving Average, UC, Undercurrent, BoS, Break of Structure, RSI, MACD, KDJ, VWAP, ExD, Gatekeeper
- **Internal scoring:** conviction score (1–10), theme scoring internals, 5-gate (when referring to internal mechanics), trailing stop percentages, Tier 1/2/3, profit lock, gear shift
- **Account-specific:** Roth IRA, PDT, UK ISA
- **Vague assertions:** "trust the process", "system keeps working", "quality over quantity"
- **Loser focus:** "still bleeding", "dragging down", "unfortunate loss", "the red one", "stubborn loser"
- **Empty promises:** "big news coming", "stay tuned for something special", "you won't believe"
- **LLM meta-language:** "I cannot generate", "please provide", "$TICKER" (literal placeholder)
- **Corporate/AI voice:** "it's worth noting", "it's important to remember", "as always", "navigating the landscape"
- **Old batch system:** "scanner found", "2 survivors", "some interesting setups"

**Use instead:**
- "Proprietary 5-gate screening system", "Structural trend confirmation", "Institutional accumulation", "Momentum confirmation", "Systematic exit discipline"
- "High conviction" / "Standard" / "Speculative" (not numbers)

### E32.4 Sanitization Pipeline

Every piece of public content must pass through before saving:

1. **Term mapping** — INTERNAL_TERMINOLOGY_MAP replaces internal terms with public alternatives
2. **Negative P&L scrub** — regex strips sentences containing −X.X% patterns
3. **STOPPED scrub** — regex strips sentences containing STOPPED
4. **Banned phrase check** — `check_banned_phrases()` scans for ALL_BANNED terms
5. **Marketing vocabulary validation** — `validate_content()` for approved language

**File:** `config/banned_terms.py` — Functions: `check_banned_phrases()`, `validate_content()`, `sanitize_text()`

Applied to: all newsletter content, all tweet content, all Substack posts, email notifications.

---

## E33. Data Accuracy & Anti-Fabrication

### Rule 1: Zero fabricated tickers
Every $TICKER in data-dependent content must exist in portfolio.csv or signals.json.

### Rule 2: Zero fabricated portfolio claims
EDUCATIONAL tweets receive accurate portfolio stats. Must never claim "zero gains" when profitable positions exist.

### Rule 3: PERFORMANCE generates when gains exist
When portfolio has positions ≥10%, at least 1 RECEIPT/PERFORMANCE tweet per day.

### Rule 4: WATCHLIST uses correct source
WATCHLIST pulls from consider_signals only. Never substitute pass_signals.

### Rule 5: Graceful data exhaustion
Slots are skipped (not force-filled) when data is exhausted for a category.

### Rule 6: No temporal hallucinations
Weekend tweets must not reference live market action. After-hours tweets must not say "markets are ripping."

### Rule 7: Winners-only framing is not fabrication
Choosing to highlight a +16% winner while omitting a −5% loser is editorial curation, not dishonesty. The system is a highlights reel. But it must never claim a losing position is winning.

---

## E34. Critical System Invariants

### 🔴 DO NOT CHANGE (backtest-validated, requires full re-backtest to alter)

1. **Sterling Grid entry conditions** — ALL 5 on same bar: HMA slope rising (NOT HMA Pivot BoS), RSI(14) > 50, MACD cross-up (single bar, NOT 3-bar lookback), UC rising above (RSI-derived, NOT VWAP Banker), Price < $25
2. **Exit conditions** — First to fire: ExD (HMA falling AND UC falling, same bar) OR tiered profit lock based on CURRENT return (tiers degrade on pullback)
3. **Profit lock thresholds** — ≥+200% → 15% trail, ≥+100% → 20% trail, ≥+50% → 25% trail, <+50% → no lock
4. **Undercurrent formula** — `UC = clip(1.5 × (RSI(10) − 50), 0, 20)` — NOT VWAP-based Banker
5. **MACD cross-up** — Single bar event: `(MACD > Signal) AND (MACD.shift(1) <= Signal.shift(1))` — NOT 3-bar lookback
6. **Weekly timeframe** — System designed for weekly bars. Daily scanner is separate pipeline. DO NOT mix timeframes.
7. **Price cap ($25)** — Backtest universe constraint. Changing invalidates results.
8. **HMA period (21)** — Optimized for weekly momentum. DO NOT change without full re-backtest.
9. **MACD parameters (12,26,9)** — Standard settings. Changing breaks signal timing.
10. **RSI periods** — 14 for entry, 10 for UC. Backtest-validated.
11. **Profit lock tier breakpoints** — +50%, +100%, +200% and 25%, 20%, 15% trail percentages.

### 🟡 DO NOT CHANGE (pipeline integrity)

1. **Gate pipeline order** — Technical → Thematic → Investment Gate → Deep DD → Portfolio. Deep DD has veto power. Only DD-PASS signals added to portfolio.
2. **Valuation regime awareness** — OPTIONALITY/FUNDAMENTAL/TRANSITION. Analysis MUST adapt to regime.
3. **Theme classification veto** — Capital Health ≤ 3 → cap at SELECTIVE.
4. **Position sizing conviction tiers** — 8–10 → 20% (max 2), 7 → 15% (max 3), 4–6 → 8% (max 2). Max 6 concurrent, 10% cash minimum.
5. **Output file paths** — Current: `scanner/output/current/`, Archive: `scanner/output/archive/YYYY-WNN/`, Portfolio: `portfolio/output/portfolio.csv`, Equity curve: `portfolio/output/equity_curve.csv`, Sheets: `portfolio/output/portfolio_google_sheets.csv`

### 🟢 SAFE TO CHANGE (with testing)

1. **Ticker universe** — `complete_tickers.txt` can be updated (keep 1–6 char alphanumeric)
2. **LLM models** — Thematic/Gate: Sonnet 4 (can upgrade). DD: Opus 4 (can upgrade). DO NOT downgrade to Haiku.
3. **Web search settings** — `use_web_search` flag (default False for cost control)
4. **Position sizing gear** — Conservative (10×8) / Recommended (15×6) / Aggressive (20×5). Do not exceed 25% per position.
5. **Theme count** — Default 5, can increase to 10. Do not decrease below 3.
6. **Newsletter content** — Formatting, section order, prose style. Do not change data fields or privacy rules.
7. **Email recipients** — Environment variable `EMAIL_RECIPIENTS`

---

## E35. File Locations (All Systems)

### Core Scanner Pipeline

| Component | File | Description |
|-----------|------|-------------|
| Technical screening | `core/sterling_indicators.py` | Backtest-validated indicator calculations |
| | `core/scanner.py` | Production weekly scanner (main entrypoint) |
| | `core/legacy_indicators.py` | Old BoS/Banker for daily scanner only |
| LLM Gates | `core/thematic_analyzer.py` | Gate 1: Theme identification + stock mapping |
| | `core/investment_gate.py` | Gate 2: Regime-aware quality assessment |
| | `core/deep_dd.py` | Gate 3: Opus deep analysis + newsletter content |
| Portfolio | `core/portfolio_manager.py` | Unified trade tracking + equity curve |
| | `portfolio/output/portfolio.csv` | Master portfolio file |
| | `portfolio/output/equity_curve.csv` | Compounding NAV over time |
| | `portfolio/output/portfolio_google_sheets.csv` | Export with live formulas |
| Daily scanner | `core/daily_scanner.py` | Separate daily pipeline |
| | `portfolio/output/daily_portfolio.csv` | Daily positions (separate from weekly) |

### Substack Content System

| File | Status | Description |
|------|--------|-------------|
| `content/substack.py` | NEW | CLI entrypoint |
| `content/data_loader.py` | NEW | Builds ContentContext |
| `content/prompts.py` | NEW | LLM prompt builders |
| `content/llm.py` | NEW | Single generate_post() function |
| `content/html_components.py` | NEW | Shared HTML components |
| `content/html_template.py` | NEW | Light-theme HTML wrapper |
| `content/safety.py` | NEW | Sanitization pipeline |
| `content/calendar.py` | NEW | Content calendar logic |
| `content/market_analyzer.py` | KEEP | Market analysis with web search |
| `content/portfolio_visual.py` | KEEP | Dark-theme social screenshots |
| `content/morning_briefing.py` | KEEP | Editorial Board data assembly |

### Tweet System

| File | Purpose |
|------|---------|
| `content/live_context_gatherer.py` | Grok API → live market context |
| `content/live_tweet_generator.py` | Claude API → tweet variants + validation |
| `content/chart_generator.py` | Chart-IMG API → chart PNGs |
| `distribution/twitter_poster.py` | Tweepy → post to X |
| `.github/workflows/live_tweet.yml` | GitHub Actions cron workflow |
| `twitter/output/live_content_queue.json` | Tweet queue (runtime) |
| `twitter/output/live_context.json` | Grok context (runtime) |
| `twitter/output/charts/` | Chart PNGs (runtime) |
| `twitter/output/live_cost_log.json` | API cost tracking (runtime) |

### Configuration

| File | Contents |
|------|----------|
| `config/__init__.py` | All thresholds, parameters, paths |
| `config/banned_terms.py` | Marketing terminology filters |
| `config/output_paths.py` | Weekly folder structure |
| `config/settings.py` | Tweet system technical configuration |

### Do Not Modify

| File | Why |
|------|-----|
| `.github/workflows/friday_scan.yml` | Upstream scanner pipeline |
| `core/scanner.py` | Scanner logic (from tweet system perspective) |
| `core/portfolio_tracker.py` | Portfolio tracking |

---

## E36. Configuration Reference (All Systems)

### Scanner Constants

```python
PRICE_CAP = 25.0
HMA_PERIOD = 21
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
UC_TARGET_DAYS = 50
UC_SENSITIVITY = 1.5
LOCK_TIERS = [(2.00, 0.15), (1.00, 0.20), (0.50, 0.25)]
MAX_CONCURRENT_POSITIONS = 6
MIN_CASH_RESERVE_PCT = 0.10
```

### Tweet System Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| `MODEL_CONTEXT` | `grok-4-fast-non-reasoning` | Context gathering |
| `MODEL_LIVE_TWEET` | `claude-sonnet-4-5-20250929` | Tweet generation |
| `CHART_IMG_WIDTH` | `1200` | Chart width px |
| `CHART_IMG_HEIGHT` | `675` | Chart height px |
| `MAX_TWEETS_PER_DAY` | `12` | Hard cap all accounts |
| `MAX_SAME_TICKER_PER_DAY` | `3` | Per-ticker limit (all accounts) |
| `MIN_HOURS_BETWEEN_SAME_TICKER` | `3` | Ticker cooldown (per account) |
| `CONTEXT_STALENESS_HOURS` | `4` | Max context age |
| `DAILY_COST_LIMIT_USD` | `1.00` | Cost kill switch |
| `WEEKEND_MAX_TWEETS` | `4` | Weekend daily cap |

### Tracked Themes

```
copper, infrastructure, defense, AI, data centers,
rare earth, quantum computing, space, crypto mining,
nuclear, semiconductors, reshoring
```

---

## E37. Environment Variables & Secrets

### Required (configured)

| Secret | Service | Status |
|--------|---------|--------|
| `ANTHROPIC_API_KEY` | Claude Sonnet 4 / 4.5 / Opus 4 | ✅ |
| `XAI_API_KEY` | xAI Grok | ✅ |
| `CHARTIMG_API_KEY` | Chart-IMG Pro | ✅ |
| `X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_SECRET` | Account 1 (Alex) | ✅ |
| `EMAIL_SENDER` / `EMAIL_PASSWORD` / `EMAIL_RECIPIENTS` | SMTP notifications | ✅ |

### Pending

| Secret | Service | Status |
|--------|---------|--------|
| `X2_*` credentials | Account 2 (Rozalia) | ⏳ |
| `X3_*` credentials | Account 3 (James) | ⏳ |
| `TRADINGVIEW_SESSION_*` / `TRADINGVIEW_LAYOUT_ID` | Custom charts | ⏳ Optional |

---

## E38. Cost Controls

### Scanner Pipeline
- Gate 1 (Thematic): ~$0.15–0.80 per run
- Gate 2 (Investment): ~$0.15–0.25 per stock
- Gate 3 (Deep DD): ~$1–2 per stock ($2–5 total per scan)

### Substack Content
- ~$0.05–$0.15 per post
- Target <$0.50/week for 3 posts

### Tweet System
- Per cycle: ~$0.04–0.08
- Monthly estimate: ~$16.50 ($9.50 API + $7 Chart-IMG)
- Daily limit: $1.00 (generation halts if exceeded)
- Monthly alert: $30.00
- Cost logged to: `twitter/output/live_cost_log.json`

---

## E39. Command-Line Usage

### Weekly Scanner

```bash
# Production scan (full pipeline with web search)
python -m core.scanner --web-search

# Testing (no LLM, no cost)
python -m core.scanner --no-llm

# Quick scan (top 100 tickers, no DD)
python -m core.scanner --top 100 --no-dd
```

**All flags:** `--no-llm`, `--no-dd`, `--no-email`, `--no-prompts`, `--web-search`, `--assess-top N`, `--top N`, `--verbose`, `--archive`, `--dry-run`

### Sterling Indicators (Standalone)

```bash
# Signal scan
python sterling_indicators.py MARA RKLB IONQ

# Position check
python sterling_indicators.py --check MARA:5.50 RKLB:12.00

# Portfolio status
python sterling_indicators.py --portfolio 120000 MARA:5.50:9 RKLB:12.00:7

# Position size calculator
python sterling_indicators.py --size 120000 8

# History dump
python sterling_indicators.py --history MARA
```

### Portfolio Manager

```bash
python portfolio_manager.py --update     # Update live prices
python portfolio_manager.py --export     # Export for Google Sheets
python portfolio_manager.py --report     # Print summary
python portfolio_manager.py --migrate    # Migrate from old format
```

### Daily Scanner

```bash
python -m core.daily_scanner             # Full daily scan
python -m core.daily_scanner --dry-run   # Show signals without writing
python -m core.daily_scanner --top 100   # Limit to top 100 by beta
```

### Substack Content

```bash
python -m content.substack --all         # Auto-detect + generate all posts
python -m content.substack --saturday    # Saturday weekly recap only
python -m content.substack --tuesday     # Tuesday theme deep dive only
python -m content.substack --thursday    # Thursday post (auto-detected)
python -m content.substack --dry-run     # Show what would generate
python -m content.substack --no-llm      # Data-only posts (no prose)
python -m content.substack --preview     # Open HTML in browser after saving
python -m content.substack --signals PATH  # Use specific signals.json
```

### Tweet System

```bash
# Via GitHub Actions: "Live Tweet Generation" → "Run workflow"
# dry_run: true → verify pipeline without posting
# dry_run: false → post to X
```

---

## E40. Testing & Verification

### Scanner Quick Checks

Run with `--no-llm` to verify technical screening without API cost. Check signals.json for correct structure.

### Substack Verification

- 2–3 self-contained HTML files generated per week with visual elements
- Each post stands alone
- No banned terms (validated by safety.py)
- No negative P&L
- Consistent light-theme design
- Cost under $0.50/week

### Tweet System Health Checks

1. **Context fresh?** `gathered_at` within 4 hours
2. **Queue has pending items?** Fresh items, varied categories, all 3 accounts
3. **Charts generating?** Recent PNGs > 20KB in `twitter/output/charts/`
4. **Tweets posting?** Recent `posted_at` timestamps, verify on X
5. **No banned terms?** Run checker against queue
6. **Category variety?** At least 6 categories represented
7. **Cross-account differentiation?** Three distinct variants per batch, <70% similarity
8. **Different tickers per slot?** `primary_ticker` differs across variants in same batch
9. **PERFORMANCE when gains exist?** RECEIPT tweets present when portfolio has >10% winners
10. **GitHub Actions green?** Check workflow runs
11. **Winner framing?** No loss-dwelling language in any posted tweets

### Tweet System Rollback

- **Quick disable (2 min):** Comment out cron lines in `live_tweet.yml`, commit + push
- **Re-enable batch (5 min):** Uncomment cron in `daily_post.yml`, commit + push
- **Zero interference:** Live and batch systems use separate queue files

---

## E41. Acceptance Criteria (All Systems)

### Scanner Pipeline
- [ ] All 5 Sterling Grid conditions validated against backtest formulas
- [ ] Gate pipeline order enforced: Technical → Thematic → Investment Gate → Deep DD → Portfolio
- [ ] Only DD-PASS stocks added to portfolio
- [ ] signals.json contains all required sections
- [ ] Profit lock tiers degrade based on CURRENT return

### Substack Content
- [ ] 2–3 self-contained HTML files per week
- [ ] Each post stands alone
- [ ] No banned terms in output
- [ ] No negative P&L in output
- [ ] Consistent light-theme visual design
- [ ] Single CLI entrypoint: `python -m content.substack --all`
- [ ] Cost under $0.50/week
- [ ] Graceful degradation with missing data
- [ ] No tweet/X code entanglement
- [ ] Backward compatibility during transition

### Tweet System — Architecture
- [ ] Grok uses Responses API with `grok-4-fast-non-reasoning`
- [ ] Tweet generation uses `claude-sonnet-4-5-20250929`
- [ ] Charts 1200×675 via chart-img.com
- [ ] 5 weekday + 2 weekend cron slots active
- [ ] Batch system disabled, `friday_scan.yml` untouched
- [ ] State commits back to repo

### Tweet System — Quality
- [ ] Every data-dependent tweet has $TICKER with price
- [ ] RECEIPT shows entry → current → % gain
- [ ] SIGNAL_ALERT appears before Monday open
- [ ] Zero banned terms, all under 280 chars
- [ ] Sounds like real FinTwit traders, not AI
- [ ] Winners-only framing

### Tweet System — Multi-Account
- [ ] Three distinct persona variants per cycle
- [ ] <70% text similarity between any two
- [ ] Different primary_ticker per account per slot (when data allows)
- [ ] Posting stagger: +0 / +10 / +20 minutes
- [ ] NFA on at most 1 of 3

### Tweet System — Anti-Repetition
- [ ] Max 3 same-ticker tweets/day (all accounts)
- [ ] Min 3h between same-ticker (per account)
- [ ] <80% similarity to last 48h
- [ ] No consecutive same category (per account)

### Tweet System — Data Integrity
- [ ] Zero fabricated tickers or portfolio claims
- [ ] Graceful data exhaustion (skip, don't invent)
- [ ] Weekend tweets don't reference live market
- [ ] Daily cost tracked, $1.00/day limit enforced

---

## E42. Known Limitations & Future Work

### Scanner Pipeline
- UC production formula uses VWAP (needs updating to RSI-derived for backtest consistency)
- Concentration risk: top 5 trades = 81% of P&L
- System depends on capturing rare 500%+ moves

### Substack Content
- Monolithic code needs refactoring per Phase 1–5 plan
- No automatic Substack publishing via API (manual copy-paste)
- No subscriber analytics or A/B testing
- Substack Notes generation (plain text) — evaluate upgrade or deprecation

### Tweet System — Current Limitations
1. Account 1 only active (2 & 3 need X API credentials)
2. No quote tweets or threads
3. Default chart styling (no custom TradingView indicators)
4. EDT/EST manual cron adjustment needed
5. No sell signal automation (only after Friday scan)
6. No reply management

### Tweet System — Future Enhancements (Prioritized)
1. Activate Accounts 2 & 3
2. Custom TradingView chart layouts
3. Quote tweet receipts
4. Thread support (weekly recaps)
5. Dynamic chart intervals (1D/1W/4H)
6. Custom theme graphics
7. Telegram/Slack failure alerts
8. Automatic DST adjustment
9. Automated Grok trending feed
10. Reply management skill

---

## Integration Points Summary

### Scanner → Substack

**Input:** `scanner/output/signals.json`
**Consumers:** `substack_content_generator.py`, `newsletter_compiler.py`, `dd_post_generator.py`
**Key fields:** `pass_signals`, `themes`, `sell_signals`, DD fields (`dd_elevator_pitch`, `dd_why_now`, `dd_the_math`, `dd_bear_case`)

### Scanner → Tweet System

**Input:** `scanner/output/signals.json`
**Consumer:** `content/live_tweet_generator.py`
**Key fields:** `pass_signals`, `themes`, `assessed_signals`, `consider_signals`

### Portfolio → Both Content Systems

**Function:** `add_trade_to_portfolio(stock)` in `core/portfolio_manager.py`
**Mapping:** `ticker = stock.symbol`, `entry_price = stock.price`, `theme = stock.theme`, `conviction = stock.dd_conviction`, `position_size_pct = stock.position_size_pct`
**Consumed by:** Both Substack (winners table, performance) and tweets (receipts, theme momentum)

### Exit Signal Processing

**Function:** `check_sell_signals(stocks)` in `core/scanner.py`
**Logic:** Load open positions → check ExD + profit lock → flag exits → SellSignal objects → signals.json + email notification

---

*End of Master PRD. This document should be consulted before modifying any core pipeline, content generation, or distribution file. When subsystem PRDs conflict with this document, this document is authoritative.*

# BoS Momentum Scanner V6 — Pipeline Reference

**Version:** V6.0 (post-P0/P1/P2/P3 fixes, February 2026)
**Purpose:** This document is the authoritative reference for what each pipeline stage does, what it should achieve, and how to diagnose issues when reviewing scanner output. Use it at the start of any analysis session.

---

## Architecture Overview

```
complete_tickers.txt (800+ micro/small-cap tickers, <$25)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Steps 1–5: DATA + TECHNICAL GATES (scanner.py)     │
│  Load tickers → Download data → Sterling Grid V6    │
│  indicators → Filter → Quality tier assignment       │
│  ~800 → ~5-15 technical signals                     │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Step 6: THEMATIC GATE (thematic_analyzer.py)       │
│  Step 1: Discover 5 macro themes (Sonnet)           │
│  Step 2: Map tickers to themes + fit scoring        │
│  Step 2b: Orphan rescue for mismatched tickers      │
│  ~15 → ~5-10 theme-confirmed signals                │
│  Model: claude-sonnet-4 + web search                │
│  Cost: ~$0.50-1.50 per run                          │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Step 7: INVESTMENT GATE (investment_gate.py)        │
│  Regime-aware quality assessment per stock           │
│  Verdict: STRONG BUY / SPEC BUY / NO GO             │
│  ~10 → ~1-4 gate passes                             │
│  Model: claude-sonnet-4 + web search                │
│  Cost: ~$0.30-0.80 per run                          │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Step 7.5: DEEP DD (deep_dd.py)                     │
│  Opus deep analysis with extended thinking           │
│  Can VETO investment gate pass                       │
│  Produces newsletter content                        │
│  ~4 → ~1-3 DD-confirmed trades                      │
│  Model: claude-opus-4 + extended thinking + web      │
│  Cost: ~$1-2 per stock ($2-5 total per run)         │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Step 8: SELL SIGNALS (scanner.py)                  │
│  ExD compound exit + Tiered profit lock              │
│  Scans ALL open portfolio positions                  │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  OUTPUT: Reports, Portfolio, Newsletter Briefing     │
│  Terminal report, text report, signals.json          │
│  Newsletter briefing (.md), analysis_log.csv         │
│  Portfolio update (open_positions.json)              │
│  Email notification                                 │
└─────────────────────────────────────────────────────┘
```

---

## Step-by-Step Detail

### Steps 1–2: Load Tickers + Download Benchmark

**File:** `scanner.py`
**What it does:** Loads `complete_tickers.txt` (micro/small-cap universe, typically 800+ tickers all priced under $25). Downloads SPY benchmark data for beta and relative performance calculations.

**What to check in output:**
- Ticker count loaded (should be 800+; if significantly lower, file may be corrupted)
- SPY data download success
- Any open portfolio positions flagged for tracking

**Common issues:**
- `complete_tickers.txt` missing or empty → scan aborts
- yfinance rate limits → partial data (warning shown if <30% downloaded)

---

### Steps 3–5: Data Download + Sterling Grid V6 Technical Gates

**File:** `scanner.py` (functions: `download_and_process`, indicator calculations)
**Config:** `config.py` (HMA_PERIOD=21, PRICE_CAP=25)

**What it does:**

1. **Downloads** OHLCV data for all tickers via yfinance
2. **Calculates** Sterling Grid V6 indicators on each:
   - **HMA(21)** — Hull Moving Average, used for pivot detection
   - **UC (Banker/Under-the-Counter)** — proprietary institutional flow indicator
   - **MACD(12,26,9)** — timing confirmation signal
   - **RSI(14)** — momentum gauge (informational, not a gate)
   - **Beta** — vs SPY benchmark
3. **Applies entry filter** — all three conditions must be met:
   - **HMA(21) Pivot Low** (V-bottom pattern: `HMA[i-2] > HMA[i-1] < HMA[i]`)
   - **Confirmation gate** (OR logic): UC rising OR MACD cross-up
   - **Price < $25** (micro/small-cap filter)
4. **Assigns quality tiers** based on which confirmation gates fired:

| Tier | Condition | Position Size |
|------|-----------|---------------|
| T1 | UC rising AND MACD cross-up | 20% of equity |
| T2 | MACD cross-up only | 10% of equity |
| T3 | UC rising only | 5% of equity |

**What GOOD output looks like:**
- 800+ tickers downloaded, 5–20 technical signals
- Tier distribution roughly: T1 (1–3), T2 (3–6), T3 (5–10)
- If 0 signals: market may be in broad correction (expected ~1-2x/year)
- If 50+ signals: likely a data/indicator bug — too many pivots

**What to check:**
- `buy_signal` count vs `hma_pivot_low` count — most pivots should NOT produce buy signals (confirmation gates filter them)
- If T3 >> T1+T2: UC is rising broadly but MACD isn't confirming — possible late-cycle/low-conviction market
- `price_under_cap` should be ~90%+ of universe (most are small caps)

**Known issues:**
- yfinance occasionally returns stale data → stock appears to have a pivot when it doesn't
- HMA pivot detection is lagging by 1 bar (confirmed signal requires 3 bars)

---

### Step 6: Thematic Analyzer Gate

**File:** `thematic_analyzer.py`
**Model:** `claude-sonnet-4-20250514` + web search
**Cost:** ~$0.50–1.50 per run (2–3 API calls)

**What it does (3 sub-steps):**

#### Step 6.1: Theme Discovery (top-down)
- LLM + web search identifies the **top 5 investable macro themes** right now
- Each theme scored on 5 factors (weighted composite → 1–10):
  - **Catalyst Strength** (30%) — specific near-term catalysts
  - **Momentum Direction** (20%) — ETF/sector performance trajectory
  - **Crowding Level** (15%) — fund flows, positioning (inverse: under-owned = good)
  - **Runway Remaining** (10%) — market penetration, TAM remaining
  - **Capital Cycle Health** (25%, HAS VETO) — capex vs revenue, regime-specific
- Each theme classified:

| Composite | Classification | Action |
|-----------|---------------|--------|
| 7.5+ | PRIME | High conviction, full sizing |
| 6.0–7.4 | INVESTABLE | Standard position sizing |
| 4.5–5.9 | SELECTIVE | Only best stocks pass |
| < 4.5 | AVOID | Do not invest |

- **Capital Health Veto:** If capital health ≤ 3, classification capped at SELECTIVE regardless of composite
- Each theme assigned a **valuation regime**: OPTIONALITY (pre-revenue), FUNDAMENTAL (revenue-driven), or TRANSITION (between)

#### Step 6.2: Ticker-to-Theme Mapping (Step 2)
- Maps each technical signal to its best-fit theme
- Scores **Theme Fit** (1–10) and **Company Position** (Leader/Challenger/Niche/Laggard)
- **⚠️ CRITICAL (P1 fix):** Theme fit measures alignment with the theme's SPECIFIC MECHANISM, not just sector membership. A pharma company in a "Healthcare AI" theme must actually use AI to score well.
- Produces verdict per stock:

| Theme Class | Fit Score | Position | Verdict |
|-------------|-----------|----------|---------|
| PRIME/INVESTABLE | 7+ | Leader/Challenger | **STRONG FIT** → pass |
| PRIME/INVESTABLE | 5–6 | Any | **GOOD FIT** → pass |
| SELECTIVE | 7+ | Leader only | GOOD FIT → pass |
| SELECTIVE | <7 | Any | MODERATE FIT → skip |
| AVOID | Any | Any | WEAK FIT → skip |

#### Step 6.2b: Orphan Rescue
- Stocks that scored WEAK FIT on all themes get a **bottom-up second chance**
- LLM discovers the stock's ACTUAL theme (which may not be in the top 5)
- Evaluates that new theme using the same 5-factor framework
- Only rescues if the discovered theme is genuinely PRIME or INVESTABLE

**What GOOD output looks like:**
- 5 distinct themes (not overlapping, e.g. not "AI Infrastructure" AND "AI Software" — those are too similar)
- Theme classifications: 1–2 PRIME, 2–3 INVESTABLE, 0–1 SELECTIVE
- Ticker mapping: Most stocks get STRONG or GOOD FIT to their best theme
- Orphan rescue: 0–3 stocks rescued (most orphans should genuinely fail)
- ~60–80% of technical signals should pass the theme gate

**What to check for problems:**
- **Sector-as-theme mapping (P1 bug, now fixed):** If a pharma stock gets "PURE PLAY 100%" on "Healthcare AI Transformation" but the company has zero AI involvement → the sector ≠ mechanism guardrail didn't work
- **Theme overlap:** If themes are "AI Infrastructure" and "AI Data Centers" — too similar, should be one theme
- **All PRIME themes:** Suspicious — at least one theme should be INVESTABLE or SELECTIVE
- **No orphan rescues ever:** Might indicate Step 2 is too generous (force-fitting instead of correctly scoring WEAK FIT)
- **Pure play scores of 10 with sector-only justification:** Check if the reasoning mentions the theme's mechanism or just the sector

---

### Step 7: Investment Gate

**File:** `investment_gate.py`
**Model:** `claude-sonnet-4-20250514` + web search
**Cost:** ~$0.05–0.10 per stock, $0.30–0.80 per run

**What it does:**
- Final quality assessment before committing capital
- Regime-aware: uses the valuation regime from Step 6 to calibrate expectations
- Searches for recent news, catalysts, earnings, insider activity, red flags
- Produces per-stock verdict:

| Verdict | Conviction | Meaning | Action |
|---------|------------|---------|--------|
| **STRONG BUY** | 7–10 | Clear catalyst + clean setup + math works | Enter Monday at market open |
| **SPEC BUY** | 4–6 | Thesis valid but needs confirmation | Enter on pullback to support level |
| **NO GO** | 1–3 | Fatal flaw OR no catalyst OR math doesn't work | Skip |

**Key fields produced per stock:**
- `conviction` (1–10)
- `catalyst_present` + `catalyst_summary` + `days_to_catalyst`
- `math_to_50` — explicit path to 50%+ return (required for any BUY verdict)
- `red_flags` — specific concerns
- `bull_case` / `bear_case` / `bear_rebuttal`
- `entry_price` / `stop_loss` / `target_price`
- `position_size_pct` — recommended as % of equity

**What GOOD output looks like:**
- 1–3 STRONG/SPEC BUY verdicts out of ~5–10 theme-confirmed inputs
- 50–70% rejection rate (gate should be selective, not a rubber stamp)
- Each BUY has a specific catalyst within 90 days
- `math_to_50` is explicit arithmetic, not vague ("revenue grows X% → earnings Y% → multiple re-rates → target $Z")
- Red flags present even on BUY verdicts (shows the analysis was genuine)

**What to check for problems:**
- **0% rejection rate:** Gate is too permissive — every stock passes
- **100% rejection rate:** Gate may be too harsh, or market conditions are genuinely poor
- **Missing catalysts on BUY verdicts:** The gate should never BUY without a specific catalyst
- **"Math to 50%" is vague:** Should be concrete numbers, not "significant upside potential"
- **No red flags on any stock:** Suspicious — every stock has risks
- **Conviction 10/10 on speculative stock:** Overconfidence signal

---

### Step 7.5: Deep Due Diligence

**File:** `deep_dd.py`
**Model:** `claude-opus-4-20250514` + extended thinking (10K token budget) + web search
**Cost:** ~$1–2 per stock, $2–5 per run
**Streaming:** Uses `client.messages.stream()` (P0 fix — `create()` times out on Opus)

**What it does:**
- Runs ONLY on stocks that passed the Investment Gate (typically 1–3 stocks)
- Opus-level deep analysis with extended thinking — genuinely different from the Sonnet-based gate
- **Two jobs:**
  1. **Newsletter content** — produces structured "Why Now", "The Math", bear/bull cases, and action items
  2. **Final veto gate** — can OVERRIDE the Investment Gate if deep research reveals issues
- Searches 7+ specific queries per stock (adapted to valuation regime)
- Tests the Investment Gate's findings: Does the catalyst hold up? Is the math realistic? Does the bear rebuttal actually work?

**Verdicts:**

| DD Verdict | Conviction | Position Size | Meaning |
|------------|-----------|---------------|---------|
| **STRONG BUY** | 7–10 | FULL | Confirmed. High conviction. Enter immediately. |
| **SPEC BUY** | 4–6 | REDUCED | Confirmed with caveats. Smaller position. |
| **NO GO** | 1–3 | PASS | Vetoed. Fatal flaw found. Do NOT trade. |

**Key fields produced:**
- Everything the Investment Gate produces, but deeper
- `elevator_pitch` — 1-sentence newsletter summary
- `why_now_narrative` — the specific timing thesis
- `the_math_narrative` — detailed return arithmetic
- `bear_case_deep` + `bear_rebuttal_deep`
- `fatal_flaw` (if NO GO) — the specific dealbreaker
- `reconsider_if` (if NO GO) — what would flip the verdict

**Error handling (P0 fix):**
- If DD fails (streaming error, import error, exception) → stocks marked `PENDING_DD`
- `PENDING_DD` stocks appear in reports with ⚠️ warnings but are NOT tradeable
- Must re-run DD before trading

**What GOOD output looks like:**
- 1–2 DD-PASS out of 2–3 inputs (some vetoes expected)
- Conviction scores within ±2 of Investment Gate (wild divergence = one gate got it wrong)
- `fatal_flaw` on NO GO is specific and researched (not generic)
- `the_math_narrative` is more detailed than Investment Gate's `math_to_50`
- Extended thinking shows genuine deliberation (available in saved reports)

**What to check for problems:**
- **DD agrees with everything 100%:** May not be adding value — Opus should find nuance Sonnet missed
- **DD verdict contradicts gate by >4 conviction points:** One of them has wrong information — check which source data is correct
- **All NO GO:** Either the Investment Gate is too loose, or DD is too conservative
- **"PENDING_DD" in final report:** DD crashed — re-run before trading
- **Streaming timeout:** Shouldn't happen with the P0 fix, but if it does, check API key billing

---

### Step 8: Sell Signal Check

**File:** `scanner.py` (function: `check_sell_signals`)
**Runs on:** ALL open portfolio positions (from `open_positions.json`)

**Two exit mechanisms:**

#### 1. ExD Compound Exit (immediate)
- **Trigger:** HMA(21) Pivot High + UC falling — both on the SAME bar
- **Meaning:** Institutional money is leaving (UC falling) AND momentum has peaked (HMA pivot high)
- **Action:** Exit immediately at next open, regardless of profit/loss

#### 2. Tiered Profit Lock (based on return from entry)
- Works on CURRENT return, not trailing from peak:

| Return Level | Lock Action |
|-------------|-------------|
| ≥ +100% | Lock 80% of gains (sell if drops to +80%) |
| ≥ +75% | Lock 60% of gains |
| ≥ +50% | Lock 40% of gains |
| Below +50% | Only ExD can trigger exit (no trailing stop) |

**Important:** Below +50% return, there is NO trailing stop — only ExD can force an exit. This prevents being shaken out of early-stage positions by normal volatility.

**What GOOD output looks like:**
- 0–2 sell signals per week (most positions are held for weeks/months)
- ExD exits should be rare (compound signal requires alignment of two indicators)
- Profit locks trigger on big winners, not on positions barely above +50%

---

## Report Output Structure (P2 Fixes Applied)

### Terminal Report (`print_final_report`)

The final report now separates stocks into distinct sections:

1. **🟢 BUY NOW** — `STRONG_BUY` verdicts → Enter Monday at market open
2. **🟡 BUY ON PULLBACK** — `SPEC_BUY` verdicts → Wait for pullback to support
3. **🟢 PASS (Other)** — Other passing verdicts
4. **⚠️ PENDING DD** — DD failed/skipped → Do NOT trade until DD completes
5. **🔵 CONSIDER** — Watchlist candidates

### ACTION SUMMARY shows per-stock sizing:
```
🟢 BUY NOW:     ETON     T1 (20% equity)
🟡 ON PULLBACK: RELY     T3 (5% equity)
⚠️ PENDING DD:  ZGN      T2 (10% equity) — re-run DD before trading
```

### Equity deployment summary:
```
💰 Total equity deployment: 20% immediate + 5% on pullback + 10% pending DD
```

---

## File Map

| File | Purpose | Model Used |
|------|---------|------------|
| `scanner.py` | Orchestrator: data, technical gates, reports, sell signals | None (pure Python) |
| `thematic_analyzer.py` | Step 6: Theme discovery + ticker mapping + orphan rescue | Sonnet 4 |
| `investment_gate.py` | Step 7: Regime-aware quality gate | Sonnet 4 |
| `deep_dd.py` | Step 7.5: Opus deep analysis + newsletter content | Opus 4 + Extended Thinking |
| `config.py` | Constants: HMA_PERIOD, PRICE_CAP, API keys | — |
| `indicators.py` | HMA, UC, MACD calculations, pivot detection | — |
| `portfolio/manager.py` | Portfolio tracking, equity curve, trade history | — |
| `utils/email_notifier.py` | Email notification delivery | — |

---

## Pipeline Cost & Timing (P3 Tracker)

The scanner now prints a timing summary at the end of each run:

```
══════════════════════════════════════════════════════════════════════
PIPELINE COST & TIMING SUMMARY
──────────────────────────────────────────────────────────────────────
  Steps 1-5: Data & Technical       0.8m  (  5.2%)
  Step 6: Thematic Gate             5.1m  ( 33.1%)
  Step 7: Investment Gate           7.2m  ( 46.8%)
  Step 7.5: Deep DD                 2.3m  ( 14.9%)
──────────────────────────────────────────────────────────────────────
  TOTAL                            15.4m
══════════════════════════════════════════════════════════════════════
```

Typical run: 12–20 minutes total, $3–7 API cost. Steps 6+7 dominate because of web search + multiple LLM calls per stock.

---

## Diagnostic Checklist for Reviewing Output

Use this when reviewing a scan's output to identify issues:

### 1. Technical Gate Health
- [ ] Reasonable signal count (5–20 out of 800+)?
- [ ] Tier distribution not all T3? (T1 presence = strong signals)
- [ ] No duplicate tickers in signal list?

### 2. Thematic Gate Health
- [ ] 5 distinct, non-overlapping themes?
- [ ] At least one PRIME theme? (If zero = tough market)
- [ ] Theme fit scores match MECHANISM, not just sector?
- [ ] Orphan rescue rescued 0–3 stocks (not 0 every time, not 10)?
- [ ] Valuation regimes make sense? (Pre-revenue = OPTIONALITY, not FUNDAMENTAL)

### 3. Investment Gate Health
- [ ] 50–70% rejection rate? (Not rubber-stamping, not rejecting everything)
- [ ] Every BUY has a specific catalyst within 90 days?
- [ ] `math_to_50` is concrete arithmetic, not vague?
- [ ] Red flags present even on BUY verdicts?
- [ ] STRONG BUY vs SPEC BUY distinction makes sense?

### 4. Deep DD Health
- [ ] Adds genuine new insight beyond Investment Gate?
- [ ] Conviction within ±2 of gate? (Wild swings = bad data)
- [ ] NO GO verdicts have specific `fatal_flaw`?
- [ ] No PENDING_DD in final output? (If present: DD crashed, re-run)
- [ ] Newsletter content is specific, not boilerplate?

### 5. Report Health
- [ ] BUY NOW vs PULLBACK correctly split by gate verdict?
- [ ] Sizing shown for every stock (T1/T2/T3 + % equity)?
- [ ] Total equity deployment is reasonable (not 100%)?
- [ ] PENDING_DD stocks clearly flagged as non-tradeable?
- [ ] Sell signals section present (even if empty)?

---

## Known Issues & Future Improvements

### Fixed in This Session
- **P0 (Deep DD streaming):** Switched to `client.messages.stream()` — no more 10-min timeouts
- **P0 (DD error handling):** Failed DD now marks stocks `PENDING_DD` instead of silently passing them
- **P1 (Theme over-mapping):** Added sector ≠ mechanism guardrail — pharma in "Healthcare AI" must actually use AI
- **P2 (Sizing display):** Every output surface now shows tier + % equity allocation
- **P2 (BUY NOW vs PULLBACK):** Split by `STRONG_BUY` vs `SPEC_BUY` gate verdict
- **P3 (Pipeline timing):** Wall-clock timer per stage + summary at end of run

### Open Items
- **Theme quality validation:** No automated check that themes are distinct (human review needed)
- **Cross-run comparison:** No tool to diff this week's themes vs last week's
- **DD cost aggregation:** Individual gates print their own API costs; no single unified total yet
- **Backtest framework:** No systematic way to measure if gate verdicts correlate with actual returns

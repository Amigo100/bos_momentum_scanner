# Sterling Grid — Complete System Reference

*Version: Final (Post V4 Validation) — February 2026*
*Source-verified against: indicators.py, v2_signals.py, v3_exits.py*

---

## 1. WHAT THIS SYSTEM IS

Sterling Grid is a weekly momentum trading system for US-listed growth stocks under $25. It combines technical entry/exit signals with LLM-powered fundamental analysis to capture outsized returns from high-momentum stocks in trending investment themes.

The system has been validated through four rounds of backtesting (V1–V4) across 924 tickers over 7+ years (2018–2025). The recommended live configuration uses conviction-tiered position sizing (15% base, 20% high-conviction, 8% speculative, max 6 concurrent) with an adaptive gear-shift protocol that adjusts sizing based on demonstrated performance. Forward expectations: 25-40% CAGR with -12 to -22% maximum drawdown.

### The Core Insight

Most retail momentum systems fail because they either enter too late (chasing) or exit too early (stop-losses cutting winners). Sterling Grid solves both problems.

**Entry:** The technical signals identify the exact week a high-momentum stock's trend turns definitively bullish — not when it's already extended, but at the structural inflection point. The LLM gates then filter for stocks where the fundamental story supports the move continuing for months, not just weeks.

**Exit:** Instead of a fixed stop loss (which backtesting proved destroys 48% of winning trades on volatile growth stocks), the system uses a tiered profit lock that progressively protects gains. A stock that has returned +200% from entry gets a tight 15% trailing stop from its peak. A stock still building momentum below +50% gets room to breathe. The primary exit is a comprehensive trend reversal signal (HMA slope + UC both turning bearish on the same bar), which catches the true end of a move rather than normal pullback noise.

---

## 2. WHY THIS WORKS — THE THEORY

### 2.1 Why These Indicators

**Hull Moving Average (HMA-21, Weekly):** The HMA is a weighted moving average designed to reduce lag while maintaining smoothness. On a weekly timeframe applied to HL2 (midpoint of high and low), it captures the underlying trend direction while filtering out day-to-day and week-to-week noise. The slope of the HMA (current value vs previous value) provides a clean trend direction signal. When the slope turns positive, the trend has decisively turned — not just bounced.

Why HMA specifically: Standard moving averages (SMA, EMA) lag significantly on weekly data. The HMA's construction (WMA of 2×WMA(n/2) − WMA(n), smoothed over √n periods) reduces lag by roughly 50% compared to an SMA of the same period, while maintaining smoother output than an EMA. This means the slope change catches trend turns closer to when they actually happen.

**RSI(14) > 50:** The Relative Strength Index above its midline is a simple momentum confirmation. It's not identifying overbought/oversold — it's confirming that upward momentum exists. When RSI is below 50, the stock is losing momentum even if price is rising; entries in this state have lower follow-through. When RSI is above 50, the stock has genuine upward pressure.

Why it's included but practically redundant: V3 testing showed that when HMA slope turns positive on high-momentum stocks, RSI is virtually always above 50. The condition is met automatically 100% of the time in the Gate-Proxy universe. It's kept as a safety filter for edge cases on lower-quality stocks.

**MACD(12,26,9) Cross Up:** The Moving Average Convergence Divergence crossover is the primary timing confirmation. While HMA slope tells you the trend has turned, MACD cross-up tells you the momentum behind the trend is actively accelerating. The MACD line crossing above the signal line means short-term momentum (12-period EMA of close) is pulling away from longer-term momentum (26-period EMA of close) — the move is gaining speed.

**Critical detail:** The MACD cross-up must occur on the **exact same weekly bar** as all other entry conditions. It is a single-bar event, not a lookback window. This is strict — if the MACD crossed up last week but HMA only turns this week, there is no signal. All four conditions must align simultaneously. This strictness is what limits the system to ~12 trades per year and ensures only the strongest setups are captured.

**Undercurrent (UC):** The Undercurrent is a normalised RSI derivative, **not a VWAP indicator**. Its exact formula is:

```
RSI_10 = RSI(close, 10)  [Wilder's smoothing, 10-bar on weekly]
UC = clip(1.5 × (RSI_10 − 50), 0, 20)
```

UC ranges from 0 to 20. When RSI(10) is at or below 50, UC is zero (bearish/neutral). When RSI(10) is above 50, UC rises proportionally, capping at 20 when RSI(10) reaches ~63.3. The "rising above" condition requires both that UC is increasing bar-over-bar AND that UC is above zero (meaning RSI(10) > 50).

Why it matters for exits: The UC condition is largely redundant with HMA for entries (they tend to fire on the same bars on high-momentum stocks). But for exits, the compound requirement that BOTH HMA slope AND UC must turn bearish on the same bar prevents premature exits on temporary pullbacks. If the HMA dips briefly but UC is still rising, short-term momentum is still strong — it's a pullback in an uptrend, not a reversal.

**Important:** The production scanner's "Banker" indicator uses a different formula — VWAP price deviation: `((Close / VWAP_20) − 1) × 100 + 50`. Banker and UC are conceptually related (both measure momentum direction) but are mathematically different calculations. The scanner needs to be updated to use the RSI-derived UC formula to match backtested behaviour.

### 2.2 Why the LLM Gates Transform the System

The technical indicators alone, applied to 924 random US stocks, produce a system that returns +140% over 7 years at 10×10 sizing. That's decent (~13% CAGR) but not exceptional. Applied to the 84-ticker Gate-Proxy universe (stocks that pass thematic and fundamental analysis), the same technical signals produce +633% (~35% CAGR).

The difference is entirely attributable to stock selection quality. The technical signals are a necessary condition — they identify the right timing. But the LLM gates are the sufficient condition — they identify the right stocks.

**Thematic Analyzer (Gate 1):** Identifies which investment themes have genuine momentum and catalysts (PRIME, INVESTABLE) vs themes that are fading or overcrowded (SELECTIVE, AVOID). Then evaluates whether each stock is a strong fit for a trending theme.

Why this works: Growth stocks move in theme clusters. Quantum computing, AI infrastructure, clean energy, crypto — when a theme is hot, multiple stocks in that theme move simultaneously because the same macro catalysts (government funding, regulatory shifts, technology breakthroughs) drive institutional flows into the entire sector. By filtering for stocks in PRIME/INVESTABLE themes with STRONG/GOOD fit, the system concentrates capital in the stocks most likely to benefit from sector-wide momentum.

**Investment Gate (Gate 2):** Regime-aware fundamental analysis. For pre-revenue stocks (OPTIONALITY regime like quantum computing), it assesses milestone velocity, funding, and narrative expansion — not P/E ratios that don't exist. For revenue-generating stocks (FUNDAMENTAL regime), it assesses earnings revisions, operating leverage, and multiple expansion potential. For transitioning stocks (TRANSITION regime), it assesses whether revenue is materialising fast enough to justify optionality-era valuations.

Why regime awareness matters: A standard fundamental screen would reject every pre-revenue quantum computing stock. But IONQ returned +293% and RGTI returned +705% on narrative momentum alone. By adapting the analysis framework to how the market actually prices each stock, the gate avoids false negatives on the highest-potential opportunities.

**Deep Due Diligence (Gate 3):** Uses Claude Opus with extended thinking for genuine deep analysis. Searches for specific red flags (SEC investigations, auditor resignations, shelf offerings), validates catalyst timelines, steelmans the bear case, and constructs specific return math. Can veto Gate 2 if deep analysis reveals issues the initial screen missed.

Why three gates and not one: Each gate catches different failure modes. Gate 1 catches stocks in dying themes. Gate 2 catches stocks with specific red flags or no catalyst. Gate 3 catches subtle issues that require deeper reasoning (e.g., a company whose revenue is growing but only because of a one-time contract). The ~50% cumulative rejection rate means only the highest-quality opportunities make it through.

### 2.3 Why Profit Locks Work on These Stocks

High-momentum growth stocks under $25 are inherently volatile. A stock heading from $5 to $50 will routinely pull back -30% to -40% along the way. A traditional stop loss at -20% or -30% from entry will trigger on these normal corrections, cutting you out of what would have been a +900% trade.

Backtesting proved this conclusively: fixed stop losses at -30% triggered on 48% of all trades, and 48% of those stopped trades would have recovered to produce positive returns. Average opportunity cost: +127% per stopped trade. One trade that was stopped at -30% would have returned +1,104%.

Profit locks solve this differently. They don't protect against initial drawdowns — they let the stock breathe. But once the position has reached significant profitability, the lock progressively tightens protection. This captures the key insight: the further a stock has run, the more you need to protect, and the more likely a pullback represents a genuine reversal rather than normal noise.

**Critical detail about tier selection:** The tier is determined by the **current return** (current close vs entry price), not the peak return. This means tiers can **degrade** as a stock pulls back. If a stock peaked at +250% from entry (activating the tightest 15% trail) but has since pulled back to +180%, the tier loosens to 20%. If it pulls further to +80%, it loosens to 25%. If it drops below +50% from entry, the lock deactivates entirely. This is intentional — it gives stocks room to recover from pullbacks rather than locking in with an aggressively tight trail that fires on a temporary dip.

At +200% current gain, the 15% trail from peak means you exit if the stock drops 15% from its highest close. Under pure ExD (waiting for full trend reversal), you might give back half the gain waiting for HMA and UC to both confirm. The tiered lock captures an extra 30-50% per trade on the big winners by exiting earlier on the downside while still letting the upside run.

**V4's most important finding:** This improvement is 99% genuine risk management, not a re-entry compounding artefact. With all re-entries blocked permanently, lock_tiered returned +1,034% vs ExD_pure's +304%.

---

## 3. BACKTESTING RESULTS SUMMARY (V1–V4)

### 3.1 Evolution

| Version | Universe | Key Innovation | 10×10 Return | Max DD | Walk-Forward |
|---------|----------|---------------|-------------|--------|-------------|
| V1 | 874 tickers (all) | Baseline HMA pivot + ATR trail | +424% | -51% | 60% pass |
| V2 | 84 tickers (Gate-Proxy) | Slope entry + ExD exit + gate-filtered universe | +401% | -27% | 80% pass |
| V3 | 84 tickers (Gate-Proxy) | Tiered profit locks + protection testing | +1,048% | -7.2% | N/A |
| V4 | 84 tickers (Gate-Proxy) | Re-entry validation, walk-forward, bootstrap | +633%* | -7.2% | 100% pass |

*2025 data cutoff (honest, excluding 2026 unrealised gains).

### 3.2 Final Validated Numbers (V2 Entry + ExD_lock_tiered, Backtested at 10×10 Sizing)

> **Sizing note:** The backtest was run at 10% × 10 positions. The recommended live configuration is **15% × 6 with conviction tiers** (see Sections 4.4 and 7). This captures more upside per trade while maintaining structural drawdown protection. The per-trade statistics below are independent of sizing and apply to all configurations.

**Trade-level statistics:**
- Trades: 82 over 7 years (~12/year)
- Win rate: 79% (CI: 71%–88%)
- Average return per trade: +85.8% (CI: +57.7% to +118.7%)
- Profit factor: 15.9
- Average hold: ~24 weeks median, ~56 weeks mean (skewed by multi-baggers)

**Portfolio-level (starting $120k AUD):**
- Total return (2025 cutoff): +633%
- Max drawdown: -7.2%
- Return/Drawdown ratio: 87.9×
- Walk-forward: 4/4 out-of-sample windows profitable (100%)
- Pessimistic transaction costs: still +941%

**Year-by-year OOS performance:**
- 2022: +7.4%
- 2023: +92.1%
- 2024: +63.6%
- 2025: +53.1%
- Average: +54.1% per year

### 3.3 Key Findings That Shape the System

| Finding | Implication |
|---------|-------------|
| Fixed stop losses (-30%) triggered on 48% of trades; 48% of those recovered. Average opportunity cost +127%. | Never use fixed stop losses on volatile growth stocks. |
| Time-based exits (force exit at 52 weeks) cost +134% per forced trade. | Let winners run. Long holds are the system's best trades. |
| UC rising and UC rising_above produce identical signals on all 61 trades. RSI>50 always met when HMA bullish. | Effective entry is just HMA slope + MACD cross up. Other conditions are automatically satisfied on high-momentum stocks. |
| Top 5 trades = 81% of total P&L. RIOT alone = 33%. | System depends on being present for a handful of 500%+ moves. You cannot skip signals. |
| 2021 contributed 72% of ExD_pure's total P&L. | Performance is lumpy. Expect flat or negative years between big cycles. |
| Gate-Proxy stocks: 82% WR, +82% avg return. Non-GP stocks: 69% WR, +41% avg. | Gates roughly double per-trade quality. The LLM pipeline is critical. |
| Lock_tiered with zero re-entries: +1,034%. ExD_pure with zero re-entries: +304%. | Lock improvement is 99% genuine risk management. |
| Medium cooldown (8–26 weeks) produces higher returns than immediate re-entry. | Some quick re-entries after lock exits are destructive (dead cat bounces). Wait 4–8 weeks. |

---

## 4. THE EXACT ENTRY AND EXIT CRITERIA

### 4.1 Entry Signal (Buy)

ALL of the following must be true on the **same weekly bar**:

1. **HMA(21) slope is rising:** Current weekly HMA value > previous weekly HMA value
   - HMA is calculated on HL2 = (High + Low) / 2
2. **RSI(14) > 50:** Weekly RSI is above its midline (Wilder's smoothing)
3. **MACD(12,26,9) cross up THIS bar:** MACD line crosses above signal line on this exact bar (single-bar event — MACD was at or below signal last bar, now above)
4. **UC rising above:** UC > UC.shift(1) AND UC > 0 (i.e., RSI(10) > 50 and improving)
5. **Price < $25:** Stock price is below $25 at signal time
6. **LLM gates passed:** Stock has passed Thematic Analyzer, Investment Gate, and Deep DD

Entry execution: Buy at Monday's market open following the Friday close that generated the signal.

**Why all four conditions must fire simultaneously:** This is the strictest possible entry. The MACD cross-up is a single-bar event — it either happens this week or it doesn't. There is no "recent" lookback. This strictness is what limits the system to ~12 trades per year across 84 stocks, ensuring only the strongest confluence setups are captured. The backtest corridor alternation also prevents consecutive buy signals (must see a sell before the next buy), but in practice this is handled by only entering when not already in a position.

### 4.2 Exit Signal (Sell)

Two mechanisms — **first to fire** triggers the exit:

**Mechanism 1 — ExD (Compound Trend Reversal):**
HMA(21) slope turns bearish (current HMA < previous HMA) AND UC turns falling (current UC < previous UC), both on the same weekly bar.

In plain terms: both the price trend and the underlying momentum must confirm the move is over. If only one turns bearish, it may be a temporary pullback — hold.

**Mechanism 2 — Tiered Profit Lock (trailing stop from peak, tier based on CURRENT return):**

| Current Return from Entry | Trail % from Peak | What This Means |
|--------------------------|-------------------|-----------------|
| ≥ +200% | 15% trail | If stock drops 15% from its highest weekly close → exit |
| ≥ +100% (but < +200%) | 20% trail | If stock drops 20% from peak → exit |
| ≥ +50% (but < +100%) | 25% trail | If stock drops 25% from peak → exit |
| < +50% | No lock active | Only ExD can trigger exit |

**Critical: Tiers are based on CURRENT return, not peak return. Tiers can DEGRADE.**

The tier is evaluated every bar using the current close vs the original entry price. If a stock peaked at +250% (15% trail active), then pulled back to a current return of +180%, it remains in the 15% tier. But if it pulls back further to +90% current return, the tier degrades to 20%. At +40% current return, the lock deactivates entirely.

From v3_exits.py:
```python
current_return = (bar_close - entry_price) / entry_price
if current_return >= 2.0:
    lock_level = peak_close * (1 - 0.15)
elif current_return >= 1.0:
    lock_level = peak_close * (1 - 0.20)
elif current_return >= 0.5:
    lock_level = peak_close * (1 - 0.25)
else:
    return False  # no lock active
if bar_close <= lock_level:
    → EXIT
```

In practice, for large drops from peak the lock fires regardless of which tier is active (a stock that's fallen from +250% to +90% has already dropped well beyond any trail percentage from its peak). The tier degradation matters most for edge cases near tier boundaries.

Exit execution: Sell at next Monday's market open following the weekly signal.

### 4.3 Re-Entry Rule

After a profit lock exit, wait at least 4–8 weeks before re-entering the same stock. Run it through the gate pipeline again (quick re-check if previously assessed). If the theme and catalysts are intact and a fresh buy signal fires, re-enter at full position size.

Rationale: V4 cooldown testing showed immediate re-entries are sometimes destructive (the stock hasn't finished pulling back). Medium cooldowns (8–26 weeks) produce optimal returns.

### 4.4 Position Sizing (Conviction-Tiered)

Base configuration: **15% of equity per position, maximum 6 concurrent positions** (~90% max deployed).

| Gate Verdict | Conviction Score | Position Size | Typical Portfolio Weight |
|-------------|-----------------|--------------|------------------------|
| STRONG BUY | 8-10 | 20% of equity | High-conviction core |
| STRONG BUY | 7 | 15% of equity | Standard full position |
| SPEC BUY | 4-6 | 8% of equity | Reduced speculative |
| Re-entry (after 4-8 week cooldown) | Same as new | Same as verdict | Based on fresh gate score |

A typical portfolio in practice: 1-2 high-conviction at 20%, 2-3 standard at 15%, 1-2 speculative at 8% → 76-96% deployed with 4-24% cash for new opportunities.

**Adaptive gear-shift:** After 6 months of live performance data, position sizing can be adjusted up or down based on demonstrated results (see Section 8).

---

## 5. INDICATOR CALCULATIONS — EXACT FORMULAS

All formulas verified line-by-line against the backtest source code (`indicators.py`, `v2_signals.py`, `v3_exits.py`).

### 5.1 HMA (Hull Moving Average)

Source: `indicators.py hma()` and `compute_hma_slope()`

```
Input:    HL2 = (weekly_high + weekly_low) / 2
half    = int(21 / 2) = 10
sqrt_n  = int(√21)    = 4

HMA = WMA( 2 × WMA(HL2, 10) − WMA(HL2, 21),  4 )

slope_rising  = HMA[i] > HMA[i-1]   (entry signal)
slope_falling = HMA[i] < HMA[i-1]   (exit component)
```

WMA weights are linearly increasing: [1, 2, 3, ..., n].

### 5.2 RSI (Pulse)

Source: `indicators.py pulse()`

```
Standard RSI(14) with Wilder's smoothing:
  avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
  avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
  RS  = avg_gain / avg_loss
  RSI = 100 − 100 / (1 + RS)

Entry condition: RSI > 50
```

### 5.3 MACD (Tide)

Source: `indicators.py tide()`, `v2_signals.py _build_macd_mask()`

```
MACD line    = EMA(close, 12) − EMA(close, 26)
Signal line  = EMA(MACD_line, 9)
Histogram    = MACD_line − Signal_line

Entry condition (SINGLE BAR cross-up):
  macd_cross_up = (MACD > Signal) AND (MACD.shift(1) <= Signal.shift(1))
```

There is no lookback window. The cross must occur on the same bar as all other entry conditions.

### 5.4 Undercurrent (UC)

Source: `indicators.py undercurrent()`

**UC is NOT a VWAP indicator. It is a normalised RSI derivative.**

```
length = round(50 / 5.0) = 10     [target_days / weekly_divisor]

RSI_10 = RSI(close, 10)            [Wilder's smoothing, same formula as above]

UC = clip(1.5 × (RSI_10 − 50),  0,  20)
```

Behaviour table:

| RSI(10) | UC Value | Interpretation |
|---------|----------|---------------|
| ≤ 50.0 | 0.0 | Bearish/neutral (clipped at floor) |
| 55.0 | 7.5 | Mild bullish |
| 60.0 | 15.0 | Strong bullish |
| ≥ 63.3 | 20.0 | Maximum (clipped at ceiling) |

Entry condition `uc_rising_above`: UC > UC.shift(1) AND UC > 0

Exit condition `uc_falling`: UC < UC.shift(1)

**This is different from the production scanner's "Banker" indicator**, which uses: `((Close / VWAP_20) − 1) × 100 + 50`. Banker and UC are directionally correlated (both measure momentum) but are different mathematical calculations.

### 5.5 Scanner vs Backtest — Full Gap Analysis

| Component | Current Scanner (scanner.py) | Backtested System (indicators.py) | Impact |
|-----------|---------------------------|----------------------------------|--------|
| Trend entry | HMA pivot (BoS bullish) | HMA slope rising | Slope fires more frequently and earlier than pivot |
| Momentum entry | Banker rising (VWAP-based) | UC rising above (RSI-10 based) | Different formulas — directionally correlated but not identical |
| Timing entry | None (pivot is the timing) | MACD(12,26,9) single-bar cross-up | Scanner lacks the key timing filter |
| Momentum confirmation | None | RSI(14) > 50 | Scanner lacks this (redundant in practice) |
| Primary exit | BoS bearish (HMA pivot reversal) | ExD: HMA slope falling AND UC falling | BoS is structurally delayed vs slope |
| Protection exit | 20% trailing stop from peak | Tiered profit lock (+50%→25%, +100%→20%, +200%→15%) | Single stop vs adaptive tiers — major performance difference |
| Lock tier basis | N/A | Current return (degrades on pullback) | N/A |

**To align the scanner with backtested results, all six gaps need to be closed.** The standalone `sterling_indicators.py` script provides all the corrected calculations ready for integration.

---

## 6. THE GATE PIPELINE — HOW IT WORKS

### 6.1 Pipeline Flow

```
Weekly Signal Scan (Technical)
    ↓ ~3-8 stocks pass technical criteria
Thematic Analyzer (Gate 1) — ~$0.30-0.80
    ↓ ~50% filtered out (wrong theme, bad fit)
Investment Gate (Gate 2) — ~$0.15-0.25 per stock  
    ↓ ~30-50% filtered out (red flags, no catalyst, math doesn't work)
Deep Due Diligence (Gate 3) — ~$1-2 per stock
    ↓ ~10-20% vetoed (issues missed by earlier gates)
YOUR REVIEW — Read the analysis, make final call
    ↓
EXECUTE — Buy Monday at market open
```

Total pipeline cost per scan: ~$2-5. At 50 weekly scans per year: ~$100-250/year in API costs.

### 6.2 Gate 1: Thematic Analyzer

**What it does:** Identifies the top 5-10 investable themes in the current market, classifies them (PRIME/INVESTABLE/SELECTIVE/AVOID), then maps each stock to its closest theme and scores the fit.

**Pass criteria:** Theme must be PRIME or INVESTABLE. Stock fit must be STRONG FIT or GOOD FIT.

**What it catches:** Stocks in dying themes (clean coal, SPACs in 2022), stocks that don't actually fit their apparent theme (a company called "Quantum Solutions" that actually sells consulting services), and overcrowded themes where the easy money has been made.

**Model:** Claude Sonnet 4.5 (cost/quality balance). Uses web search when enabled for real-time theme momentum data.

### 6.3 Gate 2: Investment Gate

**What it does:** Single comprehensive assessment answering "Should I buy this stock on Monday?" Adapts analysis to the stock's valuation regime (OPTIONALITY / FUNDAMENTAL / TRANSITION).

**Four phases:**
1. Disqualifier screen — SEC investigations, auditor resignations, imminent earnings
2. Catalyst validation — What drives the next move? When?
3. Return validation — Specific math to +50%. Steelmanned bear case.
4. Verdict — STRONG BUY / SPEC BUY / NO GO

**Pass criteria:** STRONG BUY (conviction 7-10) or SPEC BUY (conviction 4-6). Conviction score directly determines position size: 8-10 → 20% of equity, 7 → 15%, 4-6 → 8% (see Section 7.2).

**What it catches:** Stocks with hidden red flags (recent shelf offering, CFO resignation), stocks with no near-term catalyst (dead money risk), stocks where the bear case is stronger than the bull case.

**Model:** Claude Sonnet 4.5. Uses 5 targeted web searches per stock for real-time data.

### 6.4 Gate 3: Deep Due Diligence

**What it does:** Uses Claude Opus with extended thinking for genuine deep analysis. Only runs on 1-3 stocks that passed Gate 2. Can veto Gate 2 if deep analysis reveals issues.

**Produces:**
- Elevator pitch (newsletter-ready)
- "Why now" catalyst with specific date
- "The math" to +50% return (regime-adapted)
- Steelmanned bear case and rebuttal
- Specific action recommendation
- Kill switch (what triggers early exit)

**Pass criteria:** STRONG BUY or SPEC BUY verdict from Opus.

**Model:** Claude Opus (highest capability). Extended thinking enabled (10,000 token thinking budget). Uses web search for current data.

---

## 7. POSITION SIZING & RISK MANAGEMENT

### 7.1 Why 15×6 With Conviction Tiers

The backtest sizing sweep revealed a clear pattern: **more positions at moderate size captures more winners than fewer positions at larger size.** The earlier 25%×3 and 25%×4 configurations concentrated capital too heavily, missing signals when all slots were full. At 25%×3, 112 signals were skipped; at 20%×5, only 96 were skipped — and those 16 extra trades included several 50%+ movers.

The 10×10 backtest configuration (10% per position, max 10) delivered excellent risk metrics (-7.2% max DD) but traded some compounding speed for safety. The 15%×6 recommendation sits between these extremes: enough diversification to capture the big winners, enough concentration per trade to compound meaningfully.

**The conviction tier adds an additional edge.** The backtest's single biggest finding was that the top 5 trades produce 81% of total P&L. Flat sizing gives equal capital to a high-conviction STRONG BUY and a borderline SPEC BUY. Conviction tiering concentrates capital where the gate pipeline says the edge is strongest.

### 7.2 Position Sizing Rules

| Verdict | Conviction | Size | Max Slots | Rationale |
|---------|-----------|------|-----------|-----------|
| STRONG BUY | 8-10 | 20% of equity | 2 | Highest-conviction, all gates aligned, PRIME theme |
| STRONG BUY | 7 | 15% of equity | 3 | Standard strong signal, full position |
| SPEC BUY | 4-6 | 8% of equity | 2 | Interesting but uncertain — still participate, limit risk |
| NO GO | 1-3 | 0% | — | Do not enter regardless of technical signal |

**Portfolio construction example** (on $120k starting equity):

| Position | Verdict | Size | Dollar Amount |
|----------|---------|------|--------------|
| Stock A (PRIME theme, conviction 9) | STRONG BUY | 20% | $24,000 |
| Stock B (INVESTABLE theme, conviction 7) | STRONG BUY | 15% | $18,000 |
| Stock C (INVESTABLE theme, conviction 7) | STRONG BUY | 15% | $18,000 |
| Stock D (PRIME theme, conviction 8) | STRONG BUY | 20% | $24,000 |
| Stock E (conviction 5) | SPEC BUY | 8% | $9,600 |
| *Cash reserve* | — | 22% | *$26,400* |

Total deployed: 78%. Cash buffer: 22% for new opportunities or adding to winners.

Position size is calculated on **current portfolio equity** (not initial capital). As the portfolio grows, position sizes grow proportionally.

### 7.3 Risk Limits

- **Maximum deployment:** 90% of equity. Always maintain at least 10% cash for new opportunities and to avoid forced selling during drawdowns.
- **Maximum single-trade risk at entry:** 20% of equity (STRONG BUY conviction 8-10 only). No position should ever exceed 20% at entry, regardless of conviction.
- **Drawdown pause:** If portfolio drawdown exceeds -20%, pause all new entries and review. The tiered profit lock limits structural drawdowns to -10 to -20% at 15×6 sizing, so hitting -20% suggests something unexpected is happening.
- **Sector concentration cap:** No more than 3 concurrent positions in the same sector. If a fourth signal fires in a sector where you already have 3 positions, either skip it or reduce one existing position first.
- **Natural position growth:** If a stock appreciates significantly (e.g., 20% entry grows to represent 35% of portfolio), do NOT trim purely to rebalance. The profit lock system handles exit timing. Trimming winners was not tested in the backtest and would reduce the multi-bagger captures that drive 81% of P&L.

### 7.4 Sizing at Different Portfolio Levels

As your portfolio grows, the dollar amounts per trade increase but the percentages remain the same. Here is what each conviction tier looks like at different equity levels:

| Portfolio Equity | STRONG BUY (20%) | Standard (15%) | SPEC BUY (8%) |
|-----------------|-----------------|----------------|---------------|
| $120k (start) | $24,000 | $18,000 | $9,600 |
| $200k | $40,000 | $30,000 | $16,000 |
| $400k | $80,000 | $60,000 | $32,000 |
| $700k+ | Consider capping dollar amounts — liquidity in sub-$25 stocks becomes a concern |

**Liquidity warning:** Sub-$25 growth stocks can have thin order books. Once individual position sizes exceed ~$50-80k, market orders on Monday opens may cause meaningful slippage. At that point, consider using limit orders at Friday's close or scaling into positions over 2-3 days.

### 7.5 What NOT to Do (From Backtesting)

- **Do not add fixed stop losses.** V3 proved they destroy 48% of winning trades. The tiered profit lock handles downside protection.
- **Do not force-exit positions after a time limit.** V3 proved time exits cost +134% per forced trade. Let the system's exit signals do their job.
- **Do not skip signals because the stock "seems expensive."** The top 5 trades produce 81% of total P&L. Missing even one multi-bagger dramatically reduces returns.
- **Do not override the system during drawdowns.** With locks, the worst year was +4%. Trust the process.
- **Do not trim winners to rebalance.** A position that's grown from 15% to 40% of your portfolio is exactly the kind of trade that drives returns. The profit lock will manage the exit.
- **Do not size up beyond 20% per position, even during strong streaks.** The gated backtest sweep showed that 25% sizing produces -44% drawdowns. The 20% cap for high-conviction trades is already aggressive.

### 7.6 Expected Performance by Sizing Configuration

These are estimated forward projections based on backtest data, cross-referenced with consensus market outlook (constructive, broadening into small caps, continued AI theme, higher volatility expected):

| Configuration | Expected 5-Year CAGR | $120k Becomes | Expected Max DD | Character |
|--------------|---------------------|--------------|----------------|-----------|
| 10% × 10 (conservative) | 20-30% | $300-445k | -7 to -15% | Sleep well — minimal stress |
| **15% × 6 with tiers (recommended)** | **25-40%** | **$365-640k** | **-12 to -22%** | **Moderate — manageable dips** |
| 20% × 5 (aggressive) | 30-50% | $445-900k | -18 to -30% | Aggressive — stomach-churning dips |
| 25% × 3-4 (not recommended) | 35-55%+ | $550k-1M+ | -25 to -45% | Dangerous — psychologically destructive |

The recommended 15×6 configuration sits in the zone where returns are meaningfully better than conservative but drawdowns stay within most people's psychological tolerance.

---

## 8. PAPER TRADING PROTOCOL

### 8.1 Setup

Run the full pipeline weekly for 3-6 months without committing capital. Track every signal as if you had executed it at the **recommended 15×6 sizing with conviction tiers**.

**Weekly workflow:**
1. Run `sterling_indicators.py` on your watchlist to identify technical buy signals
2. For each buy signal, run through the LLM gate pipeline (thematic → investment gate → deep DD)
3. Record the decision (BUY / SKIP), the gate verdict, conviction score, and assigned position size tier
4. Track hypothetical entries at Monday's opening price with the conviction-appropriate size
5. Each week, check open positions for exit signals (ExD + profit lock)
6. Record exits and calculate returns — both per-trade and portfolio-weighted

### 8.2 What to Track

For each trade, record:

| Field | Example |
|-------|---------|
| Ticker | MARA |
| Entry date | 2026-03-09 |
| Entry price | $14.50 |
| Entry signal details | HMA rising, RSI 62.3, MACD cross-up this bar, UC 8.5 (RSI10: 55.7) |
| Gate 1 result | PRIME theme (Crypto), STRONG FIT, score 8.5 |
| Gate 2 result | STRONG BUY, conviction 8, catalyst: Bitcoin halving supply shock |
| Gate 3 result | STRONG BUY, conviction 9, math: BTC to $150k → MARA $35+ |
| **Conviction tier** | **High (20% position)** |
| **Position size** | **$24,000 of $120,000 portfolio** |
| Peak close | $28.50 |
| Current lock tier | +100% (20% trail from $28.50 = floor $22.80) |
| Exit date | 2026-07-18 |
| Exit price | $24.25 |
| Exit reason | Profit lock (current return +67%, tier: 25% trail, floor $21.38) |
| Return (per trade) | +67.2% |
| **Return (portfolio-weighted)** | **+13.4% (67.2% × 20% allocation)** |
| Hold period | 19 weeks |

**Additionally, track portfolio-level metrics weekly:**
- Total equity (mark-to-market)
- Number of open positions and their conviction tiers
- Cash percentage
- Current drawdown from portfolio peak
- Sector concentration (how many positions per sector)

### 8.3 Assessment Criteria After 3-6 Months

**Minimum sample size:** 8-12 trades (roughly 2-3 signals per month).

**Compare these metrics to the backtest benchmarks:**

| Metric | Backtest Benchmark | Acceptable Range | Red Flag |
|--------|-------------------|-----------------|----------|
| Win rate | 79% | 60-85% | Below 55% |
| Average winner | +86% | +40-120% | Below +30% |
| Average loser | -15% (estimated) | -10 to -25% | Beyond -35% |
| Profit factor | 15.9 | 5-20 | Below 3 |
| Trades per month | ~1.5 | 1-3 | 0 for 2+ months |
| Gate pass rate | ~50% cumulative | 30-60% | Below 20% or above 80% |

**Key questions to answer:**

1. **Are the LLM gates selecting stocks of Gate-Proxy quality?** Compare the win rate and average return of your actual trades to the backtest. If your win rate is below 60% after 12+ trades, the gates may need tuning.

2. **Are the technical signals firing at the right time?** Check if the HMA slope + MACD cross-up signals are catching trend starts or firing too late (after the stock has already run 50%+).

3. **Are the profit locks working as expected?** Track how many positions hit the +50%, +100%, +200% tiers. If very few reach +50%, the stock selection may not be identifying strong enough runners.

4. **Is the ExD exit catching reversals cleanly?** Check if ExD exits are occurring near actual trend tops or much later. If ExD consistently fires 20%+ below the peak, the lock is doing the real work and ExD is backup.

5. **What's the re-entry quality?** If you re-enter stocks after lock exits, track whether re-entries perform as well as first entries. V4 showed re-entries have similar quality with a 4-8 week cooldown.

6. **Are conviction tiers predicting correctly?** Do high-conviction (20%) positions outperform standard (15%) and speculative (8%) positions? If SPEC BUYs are performing as well as STRONG BUYs, the gate pipeline's conviction scoring may not be differentiating well enough.

### 8.4 Adaptive Gear-Shift Protocol

After the initial 6-month paper trading period (or once you have 12+ completed trades with live capital), evaluate your demonstrated results and shift sizing up or down accordingly. This is the key mechanism that prevents you from being locked into overly conservative sizing when the system is working well, or overly aggressive sizing when something is off.

**Gear UP — shift to more aggressive sizing when:**
- Win rate above 65% across 12+ trades
- Average winner above +50%
- No single trade lost more than -30%
- Portfolio drawdown has not exceeded -15%
- You have maintained discipline (no overrides, no panic exits)

| Current Config | Gear-Up Config | What Changes |
|---------------|---------------|-------------|
| 15% × 6 (starting) | 20% × 5 | High-conviction positions increase to 25%, standard to 20% |
| 10% × 8 (conservative) | 15% × 6 | Return to recommended baseline |

**Gear DOWN — shift to more conservative sizing when:**
- Win rate below 50% across 12+ trades
- Average loser worse than -25%
- Portfolio drawdown has exceeded -20%
- You have overridden the system more than twice (panic sells, skipped signals)

| Current Config | Gear-Down Config | What Changes |
|---------------|----------------|-------------|
| 15% × 6 (starting) | 10% × 8 | All positions capped at 12%, more diversification |
| 20% × 5 (aggressive) | 15% × 6 | Return to recommended baseline |

**Gear PAUSE — halt new entries temporarily when:**
- 3+ consecutive losing trades
- Portfolio drawdown exceeds -25%
- Market regime appears to have fundamentally shifted (e.g., rate hiking cycle begins, major crash)
- You feel compelled to override the system — this is a signal that emotional decision-making is taking over

During a pause, continue running the scanner and gates weekly. Track what you *would* have entered. Resume when either (a) the hypothetical trades show the system is working again, or (b) the market condition that triggered the pause has resolved.

**Review cadence:** Conduct a gear-shift evaluation every 6 months or after every 15 completed trades, whichever comes first.

### 8.5 When to Go Live

Proceed to live trading when:
- You have 10+ paper trades completed
- Win rate is above 60%
- Average winner exceeds +40%
- No single trade lost more than -35%
- You're comfortable with the hold periods (median 24 weeks)
- You've experienced at least one losing trade and didn't panic
- You've practiced the conviction-tiering process and it feels natural

**Phased capital deployment:**

| Phase | Timeline | Capital Deployed | Sizing Config |
|-------|----------|-----------------|---------------|
| Paper trading | Months 1-6 | $0 (simulated at full 15×6) | 15% × 6 with tiers |
| Phase 1 (live) | Months 7-9 | 50% of intended capital ($60k of $120k) | 15% × 6 with tiers on half capital |
| Phase 2 (live) | Months 10-12 | 75% of intended capital | 15% × 6 with tiers |
| Full deployment | Month 13+ | 100% of intended capital | Gear-shifted based on Phase 1-2 results |

This phased approach means your first live trade at 20% conviction on half capital is only 10% of your total intended allocation ($12,000 of $120,000). This limits the psychological impact of early losses while you calibrate the system to real-market execution.

---

## 9. PYTHON IMPLEMENTATION

The `sterling_indicators.py` script (provided separately) implements all indicator calculations with exact parity to the backtest source code, plus conviction-tiered portfolio management. Key features:

**Signal scan mode:** `python sterling_indicators.py MARA RKLB IONQ`
Checks each ticker for current buy signals. Shows all indicator values and which conditions are met/missing. If signals are found, prompts you to run through the gate pipeline and calculate position size.

**Position check mode:** `python sterling_indicators.py --check MARA:5.50 RKLB:12.00`
Checks open positions for ExD exit signals and tiered profit lock triggers. Accepts optional peak price: `MARA:5.50:28.50`.

**Portfolio status mode:** `python sterling_indicators.py --portfolio 120000 MARA:5.50:9 RKLB:12.00:7 IONQ:8.25:5`
Shows full portfolio deployment: current positions by conviction tier, available slots, cash reserve, and what the next position would look like at each conviction level. Fetches live prices for each position. The third value after each ticker is the conviction score (1-10) from the gate pipeline.

**Position size calculator:** `python sterling_indicators.py --size 120000 8`
Quick calculation of position size for a given portfolio equity and conviction score. Useful when a signal fires and you need to know the dollar amount before placing the order.

**Sizing gear override:** Add `--gear conservative` or `--gear aggressive` to any command to switch between the three sizing configurations (conservative = 10×8, recommended = 15×6, aggressive = 20×5).

**History dump mode:** `python sterling_indicators.py --history MARA`
Exports full weekly indicator history to CSV for verification against TradingView or the backtest output.

**Dependencies:** `yfinance`, `numpy`, `pandas` (all pip-installable).

**Verification:** To confirm the script produces identical signals to the backtest, run `--history` on a ticker that appears in the backtest trade list and compare the buy/sell signal dates.

---

## 10. IMPORTANT CAVEATS AND LIMITATIONS

### 10.1 What the Backtest Cannot Tell You

- **LLM gate quality in real-time.** The Gate-Proxy universe was curated retrospectively (winners and known failures). Your real-time gates will see stocks whose outcomes are unknown. Gate accuracy in practice may differ from the backtest assumption.

- **Future market regime.** 72% of ExD_pure's P&L came from 2021. The next 7 years may not contain a comparable growth stock bubble. Median-case returns are significantly lower than headline backtested returns.

- **Execution slippage on thin stocks.** Sub-$25 growth stocks can have wide spreads, especially on Monday opens. The pessimistic cost scenario (0.5% slippage) showed the system still works, but actual slippage varies by stock.

- **Psychological tolerance.** Holding a stock for 12+ months through -30% drawdowns requires conviction. The backtest executes mechanically; you may not.

### 10.2 Known Vulnerabilities

- **Sector concentration:** 63% of historical P&L from crypto (40%) and clean energy (23%). If these themes cool for multiple years, returns will be below expectations.

- **Winner dependency:** Top 5 trades = 81% of P&L. The system requires being present for rare 500%+ moves. Skipping even one signal because it "doesn't feel right" can materially impact returns.

- **Year-by-year lumpiness:** Expect 1-2 flat years out of every 5-7. The strategy makes most of its money in concentrated bursts during growth rallies.

- **Data source dependency:** yfinance data quality varies. Always cross-reference signals with TradingView or your broker's charts before executing.

---

## 11. QUICK REFERENCE — WEEKLY CHECKLIST

### Friday Evening (after market close)

1. Run `sterling_indicators.py` on your watchlist
2. Note any new BUY signals (all 4 conditions on same bar)
3. Check all open positions for EXIT signals (ExD or profit lock)
4. Run `sterling_indicators.py --portfolio` to see current deployment and available slots

### Saturday/Sunday (if buy signals found)

5. Run each buy signal through the LLM gate pipeline:
   - Thematic Analyzer → Is the theme PRIME or INVESTABLE?
   - Investment Gate → STRONG BUY or SPEC BUY? What conviction score (1-10)?
   - Deep DD → Confirms or vetoes?
6. Read the Deep DD analysis. Does it make sense to you?
7. Assign position size based on conviction tier:
   - Conviction 8-10 → 20% of equity (max 2 of these)
   - Conviction 7 → 15% of equity (standard)
   - Conviction 4-6 (SPEC BUY) → 8% of equity
8. Verify you have capacity: check current open positions (max 6) and cash (min 10%)
9. Decide: execute or skip

### Monday Morning

10. Execute buys at market open (or use limit orders at Friday's close)
11. Execute any exits flagged on Friday
12. Update your position tracker with new entries/exits, conviction tiers, position sizes, and new peak closes
13. Record everything for paper trading assessment / gear-shift evaluation

### Monthly

14. Review portfolio performance vs backtest benchmarks
15. Check sector concentration (max 3 per sector)
16. Review any positions held 6+ months — are the catalysts still intact?
17. Calculate running win rate, average winner/loser, profit factor
18. Check: are conviction tiers predicting correctly? (Do 20% positions outperform 8%?)

### Every 6 Months (or every 15 completed trades)

19. Conduct gear-shift evaluation (see Section 8.4)
20. Decide: maintain current sizing, gear up, gear down, or pause

---

## APPENDIX: CORRECTION LOG

Three critical errors were identified in the initial draft of this document and corrected after reviewing the actual backtest source code:

**1. Undercurrent is NOT a VWAP indicator.**
Initial draft described UC as a VWAP price deviation (matching the scanner's Banker formula). The actual backtest UC is `clip(1.5 × (RSI(10) − 50), 0, 20)` — a normalised RSI derivative. The scanner's Banker and the backtest's UC are directionally correlated but mathematically different. The scanner needs to be updated to use the RSI-derived formula.

**2. MACD cross-up is a single-bar event, not a 3-bar lookback.**
Initial draft allowed the MACD cross-up to have occurred within the last 3 bars. The actual backtest requires the cross on the exact same bar as all other conditions: `(MACD > Signal) AND (MACD.shift(1) <= Signal.shift(1))`. This is stricter and produces fewer but higher-quality signals.

**3. Profit lock tiers are based on current return, not peak return. Tiers can degrade.**
Initial draft implied tiers ratchet (once +200% tier activates, it stays at 15% trail). The actual backtest evaluates `current_return = (bar_close - entry_price) / entry_price` each bar. If the stock pulls back from +250% to +90% current return, the tier loosens from 15% to 20%. Below +50% current return, the lock deactivates entirely. This is intentional — it provides flexibility for recovery rather than prematurely locking in on a temporary pullback.

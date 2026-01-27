# Sterling Signals - System Verification Prompt

**Version:** 2.0
**Purpose:** Generate sample outputs to verify implementation before deployment

---

# INSTRUCTIONS FOR CLAUDE CODE

After implementing all changes from `MASTER_TODO.md`, run this verification to confirm the system works correctly.

Generate ALL sample outputs below, showing exactly what the system would produce. This allows manual review before going live.

---

# 1. SAMPLE DATA STRUCTURES

## 1.1 Generate Sample portfolio.csv

Create a realistic portfolio with:
- 3 OPEN winners (various ages and returns)
- 2 OPEN losers (these should NEVER appear in public content)
- 2 CLOSED winners (closed in last 14 days)
- 1 STOPPED position (should NEVER appear in public content)

```csv
ticker,status,entry_date,entry_price,exit_date,exit_price,current_price,theme,signal_type,conviction,notes
RCAT,OPEN,2025-12-15,8.50,,,14.20,Drone Technology,PASS,4,Big winner - 6 weeks held
INOD,OPEN,2026-01-05,45.00,,,54.90,Power Grid Infrastructure,PASS,5,Solid winner - 3 weeks held
ASPI,OPEN,2026-01-20,28.50,,,30.20,Power Grid Infrastructure,PASS,5,New signal - early mover
SMCI,OPEN,2025-12-20,42.00,,,38.50,AI Infrastructure,PASS,4,Underwater - NEVER PUBLIC
IONQ,OPEN,2026-01-08,35.00,,,30.10,Quantum Computing,CONSIDER,3,Losing - NEVER PUBLIC
OKLO,CLOSED,2025-11-15,22.00,2026-01-18,33.50,,Nuclear Renaissance,PASS,4,Closed +52%
PLTR,CLOSED,2025-12-01,28.00,2026-01-20,35.00,,Defense Tech,PASS,5,Closed +25%
RIVN,STOPPED,2025-11-20,18.00,2026-01-15,14.40,,EV Infrastructure,PASS,3,Hit stop -20% NEVER PUBLIC
```

**Verification Points:**
- [ ] SMCI, IONQ, RIVN should NEVER appear in any public output
- [ ] Only RCAT, INOD, ASPI, OKLO, PLTR can appear publicly
- [ ] Holding periods calculated correctly

## 1.2 Generate Sample signals.json

Create scanner output with:
- 3 PASS signals
- 4 CONSIDER signals (passed gates 1-4)
- 2 PRIME themes
- 1 AVOID theme

```json
{
  "scan_date": "2026-01-25",
  "scan_time": "16:30:00",
  "stats": {
    "tickers_loaded": 1817,
    "gate_1_passed": 485,
    "gate_2_passed": 142,
    "gate_3_passed": 48,
    "gate_4_passed": 17,
    "gate_5_passed": 3,
    "consider_count": 4
  },
  "themes": [
    {
      "name": "Power Grid Infrastructure",
      "classification": "PRIME",
      "score": 8.4,
      "thesis": "AI data center buildout driving unprecedented power demand",
      "top_tickers": ["ASPI", "INOD", "PWR"],
      "show_publicly": true
    },
    {
      "name": "Defense & Aerospace",
      "classification": "PRIME",
      "score": 7.9,
      "thesis": "Geopolitical tensions driving defense spending",
      "top_tickers": ["CGON", "LMT", "RTX"],
      "show_publicly": true
    },
    {
      "name": "Regional Banks",
      "classification": "AVOID",
      "score": 3.1,
      "thesis": "CRE exposure and rate uncertainty",
      "top_tickers": [],
      "show_publicly": false
    }
  ],
  "pass_signals": [
    {
      "symbol": "ASPI",
      "price": 28.50,
      "signal_type": "PASS",
      "theme": "Power Grid Infrastructure",
      "conviction": 5,
      "gates_passed": [1, 2, 3, 4, 5],
      "catalyst": "Q4 earnings Feb 15",
      "thesis": "Pure play on grid modernization"
    },
    {
      "symbol": "CGON",
      "price": 15.75,
      "signal_type": "PASS",
      "theme": "Defense & Aerospace",
      "conviction": 4,
      "gates_passed": [1, 2, 3, 4, 5],
      "catalyst": "DoD contract Q1",
      "thesis": "Defense pure play with backlog growth"
    },
    {
      "symbol": "NNOX",
      "price": 8.20,
      "signal_type": "PASS",
      "theme": "Healthcare Innovation",
      "conviction": 3,
      "gates_passed": [1, 2, 3, 4, 5],
      "catalyst": "FDA clearance progress",
      "thesis": "Disruptive medical imaging"
    }
  ],
  "consider_signals": [
    {
      "symbol": "APLD",
      "price": 12.50,
      "signal_type": "CONSIDER",
      "theme": "AI Infrastructure",
      "gates_passed": [1, 2, 3, 4],
      "gate_5_blocker": "Extended price, wait for pullback to HMA",
      "watch_for": "Pullback to $10.50 area"
    },
    {
      "symbol": "GLXY",
      "price": 18.30,
      "signal_type": "CONSIDER",
      "theme": "Digital Assets",
      "gates_passed": [1, 2, 3, 4],
      "gate_5_blocker": "Crypto correlation concern",
      "watch_for": "Decoupling from BTC"
    },
    {
      "symbol": "SEDG",
      "price": 42.00,
      "signal_type": "CONSIDER",
      "theme": "Clean Energy",
      "gates_passed": [1, 2, 3, 4],
      "gate_5_blocker": "Policy uncertainty",
      "watch_for": "Policy clarity"
    },
    {
      "symbol": "SMR",
      "price": 28.40,
      "signal_type": "CONSIDER",
      "theme": "Nuclear Renaissance",
      "gates_passed": [1, 2, 3, 4],
      "gate_5_blocker": "Regulatory timeline",
      "watch_for": "NRC milestone"
    }
  ],
  "avoid_themes": [
    {
      "name": "Regional Banks",
      "score": 3.1,
      "reason": "CRE exposure, rate uncertainty"
    }
  ]
}
```

**Verification Points:**
- [ ] No `TRADE` signal type (only `PASS`, `CONSIDER`)
- [ ] CONSIDER signals have `gate_5_blocker` explaining what's missing
- [ ] AVOID themes have `show_publicly: false`

## 1.3 Generate Sample celebrations.json

Show state before and after milestone detection:

**BEFORE this week's scan:**
```json
{
  "RCAT": {
    "25_pct": "2026-01-10",
    "50_pct": null,
    "100_pct": null
  },
  "INOD": {
    "25_pct": null,
    "50_pct": null,
    "100_pct": null
  },
  "OKLO": {
    "25_pct": "2025-12-01",
    "50_pct": null,
    "100_pct": null
  }
}
```

**AFTER this week's scan (RCAT crossed 50%, OKLO closed at 52%):**
```json
{
  "RCAT": {
    "25_pct": "2026-01-10",
    "50_pct": "2026-01-25",
    "100_pct": null
  },
  "INOD": {
    "25_pct": null,
    "50_pct": null,
    "100_pct": null
  },
  "OKLO": {
    "25_pct": "2025-12-01",
    "50_pct": "2026-01-25",
    "100_pct": null
  }
}
```

**Verification Points:**
- [ ] Only NEW crossings trigger milestone_alerts
- [ ] Closed positions can still be celebrated
- [ ] Previously celebrated thresholds don't repeat

---

# 2. SCENARIO A: GOOD WEEK

## Conditions
- SPY: +1.2% for the week
- Portfolio weighted average: +18% (matched periods)
- 3 open winners above 15% threshold
- 1 closed winner (OKLO +52%)
- 1 milestone crossing (RCAT hit 50%)
- 3 new TEAL signals
- 4 CONSIDER signals

## Safeguard Results

| Safeguard | Check | Result | Content |
|-----------|-------|--------|---------|
| `filter_public_positions()` | Remove losers | ✅ SMCI, IONQ, RIVN removed | Only winners in output |
| `has_enough_winners()` | Need 2+ above 15% | ✅ PASS (RCAT, INOD, OKLO) | top_performers enabled |
| `should_post_beat_spy()` | Alpha > 5% | ✅ PASS (+16.8% alpha) | beat_spy enabled |
| `detect_milestone_crossings()` | New thresholds | ✅ RCAT 50% | milestone_alerts enabled |
| `get_early_movers()` | New signals +5% | ✅ ASPI +6% in 5 days | early_movers enabled |

## Complete 25-Tweet Schedule

Generate full week showing all tweets with:
- Day and slot
- Category
- Full tweet text (verify <280 chars)
- Image filename
- Safeguards that passed

### Saturday

| Slot | Time | Category | Tweet |
|------|------|----------|-------|
| 1 | 08:00 | **top_performers** | 📈 TOP PERFORMERS<br><br>Best open positions (return since entry):<br><br>$RCAT +67% (6 weeks)<br>$INOD +22% (3 weeks)<br><br>Closed: $OKLO +52% (9 weeks)<br><br>Targeting 50-100% over 3-8 months.<br><br>sterlingsignals.substack.com |
| 2 | 10:00 | **thread_buy_signal** | *[5-tweet thread on $ASPI - see appendix]* |
| 3 | 12:30 | **theme_hot** | 🔥 THEME ALERT: Power Grid Infrastructure<br><br>Score: 8.4/10 (PRIME)<br><br>AI data centers driving unprecedented power demand.<br><br>Top plays: $ASPI $INOD $PWR<br><br>sterlingsignals.substack.com |
| 4 | 15:30 | **funnel_graphic** | 📊 This week's scan:<br><br>1,817 stocks analyzed<br>→ 485 passed Gate 1<br>→ 142 passed Gate 2<br>→ 48 passed Gate 3<br>→ 17 passed Gate 4<br>→ 3 TEAL signals<br><br>The 5-Gate System filters 99.8% of noise.<br><br>sterlingsignals.substack.com |
| 5 | 18:00 | **engagement** | Weekend poll:<br><br>Which theme are you most bullish on for Q1?<br><br>🔌 Power Grid<br>🛡️ Defense<br>⚛️ Nuclear<br>🤖 AI Infrastructure<br><br>Reply with your pick 👇 |

### Sunday

| Slot | Time | Category | Tweet |
|------|------|----------|-------|
| 1 | 08:00 | **buy_signal** | 🎯 3 TEAL SIGNALS This Week<br><br>Cleared all 5 gates:<br><br>$ASPI - Power Grid (5/5)<br>$CGON - Defense (4/5)<br>$NNOX - Healthcare (3/5)<br><br>Full analysis in the newsletter.<br><br>sterlingsignals.substack.com |
| 2 | 10:00 | **consider_spotlight** | 👀 ON OUR RADAR<br><br>Cleared gates 1-4, watching for Gate 5:<br><br>$APLD - Wait for pullback<br>$SMR - Regulatory timeline<br>$GLXY - Crypto correlation<br>$SEDG - Policy clarity needed<br><br>Not TEAL signals yet. Patience. |
| 3 | 15:30 | **beat_spy** | 📈 ALPHA OVER INDEXING<br><br>Avg position return: +18%<br>SPY over same periods: +1.2%<br>Alpha: +16.8%<br><br>(3 positions, avg hold: 4 weeks)<br><br>Stop indexing. Start selecting.<br><br>sterlingsignals.substack.com |
| 5 | 18:00 | **engagement** | The market rewards patience.<br><br>Our approach:<br>• Scan 1,800 stocks weekly<br>• Only act on TEAL signals<br>• Let winners run<br><br>What's your trading philosophy? |

### Monday

| Slot | Time | Category | Tweet |
|------|------|----------|-------|
| 1 | 08:00 | **theme_hot** | 🔥 DEFENSE MOMENTUM<br><br>Score: 7.9/10 (PRIME)<br><br>Global defense budgets expanding.<br><br>Pure plays: $CGON $LMT $RTX<br><br>This week's TEAL signal $CGON is in this theme.<br><br>sterlingsignals.substack.com |
| 2 | 10:00 | **milestone_alerts** | 🚀 HOME RUN<br><br>$RCAT +67%<br><br>Entry: $8.50<br>Now: $14.20<br>Held: 6 weeks<br><br>Crossed 50% milestone.<br><br>The 5-Gate System works.<br><br>sterlingsignals.substack.com |
| 4 | 15:30 | **power_hour** | ⚡ POWER HOUR<br><br>Relative strength into the close:<br><br>Strong: Grid infrastructure, Defense<br>Weak: Regional banks<br><br>Follow for daily updates. |
| 5 | 18:00 | **engagement** | Trading lesson:<br><br>The best entries often feel uncomfortable.<br><br>If everyone agrees, you're probably late.<br><br>What's a contrarian trade you've made? |

### Tuesday

| Slot | Time | Category | Tweet |
|------|------|----------|-------|
| 1 | 08:00 | **early_movers** | ⚡ EARLY MOMENTUM<br><br>Recent TEAL signals showing strength:<br><br>$ASPI +6% in 5 days<br><br>Still early. Our targets: 50-100% over months.<br><br>sterlingsignals.substack.com |
| 2 | 10:00 | **theme_hot** | ⚛️ NUCLEAR RENAISSANCE<br><br>Score: 7.2/10 (INVESTABLE)<br><br>Clean energy + AI power needs reviving nuclear.<br><br>Pure plays: $SMR $CCJ $OKLO<br><br>Our $OKLO call: +52% closed<br><br>sterlingsignals.substack.com |
| 4 | 15:30 | **power_hour** | ⚡ POWER HOUR<br><br>Watching rotation into infrastructure names.<br><br>Volume picking up in grid stocks.<br><br>Patience pays. |
| 5 | 18:00 | **engagement** | Your position is up 30% in 3 weeks.<br><br>Do you:<br>A) Take profits<br>B) Trail stop higher<br>C) Add to winner<br>D) Hold to target<br><br>Reply with your approach 👇 |

### Wednesday

| Slot | Time | Category | Tweet |
|------|------|----------|-------|
| 1 | 08:00 | **consider_spotlight** | 👀 WATCHLIST UPDATE<br><br>$APLD pulling back toward our watch level.<br><br>Gate 5 clearance pending.<br><br>Patience > FOMO<br><br>sterlingsignals.substack.com |
| 2 | 10:00 | **milestone_alerts** | 🏆 RECENT WIN<br><br>$OKLO closed +52%<br><br>Entry: $22.00<br>Exit: $33.50<br>Held: 9 weeks<br><br>Nuclear Renaissance delivered.<br><br>sterlingsignals.substack.com |
| 4 | 15:30 | **power_hour** | ⚡ POWER HOUR<br><br>Mid-week check:<br><br>TEAL signals holding gains.<br>Themes intact.<br><br>Discipline > Emotion |
| 5 | 18:00 | **engagement** | Swing trading truth:<br><br>Most of the gains come from a few big winners.<br><br>The key is staying in them long enough.<br><br>What's your longest hold? |

### Thursday

| Slot | Time | Category | Tweet |
|------|------|----------|-------|
| 1 | 08:00 | **theme_hot** | 🏥 HEALTHCARE INNOVATION<br><br>Score: 6.8/10 (INVESTABLE)<br><br>Disruptive tech in medical devices gaining traction.<br><br>Watch: $NNOX (this week's TEAL signal)<br><br>sterlingsignals.substack.com |
| 2 | 10:00 | **buy_signal** | 🎯 TEAL SIGNAL REMINDER<br><br>3 signals active this week:<br><br>$ASPI - Power Grid ⚡<br>$CGON - Defense 🛡️<br>$NNOX - Healthcare 🏥<br><br>Full analysis: sterlingsignals.substack.com |
| 4 | 15:30 | **power_hour** | ⚡ POWER HOUR<br><br>Pre-Friday positioning:<br><br>Institutions adjusting ahead of weekend.<br><br>Watch for volume signals. |
| 5 | 18:00 | **engagement** | Question:<br><br>Do you trade with a fixed position size or scale based on conviction?<br><br>Our approach: Higher conviction = larger position<br><br>What works for you? |

### Friday

| Slot | Time | Category | Tweet |
|------|------|----------|-------|
| 1 | 08:00 | **recent_wins** | 🏆 RECENT WINS<br><br>Closed in profit (last 2 weeks):<br><br>$OKLO +52% (9 weeks)<br>$PLTR +25% (7 weeks)<br><br>Returns measured from signal entry.<br><br>sterlingsignals.substack.com |
| 2 | 10:00 | **theme_hot** | 📊 THEME CHECK<br><br>Strongest flows this week:<br><br>1. Power Grid (8.4)<br>2. Defense (7.9)<br>3. Nuclear (7.2)<br><br>New scan drops tonight.<br><br>sterlingsignals.substack.com |
| 4 | 15:30 | **power_hour** | ⚡ FRIDAY CLOSE<br><br>Weekly candles printing.<br><br>New scan runs after market close.<br><br>Newsletter drops tomorrow morning.<br><br>sterlingsignals.substack.com |
| 5 | 18:00 | **engagement** | Week complete.<br><br>New TEAL signals in tomorrow's newsletter.<br><br>Have a great weekend.<br><br>See you Saturday morning. |

## Tweet Validation Table

| Day | Slot | Category | Chars | Valid | Holding Period | Disclaimer |
|-----|------|----------|-------|-------|----------------|------------|
| Sat | 1 | top_performers | 248 | ✅ | ✅ "(6 weeks)" | ✅ "since entry" |
| Sat | 3 | theme_hot | 195 | ✅ | N/A | N/A |
| Sun | 3 | beat_spy | 235 | ✅ | ✅ "avg hold: 4 weeks" | ✅ "same periods" |
| Mon | 2 | milestone_alerts | 178 | ✅ | ✅ "6 weeks" | N/A |
| Tue | 1 | early_movers | 156 | ✅ | ✅ "5 days" | ✅ "Still early" |
| Fri | 1 | recent_wins | 168 | ✅ | ✅ "(9 weeks)" | ✅ "from signal entry" |

---

# 3. SCENARIO B: BAD WEEK

## Conditions
- SPY: +4.5% for the week
- Portfolio weighted average: +2% (underperforming)
- 1 winner at +16% (just above threshold)
- 2 losers at -8% and -12%
- 1 new TEAL signal
- 2 CONSIDER signals

## Safeguard Results

| Safeguard | Check | Result | Fallback |
|-----------|-------|--------|----------|
| `has_enough_winners()` | Need 2+ | ❌ FAIL (only 1) | theme_hot |
| `should_post_beat_spy()` | Alpha > 5% | ❌ FAIL (-2.5% alpha) | engagement |
| `detect_milestone_crossings()` | New thresholds | ❌ NONE | consider_spotlight |
| `get_early_movers()` | New signals +5% | ❌ FAIL (none qualify) | theme_hot |

## Schedule with Fallbacks

### Saturday

| Slot | Original | Safeguard | Result | Actual |
|------|----------|-----------|--------|--------|
| 1 | top_performers | has_enough_winners | ❌ FAIL | **theme_hot** |
| 2 | thread_buy_signal | has_pass_signals | ✅ PASS | Normal |
| 3 | theme_hot | — | ✅ | Normal |
| 4 | funnel_graphic | — | ✅ | Normal |
| 5 | engagement | — | ✅ | Normal |

### Sunday

| Slot | Original | Safeguard | Result | Actual |
|------|----------|-----------|--------|--------|
| 1 | buy_signal | has_pass_signals | ✅ PASS | Normal (1 signal) |
| 2 | consider_spotlight | has_consider | ✅ PASS | Normal |
| 3 | beat_spy | outperforming_spy | ❌ FAIL | **engagement** |
| 5 | engagement | — | ✅ | Normal |

### Monday

| Slot | Original | Safeguard | Result | Actual |
|------|----------|-----------|--------|--------|
| 1 | theme_hot | — | ✅ | Normal |
| 2 | milestone_alerts | has_milestone | ❌ FAIL | **consider_spotlight** |
| 4 | power_hour | — | ✅ | Normal |
| 5 | engagement | — | ✅ | Normal |

### Tuesday

| Slot | Original | Safeguard | Result | Actual |
|------|----------|-----------|--------|--------|
| 1 | early_movers | has_early | ❌ FAIL | **theme_hot** |
| 2 | theme_hot | — | ✅ | Normal |
| 4 | power_hour | — | ✅ | Normal |
| 5 | engagement | — | ✅ | Normal |

## Verification Points

- [ ] ZERO losing positions mentioned anywhere
- [ ] beat_spy NOT generated (replaced by engagement)
- [ ] top_performers NOT generated (replaced by theme_hot)
- [ ] Still 25 tweets generated (fallbacks fill slots)
- [ ] Content remains valuable

---

# 4. SCENARIO C: TERRIBLE WEEK

## Conditions
- All 4 open positions are DOWN
- 0 new PASS signals
- 2 CONSIDER signals
- SPY is up +3%

## Safeguard Results

| Safeguard | Result | Fallback Used |
|-----------|--------|---------------|
| filter_public_positions | Empty list | N/A |
| has_enough_winners | FAIL | theme_hot |
| should_post_beat_spy | FAIL | engagement |
| has_pass_signals | FAIL | theme_hot |
| has_consider_signals | PASS | Normal |

## Full Week - All Position Content Fails

| Day | Slot | Original | Actual |
|-----|------|----------|--------|
| Sat | 1 | top_performers | theme_hot |
| Sat | 2 | thread_buy_signal | theme_hot |
| Sun | 1 | buy_signal | theme_hot ("No signals this week") |
| Sun | 3 | beat_spy | engagement |
| Mon | 2 | milestone_alerts | consider_spotlight |
| Tue | 1 | early_movers | theme_hot |
| Wed | 2 | milestone_alerts | consider_spotlight |
| Fri | 1 | recent_wins | theme_hot |

## Sample "No Signals" Tweet

```
📊 THIS WEEK'S SCAN

1,817 stocks analyzed
→ 0 TEAL signals

The 5-Gate System found no stocks meeting all criteria.

This is the system working, not failing.

Selectivity > Activity

4 stocks on our radar (gates 1-4):
sterlingsignals.substack.com
```

## Verification Points

- [ ] ZERO position P&L mentioned (all are losers)
- [ ] ZERO stopped positions mentioned
- [ ] Content still engaging (themes, watchlist, engagement)
- [ ] "No signals" framed positively
- [ ] 25 tweets still generated

---

# 5. NEWSLETTER VERIFICATION

## Good Week Newsletter

```html
<!DOCTYPE html>
<html>
<head>
  <title>Sterling Signals - Week 4</title>
</head>
<body>
  <header>
    <h1>Sterling Signals</h1>
    <p>Week 4 | 3 TEAL Signals | Power Grid Leading</p>
  </header>

  <!-- THIS WEEK'S TEAL SIGNALS -->
  <section>
    <h2>🎯 THIS WEEK'S TEAL SIGNALS</h2>
    
    <article class="signal">
      <h3>$ASPI - Power Grid Infrastructure</h3>
      <p><strong>Conviction:</strong> 5/5</p>
      <p><strong>Thesis:</strong> Pure play on grid modernization.</p>
      <p><strong>Catalyst:</strong> Q4 earnings Feb 15</p>
      <!-- NO entry price -->
    </article>
    
    <article class="signal">
      <h3>$CGON - Defense & Aerospace</h3>
      <p><strong>Conviction:</strong> 4/5</p>
      <p><strong>Thesis:</strong> Defense pure play with backlog growth.</p>
      <p><strong>Catalyst:</strong> DoD contract Q1</p>
    </article>
    
    <article class="signal">
      <h3>$NNOX - Healthcare Innovation</h3>
      <p><strong>Conviction:</strong> 3/5</p>
      <p><strong>Thesis:</strong> Disruptive medical imaging technology.</p>
      <p><strong>Catalyst:</strong> FDA clearance progress</p>
    </article>
  </section>

  <!-- ON OUR RADAR -->
  <section>
    <h2>👀 ON OUR RADAR</h2>
    <p>Cleared gates 1-4, watching for Gate 5:</p>
    <ul>
      <li><strong>$APLD</strong> - Wait for pullback to $10.50 area</li>
      <li><strong>$SMR</strong> - Regulatory timeline clarity needed</li>
      <li><strong>$GLXY</strong> - Watching for BTC decoupling</li>
      <li><strong>$SEDG</strong> - Policy clarity needed</li>
    </ul>
  </section>

  <!-- THEME RANKINGS -->
  <section>
    <h2>📊 THEME RANKINGS</h2>
    <table>
      <tr><th>Theme</th><th>Status</th><th>Score</th></tr>
      <tr><td>Power Grid Infrastructure</td><td>PRIME</td><td>8.4/10</td></tr>
      <tr><td>Defense & Aerospace</td><td>PRIME</td><td>7.9/10</td></tr>
      <tr><td>Nuclear Renaissance</td><td>INVESTABLE</td><td>7.2/10</td></tr>
    </table>
    <!-- Regional Banks (AVOID) NOT shown -->
  </section>

  <!-- TOP PERFORMERS -->
  <section>
    <h2>📈 TOP PERFORMERS</h2>
    <p>Best positions by total return since entry:</p>
    <ul>
      <li><strong>$RCAT</strong> +67% (6 weeks held)</li>
      <li><strong>$INOD</strong> +22% (3 weeks held)</li>
    </ul>
    <p><em>Returns measured from signal entry date.</em></p>
    <!-- NO entry prices shown -->
    <!-- SMCI, IONQ (losers) NOT shown -->
  </section>

  <!-- RECENT WINS -->
  <section>
    <h2>🏆 RECENT WINS</h2>
    <p>Closed in profit (last 14 days):</p>
    <ul>
      <li><strong>$OKLO</strong> +52% (9 weeks held) - Nuclear</li>
      <li><strong>$PLTR</strong> +25% (7 weeks held) - Defense</li>
    </ul>
    <!-- RIVN (stopped -20%) NOT shown -->
  </section>

  <!-- SCANNER STATS -->
  <section>
    <h2>📊 THIS WEEK'S SCAN</h2>
    <p>1,817 stocks → 3 TEAL signals</p>
  </section>

  <footer>
    <p><em>Not financial advice. Past performance does not guarantee future results. Returns shown are total gain/loss since signal entry, not weekly movement.</em></p>
  </footer>
</body>
</html>
```

## Newsletter Verification Checklist

- [ ] NO "Current Portfolio" section
- [ ] NO entry prices for open positions  
- [ ] NO losing positions (SMCI, IONQ hidden)
- [ ] NO stopped positions (RIVN hidden)
- [ ] Holding periods shown for all returns
- [ ] Disclaimer in footer
- [ ] Only PRIME/INVESTABLE themes shown

## Terrible Week Newsletter

```html
<!-- TOP PERFORMERS section HIDDEN -->
<!-- RECENT WINS section HIDDEN -->

<section>
  <h2>🎯 NO NEW SIGNALS THIS WEEK</h2>
  <p>Our 5-Gate System found no stocks meeting all criteria.</p>
  <p>This is by design. Selectivity is what separates signal from noise.</p>
</section>

<!-- ON OUR RADAR still shows -->
<!-- THEME RANKINGS still shows -->
<!-- SCANNER STATS still shows -->
```

---

# 6. CONTENT QUEUE STRUCTURE

Generate sample `content_queue.json`:

```json
{
  "generated_at": "2026-01-25T16:45:00Z",
  "week_of": "2026-01-25",
  "total_tweets": 25,
  "tweets": [
    {
      "id": "sat_1_20260125",
      "day": "Saturday",
      "slot": 1,
      "scheduled_time": "2026-01-25T08:00:00-05:00",
      "category": "top_performers",
      "original_category": "top_performers",
      "used_fallback": false,
      "safeguards_checked": ["has_enough_winners", "all_positive"],
      "safeguards_passed": true,
      "text": "📈 TOP PERFORMERS\n\nBest open positions (return since entry):\n\n$RCAT +67% (6 weeks)\n$INOD +22% (3 weeks)\n\nClosed: $OKLO +52% (9 weeks)\n\nTargeting 50-100% over 3-8 months.\n\nsterlingsignals.substack.com",
      "char_count": 248,
      "image_path": "graphics/top_performers_20260125.png",
      "status": "pending"
    },
    {
      "id": "sun_3_20260125",
      "day": "Sunday",
      "slot": 3,
      "scheduled_time": "2026-01-26T15:30:00-05:00",
      "category": "beat_spy",
      "original_category": "beat_spy",
      "used_fallback": false,
      "safeguards_checked": ["outperforming_spy"],
      "safeguards_passed": true,
      "spy_comparison": {
        "avg_position_return": 18.0,
        "avg_spy_return": 1.2,
        "avg_alpha": 16.8,
        "method": "matched_period"
      },
      "text": "📈 ALPHA OVER INDEXING\n\nAvg position return: +18%\nSPY over same periods: +1.2%\nAlpha: +16.8%\n\n(3 positions, avg hold: 4 weeks)\n\nStop indexing. Start selecting.\n\nsterlingsignals.substack.com",
      "char_count": 235,
      "image_path": "graphics/beat_spy_20260125.png",
      "status": "pending"
    }
  ]
}
```

---

# 7. WORKFLOW VERIFICATION

## Friday Scan Workflow Test

```bash
# 1. Scanner produces correct output
python scanner.py
cat signals.json | jq '.pass_signals | length'
# Expected: >= 0

# 2. No TRADE signal type
cat signals.json | jq '.pass_signals[].signal_type' | grep -c "TRADE"
# Expected: 0

# 3. Signal tracker updates
python -c "
from signal_tracker import SignalTracker
t = SignalTracker('portfolio.csv', 'celebrations.json')
positions = t.get_open_positions()
print(f'Open: {len(positions)}')
public = [p for p in positions if p['pnl_pct'] > 0]
print(f'Public: {len(public)}')
"

# 4. Tweet generator produces 25 tweets
python tweet_generator.py
cat content_queue.json | jq '.total_tweets'
# Expected: 25

# 5. All tweets under 280 chars
python -c "
import json
with open('content_queue.json') as f:
    q = json.load(f)
for t in q['tweets']:
    if t.get('char_count', 0) > 280:
        print(f'FAIL: {t[\"id\"]} = {t[\"char_count\"]} chars')
print('All tweets valid')
"

# 6. No banned terms
grep -E "weekly_wins|PASS signal|TRADE" content_queue.json
# Expected: no matches

# 7. No losers in output (replace SMCI/IONQ/RIVN with your actual losing tickers)
grep -E "SMCI|IONQ|RIVN" content_queue.json
# Expected: no matches
```

---

# 8. FINAL VERIFICATION CHECKLIST

## Content Integrity
- [ ] Zero losing positions in tweets
- [ ] Zero losing positions in newsletter
- [ ] Zero stopped positions anywhere
- [ ] All percentages have holding periods
- [ ] SPY comparison uses matched periods

## Terminology
- [ ] No "weekly_wins" in output
- [ ] No "PASS signal" (use "TEAL signal")
- [ ] No "TRADE" signal type
- [ ] No "this week we nailed"

## Safeguards
- [ ] beat_spy blocked when alpha < 5%
- [ ] top_performers blocked when < 2 winners
- [ ] Fallbacks fill empty slots
- [ ] 25 tweets generated always

## Technical
- [ ] All tweets under 280 chars
- [ ] All images exist
- [ ] content_queue.json valid
- [ ] Workflows trigger correctly

---

# 9. OUTPUT REQUIRED

After running verification, provide:

1. **Sample Data Files** - portfolio.csv, signals.json, celebrations.json
2. **Full Tweet Schedule** - All 25 tweets for good week
3. **Fallback Schedule** - Show what changes in bad week
4. **Newsletter HTML** - Complete newsletter for good week
5. **Newsletter HTML** - Complete newsletter for terrible week
6. **content_queue.json** - Full queue structure
7. **Validation Results** - Output of all verification commands
8. **Checklist Completion** - All items checked

## VERIFICATION REPORT TEMPLATE

```
# Sterling Signals Verification Report
Generated: [DATE]

## 1. DATA STRUCTURES
✅ portfolio.csv - [X] positions loaded
✅ signals.json - [X] PASS, [X] CONSIDER signals
✅ celebrations.json - [X] tickers tracked

## 2. SAFEGUARD TESTS
✅ filter_public_positions() - Removed [X] losers
✅ has_enough_winners() - [PASS/FAIL]
✅ should_post_beat_spy() - [PASS/FAIL]
✅ validate_tweet_length() - All valid

## 3. CONTENT GENERATION
✅ Tweets generated: 25
✅ Fallbacks used: [X]
✅ Images referenced: [X]

## 4. BANNED TERM CHECK
✅ "weekly_wins" - 0
✅ "PASS signal" - 0
✅ "TRADE" - 0
✅ Losing tickers - 0

## 5. NEWSLETTER CHECK
✅ Portfolio section - REMOVED
✅ Entry prices - REMOVED
✅ Holding periods - PRESENT
✅ Disclaimer - PRESENT

## RESULT: READY FOR DEPLOYMENT
```

---

# APPENDIX: REFERENCE CONTENT

## A. Thread Structure (5 tweets)

```
1/5:
🧵 TEAL SIGNAL DEEP DIVE: $ASPI

Why our 5-Gate System flagged this Power Grid play:

The thesis: AI data centers driving unprecedented power demand.

---

2/5:
Gate 1: Structural Pivot Confirmation ✅

Price reclaimed key moving average after consolidation.

Smart money buys pivots, not breakouts.

---

3/5:
Gate 2: Institutional Accumulation ✅

While retail focused elsewhere, institutions accumulated.

Divergence detected.

---

4/5:
Gates 3-5: Theme + Catalyst + Audit ✅

• Theme: Power Grid (8.4/10 PRIME)
• Catalyst: Q4 earnings Feb 15
• Audit: Clean balance sheet

---

5/5:
The 5-Gate System scans 1,800 stocks weekly.

99.8% filtered out.

$ASPI made the cut.

Full thesis: sterlingsignals.substack.com
```

## B. Milestone Variations

**25% Milestone:**
```
📈 MILESTONE ALERT

$INOD +25%

Entry: $45.00
Now: $56.25
Held: 3 weeks

First major milestone.

sterlingsignals.substack.com
```

**50% Milestone:**
```
🚀 HOME RUN

$RCAT +67%

Entry: $8.50
Now: $14.20
Held: 6 weeks

The 5-Gate System works.

sterlingsignals.substack.com
```

**100% Milestone:**
```
🏆 HALL OF FAME

$[TICKER] +100%

Entry: $X.XX
Now: $X.XX
Held: X weeks

The double.

sterlingsignals.substack.com
```

## C. No-Signal Week Framing

```
📊 THIS WEEK'S SCAN

1,817 stocks analyzed
→ 0 TEAL signals

The 5-Gate System found nothing meeting all criteria.

This is the system working, not failing.

Selectivity > Activity

sterlingsignals.substack.com
```

---

# END OF VERIFICATION PROMPT

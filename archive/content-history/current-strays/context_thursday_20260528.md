# THURSDAY CONTEXT PACKAGE: METHODOLOGY (Week A Rotation)

Rotation: Week A
Type: Methodology — how the system works, without revealing indicators
Topic: How 1,279 Stocks Became Three: The Anatomy of a Screening Session

---

## SCANNER STATS (from signals.json, April 13 scan)

| Stage | Count | Rejection Rate |
|-------|-------|----------------|
| Tickers loaded | 1,279 | — |
| Data downloaded | 1,269 | 0.8% failed download |
| Initial momentum confirmation | 18 | 98.6% rejected |
| Theme quality scoring (6 themes) | 6 | 66.7% of themes rejected |
| Forensic audit survivors | 3 | 50% rejected at final gate |

**Overall rejection rate:** 99.8% (1,279 → 3)

**Tier breakdown of 18 technical signals:**
- T1: 0, T2: 1, T3: 3, T4: 4, T5: 1, T6: 9
- Exit signals detected: 7

---

## THE THREE SURVIVORS

### CYRX (Conviction 8, T2)
- Theme: CGT cold chain logistics monopoly
- Theme score: 7.35 (INVESTABLE)
- System fit: STRONG
- Return driver: FUNDAMENTAL_RERATE
- Lifecycle sweet spot: TRUE

### KYTX (Conviction 7, T2)
- Theme: CAR-T autoimmune first-to-market
- Theme score: 8.35 (PRIME)
- System fit: STRONG
- Return driver: CATALYST_DRIVEN
- Lifecycle sweet spot: TRUE

### NAMS (Conviction 6, T3)
- Theme: Oral CETP inhibitor regulatory filing
- Theme score: 8.15 (PRIME)
- System fit: MODERATE
- Return driver: CATALYST_DRIVEN
- Lifecycle sweet spot: FALSE

---

## KEY REJECTION EXAMPLES (for the article's "what failed" section)

### DLO — Removed by CRO (Cross-Reference Override)
- Price: $13.12
- Theme: EM payment infrastructure
- Theme score: 7.00 (INVESTABLE)
- System fit: MODERATE
- Verdict: REMOVED_CRO
- Why: No structural force alignment. The theme lacked the multi-year government or regulatory catalyst that anchors a force. Revenue grew 47% to $1.09B. Forward P/E 14.9x vs 39.5x peer average. But General Atlantic selling, take-rate compressing 1.19% to 0.88%, dual-class voting 79.5% control.
- Teaching moment: Numbers can look right while structure is wrong. Force alignment is not optional.

### GHM — Watchlisted (not deployed)
- Theme: Navy submarine hardware manufacturing
- Theme score: 8.75 (PRIME)
- System fit: STRONG
- Verdict: WATCHLIST
- Why: Stock already tripled. 68x P/E vs 18-22x peer average. Single-segment concentration. The theme was PRIME but the entry timing was poor.
- Teaching moment: Theme quality is necessary but not sufficient. Entry price matters.

### GERN — Failed thematic scoring
- Theme: Telomerase inhibitor
- Theme score: 5.95 (below threshold)
- System fit: POOR
- Verdict: FAIL_THEMATIC
- Why: Theme quality too low despite biotech convergence in the scan.

### PENG — Failed thematic scoring
- Theme: AI memory CXL
- Theme score: 6.30
- System fit: MODERATE
- Verdict: FAIL_THEMATIC
- Why: AI infrastructure theme, but CXL memory is too early-stage with insufficient catalyst density.

---

## THEME HEATMAP (from signals.json themes array)

| Theme | Classification | Score | Deployed? |
|-------|---------------|-------|-----------|
| Navy submarine hardware | PRIME | 8.75 | No (watchlisted — valuation) |
| CAR-T autoimmune | PRIME | 8.35 | Yes (KYTX) |
| Oral CETP inhibitor | PRIME | 8.15 | Yes (NAMS) |
| CGT cold chain logistics | INVESTABLE | 7.35 | Yes (CYRX) |
| 800G optical interconnect | INVESTABLE | 7.40 | No (deferred) |
| EM cross-border payments | INVESTABLE | 7.00 | No (removed — CRO) |

---

## FUNNEL CONVERSION RATES (for the article)

- Technical gate: 18/1,279 = 1.4% pass rate
- Theme quality: 6/18 = 33.3% pass rate (by theme, not ticker)
- Forensic audit: 3/6 = 50.0% pass rate
- Overall: 3/1,279 = 0.23% pass rate

---

## BATCH ASSESSMENT CONTEXT

- Theme clustering: DETECTED — biotech convergence was strongest in session
- Wave alignment: 3 tickers ride funded structural forces from Prompt 2
- Sector concentration: 100% Healthcare/Biotech (3 distinct sub-themes)
- Sector concentration warning: TRUE
- Batch quality: STRONG

---

## WHAT THE ARTICLE SHOULD COVER

1. **The funnel in numbers.** Start with 1,279. End with 3. Show every stage.
2. **What the gates do** (without naming indicators). Describe in terms of outcomes: momentum inflection detection, institutional accumulation signals, trend confirmation. The system looks for structural reversals, not momentum continuations.
3. **Theme quality scoring.** How themes are classified (PRIME / INVESTABLE / SELECTIVE / AVOID). What makes a theme PRIME versus merely interesting.
4. **The forensic audit.** What it checks: capital structure, management stability, catalyst proximity, competitive positioning. The DLO rejection is the star example.
5. **The GHM watchlist.** Why a PRIME theme with STRONG fit was not deployed. Entry timing and valuation discipline.
6. **The outcome.** Three positions entered. Where they are now (CYRX +44%, KYTX -6%, NAMS -6%). The system made its bet. Time will score it.
7. **Connect to portfolio.** These three joined a portfolio that is now +88% total return with +43% alpha vs SPY. The screening discipline is what creates the edge.

---

## VOICE REMINDERS FOR THIS ARTICLE

- Never name HMA, MACD, RSI, Banker, UC, or any indicator
- Use: "momentum inflection," "trend reversal confirmed," "institutional accumulation signal," "five-stage filter chain," "forensic audit"
- The system is the authority. "Our screening system" not "I"
- Show the rejection as a feature, not a bug
- End with forward look: next scan is Friday, the cycle repeats
- No em dashes. Colons and periods.
- Specific numbers for every claim

---

## PROMPT TO USE

Open a new Claude.ai chat. Attach voice_rules.md. Paste this context package first, then paste Prompt 1 from the handbook Section 3 (Thursday: Education — 3 prompts: Research, Extended x2).

**Suggested title:** "How 1,279 Stocks Became Three: The Anatomy of a Screening Session"

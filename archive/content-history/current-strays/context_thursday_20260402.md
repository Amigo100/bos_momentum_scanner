# THURSDAY CONTEXT PACKAGE: FREE TOOL / RESOURCE

Rotation: Week C
Type: Free Tool or Resource (permanent lead magnet)
Topic: Balance Sheet Red Flag Checklist: 7 Capital Structure Tests Every Small-Cap Investor Should Run

---

## CONCEPT

A reusable framework that subscribers can apply to any small-cap stock before deploying capital. Built from 18 months of real scanner rejections. Each of the 7 tests comes with a real example from our screening data showing what the test caught.

This is a permanent reference piece. Free to read. Designed to be bookmarked.

---

## THE 7 TESTS (with real scanner data)

### Test 1: Share Count Growth Rate
What to check: Compare shares outstanding from the latest 10-Q to 4 quarters ago.
Threshold: >20% annual dilution is a red flag.

Real example from our scanner:
- DDD (3D printing, defence sector): 45% share dilution over two years. Revenue declining 12% YoY. Serial management turnover. Momentum signal was real; capital structure was not sustainable.
- Source: signal_history_rows.csv, scan date 2026-03-14, stage DD_FAIL.

### Test 2: Cash Runway vs Burn Rate
What to check: Unrestricted cash / quarterly operating cash burn.
Threshold: <4 quarters runway without a clear path to profitability or committed credit facility.

Real example from our scanner:
- SVCO (semiconductor EDA tools): $10M unrestricted cash vs $33.9M FY2025 operating cash burn. Only 3.5-8 months of runway. We sized this as T3 (smallest allocation) specifically because of this risk. ATM programme filed at depressed prices creates reflexive dilution spiral risk.
- Note: SVCO passed our screening on other merits (CEO track record, valuation gap, SIP revenue doubling). Cash runway shaped the sizing, not the decision. This is the distinction.

### Test 3: Insider Transaction Pattern
What to check: SEC Form 4 filings in the last 90 days. Cluster buying at lows is bullish. Cluster selling after price run-ups is bearish.
Threshold: >10% of float sold by insiders in 30 days is a red flag.

Real example from our scanner:
- TGB (copper producer): 5+ executives sold 800K+ shares in a 3-week window after the stock rallied 305% in 12 months. Combined with market cap exceeding our $2B threshold.
- Source: decisions.json no_go, stage gate.
- Positive counter-example: SVCO CEO/CFO/Chair bought $348K at the all-time low ($3.90-4.13). This is a confirmation signal, not a red flag.

### Test 4: Holding Company / Conglomerate Structure
What to check: Is the investment thesis about a subsidiary, not the parent? Does the parent extract value through management fees, serial equity raises, or intercompany loans?
Threshold: Any evidence of value extraction at the parent level.

Real example from our scanner:
- INV (data centre cooling): Subsidiary Accelsius has genuine technology (NeuCool platform, Johnson Controls $65M Series B). But INV the parent has serial dilution ($40M offering Jan 2026), activist 13D, governance tension. Smart money investing directly in Accelsius, not through INV. Stock down 61% from highs despite subsidiary tailwind.
- Source: decisions.json no_go, stage gate. Verdict: FAIL.

### Test 5: Revenue Concentration
What to check: What percentage of revenue comes from a single product, customer, or contract?
Threshold: >50% from one source creates binary risk.

Real example from our scanner:
- CPRX (rare disease pharma): 61% of revenue from FIRDAPSE, which faces active patent litigation in March 2026. If the patent trial goes against them, 61% of revenue is exposed to generic erosion. We watchlisted this despite a strong balance sheet ($709M cash, zero debt, 36% net margins) because the binary event dominates.
- Source: decisions.json no_go, stage gate.

### Test 6: ATM / Shelf Registration Activity
What to check: Has the company filed an ATM (at-the-market) offering or shelf registration in the last 6 months?
Threshold: Active ATM with shares being drawn at current prices = ongoing dilution headwind.

Real example from our scanner:
- SVCO filed a $15M ATM on March 13, 2026. This is a yellow flag, not a red flag: the CEO cluster-buy at ATL and the turnaround trajectory suggest the ATM is defensive (maintain cash runway) rather than predatory (extract value). Context matters.
- DDD comparison: serial equity raises with no line of sight to self-funding. That is the red flag pattern.

### Test 7: Debt-to-Enterprise-Value Ratio
What to check: Total debt / (market cap + total debt - cash).
Threshold: >50% for pre-profit companies. >70% for profitable companies.

Real example from our scanner:
- GOGO (business aviation connectivity): $909M debt on a company with uncertain return math. Our forensic stage rejected it. Return math failed the 50% upside threshold on a 12-month basis partially because the debt load limits equity upside.
- Source: signal_history_rows.csv, scan date 2026-03-06, stage gate, verdict SPEC_BUY downgraded to WATCHLIST.

---

## SUPPORTING DATA

### Scanner funnel statistics (for context in the post)
- Tickers loaded: 1,279
- Technical signals: 18 across 17 micro-themes
- Advanced to forensic stage: 5
- Deployed: 2
- Rejected or watchlisted: 16

### Portfolio positions that illustrate the framework
- SVCO ($5.98 entry, T3): Passed despite Test 2 flag because of Test 3 confirmation (insider cluster buy). Sized smallest.
- ACRS ($3.65 entry, T3): 96% dilution in <2 years (Test 1 flag). Passed on multi-shot pipeline optionality and institutional raise at current prices. Sized smallest.
- TMDX ($65.00 entry, T1): Clean on all 7 tests. Highest allocation tier. Now at $99.38 (+52.9%).

### Rejection examples for the post
From signal_history_rows.csv and decisions.json:
1. DDD: DD_FAIL. 45% dilution, -12% revenue, serial turnaround. (Test 1, Test 2)
2. INV: FAIL. Holding company value extraction. (Test 4)
3. TGB: WATCHLIST. Insider selling cluster, market cap exceeded. (Test 3)
4. CPRX: WATCHLIST. 61% revenue concentration, patent binary. (Test 5)
5. GOGO: WATCHLIST. $909M debt, return math failed. (Test 7)
6. SVCO: PASS (with flags). Cash runway concern shaped sizing. (Test 2, positive Test 3)

---

## CONTENT NOTES

- This is a FREE post (no paywall). Designed as a permanent lead magnet.
- Voice: data-first, direct. Each test must have a concrete threshold and a real example.
- Do NOT reveal indicator names or screening internals. Describe the forensic stage as "our capital structure analysis" or "our five-stage filter chain."
- The post should be immediately useful: a subscriber should be able to apply these 7 tests to any stock they are evaluating.
- End with forward-looking: "Next week's screening will apply these tests to a new batch. Subscribe to see the results."
- Include a summary table at the top: Test name | What to check | Red flag threshold.

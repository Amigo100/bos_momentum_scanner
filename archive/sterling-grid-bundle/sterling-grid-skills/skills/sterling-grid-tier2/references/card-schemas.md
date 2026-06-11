# Sterling Grid — Card Schemas (Tier 2, V9)

> Tier 2 is the deep-dive gate: one name in (a Tier-1.5 ADVANCE card), ADVANCE or DROP out. Two-layer
> card. Its ADVANCE card is the **input to Tier 3** (matches `sterling-grid-tier3`'s input). V9 has
> **no sizing, no bands, no watch bucket.**

---

## INPUT — the Tier-1.5 ADVANCE card
```
WORKING LAYER
TICKER — ADVANCE (Tier 1.5) · provisional Arch [V/G/N] · Theme + benchmark
Pin down for Tier 2: the one thing the gate call still needs to confirm
Exposure: confirmed real (Tier 1.5) · still early: yes · disqualifiers: clear

LINEAGE LAYER (inherited — read, don't re-derive)
· Macro / Theme / Mapping     (theme-level, from Tier 0 via Tier 1)
· Triage    T1 ADVANCE → T1.5 ADVANCE + the verify-question answered
```
**Optional:** the **Tier-0 theme map** (theme strength + off-list benchmarks) · current **holdings**
(route a held name out rather than re-gating it).

---

## OUTPUT — what Tier 2 emits

### (a) ADVANCE card — the Tier-3 input
```
WORKING LAYER
TICKER — ADVANCE · provisional type [multibagger / great trade] · Archetype [V/G/N]
Theme / benchmark: [theme] · best vehicle [benchmark or "this"] · proxy quality [strong/adequate/weak]
Path (rough):   [≥4x mechanism, one paragraph] — rough bull ~[N]x
Asymmetry:      rough bull ~[Nx] / base ~[±%] / bear ~[–%]; rough U/D ~[ratio]
Survival:       permanent-impairment ~[–%], driven by [factor]
Strongest bear: [1–2 lines]
Open questions for Tier 3: [what DD must resolve — incl. discriminators not yet verified]
Facts verified: [key numbers + sources];  unverified: [flags]

LINEAGE LAYER  — carry the FULL inherited `lineage` array forward; do NOT drop the inherited elements
· Macro / Theme / Mapping     (inherited — copied verbatim, NOT dropped)
· Triage                      (inherited)
· Gate    T2 ADVANCE + provisional type · three-judgment one-liners · strongest bear   ← append one element
```
**The output card's `lineage` = the input card's full array + the appended Gate element.** Tier 3
expects all four inherited elements (Macro · Theme · Mapping · Triage) present; dropping them is what
broke the 3c eight-line assertion in the 2026-06-06 run.

### (b) DROP log entry
```
TICKER — reason_code (spec §0: no-path / ruin / thin-setup / weak-proxy / disqualifier /
         move-exhausted / wrong-instrument) + reason, one line. → decisions.json
         (No watchlist — re-enters only via a later scan.)
```

### (c) Batch summary (for merge → Tier 2.5 / Tier 3)
- Counts: ADVANCE _n_ / DROP _n_.
- **Tier-3 deep-dive queue** (the ADVANCE tickers + provisional type).
- Theme notes for Tier 0 (strong themes whose on-list vehicles are weak proxies; any theme
  stronger/weaker than the map says).

---

## Logging
Every **DROP** appends a lightweight entry to `decisions.json` now (ticker, date, **stage=tier2**,
decision=DROP, **reason_code per spec §0**, reason). ADVANCE names get their full record at Tier 3
(the deep-dive verdict). There is no sizing or band to record — V9 is binary, decided at Tier 4.

## Handoff
ADVANCE cards → **Tier 2.5** (if a second pipeline ran) → **Tier 3** (deep dive). The ADVANCE card's
working layer + lineage is exactly what Tier 3a consumes.

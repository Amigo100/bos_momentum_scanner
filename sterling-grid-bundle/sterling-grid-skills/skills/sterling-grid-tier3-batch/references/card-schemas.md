# Sterling Grid — Output Schema (Tier 3 Batch orchestrator, V9)

> A deep-dive coordinator. Card shapes live in `sterling-grid-tier3a-research` (evidence pack) and
> `sterling-grid-tier3` (dossier / geometry / verdict + decision record). This file states the INPUT,
> the per-ticker branch handoff, and the merged OUTPUT. Binary verdicts; no sizing.

## INPUT
```
tickers:  $ARGUMENTS (space-separated survivors chosen at the deep-dive gate, ~3–6)
cards:    sterling-run/runs/<date>/tier2/<ticker>.md  (Tier-2 ADVANCE card + open questions + lineage)
```

## PER-TICKER BRANCH (isolated; run in parallel)
1. reads `sterling-grid-tier3a-research` → runs the evidence sweep (research mode) → evidence pack
2. reads `sterling-grid-tier3` → 3a interpretation (Evidence) → 3b geometry (Geometry) →
   3c verdict + memo + V9 decision record (Verdict)   [starts at 3a interpretation; pack already gathered]
3. writes dossier · verdict card · decision record → sterling-run/runs/<date>/tier3/<ticker>/

## OUTPUT (→ Tier 4)
```
verdicts: [ per name: decision (BUY|DO NOT BUY) · type · conviction · catalyst_window ·
            comprehensive memo (opens Macro→Theme→Mapping) · V9 decision record
            (scenarios · velocity · positioning · overshoot_anchor; NO size_pct/exit_regime/kill_criteria) ]
lineage:  Macro · Theme · Mapping · Triage · Gate · Evidence · Geometry · Verdict   (per name)
```
Each decision appended to `decisions.json` (calibration Part A).

## HANDOFF
Stops at the verdict cards. **Tier 4** (`sterling-grid-tier4`) runs next as a single session over the
whole set → BUY / DO NOT BUY (capital) + the Decision line, then the capital-gate checkpoint.

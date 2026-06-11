# Sterling Grid — Card Schemas (Tier 1, V9)

> Tier 1 runs on a **batch** of ≤10 tickers (handoff-card-spec §0); parallel batches **merge by
> concatenation**. Two-layer card: a working layer + the lineage. Its ADVANCE payload feeds
> **Tier 1.5**. V9 has **no sizing** — the only verbs are ADVANCE / DROP.

---

## INPUT — a batch of ≤10 signal-list tickers + the Tier-0 hunting brief

```
Batch (one row per name): TICKER (required) · sector/industry · last price · signal (type/strength)
```

**Tier-0 hunting brief (after the Shared Context)** — per live theme, carries the **three theme-level
lineage lines** a name inherits the moment it's mapped:
```
THEME — priority tier · the benchmark vehicle(s)
· Macro    regime state · posture · easing/inflection flag
· Theme    theme/sub-theme · surfaced-via · stage · recognition · demand mechanism · fuel mix ·
           floor level · priority tier
· Mapping  value-capture grade (Direct/Adjacent/Peripheral/R&D) · vehicle vs benchmark · proxy quality
           · the bull-shape
```
**Optional:** current **holdings** (flag a held name → route out, don't re-triage).

---

## OUTPUT — what Tier 1 emits (per batch)

### 1. Triage table
| Ticker | Bucket | Arch | Theme / Benchmark | 4x? | Fam |
|--------|--------|------|-------------------|-----|-----|
| IONQ   | ADVANCE| N    | Quantum compute   | YES | KNOWN |
| XYZ    | DROP   | —    | —                 | NO  | KNOWN |

Bucket: **ADVANCE / DROP / HELD** · Arch: provisional V/G/N (or `?`) · 4x?: YES/MAYBE/NO · Fam:
KNOWN/PARTIAL/UNKNOWN.

### 2. ADVANCE payload (→ Tier 1.5) — one block per name
```
TICKER — bull case in its own terms (1–2 lines): shape + inflection + why now
Arch / Theme: provisional V/G/N · [theme + benchmark, with the mapping-confidence tag]
Verify-first: the ONE thing Tier 1.5 must confirm on current data
              (real exposure · still pre-breakout · theme still early)
```
The lineage travels as the **canonical §2 array** (handoff-card-spec — copy whole, append one; never
a dict keyed by stage, which is what broke the 2026-06-07 length checks):
```json
"lineage": [
  {"stage": "Macro",   "line": "[inherited verbatim from the hunting brief]"},
  {"stage": "Theme",   "line": "[inherited verbatim]"},
  {"stage": "Mapping", "line": "[inherited verbatim, incl. proxy quality + mapping confidence]"},
  {"stage": "Triage",  "line": "T1 ADVANCE · verify-question: [the verify-first note]"}
]
```
*(NEW-CLUSTER name not yet on the top-down map: carry the cluster as the provisional theme; its
Macro/Theme/Mapping lines are provisional and flagged for Tier 0 to formalise via the §6 ledger.)*

### 3. DROP log
```
TICKER — one-line reason (calibration-checkable): a staleness-proof structural fact, or what the
         search actually showed. → decisions.json
```

### 4. Batch summary — for merge + Tier 0
- **Counts:** ADVANCE _n_ / DROP _n_ / HELD _n_.
- **ADVANCE payload** (tickers → Tier 1.5).
- **NEW-CLUSTER signals** (≥2 names converging on one mechanism → candidate theme for Tier 0).
- **Theme-map gaps** (live themes with no flagged vehicle this week; benchmarks still waited on).

## Merge rule (parallel batches)
Concatenate the triage tables and ADVANCE payloads; **union** the NEW-CLUSTER signals. Mechanical — do
not re-reason over all batches in one context.

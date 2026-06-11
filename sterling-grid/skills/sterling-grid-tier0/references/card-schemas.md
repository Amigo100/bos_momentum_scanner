# Sterling Grid — Card Schemas (Tier 0, V9)

> Tier 0 reads and writes the **carried-forward log** and ORIGINATES the three theme-level lineage
> lines (Macro · Theme · Mapping) every downstream name inherits. Four passes hand typed outputs to
> each other (0a/0b → 0c → 0d). The 0d hunting brief is **Tier 1's first input**. No sizing anywhere.

---

## INPUT — the carried-forward log + this week's inputs

```
CARRIED-FORWARD LOG (read, update, save for next week)
· theme_map.json     the scored theme map (one block per tracked theme — the 0c schema +
                     best vehicles/benchmarks + held/flagged-this-week)
· regime_log         0a's running macro read
· discovery_log      0b's running sweep (items tagged monitor / promoted / discarded)
· benchmark_set      off-list benchmarks we're waiting on (theme · name · what we're waiting for)

THIS WEEK
· signals_YYYY-WW.csv          the 30–60 technical signals (read by 0b and 0d)
· NEW-CLUSTER signals          accumulated from recent Tier-1 runs (bottom-up theme-birth feed → 0b)
· holdings / portfolio_state   to read concentration
· current macro + research     0a (macro data) · 0b (web, VC-funding, policy/capex pipeline)
```

---

## INTERNAL — pass-to-pass handoffs

- **0a → 0c, 0d:** the regime read — regime state · posture lean (RISK-ON/NEUTRAL/RISK-OFF) ·
  inflection flag · axis reads + Δ · **binding_axes (1–3)** · **regime_shift: none/minor/material**
  (material → 0c's full-map re-tag, theme-intelligence §8).
- **0b → 0c:** the candidate theme long-list — per candidate: working name · one-line why ·
  surfaced-via (cluster / top-down / VC-funding / policy-capex / bottleneck-migration) ·
  **precursors P1–P4 (dated, sourced)** · **stage_scurve guess (S0–S4)** · stage guess ·
  **cluster-lifecycle tags** (every open cluster re-tagged monitor/promoted/discarded).
- **0c → 0d:** the scored map — per theme: THEME (sub-theme granularity) · surfaced-via · Stage **+
  stage_scurve** · Recognition · **precursors n/4 · inflection_window** · Fuel mix · Floor level (1–5)
  · Regime-fit · Demand mechanism · **constraint_chain** (ordered steps, each
  `cleared|current|next|watch` + 1-line evidence) · scorecard read · Δ · Hunting priority
  (HUNT/HOLD/STAND-DOWN/AVOID) + tier (P1/P2/P3).

---

## OUTPUT — the hunting brief (→ Tier 1) + persisted log

### The hunting brief (Tier 1 reads this first)
```
REGIME (book-level context) — RISK-ON / NEUTRAL / RISK-OFF + easing-inflection flag (from 0a)
                              [theme timing only — never vetoes a flagged name, never a size]

HUNT THEMES (3–6, by priority tier) — one line why-now each. PER THEME, the three lineage lines a
name inherits the moment it's mapped:
  THEME [P1/P2/P3] · S-stage [S0–S4] · precursors n/4 (members) · est. window [e.g. 1–3Q + basis]
  · Macro    regime state · posture · easing/inflection flag                          ← 0a
  · Theme    theme/sub-theme · surfaced-via · stage · recognition · demand mechanism ·
             fuel mix · floor level · priority tier                                    ← 0c
  · Mapping  value-capture grade (Direct/Adjacent/Peripheral/R&D) · vehicle vs benchmark ·
             proxy quality (strong/adequate/weak) · the bull-shape                     ← 0d
  Best vehicles / benchmarks: [ TICKER(rung/proxy/confidence ⚑flagged), ... ]
             confidence: VERIFIED | PROBABLE | UNVERIFIED (theme-intelligence §7; only VERIFIED
             may fast-track — UNVERIFIED appears tagged, for Tier 1 to check)

ACTIONABLE BENCHMARK MATCHES — VERIFIED benchmarks that flagged this week → fast-track to Tier 2
BOTTLENECK WATCH — per active wave: current constraint → next candidate + 1-line evidence (§4)
NEW / EMERGING THEMES added this week
DOWNGRADED / STAND-DOWN / RETIRED themes
```

### Persisted artifacts (overwrite the carried log; new fields are ADDITIVE — never rename legacy keys)
- **theme_map.json** — the 0c schema per theme (now incl. `stage_scurve` · `precursors` ·
  `inflection_window` · `constraint_chain` · `false_matches`) + best vehicles/benchmarks (each with
  `mapping_confidence`) + held/flagged-this-week; meta notes `regime_retag: full @<date>` when §8 fired.
- **benchmark_set** — off-list benchmarks (theme · name · what we're waiting for · mapping_confidence).
- **regime_log** (0a — now incl. `binding_axes` + `regime_shift`) · **discovery_log** (0b — now incl.
  `cluster-candidate` records: mechanism · member_tickers · first_seen · weeks_tracked · corroborators
  · cluster_status) — carried forward.

---

## Lineage — Tier 0 originates the theme-level layer
```
· Macro     regime state · posture · easing/inflection flag                            ← 0a
· Theme     theme/sub-theme · surfaced-via · stage · recognition · demand mechanism ·
            fuel mix · floor level · priority tier                                     ← 0c
· Mapping   value-capture grade · vehicle vs benchmark · proxy quality · the bull-shape ← 0d
```
These three lines are **stored on the theme** and travel into the hunting brief. **A name inherits all
three verbatim the moment it is mapped** — at a benchmark here in 0d, or at Tier 1 for a newly-flagged
name — so the macro and theme reasoning reaches the Tier-3c verdict memo without any tier re-deriving it.

## Handoff
The hunting brief → **Tier 1** (shape triage reads it first, inherits the theme-level lineage).
Actionable benchmark matches → **fast-track to Tier 2**. The scored map + logs persist for next week.

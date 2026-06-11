# Sterling Grid — The Lineage Block (the report-handoff spine)

> This is the mechanism that carries reasoning intact from the macro read all the way to the
> published report, **without any tier re-deriving upstream work.** Every tier loads this, reads the
> lineage it received, appends exactly one compressed line for its stage, and passes the whole block
> forward. By Tier 3c the lineage *is* the comprehensive report; Tier 3d and the newsletter write
> from it. Companion to Shared Context §10.

## The card has two layers

1. **Working layer** — what the *next* tier needs to act on. Consumed and replaced each tier
   (schemas live in each tier's `references/card-schemas.md`): ticker · archetype · theme +
   benchmark · the three spine judgments · the decision (ADVANCE / DROP in the funnel; BUY / DO NOT
   BUY at the decision) · type (multibagger / great trade) · conviction (Extremely Bullish /
   Bullish) · expected path + target · evidence flags · open questions.
2. **Lineage layer** — accumulating context. **Read for grounding, append one line, never
   re-derive.** Each line is *compressed but sufficient* — rich enough to write a paragraph from, not
   the tier's full output.

## The lineage schema — ONE array, carried whole

**Represent the lineage as a single ordered `lineage` array, carried as one field on every working
card.** Each tier does exactly this: **copy the entire array you received → append exactly one element
(your stage's line) → write the WHOLE array onto your output card.** Never store the elements as
separate, individually-droppable fields; never truncate the inherited elements; never re-derive them.
The array only ever grows.

**Hard assertion at Tier 3c:** the array must contain all eight elements — Macro · Theme · Mapping ·
Triage · Gate · Evidence · Geometry · Verdict. If any inherited element is missing, the handoff broke
upstream: **stop and surface it; do not proceed and do not re-derive.**

```
lineage: [ ... ]   (ONE array; copy whole → append one → pass forward; never drop/truncate/re-derive)
             elements, in order:

THEME-LEVEL  (produced by Tier 0, stored on the theme; a name INHERITS these the moment it is
              mapped to the theme — at a benchmark in 0d, or at Tier 1 for a newly-flagged name)
· Macro      regime state · posture (which waves open) · easing/inflection flag          ← Tier 0·0a
· Theme      theme/sub-theme · surfaced-via · stage · recognition · demand mechanism ·
             fuel mix · floor level · priority tier                                       ← Tier 0·0c
· Mapping    value-capture grade (Direct/Adjacent/Peripheral/R&D) · vehicle vs benchmark ·
             proxy quality (strong/adequate/weak) · the bull-shape                        ← Tier 0·0d

NAME-LEVEL   (accumulate down the pipeline)
· Triage     T1 ADVANCE/DROP → T1.5 ADVANCE + the verify-question answered                ← Tier 1/1.5
· Gate       T2 ADVANCE + provisional type · the three-judgment one-liners · strongest bear ← Tier 2
· Consensus  source BOTH / THIS / OTHER + the reconciliation ruling (only if 2nd pipeline)  ← Tier 2.5
· Evidence   discriminator scorecard (4 signals: present/partial/absent) · survival +
             accounting reads (runway/dilution · KS-3 accounting-quality · Yartseva
             asset–EBITDA, where the name warrants) · disqualifier status ·
             comparable-winner anchor (peaks + time-to-peak) · theme-trajectory anchor
             (lifecycle stage · peer-set/moat · theme catalyst-window)                    ← Tier 3a/3a-T
· Geometry   floor / target (decoupled) · FOOTBALL FIELD (the 2–3 methods used → low/high) ·
             scenarios (bear/base/re-rate/overshoot) + probs · velocity (t-to-rerate, IRR,
             P(≥2x@6/12/18mo)) · catalyst expected-window · type                          ← Tier 3b
· Verdict    BUY / DO NOT BUY + type + conviction + expected path & target +
             catalyst-window (carried explicitly for Tier 4)                              ← Tier 3c
· Decision   BUY / DO NOT BUY (capital) + opportunity-vs-RKLB-2024 + reason               ← Tier 4
```

**The array grows, never shrinks** (worked): Tier 0→1 hands a name `lineage:[Macro, Theme, Mapping]`
→ Tier 1 appends Triage → `[…, Triage]` (4) → Tier 1.5 updates the Triage element **in place** → Tier 2
appends Gate (5) → [Tier 2.5 appends Consensus] → Tier 3a + 3a-T append Evidence → 3b appends Geometry → 3c
appends Verdict → **(8) — assert here** → Tier 4 appends Decision (9). **A tier whose output card has
fewer lineage elements than its input card has dropped inherited context — that is the exact break this
spec exists to prevent** (it is what failed at Tier 2→3 in the 2026-06-06 run: the gate card kept only
its own Gate line and dropped the inherited Macro/Theme/Mapping/Triage, so 3c could not assert the
eight-line block and the article re-derived the upstream framing by hand).

**MANDATORY runtime assertion — do not skip it, do not patch around it.** At every handoff the
orchestrator asserts `len(output.lineage) == len(input.lineage) + 1` (Tier 1.5 is the one exception: it
edits the Triage element in place, so equal length). If the array shrank, an agent dropped inherited
context — **fail loudly and fix the agent's output. Never stitch the array back together downstream at
persist time**: an external patch hides the break and will not survive a run where you don't happen to
catch it (this patched-externally pattern is exactly what recurred at Tier 2→3 in the 2026-06-06 runs).

## How the report is assembled

- **Tier 3c is the comprehensive report.** Its memo *opens with the lineage's upstream framing* —
  Macro (the regime it rides) → Theme (why it qualifies, stage, recognition) → Mapping (value-capture
  grade, vehicle vs benchmark) — then the name-level thesis (numbers, valuation + geometry, the bear
  and why we're paid, the call: type + conviction + expected path, how we'd be wrong). Because the
  upstream lines were *inherited and accumulated*, 3c renders Macro → Theme → Mapping → selection →
  deep-dive → verdict as one top-to-bottom report, not a name-level note.
- **Tier 3d (the published article)** is pure content generation from the *completed* work — the
  3a dossier, the 3b geometry, the 3c memo, and this lineage. It introduces **nothing new** and
  **adapts to whatever the analytical tiers produced** (the analytical tiers are authoritative; the
  article renders their output, it never demands extra analysis). Its scorecard section renders 3a's
  discriminator scorecard + survival/accounting reads; its valuation section renders 3b's
  methods-used floor/target + scenarios; the **structural force** is the Theme line; the
  **comparable-winner** and **type** come from the Evidence/Geometry lines.
- **The weekly newsletter** aggregates the week from the lineage + the decision log: structural
  forces = the Theme lines of the week's names; each new entry's thesis = its 3c memo / 3d article;
  the funnel = the Triage/Gate/Consensus lines + the DO-NOT-BUY log. **Prices come only from
  `portfolio.csv`** — the newsletter introduces no price not in that file.

## Sufficiency rules each tier must honour

- **Inherit, don't re-derive.** A name mapped to a theme copies that theme's Macro/Theme/Mapping
  lines verbatim. Tier 0·0d's hunting brief therefore **carries the three theme-level lineage lines
  per theme**, so Tier 1 can stamp them onto a newly-flagged name with no macro/theme work of its own.
- **Compressed but paragraph-sufficient.** If a downstream writer (3c/3d/newsletter) couldn't write a
  paragraph from your line, it's too thin — but it is never the tier's full output either.
- **Append-only.** Never edit or re-derive an upstream line; if you disagree, note it in your own
  line (e.g. Gate or Evidence), don't rewrite Theme.
- **`[UNVERIFIED]` travels.** An unverified upstream fact stays flagged down the chain until a tier
  with the budget confirms it (typically Tier 3a).
- **Content tiers adapt to analytical tiers — never the reverse.** 3d and the weekly newsletter
  render whatever 3a/3b/3c and Tier 4 actually produced. Where a legacy article/newsletter section
  outruns the analytical output (e.g. a 5-metric forensic scorecard or a 7-method football-field the
  deep dive didn't compute), trim or adapt the *content* section to the real output — do not bend an
  analytical tier to satisfy a publishing template. Build 3a/b/c first; expect to update 3d.

## Persistent state (the data layer this reads/writes)

- `decisions.json` — every BUY, DO NOT BUY, and technical SELL (the 3c + Tier 4 records).
- The **carried-forward log** — `theme_map.json` · benchmark set · regime log · discovery log —
  holds the theme-level lineage lines week to week (Tier 0 reads + updates it).
- `portfolio.csv` — current positions + prices; the **sole** price source for the newsletter.

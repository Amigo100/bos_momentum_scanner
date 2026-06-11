# Sterling Grid — Card Schemas (Tier 4, V9)

> Tier 4 is comparative: it consumes the **whole batch** of Tier-3c verdict cards (+ dossiers + the
> accumulated lineage), the held book, and the Tier-0 theme map, and emits the binding capital
> decision. No sizing anywhere. Tier 4 appends the final **Decision** lineage line.

---

## INPUT — the deep-dived batch (one card per name) + book + map

Per name, the **Tier-3c verdict card + dossier + lineage** (from `sterling-grid-tier3`):

```
WORKING LAYER (per name)
TICKER — BUY (3c) · type [multibagger / great trade] · [Extremely Bullish / Bullish] · [V/G/N]
Expected path: [target] over [horizon] driven by [catalyst + mechanism]
Catalyst window: [the ~near-term window + next dated proof point]   ← scored in dimension 3
Floor / target: [floor] (method) · [target] (method) — decoupled
Scenarios: bear/base/re-rate/overshoot levels + probs
Decisive bear: [refuted / real-but-priced / real-and-mispriced / unresolved-binary]
(3a discriminator scorecard + 3b geometry available behind the card if a claim needs checking)

LINEAGE LAYER (inherited — read to score the bar, do NOT re-derive)
· Macro / Theme / Mapping     → the theme-early + macro-tailwind read (dimensions 1)
· Evidence                    → which discriminators are present (dimension 2)
· Geometry                    → catalyst window + scenarios (dimensions 3–4)
· Verdict                     → type · conviction · expected path (carried, not re-judged)
```

Plus:
- **The held book** — `portfolio_state.json` / current positions + their themes (double-buy guard +
  inferior-expression overlap check).
- **The theme map (Tier 0)** — `theme_map.json`: confirm each candidate's theme is early / strong; read
  concentration across the book.

*(Names with a 3c **DO NOT BUY** don't reach Tier 4 — they were already logged at 3c.)*

---

## OUTPUT — what Tier 4 emits

### (a) Buy list (ranked)
```
TICKER — BUY · type [multibagger / great trade] · [Extremely Bullish / Bullish] · [V/G/N]
Opportunity read: theme [early + tailwind] · inflection [discriminators present] · catalyst [+ window]
                  · reward-vs-substance · risk — vs RKLB-2024: [stronger / comparable / weaker]
Why it clears the bar: [1–2 lines]
Entry: scanner's signal — one full, equal-weight position
Expected-path checkpoint: [next proof point — informational, NOT a sell trigger]
```

### (b) Do not buy
```
TICKER — reason_code (spec §0) + one line.  (Re-enters only via a later scan.)
  Prose→code legend:  late theme → theme-posture · no near-term catalyst / distant catalyst →
  distant-catalyst · lottery ticket → lottery-ticket · ruin → ruin · inferior expression →
  inferior-expression · unproven inflection → pre-inflection · outclassed → outclassed
```

### (c) Portfolio impact
- New full equal-weight positions added · **theme concentration** they create (flag heavy tilt) ·
  inferior-expression overlaps avoided. No slot or position cap (§5).

### (d) Decision log rows (→ `decisions.json`)
```json
{ "date": "YYYY-MM-DD", "week_id": "", "ticker": "",
  "stage": "tier4",
  "decision": "BUY|DO_NOT_BUY",
  "reason_code": "",
  "type": "multibagger|great_trade|null",
  "conviction": "Extremely Bullish|Bullish|null",
  "opportunity_vs_RKLB": "stronger|comparable|weaker|null",
  "catalyst_window": "",
  "concentration_flag": null,
  "reason": "" }
```
`reason_code` per the spec §0 enum (the (b) legend maps the prose); REQUIRED on DO_NOT_BUY, `null` on
BUY. `concentration_flag` carries the heavy-tilt tag on BUYs (informational, §5 — never a cap).
This is the **binding capital decision.** Where it diverges from the 3c verdict (a 3c BUY declined here
for diversification or timing), **this row governs**; the 3c record stays in the log as the per-name
analytical verdict, so calibration can see both.

### (e) Lineage — append the final line
```
· Decision   BUY / DO NOT BUY (capital) · opportunity-vs-RKLB-2024 · reason                ← Tier 4
```

---

## Handoff
- **BUYs** → execution at the scanner-timed entry (one full, equal-weight position each) → the held book.
- Each BUY's **dossier + full lineage** → **Tier 3d** (the deep-dive article).
- The week's **BUYs + DO-NOT-BUY log** → the **weekly newsletter**.
- **No watchlist** — DO-NOT-BUYs re-enter only via a later scan.

# Sterling Grid — Card Schemas (Tier 3, V9)

> Two-layer card (Shared Context §10; full spec in `lineage-block.md`): a **working layer** consumed
> and replaced each phase, and a **lineage layer** read-appended-never-re-derived. Tier 3 consumes the
> Tier-2 (or Tier-2.5) card and produces the binary verdict, the comprehensive memo, and the V9
> decision record. There is **no sizing** anywhere in V9.

---

## INPUT — the Tier-2 card (or the Tier-2.5 reconciled card)

A name only reaches Tier 3 if Tier 2 routed it **ADVANCE** (or Tier 2.5 ranked it into the DD queue).

```
WORKING LAYER
TICKER — ADVANCE · provisional type [multibagger / great trade] · Archetype [V/G/N]
Theme / benchmark: [theme] · best vehicle [benchmark or "this"] · proxy quality [strong/adequate/weak]
Path (rough):   [≥4x mechanism, one paragraph] — rough bull ~[N]x
Asymmetry:      rough bull ~[Nx] / base ~[±%] / bear ~[–%]; rough U/D ~[ratio]
Survival:       permanent-impairment ~[–%], driven by [factor]
Strongest bear: [1–2 lines]
Open questions for Tier 3: [what DD must resolve — incl. any discriminators T2 couldn't verify]
Facts verified: [key numbers + sources];  unverified: [flags]

LINEAGE LAYER (inherited — read for grounding, do NOT re-derive)
· Macro / Theme / Mapping   (theme-level, inherited from Tier 0)
· Triage / Gate [/ Consensus] (name-level so far)
```

---

## INTERNAL — 3a → 3b (the evidence dossier + the Theme/Space block)
3a + 3a-T emit; 3b reads. Stays inside the single Tier-3 invocation.

- **Re-validation:** clean / broken (+ detail).
- **Discriminator scorecard:** each of the four — present / partial / absent + evidence + source.
- **Disqualifier status:** all clear / fired (which).
- **≥4x drivers:** the verified current numbers behind the mechanism.
- **Survival picture:** balance sheet, runway, burn, debt maturities, dilution path — plus the
  accounting/solvency reads where the name warranted them (KS-3 accounting quality; Yartseva
  asset–EBITDA for a revenue-generating name).
- **Positioning & tension:** short interest % float · days-to-cover · borrow/utilisation · float size ·
  options skew/gamma (if available) · sentiment / attention-velocity — flagged as the re-rate amplifier.
- **Comparable-winner read:** 2–3 analogs at *their* pre-breakout + **peak multiples + time-to-peak** +
  the theme leaders' re-rate + the look-alike failure + what separates them.
- **Open questions:** each resolved or still-open.
- **Bear landscape:** strongest bears in best form, bear-type checklist swept.
- **Theme/Space Trajectory (3a-T):** peer-set & competitive position (live field · share trajectory) ·
  theme lifecycle & growth (S-curve stage + this-name placement: early/inflection/late) · capex/demand &
  segment TAM (the name's slice, not the global theme) · moat / value-capture durability (structural vs
  temporary · substitute risk) · theme tailwinds/catalysts/risks (incl. TD-1…5) · **the theme→price
  synthesis** (multiple-ceiling read · theme catalyst-window · thesis durability). Inherits Tier-0
  Theme/Mapping; enriches the **Evidence** line (no ninth lineage element).
- **Archetype:** confirmed/updated (V/G/N) + why.   **Unverified items:** flagged.

## INTERNAL — 3b → 3c (the geometry read)
3b emits; 3c reads.

- **Pre-mortem:** the 2–3 most likely causes of loss.
- **Downside floor** (method) and **upside path / target** (the **methods-used range** + the re-rate
  and overshoot tiers) — explicitly decoupled; the **overshoot tier is gated by 3a-T's multiple-ceiling
  read** (early/accelerating theme supports it, maturing/already-priced caps it).
- **What's priced in:** expectations the price embeds + the remaining room + the one-line steelman.
- **Scenarios:** bear / base / re-rate / overshoot levels + probabilities (overshoot anchored to the
  comparable peak); market-implied cross-check; probability-weighted return; U/D ratio.
- **Re-rating velocity:** time-to-re-rate · implied IRR · P(≥2x within 6/12/18 months) · the amplifiers.
- **Catalyst timing:** expected window vs the underwritten horizon and the funding clock; the next
  dated proof point (this is the **catalyst window Tier 4 reads**), folding in 3a-T's theme-level catalysts.
- **Path verdict:** multibagger / great trade / DO NOT BUY.
- **Survival:** permanent-impairment %, survives-to-realise (ruin → DO NOT BUY).
- **Bear classifications:** each bear + label; any unresolved-binary as a conviction strike / open risk.

---

## OUTPUT — what 3c returns

### (a) Verdict card (working layer → Tier 4)
```
TICKER — BUY  · type [multibagger / great trade] · [Extremely Bullish / Bullish] · [V/G/N]
Expected path: [target] over [horizon] driven by [catalyst + mechanism]
Catalyst window: [the ~near-term window + next dated proof point]   ← Tier 4 reads this
Floor / target: [floor] (method) · [target] (method) — decoupled
Decisive bear: [class]
        — or —
TICKER — DO NOT BUY · reason_code (spec §0: no-path / ruin; a re-validation break logs the code of
         WHAT broke — false-match / disqualifier / verify-failed) + one line
```

### (b) Investment memo (BUY; article-ready — the comprehensive report)
Opens with the lineage's upstream framing (Macro → Theme → Mapping), then the name-level thesis
(sentence · what it does · why now · numbers · valuation + geometry · the bear and why we're paid · the
call: type + conviction + expected path · how we'd be wrong). Renders Macro → Theme → Mapping →
selection → deep-dive → verdict. Seeds Tier 3d.

### (c) Decision record (→ `decisions.json`)
```json
{
  "ticker": "", "date": "YYYY-MM-DD", "week_id": "", "archetype": "V|G|N", "theme": "",
  "stage": "tier3",
  "decision": "BUY|DO_NOT_BUY",
  "reason_code": null,
  "type": "multibagger|great_trade|null",
  "conviction": "Extremely Bullish|Bullish|null",
  "entry_price": 0,
  "scenarios": {
    "bear":      {"price": 0, "prob": 0},
    "base":      {"price": 0, "prob": 0},
    "rerate":    {"price": 0, "prob": 0},
    "overshoot": {"price": 0, "prob": 0}
  },
  "target": 0,
  "expected_path": {"horizon": "", "driver": ""},
  "catalyst_window": "",
  "decisive_bear_class": "refuted|real-but-priced|real-and-mispriced|unresolved-binary",
  "discriminator_scorecard": {
    "backlog_converting": "present|partial|absent",
    "milestone_on_date":  "present|partial|absent",
    "firm_cash_contract": "present|partial|absent",
    "margin_cf_inflection":"present|partial|absent"
  },
  "rerating_velocity": {"time_to_rerate": "", "implied_irr": 0,
                        "p_2x_6mo": 0, "p_2x_12mo": 0, "p_2x_18mo": 0},
  "positioning": {"short_interest_pct_float": null, "days_to_cover": null,
                  "borrow_fee": null, "float_size": null, "sentiment_velocity": null},
  "overshoot_anchor": "comparable-winner peak multiple(s) the upside was anchored to",
  "open_unverified": ["", ""]
}
```
**No `size_pct`, no `exit_regime`, no `kill_criteria`** — V9 has no sizing and exits are the scanner's
technical rule (recorded separately as technical SELLs, not per-name here). Unsourced field → `null` /
`[UNVERIFIED]`, never filled from memory. **`reason_code` (spec §0) is REQUIRED on DO_NOT_BUY, `null`
on BUY.** Calibration Part A copies `stage` + `reason_code` onto the ledger row and maps
`entry_price` → `price_at_decision`.

### (d) Lineage — append, then pass forward
```
· Evidence   discriminator scorecard · survival + accounting reads · disqualifier status ·
             comparable-winner anchor (peaks + time-to-peak)                              ← 3a
· Geometry   floor / target · methods-used range · scenarios + probs · velocity ·
             catalyst expected-window · type                                             ← 3b
· Verdict    BUY / DO NOT BUY + type + conviction + expected path & target + catalyst window ← 3c
```

---

## Handoff
The verdict card + memo + record + full lineage go to **Tier 4** (the binding capital decision against
the opportunity bar). Tier 4's confirmed BUYs feed **Tier 3d** (the deep-dive article), which renders
this dossier + lineage as content — adapting to what 3a/3b produced, never demanding more.

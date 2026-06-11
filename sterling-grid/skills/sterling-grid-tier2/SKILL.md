---
name: sterling-grid-tier2
description: >-
  Sterling Grid Tier 2 (V9) — the DEEP-DIVE GATE on a single small-cap name (or two). Takes an ADVANCE
  name from Tier 1.5 and decides whether it earns one of the scarce Tier-3 deep-dive slots: ADVANCE or
  DROP. This is where recall hands off to precision. It applies the three-judgment spine — a credible
  path of either kind (≥4x multibagger / high-confidence protected 3–4x great trade) · asymmetry ·
  survival — on a light targeted web budget (~8–15 searches, discriminators first), NOT a full data
  pull (that's Tier 3), and tags each ADVANCE a provisional type. There is NO sizing, NO bands, NO
  watch/defer, NO caps — V9 is binary, and Tier 2 only sorts ADVANCE / DROP.
  INVOCATION: invoked deliberately — one name per run (two at most) — by the pipeline orchestrator or
  the operator; parallel across names. NOT a keyword-triggered skill. On EVERY invocation, re-read this
  file and its reference files from disk; never run it from memory.
disable-model-invocation: true
effort: high
allowed-tools: WebSearch WebFetch Read Write Bash
---

# Sterling Grid — Tier 2 (V9): Deep-Dive Gate

## How this skill is invoked

Explicitly-invoked, looked-up-each-time. **One name per invocation** (two at most — the gate deserves
focus), on a single Tier-1.5 ADVANCE card. Different names run in **parallel, each in its own context**.
On every run, re-read this file and `references/` fresh from disk. Don't run it from topic keywords.

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (V9 — §4 the spine, §5 the binary decision with **no
sizing**, §7 discriminators, §9 firewall) and **`references/lineage-block.md`** (you inherit the
theme-level + Triage lineage and **append** the Gate line). Load **`references/diagnostic-reference.md`**
only if a name needs depth (an archetype call, a disqualifier question). Card shapes are in
**`references/card-schemas.md`**.

## Operating rules for the whole pass

1. **This is the deep-dive gate — ADVANCE or DROP, nothing else.** Decide whether the name earns a
   *scarce deep-dive slot.* There is **no sizing, no band, no watch/defer, no caps** — V9 abolished all
   of that. The output is ADVANCE (with a provisional type) or DROP.
2. **Selective because slots are scarce — this is where recall hands off to precision.** Earlier tiers
   kept everything plausible; here you DROP names that, while not disqualified, don't merit the
   expensive deep dive — a thin path, a weak proxy, a setup that isn't a real shot. The two **automatic
   DROPs** are the §4/§9 hard kills (no credible path of either kind; ruin); beyond those, DROP the
   merely-marginal rather than passing it on.
3. **Provisional, not the full thesis.** Confirm what a light budget (~8–15 searches) reaches —
   **discriminators (§7) first**, plus a fast disqualifier scan — and **flag the rest as open questions
   for Tier 3.** Don't build the primary-source scorecard or a rigorous model here.
4. **Never penalise a name for being expensive or pre-profit** (§7 traps). If you catch yourself, undo
   it.
5. **Facts from current sources, never memory** (§9). Mark anything unconfirmed `[UNVERIFIED]`.
6. **Tag a provisional type on ADVANCE.** **multibagger** (a credible ≥4x shot) or **great trade** (a
   high-confidence, protected 3–4x). A label that frames the deep dive — *never a size* (there is none)
   and never a second gate.
7. **Inherit the lineage; append the Gate line.**

**Input:** a Tier-1.5 ADVANCE card (ticker + the one thing to pin down + inherited lineage), optionally
the Tier-0 theme map and holdings — see `card-schemas.md`.

---

## Step 0 — Footing check
ADVANCE names arrive **pre-verified** by Tier 1.5 (real exposure, still-early, no disqualifier) — don't
repeat that; a quick footing check confirms nothing broke since (a financing, a guidance cut, a
catalyst slip, the move already run). **Broke → DROP** with reason. **Clean → the spine.**

## The three-judgment spine
Use the **V/G/N lens** (§6) to decide which evidence matters; confirm the facts each judgment hinges on
with the light budget (current revenue/cash/share count, the specific catalyst + timing, rough TAM,
recent dilution) — **discriminators first.**

### Judgment 1 — A credible path, of either kind
Build the bull case to a *specific mechanism and rough magnitude*: *if [catalyst/inflection], [driver]
goes [A]→[B], implying ~[N]x.* Named mechanism anchored to real numbers, not vague upside.
- **Test against the discriminators (§7):** how many of the four does it *show* vs merely *assert*? A
  path resting on *converting* backlog, an *on-date* milestone, a *firm cash* contract, or a printed
  margin/cash inflection is real; one resting on reservations, an announced-only milestone, an MOU, or
  "approaching profitability" is a likely round-tripper. Note any obvious **revenue-quality flag** on a
  "shows" (one-shot revenue, a single customer, collapsing gross margin) for Tier 3's open questions —
  the full quality read is 3a's. Don't discount for expensive/pre-profit.
- If the best vehicle is an off-list **benchmark**, judge whether *this* on-list name is a good enough
  proxy — **graded per the `theme-intelligence.md` §7 rubric (revenue exposure · causal linkage ·
  confounds · stage-fit), not by feel** — a WEAK proxy for a strong theme is a **DROP** (reason code
  `weak-proxy`; the theme stays live in the Tier-0 map; wait for the better vehicle to flag), not a
  pass-through.
- **Output:** credible ≥4x? `YES` → provisional type **multibagger**. **No**, but a high-confidence,
  downside-protected 3–4x with a defined catalyst → provisional type **great trade** (the operational
  anchors are DNA §4: ~≥55–60% weight on the 3–4x · floor within ~25–30% · catalyst ≤~12mo — anchors,
  not a checklist gate). **Neither → DROP** (automatic). A merely *possible* 3–4x without high
  confidence *and* protection is a DROP, not a great trade.

### Judgment 2 — Asymmetry
Sketch bull / base / bear lightly (rough magnitudes + probabilities — geometry, not the rigorous Tier-3
model). Probability-weighted upside should clearly dominate downside. Weak asymmetry → **DROP** (doesn't
merit a deep-dive slot), not a hedged pass.

### Judgment 3 — Survival to realise it
Identify the realistic *permanent-impairment* downside (going concern, dilution death-spiral,
thesis-to-zero) — not a temporary drawdown the scanner's stop handles. *Pre-profit is not impairment —
judge on runway and the dilution path (§7 trap).* **Ruin → DROP** (automatic), judged on the **§9
operational triggers** (going-concern qualification · <4 quarters with no committed financing · an
uncovered ≤18mo debt wall · a toxic/ratcheting structure) — **fragile but funded passes** (financed
through the catalyst window is survival, not ruin).

## Honest bear
Before the gate call, state the strongest bear in its best form (1–2 lines). If it materially threatens
the path or survival, it informs the DROP.

---

## The gate decision — ADVANCE or DROP

- **ADVANCE → Tier 3 deep-dive queue.** A credible path of either kind, asymmetry that clears, survives
  to realise it, and a *real enough shot* to merit a scarce slot. Tag the **provisional type**
  (multibagger / great trade) and carry the **open questions** Tier 3 must resolve.
- **DROP → logged.** An automatic kill (no credible path of either kind; ruin), **or** a real-but-thin
  setup that doesn't earn the expensive deep dive (weak proxy, marginal asymmetry, a path that needs
  heroic assumptions). One-line reason. No watchlist — it re-enters only via a later scan.

## Not at this tier
No full three-statement model, no rigorous scenario probabilities, no valuation, no verdict, and **no
sizing of any kind** — those are Tier 3/4. Confirm only what the spine hinges on; a name that genuinely
can't be judged without deep work either ADVANCEs (if the shot is real) or DROPs (if it's marginal) —
don't grind it here.

---

## Output (schemas in `card-schemas.md`)
Per name: an **ADVANCE card** (the Tier-3 input) carrying the provisional type, the rough path,
asymmetry, survival, the strongest bear, the **open questions for Tier 3**, verified/unverified facts,
and the carried lineage; **or** a **DROP log entry** (one-line reason → `decisions.json`). **Append the
lineage `Gate` line:** `T2 ADVANCE` + provisional type · the three-judgment one-liners · strongest bear.

## Self-check
- Did I DROP anything that actually merits a deep dive — or ADVANCE a marginal name that doesn't earn a
  scarce slot? · Is every ADVANCE/DROP a *gate* judgment (worth the deep dive?), not a buy/size call? ·
  Did I tag a provisional type without implying a size (there is none)? · Did I test the path against
  the discriminators and avoid penalising expensive/pre-profit? · Is each survival call about
  *permanent impairment*, not a temporary drawdown? · Does each ADVANCE card carry the specific open
  questions for Tier 3, and is the Gate lineage line appended?

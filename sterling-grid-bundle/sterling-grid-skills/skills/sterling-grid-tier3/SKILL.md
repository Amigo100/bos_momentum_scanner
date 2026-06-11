---
name: sterling-grid-tier3
description: >-
  Sterling Grid Tier 3 (V9) — the deep due-diligence pass on a SINGLE small-cap name, run as four
  sequential sub-passes, each its own session with its own attention budget (3a Evidence &
  Interpretation → 3a-T The Space [theme & space trajectory] → 3b Valuation, Scenarios &
  Geometry → 3c Verdict & Memo). The final analytical stage before the Tier-4 buy decision, run only
  on a name Tier 2 (or, if a second pipeline ran, Tier 2.5) routed to the deep-dive queue. Output: a
  primary-source evidence dossier, a decoupled floor/target valuation with four scenarios and a
  velocity read, a BINARY verdict — BUY or DO NOT BUY — tagged type (multibagger / great trade),
  conviction (Extremely Bullish / Bullish), and an expected path + target, plus the lineage-rendered
  comprehensive memo and a decisions.json record. There is NO sizing, NO kill-criteria, and NO
  position plan — entry and exit both belong to the scanner.
  INVOCATION: invoked deliberately — once per surviving name — by the pipeline orchestrator or the
  operator running the Tier-3 stage; parallel across names, sequential 3a→3a-T→3b→3c within a name. NOT a
  keyword-triggered skill: do not auto-fire from a passing mention of "due diligence" or a ticker. On
  EVERY invocation, re-read this file and its reference files from disk; never run it from memory.
disable-model-invocation: true
effort: xhigh
allowed-tools: WebSearch WebFetch Read Write Bash
---

# Sterling Grid — Tier 3 (V9): Deep Due Diligence (3a → 3a-T → 3b → 3c)

## How this skill is invoked

Explicitly-invoked, looked-up-each-time. One name per invocation. Run **3a → 3a-T → 3b → 3c as four
sequential sessions, each with its own attention budget** (the console's design): **3a and 3a-T are both
deep-research with the full web budget** — 3a underwrites the *name*, 3a-T underwrites the *space the name
rides* (theme & space trajectory); 3b reasons over 3a's dossier **plus 3a-T's Theme/Space block**; 3c over
those + 3b's typed **geometry read** (the handoffs are defined in `references/card-schemas.md`). Do not
parallelise the sub-passes against each other (they build on one another), and do not collapse the
deep-research passes (3a, 3a-T) into the same context as 3b/3c — separate sessions keep each block's
attention clean. Different *names* are parallelised by the orchestrator. On every run, re-read this file
and `references/` fresh from disk. Do not run it from topic keywords.

## Setup, effort & cost
Run **3a and 3a-T as deep-research workflows** (`/sterling-grid-tier3a-research $TICKER`; prefix
`ultracode` or set `/effort ultracode`). Effort and transport are that skill's **STEP 0** job (the M3
fix made structural — `references/handoff-card-spec.md` §W): session effort set **and confirmed via
`/status`**, per-agent effort in every spawn, the ticker + Tier-2 card interpolated into the workflow
text (never `args`), flat schemas. Enable Dynamic workflows in `/config` (v2.1.154+); watch with
`/workflows`. The deep pull is many agents and uses meaningfully more tokens than a chat turn.

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (the V9 decision DNA — binary BUY / DO NOT BUY, no
sizing; the phases reason against §4 spine, §7 discriminators, §9 firewall) and
**`references/lineage-block.md`** (the report-handoff spine — you will append the Evidence, Geometry,
and Verdict lines). Load **`references/diagnostic-reference.md`** only when a name warrants depth
(an archetype call, the Yartseva or KS-3 reads, the valuation menu, the comparable-winner method).
Card shapes are in **`references/card-schemas.md`**.

## Operating rules for the whole pass

1. **Binary only — no sizing, no bands.** Tier 3 lands a BUY or a DO NOT BUY. A BUY is one full,
   equal-weight position; type (multibagger / great trade) and conviction (Extremely Bullish /
   Bullish) are *labels we publish and hold against, never a size and never a second gate.* Only two
   things hard-kill (DO NOT BUY): no credible path of either kind, or ruin. Everything else is a
   characterisation, not a cut.
2. **No new gates beyond the §9 firewall**, and **never penalise a name for being expensive or
   pre-profit** (§7 traps). If you catch yourself doing either, undo it.
3. **Entry and exit belong to the scanner.** Write **no** position plan — no scaling, adds, trims,
   thesis-based sell rules, or kill criteria. A broken thesis shows up as price; price is the
   scanner's job. The published path/target is the thesis and the scoreboard, **not** a sell trigger.
4. **Facts from current sources, never memory** (§9). Every present-day number, date, or "what it
   does now" is fetched in-session; anything unfetchable is `[UNVERIFIED]` and never load-bearing.
5. **Append the lineage, never re-derive it.** Each phase reads the inherited lineage and appends its
   one compressed line (Evidence / Geometry / Verdict), encoded as the canonical ordered
   `[{stage, line}]` array (`references/handoff-card-spec.md` §2 — never a dict, never a
   `lineage_complete` flag in place of the array). The upstream Macro / Theme / Mapping lines are
   inherited **byte-identical** — do not rewrite them. **Carry the full `lineage` array forward on
   every phase's card (copy the whole array, append one element); at 3c, ASSERT the array holds all
   eight elements — Macro · Theme · Mapping · Triage · Gate · Evidence · Geometry · Verdict. If any
   inherited element is missing, the handoff broke upstream: stop and surface it, do not proceed and
   do not re-derive the missing framing.** (`sterling_validate --check lineage` is the machine check.)
6. **Stop early on a hard-kill.** If re-validation breaks the thesis, a disqualifier fires, or ruin
   can't be ruled out — emit the DO NOT BUY record (with the lineage to that point) and stop; don't
   grind the remaining phases.

---

# PHASE 3a — Evidence & Interpretation

*Deep evidence pass, deep-research mode, full web budget. Re-validate, verify the discriminating
signals as a scorecard, run the §9 disqualifiers, pull the survival picture, assemble the bear
landscape, read the comparable winners. Evidence and interpretation — not the verdict; no new gates.*

> **Run the evidence pull as a deep-research workflow.** The gathering in steps 2–6 below is the same
> breadth-and-cross-check job as Tier 0's: invoke **`/sterling-grid-tier3a-research $TICKER`** (as a
> workflow — prefix `ultracode` or set `/effort ultracode`, or via `/deep-research`) to fan parallel
> agents across the evidence dimensions (contracts/backlog, survival/accounting, comparable-winner,
> bear types, positioning) and **adversarially cross-check bull vs bear before reporting**. This phase
> then interprets that evidence pack into the dossier and appends the `Evidence` lineage line; the
> interpretation, the §9 judgment, and 3b/3c remain here. Without workflows enabled, run the pull
> inline at the full web budget as below.

**Input:** the Tier-2 card (or the reconciled card from Tier 2.5) — ticker, archetype, theme +
benchmark + proxy quality, the ≥4x mechanism + rough bull multiple, rough asymmetry, survival
downside, strongest bear, provisional type, the inherited lineage (Macro / Theme / Mapping /
Triage / Gate [/ Consensus]), and the **open questions** Tier 2 couldn't verify on its light budget.

### 1 — Re-validate (quick gate-in)
Has anything *material* broken since Tier 2 — a financing, a guidance cut, a catalyst slip, a regime
shift? A few searches. Thesis killed → **DO NOT BUY** with reason, append lineage, **stop**.

### 2 — The discriminator scorecard (the heart of 3a)
For each of the four leading signals (§7), pull the **primary source** (10-Q/10-K/8-K/transcript/
regulatory calendar) and mark **present · partial · absent** with the evidence:
- **Backlog / RPO converting to revenue** — two consecutive quarters of YoY acceleration, book-to-bill
  >1.0, prior backlog landing as *current* revenue. *Reject reservations / pre-orders / LOI wording.*
- **Binary milestone hit on or ahead of its original date** — extract the *originally committed* date
  from older decks/transcripts + the regulatory calendar; score hit-vs-slip against *that* date.
- **Tier-1 anchor under a firm fixed-price cash contract** — read the material-agreement 8-K and
  classify the *structure*: firm PO with cash terms ✓ vs MOU / LOI / logo / warrant-rebate / asset-sale ✗.
- **Margin / cash-flow inflection** — ~300bps+ YoY gross-margin expansion for two quarters; operating
  cash flow turning positive *before* net income. The inflection is the signal; don't require a profit.

**Read:** how many present, and — critically — is any *absent where the thesis needs it*? That absence
is the round-tripper tell. Score by the **per-industry focus** (`diagnostic-reference.md` §2): a
structurally-N/A signal (backlog for a SaaS or pre-revenue name) scores `absent (N/A: <why>)` — an
N/A is never the round-tripper tell; only a *load-bearing* signal missing is.

**Quality modifier (a read, never a fifth gate):** when a signal scores *present*, note the **revenue
quality behind it** — gross-margin level/trend, customer concentration, one-shot vs recurring, cash
conversion. A 4/4 scorecard built on low-quality revenue scores **"present (low-quality)"** and feeds
conviction and 3b's scenario weights only; it never becomes a new gate.

### 3 — Disqualifier scan (§9)
Reservations-as-backlog · warrant-rebate or asset-sale as a "win" · >1 slipped milestone in 12 months
· >1 guidance cut in a fiscal year · a management-credibility event · runway <6 quarters with no
GAAP-positive quarter. **Any one fires → DO NOT BUY, stop here** (log it).

### 4 — Targeted deep evidence pull
Pull the rest the spine and the Tier-2 open questions hinge on — targeted, not a generic sweep:
- **The ≥4x drivers** — real current numbers behind the mechanism (revenue/units/backlog/margins/
  share count/TAM; catalyst status + timing).
- **The survival picture** — balance sheet, cash runway, burn, debt maturities, dilution/financing
  history and likelihood. *(Where the name warrants it, this is where the accounting/solvency reads
  live — the §9 KS-3 accounting-quality check and the diagnostic ref's Yartseva asset–EBITDA
  alignment for a revenue-generating name. Compute them when they bear on survival; don't bolt on a
  full forensic battery a name doesn't call for.)*
- **Positioning & tension** *(an amplifier on an already-qualified name, never an initiator — §7)* —
  short interest % float, days-to-cover, borrow / utilisation, **float size**, options skew / gamma
  where available, and a **sentiment / attention-velocity** read. Gauges how *violent and fast* a
  re-rate can be; feeds the bull magnitude and the velocity layer in 3b. Unfetchable → `[UNVERIFIED]`.
- **Each Tier-2 open question** — explicitly resolved or still-open.

Archetype emphasis — **N:** leading indicators, runway-to-milestone, dilution path. **G:** durability
of growth, unit economics, reinvestment runway, moat. **V:** normalised earnings/asset value, the
re-rating catalyst, downside-to-tangible-value.

### 5 — Bear landscape
Assemble the strongest documented bears *in their best form* (you classify them in 3b). Sweep the
**bear-type checklist** so the assembly is complete: **Fake-theme · Already-priced · Dilution machine
· Inferior expression · TAM fantasy · Customer concentration · Cyclical head-fake · No terminal
buyer.** Assemble each that bites in its strongest form, not a strawman.

### 6 — Comparable-winner read
Name **2–3 historical winners this name most resembles at *their* pre-breakout moment** — matched on
*specific shared features* (stage, driver, the inflection underway, coverage/ownership), not surface
similarity. **For each, record the multiple it actually reached at its run's *peak*** (P/S, EV/Rev or
EV/EBITDA — archetype-appropriate), the months to that peak, and what the theme's *leaders* re-rated
to — the anchor for 3b's overshoot scenario — **and the macro/liquidity regime that peak printed in**
(the §3 regime guard in `diagnostic-reference.md`: an easing-regime peak is the overshoot's ceiling,
not its base, when today's Macro line reads tighter). Then name **one look-alike that failed** at the
same stage and what was different. No credible winner-comparable (or the closest analog is the
failure) → the setup is more speculative than it looks; record that.

### Output — the evidence dossier (→ 3b) + lineage
Emit the dossier (schema in `card-schemas.md`): re-validation · discriminator scorecard · disqualifier
status · ≥4x drivers · survival picture (+ accounting/Yartseva reads where pulled) · positioning &
tension · comparable-winner read (peaks + time-to-peak) · open questions resolved/open · bear
landscape (types swept) · confirmed archetype · unverified items.
**Append the lineage `Evidence` line:** discriminator scorecard · survival + accounting reads ·
disqualifier status · comparable-winner anchor.

### 3a self-check
Primary sources for the discriminators? · Milestones scored against the *original* date, contract
*structure* classified? · Full §9 disqualifier scan run? · Full bear-type checklist swept (strongest
form, not strawman)? · A genuine winner-comparable **with peak multiple recorded**, or is the closest
analog the failure? · Positioning pulled as an *amplifier* only, unfetchables `[UNVERIFIED]`? · Every
number sourced or flagged? · Evidence lineage line appended?

---

# PHASE 3a-T — The Space (Theme & Space Trajectory)

*A distinct deep-research phase, full web budget, run after 3a and before 3b. Where 3a underwrites the
**name**, 3a-T underwrites the **space the name rides** — the live competitive field, the theme's lifecycle
and capex arc, the moat, the theme-level catalysts and risks — and synthesises how that space trajectory
drives **this stock's** price. Evidence and interpretation, not the verdict; no new gates. The two automatic
DO NOT BUYs (no credible path / ruin) belong to 3a/3b — 3a-T characterises, it does not cut.*

> **Run the theme pull as part of the deep-research workflow.** `/sterling-grid-tier3a-research $TICKER`
> carries a **theme/space-trajectory** dimension in its parallel fan-out; this phase interprets that pack
> into the Theme/Space Trajectory block. Without workflows, run the pull inline at the full web budget below.

**Input:** the inherited **Theme** and **Mapping** lineage lines from Tier 0 (theme/sub-theme · stage ·
recognition · demand mechanism · fuel mix · floor level · value-capture grade · proxy quality) **and** the
3a dossier. **Inherit these verbatim — do not re-derive the theme's existence, the macro, or the value-capture
grade.** 3a-T goes *deeper than Tier 0's hunting-level read, at the level of this specific name.* Reuse the
`diagnostic-reference.md` frameworks by name (T1–T7 theme cues, TD-1…5 theme-death triggers, the value-capture
grades, the comparable-winner method) — do not invent new ones.

Research five dimensions, each on current primary / industry sources:

### 1 — Peer-set & competitive position
The **direct competitors this name faces in its segment** of the theme — the *live* field, distinct from
3a's *historical* comparable-winners. Relative value-capture, who is gaining vs losing share, the share
trajectory, and which player the theme's economics most accrue to. Where does *this* name sit: leader,
fast-follower, or also-ran riding the wave?

### 2 — Theme lifecycle & growth (T1 · T7)
Where the theme sits on the S-curve and the hype cycle (**T1** lifecycle maturity), and whether theme
capital / coverage / mindshare is still **accelerating in** (**T7**). Then place *this name* within it:
entering early, riding the inflection, or late to a fading wave. Flag a **too-early** (mechanism real, no
inflection yet) or **already-priced** (cohort already re-rated) mismatch even where the theme itself is strong.

### 3 — Capex / demand & segment TAM (T2 · T3)
The demand mechanism's **$ size and the capex funding it** (**T3** capex / investment-cycle direction; **T2**
end-demand momentum), then **the name's addressable *segment*** — not the global theme TAM — and its
18–36-month growth runway. Is demand inflecting *for this name's product* now, or is the theme hot while this
segment is still early?

### 4 — Moat / value-capture durability
Can the name **hold its Tier-0 value-capture grade** (Direct / Adjacent / Peripheral / R&D) as the theme
matures and capital crowds in? Is the moat **structural** (scale, switching cost, IP, a real bottleneck) or
**temporary** (first-mover, pre-competitive positioning)? Name the substitute risk *within* the theme — a
different approach that serves the same demand.

### 5 — Theme tailwinds / catalysts / risks for this stock
The **theme-level catalysts** that would lift the whole space (policy, committed capex, a marquee adopter, a
regulatory unlock) and how each aligns with *this name's* clock. The downside via the **theme-death triggers
(TD-1…5)** — mechanism-class abandonment, regulatory disqualification, capital-flow reversal, a superior
liquid proxy saturating the trade, secondary-ticker crowding — mapped to whether each would break the thesis
*for this name*.

### The theme → price-trajectory synthesis (the payoff)
Tie the space read to *this stock's* price path, for 3b to consume:
- **Multiple ceiling.** An early, accelerating theme with runway supports the **overshoot** tier; a maturing
  / already-priced / crowding theme **caps** it. State which, and why — this gates 3b's overshoot.
- **Catalyst window.** Which theme-level catalysts widen or align with the name's own window (carried into
  3b's catalyst-timing and the Tier-4 read).
- **Thesis durability.** Whether the moat lets the name hold value-capture as the theme matures — the
  space-side input to 3b's survival / durability read.

### Output — the Theme/Space Trajectory block (→ 3b) + lineage
Emit the block (schema in `card-schemas.md`): peer-set & competitive position · theme lifecycle & growth
(stage + this-name placement) · capex/demand & segment TAM · moat / value-capture durability · theme
tailwinds/catalysts/risks · the theme→price synthesis (multiple-ceiling read · theme catalyst-window ·
durability). **Enrich the existing `Evidence` lineage line** with a `theme-trajectory anchor (lifecycle
stage · peer-set/moat · theme catalyst-window)`. 3a-T is a sub-phase of evidence, so it appends to the
**Evidence** element — **not a ninth lineage element.** The eight-element spine (Macro · Theme · Mapping ·
Triage · Gate · Evidence · Geometry · Verdict) is unchanged.

### 3a-T self-check
Theme + Mapping inherited verbatim, not re-derived? · Peer-set is the *live* competitive field, distinct from
3a's historical comparable-winners? · Lifecycle placed for *this name* (too-early / inflection / late), not
just the theme? · Segment TAM/capex sized to the name's product, not the global theme number? · Moat judged
*structural vs temporary* with the substitute risk named? · TD-1…5 swept as the theme downside? · The
theme→price synthesis states a multiple-ceiling read + catalyst-window + durability for 3b? · `Evidence` line
**enriched** (not a ninth element), eight-element spine intact?

---

# PHASE 3b — Valuation, Scenarios & Geometry

*Turn 3a's evidence into numbers and geometry — the rigorous spine plus the bear classification.
Mostly reasoning over the dossier; light web only for comparables/multiples. Same spine, no new gates;
only the two automatic DO NOT BUYs can DROP a name here.*

**Input:** the 3a evidence dossier **and the 3a-T Theme/Space Trajectory block** (this context).

### Pre-mortem (run first)
Assume it is 18 months on and the position **lost money**. Write the 2–3 most likely causes. If the
single most likely cause is a *ruin* you can't currently rule out → **DO NOT BUY**; otherwise it is a
strike against conviction the published thesis must name.

### J1 — The path, pinned to numbers
Translate the verified drivers into a path: *driver A → B over the horizon → implied multiple.* Two
**separate, decoupled** figures:
- a **conservative downside floor / entry fair value** — archetype-appropriate (asset / normalised-
  earnings for V; growth-DCF or reverse-DCF for G; dilution-adjusted milestone / TAM-capture for N).
  Feeds survival + asymmetry; **never** the target.
- an **evidence-gated upside path** in two explicit tiers, decoupled from the floor and anchored to the
  **multiples comparable winners actually reached** (from 3a) — Street highs are a *floor* on the bull,
  never a cap. **Re-rate** (multiple converges to where the theme's quality names trade *now*) and
  **overshoot** (multiple overshoots to the comparable-winner peak — the reflexive, fast-multibagger
  case). A high forward multiple is *never* a reason to clip the path. **Gate the overshoot on 3a-T's
  multiple-ceiling read:** an early, accelerating theme supports it; a maturing / already-priced / crowding
  theme caps it. Where 3a recorded a comparable's peak as printed in an easier regime, use the
  **regime-adjusted anchor** (diagnostic-reference §3) for the overshoot level — an anchor adjustment
  only, never a path clip.

Present the valuation as a **compact range from the 2–3 methods actually used** (method → low/high) —
this is what the published article renders; don't manufacture methods the analysis didn't use.

**What's already priced in.** Back out what the *current* price implies and judge the **remaining
room**: not *is it cheap*, but *how much optimism is already in the price, and is there still ≥4x
beyond it?* **Steelman the price** in one line. Strong steelman + ≥4x still visible → real edge; strong
steelman + ≥4x needs heroic inputs → down-weight.

Does a credible ≥4x survive? **Yes →** type **multibagger**. **No, but** a high-confidence, downside-
protected 3–4x with a defined catalyst → type **great trade** (the target is the published thesis, not
a sell trigger; the operational bar is DNA §4 — roughly ≥55–60% weight on the 3–4x with the
discriminators present, a floor within ~25–30%, a dated catalyst inside ~12 months — anchors for this
judgment, not a checklist gate). **Neither →** DO NOT BUY.

### J2 — Asymmetry (four scenarios)
Build **bear / base / re-rate / overshoot** with real price levels and honest probabilities. **Bear:**
thesis stalls / multiple compresses (relate to the permanent-impairment floor). **Base:** executes,
multiple barely moves. **Re-rate:** multiple converges to the theme's quality names now. **Overshoot:**
multiple overshoots to the comparable-winner *peak*. **Anchor the four probabilities on the
scenario-probability playbook (`diagnostic-reference.md` §11): start at the prior (bear 30 · base 40 ·
re-rate 20 · overshoot 10) and justify each shift in writing**, tied to the discriminator scorecard
(signals *present* earn re-rate/overshoot weight; *absent-where-needed* pushes the bear).
**Base-rate humility is the default — but release it** when all three co-occur: the floor sits *near*
the current price, the discriminators are *present*, and the theme is *early/rising* on the Tier-0
map → shift weight out of base into re-rate/overshoot. **Cross-check the market:** a market priced for
*failure* on a name whose discriminators are *present* is the edge to weight into, not a number to
converge toward. → probability-weighted return + U/D over the horizon (2–4yr; sooner for binary/hot-
theme).

### Catalyst-timing alignment
The path rests on a *named catalyst*. Check its **timing**, not its entry:
- **Does the catalyst land inside the underwritten horizon?** Pin its *expected window* from the
  regulatory calendar / guidance / milestone schedule. Beyond the window → widen the horizon or
  down-weight the bull.
- **Does the catalyst clock match the funding clock?** For an N / pre-profit name the catalyst must
  arrive *before* runway forces a bad-terms raise. Gap → strike against conviction (and if it rises to
  genuine ruin, DO NOT BUY).
- **Name the next dated proof point** — it anchors the expected-path timing in 3c **and is the catalyst
  window Tier 4 reads.** Fold in the **theme-level catalysts from 3a-T** that would lift the whole space, not
  only the name's own events.
A real-but-mis-clocked catalyst lowers conviction and widens the horizon; it is not a DROP.

### Re-rating velocity (the fast-double layer)
Underwrite *how fast*, not just *whether*: expected **time-to-re-rate**, implied **IRR** over that
window, and **P(≥2x within 6 / 12 / 18 months)**, using catalyst proximity, theme momentum (Tier-0),
and the 3a positioning read. A conviction / expected-path input, **never a gate**.

### J3 — Survival to realise it
State the realistic **permanent-impairment** downside (runway / dilution / debt / going-concern) — not
a temporary drawdown the scanner's stop handles. **Ruin → DO NOT BUY**, judged on the §9 operational
triggers (going-concern qualification · <4 quarters with no committed financing · an uncovered ≤18mo
debt wall · a toxic/ratcheting structure) — **fragile but funded is NOT ruin**: a pre-profit name
financed through its catalyst window passes. *(Pre-profit is not impairment.)*

### Bear classification
Classify each material bear from 3a: **refuted / real-but-priced / real-and-mispriced (our edge) /
unresolved-binary**. An unresolved-binary lowers conviction and is an open risk the thesis must name.

### Output — the geometry read (→ 3c) + lineage
Emit (schema in `card-schemas.md`): pre-mortem · decoupled floor + upside path (the methods-used
range) · what's priced in + steelman · four scenarios + probs (overshoot anchored to the comparable
peak) + prob-weighted return + U/D · re-rating velocity · catalyst expected-window + next proof point ·
path verdict (multibagger / great trade / DO NOT BUY) · survival (permanent-impairment %) · bear
classifications. **Append the lineage `Geometry` line:** floor / target · the methods-used range ·
scenarios + probs · velocity · catalyst expected-window · type.

### 3b self-check
Floor and target genuinely **decoupled**? · Penalised expensive/pre-profit anywhere (undo)? · Checked
what's *already priced in* so the ≥4x is room **beyond** it? · Catalyst lands inside the horizon and
before forced dilution (else conviction lowered + flagged), with the window carried for Tier 4? ·
Overshoot anchored to comparable-winner *actual* peaks, the two upside tiers not collapsed? ·
Probabilities anchored in the scorecard + base rate, humility **released** where floor-near-price +
discriminators-present + early-theme held? · Velocity estimated as a conviction input, not a gate? ·
Verdict is **type**, set by path + survival — not a size? · Geometry lineage line appended?

---

# PHASE 3c — Verdict & Memo

*Render the binary verdict and the thesis to publish. Thinking only — synthesise the 3a dossier and
the 3b geometry; no new web. **Introduce no new facts:** a missing fact is an open question, not
something to fill from memory. Conviction is a descriptor, never a size. Only the two automatic DO NOT
BUYs can DROP here.*

**Input:** the 3a dossier + the 3b geometry read (this context) + the accumulated lineage.

### 1 — Operator bias check
*What would make this a DO NOT BUY?* · *Where am I over-weighting confirming evidence?* · *Has any bear
3b called "refuted" actually been tested, or just dismissed?* Adjust if they bite.

### 2 — The verdict: BUY or DO NOT BUY
- **BUY** — a credible path survived 3a/3b and the name survives to realise it. Tag three ways:
  - **Type** — **multibagger** (open-ended ≥4x) or **great trade** (high-confidence, protected 3–4x).
    A label, not a size; both are full positions competing on asymmetry.
  - **Conviction** — **Extremely Bullish** or **Bullish**, set by counting the strikes: a load-bearing
    discriminator only partial/absent · the decisive bear is an unresolved binary · the catalyst sits
    12–18 months out · the floor sits materially below price · the pre-mortem's top cause is
    unresolved. **ZERO strikes → Extremely Bullish. ONE → Bullish. TWO OR MORE → re-examine the BUY
    itself before labelling** (the strikes are usually telling you the path or survival judgment is
    softer than written). A descriptor, never a size or a second gate.
  - **Expected path + target** — where it goes, over what horizon, on which driver: the re-rate and
    overshoot levels from 3b and the expected time-to-target from the velocity read, plus the
    **catalyst window**. The thesis we publish — **not** a sell trigger.
- **DO NOT BUY** — an automatic kill only (no credible path of either kind, ruin, or re-validation
  breakage). Logged with reason; re-enters only if a later scan re-flags it. No watchlist.

### 3 — Entry & exit (the scanner's, not ours)
Selection ends at the BUY. **No position plan** — no scaling, adds, trims, thesis-based sell rules, or
kill criteria. Entry = one full equal-weight position at the scanner's existing technical signal,
entered once. Exit = the scanner's technical rule, monitored weekly. The target is **not** an exit.

### 4 — Investment memo (BUY verdicts; article-ready, the comprehensive report)
A tight memo that **opens with the lineage's upstream framing** — the macro regime it rides, the theme
(why it qualifies, its stage and recognition), and how this name maps to and captures it (value-capture
grade, vehicle vs benchmark) — **then the name-level thesis:** thesis in a sentence · what it does ·
why now · **The Space** (a dedicated section rendering 3a-T: the live competitive field, the theme's
lifecycle & growth, capex/demand & segment TAM, the moat, the theme catalysts/risks, and how the space
drives *this stock's* price) · the numbers · valuation + geometry (floor and target, decoupled) · the bear
and why we're paid · the call (type, conviction, expected path: target + horizon + driver) · how we'd be
wrong.
Drawing the upstream context from the lineage makes this the **comprehensive top-to-bottom report —
Macro → Theme → Mapping → selection → deep-dive → verdict — not a name-level note.** It seeds Tier 3d.
**Write in the voice of the verdict:** an Extremely Bullish memo argues declaratively (the risks
weighed, then overruled in writing); a Bullish memo keeps its hedges visible. Never a hedged memo over
an Extremely Bullish call — the conviction label and the prose must agree.

### 5 — Decision record (→ `decisions.json`)
Emit the V9 record (full schema in `card-schemas.md`): ticker, date, **stage (tier3) + reason_code
(spec §0 — required on DO NOT BUY, null on BUY)**, archetype, theme, **decision
(BUY / DO NOT BUY), type, conviction**, entry price (the scanner's signal), the four scenario levels +
probabilities, expected path (target + horizon + driver), **catalyst window**, decisive-bear class,
discriminator-scorecard summary, the **re-rating-velocity** block, the **positioning** block, and the
**overshoot anchor**, plus open/unverified items. **No size, no exit/kill-criteria** (exits are the
scanner's). **Append the lineage `Verdict` line:** BUY / DO NOT BUY + type + conviction + expected path
& target + catalyst window.

### 3c self-check
Clean BUY / DO NOT BUY — DO NOT BUY only on an automatic kill, never for box-failing or for being
expensive/pre-profit? · Verdict is **type + conviction + expected path**, never a size or a hidden
score? · Exits left with the scanner — no sell rules, no kill criteria, no clipping the target? · Memo
opens with the lineage upstream framing (the comprehensive report), not just a name note? · Memo carries
a dedicated **The Space** section rendering 3a-T's theme→price read? · Record
carries the scorecard, the four scenario levels, the velocity block, the positioning block, the
overshoot anchor, and the catalyst window — and the Verdict lineage line is appended?

---

## What the skill returns to the orchestrator
For a **BUY**: the verdict card (BUY · type · conviction · expected path + target + catalyst window),
the comprehensive memo, the `decisions.json` record, and the fully-appended lineage. For **DO NOT
BUY**: the one-line reason, the record, and the lineage to that point. The orchestrator passes BUYs to
**Tier 4** (the binding capital decision); Tier 4's confirmed BUYs then feed **Tier 3d** (the article).

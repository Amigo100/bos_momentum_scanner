---
name: sterling-grid-tier0
description: >-
  Sterling Grid Tier 0 (V9) — the weekly theme & benchmark engine, run as FOUR passes off a
  carried-forward log: 0a Regime (the macro frame + which waves are opening) → 0b Discovery (widest-net
  surfacing of forming waves — recall) → 0c Qualification & Scoring (the eligibility and recognition
  gates, then the priority-tier scorecard — precision) → 0d Vehicle Mapping (value chain, benchmark
  vehicles, cross-reference this week's signals, write the hunting brief). It ORIGINATES the three
  theme-level lineage lines (Macro · Theme · Mapping) that every downstream name inherits, and outputs
  the scored theme map + the hunting brief Tier 1 reads first. Regime and score INFORM, never gate:
  they tilt which waves are open, never block a HUNT, never override the scanner, never change size
  (there is none). Deep research.
  INVOCATION: invoked deliberately, weekly, by the pipeline orchestrator. Each pass runs as its own
  session for its own attention budget (0a ∥ 0b can run in parallel; then 0c; then 0d), reading the
  carried log + the prior pass's output. NOT a keyword-triggered skill. On EVERY invocation, re-read
  this file and its reference files from disk; never run it from memory.
disable-model-invocation: true
effort: high
allowed-tools: WebSearch WebFetch Read Write Bash
---

# Sterling Grid — Tier 0 (V9): Theme & Benchmark Engine (0a → 0b → 0c → 0d)

## How this skill is invoked

Explicitly-invoked, looked-up-each-time, weekly. **Each of the four passes runs as its own session
with its own attention budget** (the 3a/b/c pattern — discovery wants to cast *wide*, scoring wants to
judge *hard*; one context starves one of them). The orchestrator runs **0a and 0b in parallel** (they
are independent), then **0c** (consumes 0b's long-list + 0a's regime + the carried map), then **0d**
(consumes 0c's scored map). Each pass reads the **carried-forward log** and the prior pass's typed
output, and appends its lineage line. All four run weekly off the log — **discovery is built into 0b
every week, so there is no separate monthly pass.** On every session, re-read this file and
`references/` fresh from disk. Don't run it from topic keywords.

## Research execution — 0a and 0b run as a deep-research workflow

0a (macro regime) and 0b (theme discovery) are the breadth-heavy research passes. Run them as a
**dynamic workflow / parallel research job**, not a single linear pass: invoke
**`/sterling-grid-tier0-research`** (trigger it as a workflow — prefix the call with `ultracode` or set
`/effort ultracode`, or feed its question to the bundled `/deep-research`). It fans search across the
three surfacing streams, cross-checks and votes on the sources, and returns the macro read + the
cross-checked candidate-theme universe. **This skill then runs 0c (scoring → the Theme lineage line)
and 0d (mapping → the Mapping lineage line) over that research pack** and emits the scored map + hunting
brief; 0a's macro read seeds the Macro lineage line. See `sterling-grid-tier0-research` for setup
(enable Dynamic workflows in `/config`; Claude Code v2.1.154+). Without workflows enabled, fall back to
running 0a/0b inline at `xhigh` effort.

**Transport (the M3 fix, structural):** the tier0-research workflow's **STEP 0 — TRANSPORT GUARD**
governs (rules in `references/handoff-card-spec.md` §W): session effort set **and confirmed via
`/status`** + per-agent effort in every spawn; the **carry digest interpolated into the workflow text
— never passed as `args`** (the 2026-06-08 cold-discovery failure); missing digest → STOP, cold only
when explicitly requested; flat StructuredOutput schemas only.

## Read first — load the DNA, the lineage spec, and the toolkit

Load **`references/shared-context-dna.md`** (V9 — §3 recall→precision, §7 the discriminating signals,
§8 themes top-down + bottom-up, §10 the lineage rule; the model is binary BUY / DO NOT BUY with **no
sizing**) and **`references/lineage-block.md`** (you **originate** the three theme-level lines — Macro
from 0a, Theme from 0c, Mapping from 0d — that names inherit). Load **`references/theme-intelligence.md`**
— the prospective wave method this tier runs: §1 S0–S4 staging · §2 P1–P4 precursors (+ the
RKLB/PLTR/Quantum anchors) · §3 lead-time priors · §4 bottleneck-migration · §5 recognition
progression · §6 NEW-CLUSTER lifecycle · §7 proxy + mapping-confidence rubrics · §8 regime-shift
re-rank. Load **`references/diagnostic-reference.md`** for the toolkit 0c/0d draw on (the T1–T7
theme-strength cues, the theme-death triggers, the value-capture grades, the six markers, entry-zone
labels) — aids, never gates. Card shapes are in **`references/card-schemas.md`**.

## Operating rules for the whole tier

1. **Recall in 0b, precision in 0c.** 0b surfaces wide and does **not** score or prune (0c cuts);
   breadth is near pure upside because nothing is funded until it clears 0c and the §7 name-evidence
   downstream. 0c runs the **gates first, then the score** — and **a high score never overrides a
   gate.**
2. **Regime and score INFORM, never gate.** Themes run in imperfect regimes; the regime tilts *which
   waves are opening* and the posture lean. It never blocks a HUNT, never overrides the screener, and
   **never changes size (there is none).** A theme downgrade *stops hunting new names* — it is **never
   a sell** (exits are the scanner's).
3. **Current data, never memory** (§9). Every regime read, funding flow, capex commitment, and theme
   state comes from current sources; Δ vs last week comes from the carried log.
4. **The carried-forward log is the state.** Read it (theme map · regime log · discovery log ·
   benchmark set), update it, and save it for next week. First run: bootstrap from scratch.
5. **Originate the theme-level lineage; never re-derive it downstream.** 0a writes Macro, 0c writes
   Theme, 0d writes Mapping — stored on each theme so a name inherits all three the moment it's mapped.

**Input:** the carried-forward log + this week's technical signal list (the 30–60 names) + accumulated
NEW-CLUSTER signals from recent Tier-1 runs + holdings + current macro/research — see `card-schemas.md`.

---

# PASS 0a — Regime  *(∥ 0b; sets the macro frame)*

**Input:** the carried **regime log** (last week) + current macro data (rates, inflation, real rates,
financial conditions / liquidity, credit spreads **and** availability, the small-cap funding /
refinancing environment).

**Method.** Read the small-cap-relevant axes from *current* data: growth direction, inflation
trajectory, **real** rates, financial conditions / liquidity, credit spreads and availability, the
funding environment for unprofitable small-caps. **Most important — watch the tightening→easing
inflection** (2y rolling over, real rates falling, spreads compressing, conditions loosening,
R2K-vs-NDX turning up): that turn is the leading *new-wave-window-opening* signal and the single
highest-value macro read for this book, because small-cap thematic waves ignite and sustain on it.

**Informs, never gates** — it tilts which waves are opening and the posture lean; it never blocks a
HUNT, never overrides the screener, never changes size.

**Output (→ regime log + the 0d brief; append the `Macro` lineage line):** one-line **regime state** ·
**posture lean** (RISK-ON / NEUTRAL / RISK-OFF) · **inflection flag** (is an easing turn underway) ·
the axis reads + **Δ vs last week** · **`binding_axes`** (the 1–3 reads that would change the posture
if crossed) · **`regime_shift: none / minor / material`** (theme-intelligence §8 — material := the
posture lean changed, the easing state changed, or a prior binding axis crossed; material triggers
0c's full-map re-tag).

---

# PASS 0b — Discovery  *(∥ 0a; widest net, recall-mode)*

**Recall-mode: surface, do not score or prune beyond obvious non-themes — 0c does the cutting.**

**Input:** the carried **theme map** + **discovery log** (last week's sweep) · **accumulated
NEW-CLUSTER signals** from recent Tier-1 runs (≥2 flagged names converging on one mechanism — the
bottom-up theme-birth feed) · **this week's signal list** (to read what the week's flow clusters
around) · **fresh research** — with **private/VC funding and the policy/capex pipeline as the leading
feeds**; public-market flow is *confirming* (a theme is being adopted), not a leading oracle.

**Method — three surfacing streams, cast wide:**
1. **Bottom-up.** Run the **§6 NEW-CLUSTER lifecycle** (theme-intelligence): birth a
   `cluster-candidate` at ≥2 flagged names on one mechanism (rolling 4 weeks); **explicitly re-tag
   every open cluster this pass** (monitor / promoted / discarded + reason — silent drops prohibited);
   promote on a 3rd name, a §3 corroborating indicator, or a member clearing Tier 2; discard only at
   6 dry weeks (rebirth free). A promoted cluster enters 0c as a candidate theme even if unnamed
   anywhere — this is how we catch a wave (Quantum-style) before any top-down scan makes it legible.
2. **Top-down.** Building waves not yet tracked, read at a *surfacing* level — narrative
   crystallization (a sell-side initiation cluster / a marquee endorsement / sentiment turning),
   policy/regulatory underwriting, hyperscaler/Tier-1 capex, the liquidity/duration regime (from 0a).
3. **Leading-indicator sweep — surface *before* legibility (theme-intelligence §2/§3/§4):** gather
   the **P1–P4 precursor evidence per candidate, dated and sourced** (P1 private/VC capital
   dislocation — the earliest read · P2 capability-milestone cadence compressing · P3 the first firm
   *paid* demand · P4 recognition still open), and run the **§4 bottleneck-migration method over
   *every* active wave's `constraint_chain`** (locate the binding constraint by its scarcity
   signature; when its relief is dated, the next constraint is the underpriced sub-theme — the market
   prices the current bottleneck and underprices the next).

**Output (→ 0c; update the discovery log):** a **candidate theme long-list** — per candidate: working
name · one-line why · **surfaced-via** (cluster / top-down / VC-funding / policy-capex /
bottleneck-migration) · rough stage guess. Tag each discovery-log item *monitor / promoted / discarded*
with a one-line reason so next week builds on it.

---

# PASS 0c — Qualification & Scoring  *(precision: the gates and the score)*

**Input:** 0b's candidate long-list (with surfaced-via tags) + the carried **scored theme map** + 0a's
regime read.

**Method.**

**1 — Carry forward + integrate.** Refresh tracked themes (stage, capex direction, flow/sentiment, the
weekly **Δ**); fold in 0b's candidates; downgrade themes drifting to mature/fading; retire dead ones.
A downgrade *stops hunting*, **never** triggers a sell. **If 0a flagged `regime_shift: material`,
perform the §8 full-map re-tag** (theme-intelligence): re-derive `regime_fit` for *every* tracked
theme — not only the Δ-touched ones — then re-tier the HUNT set, noting `regime_retag: full @<date>`
in the map meta. A re-tag moves tiers and hunting priority only — never a STAND-DOWN, never a sell.
Fold in any RED/AMBER escalations from last week's theme-health note (held themes whose TD triggers
fired) as refresh inputs here.

**2 — Eligibility gate · the real-theme discriminator.** A theme need not be official to be real, but
it must have a **genuine demand mechanism with rising capital behind it.** Narrative with no mechanism
and no capital → log as *monitor*. Set the **floor level (1–5)**; level 5 (flow + story, no mechanism)
is *monitor / context-only.* This is the line that lets us be early without chasing pure story.

**3 — Recognition gate · the recognition-closed line.** Once a theme's mispricing is fully recognised,
the ≥4x entry is gone even while fundamentals still accelerate → **hard STAND-DOWN** (no new names) —
the one place the system cuts on a *theme* rather than per-name.
- **CLOSED only on an *indiscriminate* cohort re-rate.** *Necessary:* dispersion has collapsed — the
  low-quality / story-only names running *with* the leaders. While the market still discriminates
  (leaders rewarded, also-rans not), it is **not** closed — keep hunting. *(Winners look "late" at
  every doubling; leader strength alone never triggers stand-down.)* Plus **≥2 confirmers:** coverage
  saturated · a dedicated ETF gathering assets · issuance into strength · retail / front-page saturation.
- **Sub-theme escape.** STAND-DOWN binds the theme *as mapped*; a genuinely early sub-theme at finer
  granularity (Sandisk-as-AI-memory) is a *new* theme entry, given a distinct mechanism and a cohort
  that hasn't re-rated.
- **Decoupled-leader escape.** A constituent decoupled on its *own* §7 floor — rewarded for
  *converting* backlog/RPO while no-fundamental names lag (IonQ-inside-frothy-quantum) — is judged on
  its own merits. *Guards:* genuinely decoupling on relative strength, and actually clears §7. Still
  moving *with* the basket → not decoupled.

**3.5 — Stage & inflection-window read** *(diagnostic inputs to the tier — never a gate)*. Per
surviving theme, from the research pack's evidence: assign **`stage_scurve` (S0–S4)** per
theme-intelligence §1 (S1-IGNITION = ≥2 of P1–P3 dated inside 12 months + P4 holds — the target zone:
build the value-chain map and benchmark set NOW); record **`precursors n/4`** with members (§2); derive
the **`inflection_window`** from the newest firing precursor + the §3 lead-time priors (e.g. "1–3Q,
basis P1 aged 2Q + P3 award Mar-2026"). These tilt the priority tier alongside regime-fit and are
monitored against, never optimised against.

**4 — Score** each surviving theme on the scorecard (below).

**5 — Tag + prioritise.** Tag fuel mix + regime-fit (from 0a). Set hunting priority — **HUNT / HOLD /
STAND-DOWN / AVOID** — and rank the HUNT themes into a **priority tier (P1 / P2 / P3)**. HOLD = *stop
hunting new names* (never a sell).

### The scorecard (diagnostic → a priority tier, never a verdict)
**Gates run first (steps 2–3); the score ranks the survivors. A high score never overrides a gate** —
a level-5 floor stays context-only, a closed-froth theme stays STAND-DOWN, regardless of score.

**Scored axes** — each **strong / building / weak** (backbone: explosive · early · inflecting · durable
· tech advancing): **Demand / floor strength** (mechanism real and *converting*; where on the floor
ladder) · **Growth magnitude** (size + slope of the TAM/demand curve) · **Inflection evidence**
(companies *actually* inflecting — revenue/backlog/margin turning; this axis stays the *realized* read
— the *prospective* read lives in step 3.5's precursors/stage/window) · **Durability / tech curve**
(fast cost-down / performance-up + multiple independent drivers, not a fad) · **Catalyst density**
(concrete, *dated* near-term catalysts) · **Capital momentum** (capital accelerating in,
private→public, **and** still early — not crowded) · **Vehicle quality** (clean small-cap pure-play /
picks-and-shovels available — feeds 0d).

**Classifying tags** (set handling, not summed): **Floor level (1–5)** — eligibility + the *evidence
bar the §7 name-work faces downstream* (weaker floor → the path must prove more at Tier 2/3; level 5 →
context-only) · **Fuel mix** — fundamental / narrative / flow dominant (flow-dominant + no floor →
context-only) · **Recognition** — open / closing / closed-froth (closed-froth → STAND-DOWN, with the
escapes) · **Regime-fit** — tailwind / neutral / headwind (from 0a; tilts the tier).

**Priority tier:** combine the scored axes into **P1 (lead) / P2 / P3** among HUNT themes — a rank as a
tier, never a false-precise total to optimise against.

**Output (→ 0d; persist as the scored map; append the `Theme` lineage line):** per theme — THEME
(sub-theme granularity) · surfaced-via · Stage **+ stage_scurve** · Recognition · **precursors n/4 +
inflection_window** · Fuel mix · Floor level · Regime-fit · Demand mechanism · **constraint_chain
(where the wave has one)** · the scorecard read · Δ this week · Hunting priority + tier.

---

# PASS 0d — Vehicle Mapping  *(value chain, benchmarks, the hunting brief)*

**Input:** 0c's scored, ranked map + the carried **benchmark set / watchlist** (off-list names we're
waiting on) + this week's signal list.

**Method.**
1. **Value-chain map** per theme — **Direct / Adjacent / Peripheral / R&D-stage**; carry the theme's
   `constraint_chain` and note where the bottleneck is migrating (favour the rung the S-stage implies:
   pure-plays in early-flow, picks-and-shovels in the capex phase — theme-intelligence §1/§4).
2. **Benchmark set + proxy quality + mapping confidence.** Keep the purest-play vehicles per theme,
   including **off-list benchmarks** we want but that haven't flagged technically. Grade proxy quality
   **per the theme-intelligence §7 rubric** (revenue exposure · causal linkage · confounds — the AXON
   and GXAI rules · stage-fit), not by feel. **Every NEW ticker→theme mapping gets one targeted
   identity check** ("what does this company do *now*, per its latest filing/IR") and a
   **mapping-confidence tag** (VERIFIED / PROBABLE / UNVERIFIED); a mapping that fails goes on the
   theme's `false_matches` list (ticker · why · date) and stays there.
3. **Cross-reference** the benchmark set against **this week's signal list** — **check `false_matches`
   first** (a listed false match is rejected in one line, never re-investigated). Any genuine match
   means a name we were waiting on has just become actionable → **fast-track to Tier 2 — VERIFIED
   mappings only** (an UNVERIFIED match still appears in the brief, tagged, for Tier 1 to check —
   recall is preserved; only the *fast-track* requires verification).
4. **Assemble the weekly hunting brief.**

**Output — the hunting brief Tier 1 reads first (append the `Mapping` lineage line per benchmark
vehicle):**
- **Regime read (book-level context)** — RISK-ON / NEUTRAL / RISK-OFF + any easing inflection turning
  (from 0a). Informs *theme timing*; **not** a market-timing switch — never vetoes a flagged name,
  never changes size.
- **HUNT themes (3–6), by priority tier** — the early/accelerating waves we're seeking names in, one
  line each on why-now **+ the step-3.5 tags (`S-stage · precursors n/4 · est. window`)**, **each
  carrying its three theme-level lineage lines (Macro / Theme / Mapping) so Tier 1 can stamp them onto
  a newly-flagged name.** Vehicles listed compact as `TICKER(rung/proxy/confidence ⚑flagged)`.
- **Actionable benchmark matches** — VERIFIED benchmarks that flagged this week → fast-track to Tier 2.
- **BOTTLENECK WATCH** — per active wave with a constraint chain: current constraint → next candidate
  + the one-line evidence (§4). The next constraint is next week's sub-theme birth to watch.
- **New / emerging themes added this week.**
- **Themes downgraded / moved to STAND-DOWN / retired.**

**Persist (next week's input):** the **theme map** (one block per tracked theme — the 0c schema +
**Best vehicles / benchmarks** + **Held / flagged this week**) · the **benchmark set** (off-list:
theme · name · what we're waiting for) · the **regime log** (0a) · the **discovery log** (0b).

---

## Self-check (the tier)
- 0a: read from current data, easing inflection flagged, `binding_axes` named and `regime_shift`
  graded; output is a *lean*, never a size or a screener override?
- 0b: cast wide across all three streams without pruning (0c cuts), every candidate's surfaced-via
  tagged + precursors dated/sourced, every open cluster explicitly re-tagged (§6 — no silent drops),
  every active wave's constraint chain swept (§4), the sweep logged?
- 0c: gates *before* score (eligibility → recognition); a material regime shift handled with the §8
  full-map re-tag; every theme carrying `stage_scurve` + `precursors n/4` + `inflection_window`
  (step 3.5 — diagnostic, never a gate); the score kept diagnostic (a tier that never overrides a
  gate); recognition-*closed* (indiscriminate re-rate → STAND-DOWN) separated from merely *strong*;
  the decoupled-leader and sub-theme escapes applied?
- 0d: proxy quality graded per the §7 rubric and every new mapping identity-checked + confidence-
  tagged; `false_matches` checked before the cross-reference and updated after; every actionable
  match VERIFIED; the BOTTLENECK WATCH present; the map focused (flagged / held / emerging /
  building), not encyclopedic?
- Did each pass append its lineage line (§10), and is the carried-forward log saved for next week?

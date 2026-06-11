# Sterling Grid — Orchestration (the V9 weekend run)

The pattern an orchestrator (a Claude Code driver, or a scheduled task) follows to run the V9
pipeline. It holds **no analysis logic** — that lives in the tier skills. Its job is **sequencing,
context isolation, merging, and carrying the lineage + the persistent log**.

## Three principles this encodes

**1. Looked up each time, not keyworded.** At each step the orchestrator names the skill explicitly
and instructs the worker to **read that skill's `SKILL.md` (and its `references/`) fresh from disk
before doing anything**. No step relies on a skill auto-triggering, or on a remembered version. The
files on disk are the single source of truth, re-read every run.

**2. Isolation per unit of work, merge by card.** Each pass (Tier 0's 0a–0d), each batch (Tier 1 /
1.5), and each name (Tier 2 / 3) runs in its **own isolated session** (a sub-agent), so attention and
the web budget are spent on that unit alone, never diluted across the week's ~100 names. Because every
tier emits a **fixed-format card** (see each skill's `card-schemas.md`), parallel runs **merge by
concatenation** — mechanical, not a reasoning step that re-reads everything in one bloated context.

**3. The lineage travels in every card.** Each session reads the inherited **lineage block**
(`shared/lineage-block.md`), appends its one compressed line, and passes it forward. Tier 0
*originates* the three theme-level lines (Macro / Theme / Mapping); a name inherits them when mapped;
the name-level lines accumulate. By Tier 3c the lineage **is** the comprehensive report, and Tier 3d +
the newsletter write from it. The orchestrator never lets a tier re-derive an upstream line.

> Why this matters for quality: a single long chat that runs all stages accumulates context and
> degrades the later, highest-value steps. Isolated per-unit sessions do the opposite — each gets full
> per-token attention over a short, relevant context, and the lineage carries the reasoning forward
> without re-derivation. The funnel concentrates the *expensive* web budget on the few survivors
> (Tier 0, Tier 3a), one unit at a time.

---

## The funnel

`~30–60 weekly signals → Tier 1 (~8–15 ADVANCE) → Tier 1.5 (batch-verify) → Tier 2 (deep-dive gate;
~3–6 ADVANCE) → Tier 2.5 (reconcile into one ranked queue — only if a 2nd pipeline ran) → Tier 3 (deep
dive on the final few) → Tier 4 (BUY / DO NOT BUY) → publish (3d → newsletter → notes).`
**No cap on how many BUYs result** — every name that clears the bar is a full, equal-weight buy.
Cheap-and-wide at the top, deep-and-narrow at the bottom. Sessions within a tier run in parallel.

## The weekend, in order

For each step: **(a)** explicitly load the named skill from disk; **(b)** run it in the stated
isolation; **(c)** collect its cards (with the appended lineage); **(d)** hand them to the next step.

### ① Tier 0 — theme & benchmark refresh  *(four passes; deep research)*
Load `sterling-grid-tier0/SKILL.md`. Run the four passes as **their own sessions for their own
attention budget**: **0a Regime ∥ 0b Discovery** (independent — run in parallel, as the
`sterling-grid-tier0-research` deep-research workflow: parallel cross-checked web fan-out; **build the
carry digest from `log/` and interpolate it into the workflow text per that skill's STEP 0 — never via
`args`** (the 2026-06-08 cold-discovery failure), and keep StructuredOutput schemas flat) → **0c
Qualification & Scoring** (incl. the §8 regime-shift re-tag and the stage/precursor/window read) →
**0d Vehicle Mapping** (the §7 proxy rubric + mapping-confidence tags + `false_matches` + the
BOTTLENECK WATCH). Inputs: the carried-forward log (theme map · regime log · discovery log ·
benchmark set) + this week's signal list + accumulated NEW-CLUSTER signals from last week's Tier 1 +
holdings. Output: the scored theme map + **the hunting brief** (carrying the three theme-level lineage
lines + S-stage/precursor tags per theme) + actionable benchmark matches. **0d's hunting brief feeds
Tier 1.** All four run weekly — the 0b leading-indicator sweep runs every week, so there is **no
separate monthly discovery pass**.

### ①b Theme health — the weekly TD sweep on held themes  *(1 cheap session; parallel with ②)*
Load `sterling-grid-theme-health/SKILL.md`. One bounded session over `portfolio.csv` + the fresh theme
map: TD-1…5 checked per held theme (≤2 searches each) → the GREEN/AMBER/RED health note +
`log/theme_health.jsonl`. **Informational only — never a sell** (exits are the scanner's); RED/AMBER
findings feed next week's 0c refresh.

### ② Tier 1 — shape triage  *(FAN-OUT: one isolated session per batch of ≤10 tickers, parallel)*
Load `sterling-grid-tier1/SKILL.md` (or invoke the whole ②–③ fan-out as the `sterling-grid-triage`
workflow, which runs these steps with manifests + validation built in). Split the week's signals into
batches of **≤10** (handoff-card-spec §0), writing `tier1/_batch_manifest.json` **before** spawning;
spawn **one isolated sub-agent per batch**, each handed its batch + the Tier-0 hunting brief. Each
emits a triage set — a verdict for EVERY manifest ticker: **ADVANCE / DROP / HELD** + the inherited
theme-level lineage (the §2 array) + NEW-CLUSTER signals. Validate counts
(`sterling_validate --check counts --json`) and auto-gapfill any `missing` in batches of ≤5 (two
rounds, then surface). **Merge by concatenation:** ADVANCE payloads → Tier 1.5 queue; DROP log →
`decisions.json`; NEW-CLUSTER signals → next week's Tier 0. *Never run all batches in one context.*

> Efficiency option: pre-tag the unambiguous ticker→theme assignments in **code** (a theme→sector/
> keyword map) and send only genuinely ambiguous names to the skill — cuts batches and rate-limit
> pressure, reserves attention for the real judgment calls.

### ③ Tier 1.5 — batch verify the ADVANCE pile  *(FAN-OUT: one session per batch of ≤8)*
Load `sterling-grid-tier1_5/SKILL.md`. Same fan-out at the **≤8** ceiling (manifest → validate →
auto-gapfill, exactly as ②). Each batch verifies on current data (3–6 searches/name; the fast
disqualifier subset) and sorts **ADVANCE / DROP** (no watchlist in V9). Merge: ADVANCE → Tier 2 queue;
DROP → `decisions.json`. Then run the **recall audit** (the triage skill's STEP 5): one reviewer agent
flags possible false-drops (R1–R6 — conceded great-trade, size-class error, trap-attribute drop,
theme-veto-on-name, unexposed fact, couldn't-tell-as-drop) for Checkpoint A. **Reinstatement-only — it
never re-litigates ADVANCEs.**

> **HUMAN CHECKPOINT A — the deep-dive gate.** Before the expensive per-name work, review the merged
> ADVANCE list **+ the possible-false-drop flags + the validator summary** (post Tier 2, below, is the
> binding cut, but a look here is cheap). What enters Tier 3 consumes the deep web budget. Approve /
> trim / reinstate, then continue.

### ④ Tier 2 — deep-dive gate  *(one isolated session per name; parallel across names)*
Load `sterling-grid-tier2/SKILL.md`. For each Tier-1.5 ADVANCE name, run an isolated sub-agent on its
card (+ theme map + holdings). Each emits **ADVANCE (+ provisional type: multibagger / great trade) /
DROP** + the appended Gate lineage line + open questions. Merge: ADVANCE cards → the **Tier-3 DD
queue**; DROP → `decisions.json`. *No sizing — the gate is ADVANCE/DROP only.*

### ⑤ Tier 2.5 — cross-pipeline reconciliation  *(1 session; ONLY if a second pipeline ran)*
**If a second selection pipeline ran**, load `sterling-grid-tier2_5/SKILL.md` and hand it both
pipelines' DD-progressed + dropped lists (the companion-spec blocks). It debates divergences into **one
ranked DD queue** (firewall-first ruling) + a divergence log. **If only one pipeline ran, skip this
step** — the Tier-2 queue goes straight to Tier 3. *(When to run a second pipeline at all: the trigger
policy in the tier2_5 skill — default NO.)*

### ⑥ Tier 3 — deep DD  *(parallel ACROSS names; 3a→3a-T→3b→3c as their own sessions WITHIN each name)*
Load `sterling-grid-tier3/SKILL.md`. For **one** name, run **3a → 3a-T → 3b → 3c as four sequential
sessions, each with its own attention budget** (3a and 3a-T are both deep-research / full web — 3a
underwrites the *name* via `sterling-grid-tier3a-research`, and 3a-T "The Space" underwrites the
*theme/space trajectory* it rides, enriching the Evidence line with no ninth element; 3b and 3c reason
over the prior sessions' typed output — the dossier + the Theme/Space block, then the geometry read).
For **two or more** names, invoke **`sterling-grid-tier3-batch <TICKERS>`** — the parallel-branch
workflow that runs the same single-sourced logic, one isolated branch per ticker, validating each
branch's lineage on persist. Different names run in parallel. Each name emits: the binary verdict card
(BUY / DO NOT BUY + type + conviction + expected path + catalyst window), the lineage-rendered
**comprehensive memo** (carrying a dedicated **The Space** section), and the `decisions.json` record.
*Exits are the scanner's — the skill writes no position plan.*

### ⑦ Tier 4 — the buy decision  *(1 isolated session; thinking + light web)*
Load `sterling-grid-tier4/SKILL.md`. Hand it the **whole deep-dived batch** (each 3c dossier + lineage)
+ the held book + the Tier-0 map. It decides comparatively against the opportunity bar (RKLB-early-2024):
**BUY / DO NOT BUY**, every BUY a full equal-weight position, diversification enforced at selection. It
appends the Decision lineage line and emits the buy list + DO-NOT-BUY log + portfolio impact + decision
rows.

> **HUMAN CHECKPOINT B — the capital gate.** Review the Tier-4 buy list before capital and before
> publishing. This is the consequential decision; keep it with you.

### ⑧ Publish the buys  *(writing; no new research)*
For **each confirmed BUY**, load `sterling-grid-tier3d/SKILL.md` and write its deep-dive article from
the 3a/3b/3c work + lineage. Then **once for the week**, load `sterling-grid-newsletter/SKILL.md`
(prices from `portfolio.csv` only) to aggregate everything — buys, technical sells, rejections, the
structural forces, the portfolio — and load `sterling-grid-notes/SKILL.md` to spin the notes out of
that newsletter. *(Run `python3 -m scripts.sterling_price_refresh` BEFORE the newsletter — it
rewrites only the Current/P&L% columns of `portfolio.csv`; fetch failures keep old values.)*

### ⑨ Close out — calibration Part A, then Part C (the weekly close)
Load `sterling-grid-calibration/SKILL.md`. **Part A:** append every decision (buys *and* rejects, plus
any technical SELL) to `decisions.json` with the forward-snapshot block — the sole ledger. **Part C
(runs last):** `python -m scripts.sterling_weekly_close <date>` builds the operator report +
`theme_research_history.csv` + `ticker_journey_history.csv`, writes new buys / DD'd sells into
`portfolio.csv`, **and mirrors the run into the two findability views** — `research/<TICKER>/`
(per-name artifacts + status index across runs) and `weeks/<YYYY-WNN>/` (newsletter · notes ·
deep-dives · the week's decisions.csv + manifest) — idempotently. **Save the carried-forward log** —
theme map · benchmark set · regime log · discovery log — for next week. Each week, also check held
names for the scanner's **technical exit** and sell in full when it flags.

**Cadence:** ①→⑨ weekly (including Tier 0's full four-pass cycle; no separate monthly pass) ·
Calibration **K.1 quarterly** on the matured log (load `sterling-grid-calibration/SKILL.md`); change
thresholds only through it, one at a time. In the first 2–3 quarters there isn't enough forward history
to tune — bias to recall and keep logging cleanly.

---

## The persistent state (the data layer)

The chain passes files, not chat memory:
- **The carried-forward log** (Tier 0 reads + rewrites it weekly): `theme_map.json` · `benchmark_set`
  · `regime_log` · `discovery_log`. Holds the theme-level lineage lines week to week.
- **`decisions.json`** — every BUY, DO NOT BUY, technical SELL, and DROP (the 3c + Tier-4 records, and
  the lightweight tier DROPs). The calibration substrate.
- **`portfolio.csv`** — current positions + prices; the **sole** price source for the newsletter. A
  price-refresh step (`python3 -m scripts.sterling_price_refresh`) must write it before step ⑧.

---

## Configuration that protects quality (set per step)

The real levers — not "is it a skill":
- **Model + extended thinking.** Run the high-judgment tiers — **Tier 2, Tier 3, Tier 4** — and the
  reconciliation (**Tier 2.5**) on a strong model with extended thinking **on**. Don't let the
  orchestrator silently downgrade them for speed/cost.
- **Effort reaches the workers (the M3 fix, now STEP 0 in every workflow skill).** A workflow's
  spawned sub-agents inherit the *session* effort, NOT a skill's frontmatter `effort` — so **set
  `/effort xhigh`** for the deep tiers, **confirm via `/status`**, and set per-agent effort in every
  spawn, else xhigh applies only to the orchestration context and the analysis runs shallow. This was
  the repeated Critical finding from the 2026-06-06 run.
- **Workflow transport (`shared/handoff-card-spec.md` §W).** Inputs and continuity are interpolated
  into the workflow script text — never passed as `args` (they can arrive undefined: the 2026-06-08
  cold-discovery failure); StructuredOutput schemas stay flat; `sterling_validate` runs at every merge.
- **Research depth.** **Tier 0** (esp. 0b/0c) and **Tier 3a** are deep-research / heavy-web; the skills
  specify the depth ("primary sources", "the leading-indicator sweep", "8–15 searches"). Make sure the
  worker actually has web access and isn't capped below what the skill asks. An under-searched 3a is
  the real quality risk.
- **Deterministic facts.** Keep the screener and any data pulls (prices, share counts, filings,
  `portfolio.csv`) as **code** feeding the skills, so the facts are guaranteed regardless of an agent's
  choices. The LLM reasons; the numbers come from sources.
- **Pacing vs rate limits.** Many isolated sessions each searching can hit usage limits in a window.
  That's a throughput constraint, not a per-name quality one — pace the fan-out (cap concurrent
  sub-agents) rather than cramming work into one context to "save" calls.

---

## Skill inventory (build status)

| Tier | Skill dir | Status (V9) |
|------|-----------|-------------|
| 0 (0a–0d) | `sterling-grid-tier0`     | **V9 ✓** (4 passes; originates the theme-level lineage) |
| 0-R  | `sterling-grid-tier0-research` | **V9 ✓** (0a/0b deep-research workflow; carry digest interpolated, precursor evidence) |
| 0-H  | `sterling-grid-theme-health` | **V9 ✓** (weekly TD-1…5 sweep on held themes; informational, never a sell) |
| 1+1.5| `sterling-grid-triage`    | **V9 ✓** (fan-out orchestrator: manifests · auto-gapfill · recall audit R1–R6) |
| 1    | `sterling-grid-tier1`     | **V9 ✓** (ADVANCE/DROP; inherits + appends lineage; batches ≤10) |
| 1.5  | `sterling-grid-tier1_5`   | **V9 ✓** (ADVANCE/DROP; no watchlist; batches ≤8; 3–6-search budget) |
| 2    | `sterling-grid-tier2`     | **V9 ✓** (deep-dive gate ADVANCE/DROP + provisional type; no sizing) |
| 2.5  | `sterling-grid-tier2_5`   | **V9 ✓** (cross-pipeline reconciliation; firewall-first; explicit trigger policy) |
| 3    | `sterling-grid-tier3`     | **V9 ✓** (3a→3a-T→3b→3c as sessions; 3a-T "The Space"; binary; lineage appended) |
| 3a-R | `sterling-grid-tier3a-research` | **V9 ✓** (per-name evidence-sweep workflow; adversarial cross-check; feeds 3a/3a-T) |
| 3-B  | `sterling-grid-tier3-batch` | **V9 ✓** (multi-name deep-dive orchestrator; one isolated branch per ticker) |
| 4    | `sterling-grid-tier4`     | **V9 ✓** (opportunity-bar buy decision; concentration lens) |
| 3d   | `sterling-grid-tier3d`    | **V9 ✓** (article; renders 3a scorecard + 3b methods-used valuation) |
| 5a   | `sterling-grid-newsletter`| **V9 ✓** (The Weekly Screening; prices from `portfolio.csv` only) |
| 5b   | `sterling-grid-notes`     | **V9 ✓** (21+3 notes, 7 categories; complement-card rule) |
| —    | `sterling-grid-calibration` | **V9 ✓** (Part A log + quarterly K.1; tail-catching + theme calibration) |

All tier skills share the canonical `shared/shared-context-dna.md` (V9), `lineage-block.md`,
`diagnostic-reference.md`, `handoff-card-spec.md` (envelope · constants · lineage encoding · workflow
transport), and `theme-intelligence.md` (staging · precursors · bottleneck-migration · proxy rubric)
— propagated by `sh sterling-grid/install.sh` (which also installs the skills from the canonical
`sterling-grid/skills/` source into the `.claude/skills/` runtime) — plus their own card schemas.
The deterministic checks live in
`scripts/sterling_validate.py` (lineage · counts · decisions · layout).

---
name: sterling-grid-tier0-research
description: >-
  Sterling Grid Tier 0 RESEARCH (V9) — the deep, parallel, cross-checked research that feeds Tier 0's
  macro regime (0a) and theme discovery (0b). Run as a DYNAMIC WORKFLOW (orchestrated subagents), not a
  single linear pass: it fans web search across the three surfacing streams, fetches and cross-checks
  primary sources, votes on each candidate, and returns the macro read plus a cross-checked
  candidate-theme universe with citations. This is GATHERING + CROSS-CHECK only — the Tier-0 skill's 0c
  (scoring) and 0d (mapping) turn the pack into the scored map and hunting brief. Save the run as a
  reusable command for the weekly cadence.
  INVOCATION: invoked deliberately, weekly, by the operator or the Tier-0 orchestrator. Trigger it as a
  workflow (prefix the call with `ultracode`, or `/effort ultracode`, or feed the question to the
  bundled `/deep-research`). NOT keyword-triggered. On EVERY invocation, re-read this file and its
  references from disk; never run it from memory.
disable-model-invocation: true
effort: xhigh
allowed-tools: WebSearch WebFetch Read Write Bash
---

# Sterling Grid — Tier 0 Research (V9): Macro & Theme Discovery, as a workflow

## How this skill is invoked

Explicitly, weekly, and **as a dynamic workflow** so the research runs as parallel cross-checked
subagents rather than one linear turn. Three ways to trigger the workflow:
- prefix the invocation with **`ultracode`** (e.g. `ultracode /sterling-grid-tier0-research`), or
- set **`/effort ultracode`** for the session, or
- feed the macro/theme question below to the bundled **`/deep-research`**.
Once a run does what you want, **save it** (`/workflows` → select → `s`) as `/sterling-grid-tier0-research`
so the weekly run reruns the identical orchestration. On every run, re-read this file and `references/`
fresh. Requires Dynamic workflows enabled (`/config` → Dynamic workflows; Claude Code v2.1.154+).
**Fallback** with workflows off: run inline at `xhigh`, searching each stream in turn.

## Read first — load the DNA and the toolkit

Load **`references/shared-context-dna.md`** (V9 — §3 recall→precision, §7 the discriminating signals,
§8 themes top-down + bottom-up; binary model, no sizing), **`references/diagnostic-reference.md`**
(the T1–T7 theme-strength cues, theme-death triggers, value-capture grades), and
**`references/theme-intelligence.md`** §1–§4 (the S0–S4 staging vocabulary, the P1–P4 inflection
precursors with the RKLB/PLTR/Quantum worked anchors, the lead-time priors, the bottleneck-migration
method — this research pass gathers *that* evidence; 0c interprets it). The research must respect
these: surface **wide** (recall), gather **evidence**, and do **not** score or gate here — that is 0c's
job. Output schema in **`references/card-schemas.md`**; transport rules in
**`references/handoff-card-spec.md`** §W.

## The research job (the workflow orchestration)

**STEP 0 — TRANSPORT GUARD** (before authoring or spawning anything; rules: `handoff-card-spec.md` §W):
- **Effort:** set the session (`/effort xhigh`, or `ultracode` for the workflow trigger); **confirm via
  `/status`**; set per-agent effort explicitly in every `agent()` call; record `effort_verified` in
  `runs/<date>/tier0/_run_context.json`.
- **Carry digest, interpolated — never `args`.** Build the continuity block from `sterling-run/log/`
  (one line per HUNT/HOLD theme: name · stage_scurve · recognition · priority · constraint-chain
  status; every open cluster: mechanism · weeks tracked; the regime prior: posture · easing flag ·
  binding axes) and paste it **verbatim into the workflow prompt text**. Workflow `args` can arrive
  undefined inside the script — that is how the 2026-06-08 run silently fell back to cold discovery.
  First action of the run: assert the digest is present and non-empty; **missing → STOP and surface
  it.** Cold/bootstrap discovery runs only when the operator explicitly asks; the pack header then
  states `run_mode: cold (explicit)`.
- **Flat StructuredOutput schemas only** in `agent()` calls (top-level strings/numbers/arrays);
  nested payloads travel as JSON-encoded string fields, parsed and re-validated at the merge.

Then fan the work out in parallel, and cross-check before reporting.

**Phase A — Macro regime (0a).** Research the current liquidity / rates / credit / risk regime and the
**easing-inflection watch** (is policy at or near a turn?). Produce the regime read + posture. Posture
**informs, never gates** selection. → seeds the **Macro** lineage line.

**Phase B — Theme discovery (0b), three parallel surfacing streams** (each a subagent or agent set):
1. **NEW-CLUSTER bottom-up** — what is quietly clustering: unusual, correlated strength across a niche
   of small-caps that no one has named yet (recall mode; this is where catalog-gap themes are found).
2. **Top-down** — the secular / macro forces, and which themes they fund.
3. **Leading-indicator sweep** — surface *before* legibility, per `theme-intelligence.md` §2/§3: for
   each candidate, establish **which of the P1–P4 precursors fire, each with a date and a primary
   source** (P1 private-capital dislocation · P2 capability cadence compressing · P3 first firm *paid*
   demand · P4 recognition still open). Additionally, for **every active wave in the carry digest**,
   re-check its `constraint_chain` for §4 bottleneck-migration evidence (current constraint's relief
   now dated? next constraint's scarcity signature appearing?) — a migration finding is a candidate
   sub-theme.
For each candidate theme gather, with **primary sources**: the demand mechanism and its $ size/flow,
the precursor evidence (P1–P4, dated), an S0–S4 `stage_scurve` guess (§1), the recognition state (is
the market already onto it?), the fuel mix (fundamental vs sentiment), and the best candidate
vehicles / benchmarks.

**Cross-check (the quality pattern).** Run independent agents that **adversarially test** each
candidate — is the theme real or narrative, is demand firm or merely announced, is the move already
priced. **Filter** candidates whose support does not survive; flag the rest with caveats.

## Output contract (→ the Tier-0 skill's 0c / 0d)

Return a research pack, not a verdict:
- **Macro read** — regime, posture, easing-inflection flag, key data points (the Macro lineage seed).
- **Cross-checked candidate-theme list** — per theme: name / sub-theme · surfaced-via (cluster /
  top-down / leading-indicator) · demand mechanism (+ $) · stage · recognition state · fuel mix ·
  candidate vehicles / benchmarks · **key sources (URLs)** · the adversarial verdict (survived / with
  caveats / filtered + why).
0c scores and gates this (→ **Theme** line); 0d maps vehicles (→ **Mapping** line). **Do not score,
rank, or assign priority tiers here.** Cite every claim; mark anything unverifiable `[UNVERIFIED]`.

## Setup, effort & cost
Effort and transport are STEP 0's job (the M3 fix made structural — `handoff-card-spec.md` §W); do not
skip the `/status` confirmation. Enable Dynamic workflows in `/config` (v2.1.154+). Watch the run with
`/workflows`. A workflow spawns many agents and uses meaningfully more tokens than a chat turn — gauge
on a narrow theme question first; the `/workflows` view shows per-agent token use and you can stop
without losing completed work.

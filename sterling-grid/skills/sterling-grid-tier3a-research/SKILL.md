---
name: sterling-grid-tier3a-research
description: >-
  Sterling Grid Tier 3a RESEARCH (V9) — the deep, parallel, cross-checked evidence sweep on a SINGLE
  small-cap name that feeds Tier 3's 3a interpretation. Run as a DYNAMIC WORKFLOW (orchestrated
  subagents), not a single linear pass: it fans parallel agents across the evidence dimensions
  (contracts/backlog, survival/accounting, comparable-winner, bear types, positioning), pulls primary
  sources, and runs an ADVERSARIAL bull-vs-bear cross-check before reporting. This is GATHERING +
  CROSS-CHECK only — the Tier-3 skill's 3a turns the pack into the evidence dossier and appends the
  Evidence lineage line; 3b/3c proceed from there. Pass the ticker as an argument. Save the run as a
  reusable command.
  INVOCATION: invoked deliberately, once per name, by the operator or the Tier-3 orchestrator. Trigger
  it as a workflow (prefix `ultracode`, or `/effort ultracode`, or via `/deep-research`). NOT
  keyword-triggered. On EVERY invocation, re-read this file and its references from disk; never run it
  from memory.
disable-model-invocation: true
effort: xhigh
allowed-tools: WebSearch WebFetch Read Write Bash
argument-hint: "[TICKER]"
---

# Sterling Grid — Tier 3a Research (V9): Single-Name Evidence Sweep, as a workflow

## How this skill is invoked

Explicitly, **one name per run**, and **as a dynamic workflow** so the evidence dimensions are gathered
by parallel cross-checked subagents. Pass the ticker: `/sterling-grid-tier3a-research $ARGUMENTS`.
Trigger the workflow by prefixing **`ultracode`**, setting **`/effort ultracode`**, or feeding the
brief to **`/deep-research`**. Save a good run (`/workflows` → `s`) as `/sterling-grid-tier3a-research`
for reuse. Re-read this file and `references/` fresh each run. Requires Dynamic workflows
(`/config`; Claude Code v2.1.154+). **Fallback** with workflows off: run inline at the full web budget.

## Read first — load the DNA and the toolkit

Load **`references/shared-context-dna.md`** (V9 — §7 the discriminating signals, §9 the disqualifiers,
the binary model with no sizing) and **`references/diagnostic-reference.md`** (the six markers, the KS
disqualifiers, value-capture grades, the Yartseva asset–EBITDA gap, the comparable-winner method) — so
the sweep gathers the **right** discriminators, not generic news. Output schema in
**`references/card-schemas.md`**.

## Input
The **Tier-2 ADVANCE card** (via Tier 2.5 if a second pipeline ran): ticker, provisional type, theme +
benchmark + proxy quality, the rough ≥4x mechanism, rough asymmetry, survival downside, strongest bear,
and the **open questions** Tier 2 couldn't verify. The ticker arrives as `$ARGUMENTS`.

## The research job (the workflow orchestration)

**STEP 0 — TRANSPORT GUARD** (rules: `references/handoff-card-spec.md` §W): set the session effort
(`/effort xhigh` or `ultracode`), **confirm via `/status`**, set per-agent effort explicitly in every
`agent()` call, and record `effort_verified` in the name's run context. **Interpolate the ticker and
the Tier-2 ADVANCE card text literally into the workflow script** — never rely on `args`/`$ARGUMENTS`
reaching spawned agents (they can arrive undefined; the 2026-06-08 tier0 failure); assert both are
non-empty before spawning, else STOP and surface. StructuredOutput schemas stay **flat** (the lineage
array travels as a JSON-encoded string field, parsed and re-validated at merge). Hand agents the
evidence and the open questions, **never pre-formed conclusions**.

Then fan parallel agents across the evidence dimensions, pulling **primary sources** (filings,
transcripts, IR, regulators, contract/award notices), and cross-check before reporting:
1. **Demand firmness** — is revenue **firm** (signed contracts / POs) or merely **announced**
   (MOU / LOI / reservations)? backlog and its conversion.
2. **Survival & accounting** — runway, burn, the dilution path; the discriminator inputs
   (margin / cash-flow inflection); Altman-Z, Piotroski-F, Beneish-M where warranted; the Yartseva
   asset–EBITDA gap; the KS disqualifiers.
3. **Comparable-winner read** — the historical analog(s): the winner's trajectory (peak multiple, time
   to it) **and** the look-alike **failure** and what differed (usually firm-contract presence).
4. **Bear landscape** — sweep the bear **types** (fake-theme · already-priced · dilution-machine ·
   inferior-expression · TAM-fantasy · customer-concentration · cyclical-head-fake · no-terminal-buyer)
   and name the lead bear.
5. **Positioning (amplifier only)** — short interest, float, borrow fee, days-to-cover.
6. **Disqualifier scan (§9) + re-validation** — did anything break since Tier 2?
7. **Theme & space trajectory (feeds Tier-3 3a-T)** — the *space the name rides*, deeper than Tier 0's
   hunting read: the **live competitive field** (peer-set, share trajectory, which player the theme's
   economics accrue to — distinct from the *historical* comparable-winners in dimension 3), theme
   **lifecycle / hype-cycle stage (T1)** and whether capital is still **accelerating in (T7)**, the demand
   mechanism's **$ size + capex (T2 · T3)** and the name's *segment* TAM, **moat / value-capture
   durability** (structural vs temporary + the substitute risk within the theme), and the theme-level
   **catalysts + theme-death triggers (TD-1…5)**. Reuse the `diagnostic-reference.md` frameworks by name;
   invent none.

**Adversarial cross-check (the quality pattern).** Run a dedicated **bear agent** that argues the
strongest short case against the assembled bull evidence; **flag claims that don't survive**. This is
the workflow's adversarial-review pattern applied to the bull/bear DD.

## Output contract (→ the Tier-3 skill's 3a interpretation)

Return an evidence pack, not the dossier or the verdict:
- **Re-validation** status (clean / broke — what)
- **Discriminator scorecard** — each marker **present / partial / absent** with its **source**
- **Disqualifier status** (§9, each clear / triggered)
- **≥4x drivers** (the firm evidence behind the path)
- **Survival picture** — runway, dilution, accounting reads; ruin flag or none
- **Positioning** — SI / float / borrow / days-to-cover
- **Comparable-winner read** — analog (peak multiple, time) + the failure case and the differentiator
- **Bear landscape** — types swept, lead bear, and which bull claims the bear agent could **not** break
- **Theme/space trajectory (for 3a-T)** — peer-set & competitive position · lifecycle stage + this-name
  placement (early / inflection / late) · segment TAM + capex · moat durability (structural vs temporary) ·
  theme catalysts + TD-1…5. The Tier-3 **3a-T** phase interprets this and **enriches the Evidence lineage
  line** — it is *not* a ninth lineage element.
- **Archetype** confirmation
Cite every claim (primary sources preferred); tag anything unverifiable `[UNVERIFIED]`. The Tier-3
skill's 3a interprets this into the **evidence dossier** and appends the **Evidence** lineage line; 3b
(geometry) and 3c (verdict + memo) proceed from there.

## Setup, effort & cost
Effort and transport are STEP 0's job (the M3 fix made structural — `handoff-card-spec.md` §W); do not
skip the `/status` confirmation. Enable Dynamic workflows in `/config` (v2.1.154+); watch with
`/workflows`. Many agents → more tokens than a chat turn; the search space is one company, so cap the
fan-out and gauge on the costly dimensions (filings, comparable-winner) first.

---
name: sterling-grid-tier3-batch
description: >-
  Sterling Grid Tier 3 Batch (V9) — the deep-dive orchestrator. Takes the handful of survivors chosen
  at the deep-dive gate (typically ~3–6 tickers) and runs a FULL Tier-3 deep dive on each, in its own
  isolated branch, in parallel. Per ticker it runs the research-mode 3a evidence sweep (the parallel,
  adversarially cross-checked fan-out from sterling-grid-tier3a-research), then 3a interpretation →
  3a-T (The Space, theme/space trajectory) → 3b geometry → 3c verdict + memo + V9 decision record — the
  existing Tier-3 logic, single-sourced. It
  returns one BUY / DO NOT BUY verdict card per name, ready for Tier 4. Run as a DYNAMIC WORKFLOW so the
  per-ticker deep dives run as isolated parallel branches rather than five names crammed into one
  context. This is the heaviest run in the system.
  INVOCATION: invoked deliberately, after the deep-dive-gate checkpoint, with the chosen tickers. Run as
  a workflow (prefix `ultracode`, or `/effort ultracode`). NOT keyword-triggered. On EVERY invocation,
  re-read this file and its references from disk; never run it from memory.
disable-model-invocation: true
effort: high
allowed-tools: WebSearch WebFetch Read Write Bash
argument-hint: "[TICKER ...]"
---

# Sterling Grid — Tier 3 Batch (V9): per-name deep dives, as a workflow

## How this skill is invoked

Explicitly, **after the deep-dive-gate checkpoint** (the operator has chosen which Tier-2 survivors get
the scarce deep-dive slots), with those tickers: `ultracode /sterling-grid-tier3-batch TMDX CRSP AVAV`.
Run it **as a dynamic workflow** so each name's deep dive is an **isolated parallel branch** — the
design's "one name per session" realised as one branch per ticker, so no name's context dilutes
another's. Save a good run (`/workflows` → `s`) as `/sterling-grid-tier3-batch`. Re-read this file and
`references/` fresh each run. Requires Dynamic workflows (`/config`; v2.1.154+). **Fallback** with
workflows off: run the names **one at a time**, each as its own Tier-3 session — never several in one
context.

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (V9 — binary, no sizing, exits owned by the scanner) and
**`references/lineage-block.md`** (the Evidence / Geometry / Verdict lines this stage appends). This is
the **deep-dive coordinator only** — it does not re-implement the analysis. Each ticker branch **reads
`.claude/skills/sterling-grid-tier3a-research/SKILL.md` for the evidence sweep and
`.claude/skills/sterling-grid-tier3/SKILL.md` for the interpretation/geometry/verdict, and applies
them**, so the logic stays single-sourced. Output schema in **`references/card-schemas.md`**.

## Input
The chosen survivor tickers (`$ARGUMENTS`, space-separated) and their **Tier-2 ADVANCE cards** from
`sterling-run/runs/<date>/tier2/` (each carrying the inherited Macro / Theme / Mapping / Triage / Gate
lineage, the provisional type, and the open questions). Read each card before its branch starts.

## The orchestration (the workflow)

**STEP 0 — TRANSPORT GUARD** (rules: `references/handoff-card-spec.md` §W): set the session effort
(`/effort xhigh` or `ultracode`), **confirm via `/status`**, set per-agent effort explicitly in every
`agent()` call, and record `effort_verified` in `runs/<date>/tier3/_run_context.json`. **Interpolate
the ticker list and each name's Tier-2 ADVANCE card text literally into the workflow script** — never
rely on `args`/`$ARGUMENTS` reaching spawned agents (they can arrive undefined; the 2026-06-08 tier0
failure); assert every branch's inputs are non-empty before spawning, else STOP and surface.
StructuredOutput schemas stay **flat**; the lineage array travels as a JSON-encoded string field,
parsed and re-validated per branch.

**For each ticker, in its own isolated parallel branch:**

1. **3a evidence sweep — research mode.** Run the `sterling-grid-tier3a-research` orchestration on this
   one name: fan parallel agents across the evidence dimensions (contracts/backlog, survival/
   accounting, comparable-winner, bear types, positioning, **theme/space trajectory**), pull primary
   sources, and run the **adversarial bull-vs-bear cross-check** before reporting. → the cross-checked
   evidence pack (name evidence **plus** the theme/space pack).
2. **3a interpretation → 3a-T (The Space) → 3b → 3c.** Apply the `sterling-grid-tier3` skill over that
   pack, **starting at 3a interpretation** (the evidence is already gathered — do not re-run the sweep):
   interpret into the evidence dossier; **3a-T interprets the theme/space pack into the Theme/Space
   Trajectory block — peer-set, lifecycle, capex/demand & segment TAM, moat, theme catalysts/risks, and
   the theme→price read — enriching the Evidence line, NOT a ninth lineage element** (append **Evidence**);
   3b floor/target, four scenarios, velocity, catalyst window, type (append **Geometry**); 3c the binary
   **BUY / DO NOT BUY** verdict + the memo that opens Macro → Theme → Mapping and carries a dedicated
   **The Space** section + the V9 decision record (append **Verdict**). No sizing; no
   `size_pct`/`exit_regime`/`kill_criteria`.
3. **Write out:** the dossier, the verdict card, and the decision record to
   `sterling-run/runs/<date>/tier3/<ticker>/`. After each branch persists, run
   `python3 -m scripts.sterling_validate <date> --check lineage` — a branch whose verdict card lacks
   the eight-element §2 array is **re-emitted by that branch's agent**, never patched at persist time.

Run the ticker branches concurrently; the runtime paces them under its concurrency cap. Each branch is
independent — one name's bear case never contaminates another's.

## Output contract (→ Tier 4)
Return **one verdict card per name** — BUY / DO NOT BUY · type · conviction · catalyst window · the
comprehensive memo · the V9 decision record — with the lineage block now carrying Macro · Theme ·
Mapping · Triage · Gate · Evidence · Geometry · Verdict. Append each decision to `decisions.json`
(calibration Part A).

**Stop here.** **Tier 4** is the next step and runs **as before — one session over the whole set** of
verdict cards (the comparative buy decision against the opportunity bar, reading each name's catalyst
window), followed by the **capital-gate checkpoint**. Keep Tier 4 separate: it is a single comparative
judgment and the capital gate wants your eyes on it, and a workflow can't pause mid-run for that
sign-off anyway.

## Setup, effort & cost
Effort and transport are STEP 0's job (the M3 fix made structural — `handoff-card-spec.md` §W); do not
skip the `/status` confirmation.
This is the **most expensive run in the system**: N names × (a full evidence fan-out + the analytical
passes). Enable Dynamic workflows (`/config`; v2.1.154+); watch with `/workflows` (it shows per-branch
agent and token use, and you can stop without losing completed branches). If the spend or concurrency
is a concern, run the deep dives in **two smaller batches** (e.g. 3 then 2) rather than all at once —
the per-name isolation means batching the orchestrator costs nothing analytically.

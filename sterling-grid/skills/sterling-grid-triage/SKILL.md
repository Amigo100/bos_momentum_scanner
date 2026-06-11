---
name: sterling-grid-triage
description: >-
  Sterling Grid Triage (V9) — the batch fan-out that takes the week's full scanner signal list
  (~30–60 tickers) through Tier 1 (shape triage) and Tier 1.5 (batch verification) and hands back ONE
  merged, verified ADVANCE list (the Tier-2 queue), plus the consolidated DROP log, the recall-audit
  flags, and NEW-CLUSTER signals. Run as a DYNAMIC WORKFLOW: it splits the signals into batches at the
  handoff-card-spec §0 ceilings (Tier 1 ≤10 · Tier 1.5 ≤8), runs each batch as an isolated parallel
  subagent applying the Tier-1 / Tier-1.5 skills, validates count conservation with the manifest +
  sterling_validate, auto-gapfills any truncated batch, and merges by concatenation — never 50 tickers
  in one pass. It does not re-implement Tier 1 / Tier 1.5; each batch subagent reads those skills from
  disk and applies them, so the logic stays single-sourced. The merged ADVANCE list + the
  possible-false-drop flags are Checkpoint A — reviewed before the per-name Tier-2/Tier-3 work.
  INVOCATION: invoked deliberately, weekly, by the operator or the orchestrator. Trigger as a workflow
  (prefix `ultracode`, or `/effort ultracode`). NOT keyword-triggered. On EVERY invocation, re-read this
  file and its references from disk; never run it from memory.
disable-model-invocation: true
effort: high
allowed-tools: WebSearch WebFetch Read Write Bash
argument-hint: "[signals-csv-path]"
---

# Sterling Grid — Triage (V9): Tier 1 + Tier 1.5 batch fan-out, as a workflow

## How this skill is invoked

Explicitly, weekly, and **as a dynamic workflow** so the batches run as parallel isolated subagents
rather than one bloated pass. Trigger the workflow by prefixing **`ultracode`** (e.g.
`ultracode /sterling-grid-triage`) or setting **`/effort ultracode`**. Save a good run (`/workflows` →
select → `s`) as `/sterling-grid-triage` for the weekly cadence. Re-read this file and `references/`
fresh each run. Requires Dynamic workflows enabled (`/config` → Dynamic workflows; Claude Code
v2.1.154+). **Fallback** with workflows off: process the list one batch at a time at the same §0
ceilings (Tier 1 ≤10, Tier 1.5 ≤8), in sequence, merging by concatenation — never the whole list in
one pass, and the same manifests + validation steps apply.

## Read first — load the DNA and the seam spec

Load **`references/shared-context-dna.md`** (V9 — §3 recall→precision, §10 the lineage rule; binary
model, no sizing) and **`references/handoff-card-spec.md`** (§0 ceilings · §1 envelope · §2 lineage
array · §5 manifests · §W transport). This skill is the **fan-out coordinator only** — it does not
re-implement the triage logic. Each batch subagent **reads
`.claude/skills/sterling-grid-tier1/SKILL.md` (STEP 2) or
`.claude/skills/sterling-grid-tier1_5/SKILL.md` (STEP 4) and their `references/` from disk and applies
them**, so the rules stay single-sourced. Output schema in **`references/card-schemas.md`**.

## Input
The week's full signal list — **`sterling-run/signals/this-week.csv`** (`$ARGUMENTS` if a path is
passed), ~30–60 tickers — and the **Tier-0 hunting brief** (carrying the three theme-level lineage
lines + the S-stage/precursor tags per HUNT theme). Read both before splitting.

## The orchestration (the workflow, as numbered steps)

**STEP 0 — TRANSPORT GUARD** (rules: `handoff-card-spec.md` §W). Set the session effort
(`/effort high` minimum, `ultracode` for the workflow trigger); **confirm via `/status`**; set
per-agent effort explicitly in every `agent()` call; record `effort_verified` in
`runs/<date>/tier1/_run_context.json`. **Interpolate** the signal rows and the hunting-brief text
literally into the workflow script — never pass them as workflow `args` (they can arrive undefined);
assert both are non-empty before spawning, else STOP and surface. StructuredOutput schemas stay
**flat**; the lineage array travels as a JSON-encoded string field, parsed and re-validated at merge.

**STEP 1 — MANIFEST.** Split the signal list into **batches of ≤10** (spec §0; smaller if the week
needs heavy searching) and write `runs/<date>/tier1/_batch_manifest.json` — every batch's
`input_tickers` — **before** spawning anything. Count conservation is proven against this file, not
remembered.

**STEP 2 — TIER-1 FAN-OUT.** For each batch spawn **one isolated subagent**, given: its batch rows
(ticker + sector / price / signal strength), the hunting brief, and the instruction to **read
`sterling-grid-tier1/SKILL.md` + references and apply it** — grounding every judgment in current
facts, inheriting the three theme-level lineage lines (with their mapping-confidence tags) onto each
ADVANCE as the **§2 array**, and appending the `Triage` element. Each subagent returns **a verdict
for EVERY ticker in its manifest slice** (ADVANCE / DROP / HELD — never silence) as the fixed Tier-1
card. Write each batch to `runs/<date>/tier1/batch<N>.json`.

**STEP 3 — VALIDATE + AUTO-GAPFILL** (no operator needed). Run
`python3 -m scripts.sterling_validate <date> --check counts --json`. If any phase reports `missing`
tickers: split them into **gapfill batches of ≤5**, append the batches to the manifest, re-run as
`gapfill<N>.json`, and validate again. **Up to TWO gapfill rounds**; anything still missing after two
→ STOP and surface the residue at Checkpoint A with the validator output. **Never merge a short phase
silently** — a missed ADVANCE is a missed multibagger. Run `--check lineage` here too; a batch whose
cards carry a malformed lineage (dict, missing, or flag-instead-of-array) is **re-emitted by that
agent**, never patched at persist time.

**STEP 4 — MERGE + TIER-1.5 FAN-OUT.** Merge Tier 1 by concatenation (ADVANCE payloads → the verify
queue; DROP log → the consolidated drop log; NEW-CLUSTER signals → union). Write
`runs/<date>/tier1_5/_batch_manifest.json` over the ADVANCE pile in **batches of ≤8** (spec §0), then
fan out exactly as STEP 2–3 (isolated subagents reading `sterling-grid-tier1_5/SKILL.md`; verify on
current data; **DROP only on confirmed evidence, never "couldn't tell"**; update the `Triage` element
in place — array length unchanged; validate; auto-gapfill ≤5, two rounds max). Write to
`runs/<date>/tier1_5/`.

**STEP 5 — RECALL AUDIT** (the systematized Checkpoint-A safety net). Spawn **one dedicated reviewer
subagent** over the consolidated DROP log (both phases) + DNA §3/§4/§7. It flags any drop matching
these patterns — each flag names its rule so K.1 can score the audit itself:

```
R1 conceded-great-trade   the reason itself concedes a high-confidence 3–4x path while rejecting
                          only the ≥4x venture mechanism (§4 has TWO qualifying paths)
R2 size-class-error       "can't 4x" applied where a 3–4x great trade is geometrically trivial
                          (cap ≲ $1.5B), or the cap figure used is wrong
R3 trap-attribute drop    established / profitable / dividend / "expensive" doing the load-bearing
                          work (§7's traps) while bullish discriminators are present
R4 theme-veto-on-name     theme HOLD / STAND-DOWN / AVOID cited against a name with live name-level
                          evidence (a theme posture stops hunting; it is not a name disqualifier)
R5 unexposed-fact         "confirmed negative" claimed without stating the load-bearing fact
                          (unfalsifiable = not confirmed)
R6 couldnt-tell-as-drop   the wording reveals an unresolved check recorded as DROP (§3: unresolved
                          → ADVANCE)
```

**The audit agent may ONLY flag for reinstatement — it never adds drops and never re-litigates
ADVANCEs.** (Recall-only by construction: this is §3's safety net, not a new gate.) Output:
`possible_false_drops[]` — ticker · stage · rule · a one-line case — on the Checkpoint-A card.
Reinstatement mechanic: operator-approved Tier-1 flags re-enter as a Tier-1.5 gapfill batch; Tier-1.5
flags join the Tier-2 queue; either way annotate the `Triage` element in place:
`reinstated at Checkpoint A (recall audit R<n>)`.

**STEP 6 — CHECKPOINT A ASSEMBLY.** Return, and stop.

## Output contract (→ Checkpoint A, then Tier 2)
- **The verified ADVANCE list = the Tier-2 queue** — each name's Tier-1.5 ADVANCE card, carrying the
  inherited Macro / Theme / Mapping lines and the updated `Triage` element (§2 array).
- **The consolidated DROP log** (with reasons + §0 reason codes) → `decisions.json` via calibration.
- **`possible_false_drops[]`** — the recall-audit flags (R1–R6) for operator review.
- **The validator summary line** — counts conserved? lineage intact? gapfill rounds used? residue?
- **NEW-CLUSTER signals** → next week's Tier 0 (the §6 cluster ledger).
This is **Checkpoint A**: the operator reviews the merged ADVANCE list + the false-drop flags before
the expensive per-name work. **Stop here** — Tier 2 runs per name, and Tier 3 per name (via
`sterling-grid-tier3a-research`); those are separate, not part of this fan-out. (Workflows can't pause
mid-run for sign-off, so Checkpoint A falls naturally after this workflow returns.)

## Setup & cost
Effort and transport are STEP 0's job (the M3 fix made structural — `handoff-card-spec.md` §W); do
not skip the `/status` confirmation. Enable Dynamic workflows in `/config` (v2.1.154+); watch with
`/workflows`. Tier-1 batches are light, so this is cheaper than the research workflows, but it still
spawns many agents — gauge on a partial signal list first if you're unsure of the spend.

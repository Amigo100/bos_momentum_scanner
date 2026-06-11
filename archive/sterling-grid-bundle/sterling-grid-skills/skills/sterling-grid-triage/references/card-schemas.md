# Sterling Grid — Output Schema (Triage workflow, V9)

> A fan-out coordinator. It does not define card shapes — those live in `sterling-grid-tier1` and
> `sterling-grid-tier1_5`. This file states the workflow's INPUT, the per-batch handoff, and the merged
> OUTPUT. Ceilings, envelope, lineage encoding, and manifests: `references/handoff-card-spec.md`
> (§0 · §1 · §2 · §5). No scoring, no sizing, no verdict.

## INPUT
```
signals:  sterling-run/signals/this-week.csv  (~30–60 tickers; $ARGUMENTS overrides the path —
          INTERPOLATED into the workflow text, never passed as workflow args; spec §W)
brief:    the Tier-0 hunting brief (carries the 3 theme-level lineage lines + S-stage/precursor
          tags per HUNT theme)
```

## PER-BATCH (each isolated subagent)
- **Phase 1:** reads `sterling-grid-tier1/SKILL.md` (+ references) → emits that skill's card
  (triage table · ADVANCE payload with inherited lineage [the §2 array] + appended `Triage` · DROP log
  · NEW-CLUSTER). Batch size **≤10** (spec §0).
- **Phase 2:** reads `sterling-grid-tier1_5/SKILL.md` (+ references) → ADVANCE / DROP, `Triage`
  element updated in place to `→ T1.5 ADVANCE · verify-question answered`. Batch size **≤8** (spec §0).
- Gapfill batches **≤5**, two rounds max. Cards written to `sterling-run/runs/<date>/tier1/` and
  `.../tier1_5/`, each phase under its `_batch_manifest.json` (spec §5).

## MERGE (mechanical — concatenation, not re-derivation; validated, never trusted)
- Run `python3 -m scripts.sterling_validate <date> --check counts --json` per phase; `missing` →
  auto-gapfill; `--check lineage` on the merged cards.
- ADVANCE payloads → concatenated → Phase 2 input → the **Tier-2 queue**.
- DROP logs → concatenated (each with the §0 `reason_code`) → `decisions.json` via calibration Part A.
- NEW-CLUSTER signals → unioned → next week's Tier 0 (the theme-intelligence §6 ledger).

## OUTPUT (→ Checkpoint A)
```
tier2_queue:        [ each name's Tier-1.5 ADVANCE card — inherited Macro/Theme/Mapping + updated Triage ]
drop_log:           [ ticker · stage (tier1/tier1_5) · reason_code · reason ]  → decisions.json
possible_false_drops: [ {ticker · stage · rule R1–R6 · one-line case} — the recall audit's flags;
                        reinstatement-only, never re-litigates ADVANCEs ]
validator_summary:  counts conserved? lineage intact? gapfill rounds used? residue?
new_cluster:        [ bottom-up theme-birth signals ]  → next week's Tier 0
```

## HANDOFF
Stops at the verified ADVANCE list + the recall-audit flags (**Checkpoint A**). Then: **Tier 2**
(`sterling-grid-tier2`, one or two names per session) → **Tier 3** (`sterling-grid-tier3`, per name;
evidence via `sterling-grid-tier3a-research`; two-plus names via `sterling-grid-tier3-batch`) →
**Tier 4**.

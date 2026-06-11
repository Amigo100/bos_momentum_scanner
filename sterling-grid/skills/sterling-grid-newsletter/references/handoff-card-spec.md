# Sterling Grid — Handoff Card Spec (the unified seam contract, V9)

> **The single source of truth for everything that crosses a tier boundary**: the pipeline constants,
> the card envelope, the lineage encoding, the file layout, the count-conservation manifests, and the
> workflow transport rules. Per-tier `card-schemas.md` files remain authoritative for **working-layer
> content** (what each tier's card *says*); this spec governs the **envelope and the seams** (what
> shape it travels in, where it lands, and how the orchestrator proves nothing was lost). Other docs
> point here — **never restate these constants elsewhere**; restated numbers are how the 2026-06-07
> batch-size contradiction (≤8 in one doc, ~10–15 in four others) truncated a run.
> Machine checks: `python3 -m scripts.sterling_validate <date> --check all`.

## §0 Pipeline constants (the ONLY place these live)

```
BATCH CEILINGS (hard; auto-split above, never "fit it in"):
  Tier 1 ≤ 10 per batch        (a 12-name batch content-truncated a card in the 2026-06-07 run)
  Tier 1.5 ≤ 8 per batch       (verify agents truncated a 12-name batch in the 2026-06-06 run)
  Gapfill ≤ 5 per batch        (re-runs of missing names; two rounds max, then STOP and surface)

STAGE IDS (canonical, for decisions.json and card `stage` fields):
  tier0 · tier1 · tier1_5 · tier2 · tier2_5 · tier3 · tier4 · exit

DECISION SPELLINGS (JSON fields; prose may write "DO NOT BUY"):
  ADVANCE · DROP · BUY · DO_NOT_BUY · SELL

REASON CODES (closed enum; the free-text `reason` carries the nuance, the code makes it calibratable):
  no-path            no credible ≥4x or 3–4x mechanism of either kind
  ruin               §9 ruin test fired (going-concern / debt wall / dilution death-spiral)
  disqualifier       a §9 fake-demand/fake-inflection item fired (LOI-as-backlog, slipped
                     milestones, guidance cuts, credibility event)
  verify-failed      the Tier-1/1.5 verify-question resolved confirmed-negative
  false-match        the ticker does not do the thing the theme mapping claimed
  weak-proxy         exposure real but too dilute/derivative to capture the theme (per
                     theme-intelligence.md §7 — graded, not vibed)
  inferior-expression a strictly better vehicle exists for the same exposure
  theme-posture      a theme-level state did the cutting, not name-level evidence: a Tier-0
                     HOLD/STAND-DOWN/AVOID posture, a thesis resting only on an unqualified theme
                     (Tier 2.5 theme-only), or a late/crowded theme at the Tier-4 bar — `stage`
                     separates the cohorts. A posture stops hunting NEW names; it never
                     retroactively drops an already-flagged name (DNA §8: a theme stage gates a
                     theme, never a name)
  pre-inflection     mechanism real but no inflection underway yet (too early, re-enters via scan)
  distant-catalyst   nothing dated inside the underwritable window
  move-exhausted     the re-rate already happened; entry geometry gone
  thin-setup         real but not worth a scarce slot (asymmetry/conviction too thin)
  lottery-ticket     binary with no quantified leading indicator (the RGTI-at-pure-hype shape)
  outclassed         lost the comparative Tier-4 ranking this cycle
  wrong-instrument   fine company, not this book's instrument (income/defensive/ETF-shape)
  held-routed-out    already held — routed out of the funnel, not re-triaged

TYPE SPELLINGS (JSON fields; prose writes "great trade"):
  multibagger · great_trade

LINEAGE STAGES, in order (Consensus only when Tier 2.5 ran):
  Macro · Theme · Mapping · Triage · Gate · [Consensus] · Evidence · Geometry · Verdict · Decision
```

## §1 The card envelope

**Per-name card** (one JSON object — standalone file or a row inside a batch file):

```json
{ "ticker": "XYZ", "stage": "tier2", "date": "YYYY-MM-DD", "week_id": "YYYY-WNN",
  "decision": "ADVANCE", "lineage": [ ...§2... ], "working": { ...per-tier card-schemas... } }
```

**Batch file** (fan-out tiers — Tier 1 / 1.5):

```json
{ "batch_id": "b1", "phase": "tier1", "date": "YYYY-MM-DD",
  "counts": { "input": 10, "advance": 4, "drop": 5, "held": 1 },
  "advance": [ ...per-name cards... ],
  "drops":   [ { "ticker": "QRS", "stage": "tier1", "reason_code": "false-match",
                 "reason": "one line, calibration-checkable" } ] }
```

`counts.input` must equal `advance + drop + held` and match the manifest (§5). Every name gets a
verdict — a batch that returns fewer rows than its manifest slice is truncated, not finished.

## §2 Canonical lineage encoding (fixes the dict / missing / boolean drift)

```json
"lineage": [
  { "stage": "Macro",   "line": "regime state · posture · easing/inflection flag ..." },
  { "stage": "Theme",   "line": "theme/sub-theme · surfaced-via · stage · recognition ..." },
  { "stage": "Mapping", "line": "value-capture grade · vehicle vs benchmark · proxy quality ..." },
  { "stage": "Triage",  "line": "T1 ADVANCE → T1.5 ADVANCE · verify-question answered: ..." }
]
```

- **One ordered array of `{stage, line}` objects** — never a dict keyed by stage (it entered the
  2026-06-07 tier1 cards that way and made length checks meaningless), never separate fields, never
  a `lineage_complete: true` flag in place of the array.
- **Copy whole → append one → write the WHOLE array out.** `len(out) == len(in) + 1` at every
  handoff. The one exception: **Tier 1.5 edits the Triage element in place** (length unchanged);
  **3a-T enriches the Evidence element** (no ninth element).
- **Inherited `line` strings travel byte-identical.** A changed upstream line is silent re-derivation
  — the exact 2026-06-06 Tier-2→3c failure. Disagree in your own line, never by rewriting theirs.
- Stage names must form a prefix of the §0 canonical order (Consensus optional).
- **3c asserts the eight elements** Macro·Theme·Mapping·Triage·Gate·Evidence·Geometry·Verdict (nine
  with Consensus). Fewer → the handoff broke upstream: STOP, surface, fix the agent that dropped it.
  Never re-derive, never stitch the array at persist time.

## §3 Boundary table (expected shape at each seam)

| Handoff | Required working keys (see that tier's card-schemas for content) | lineage in → out |
|---|---|---|
| 0d → T1 (hunting brief) | per HUNT theme: priority tier · benchmarks · the 3 theme-level lines · S-stage/precursors/window | — → 3 (on the theme) |
| T1 → T1.5 (ADVANCE) | ticker · bull-case · arch · theme+benchmark · verify-first | 3 → 4 (+Triage) |
| T1.5 → T2 (ADVANCE) | ticker · pin-down-for-Tier-2 · exposure/early/disq reads | 4 → 4 (Triage edited in place) |
| T2 → T2.5/T3 (ADVANCE) | ticker · provisional type · path · asymmetry · survival · strongest bear · open questions | 4 → 5 (+Gate) |
| T2.5 → T3 (queue) | ranked queue · per-name reconciliation ruling | 5 → 6 (+Consensus) |
| 3a/3a-T → 3b | evidence dossier + Theme/Space block | 5/6 → 6/7 (+Evidence) |
| 3b → 3c | geometry card: floor/target · 4 scenarios+probs · velocity · catalyst window · type | +1 (+Geometry) |
| 3c → T4 | verdict card: BUY/DO_NOT_BUY · type · conviction · expected path+target · catalyst window · memo · decision record | +1 (+Verdict; assert 8) |
| T4 → 3d/ledger | buy list · DO-NOT-BUY log · concentration_read · decision rows | +1 (+Decision) |
| any tier → decisions.json | ticker · date · week_id · **stage** · decision · **reason_code** · reason · price_at_decision · forward | n/a |

## §4 Canonical file layout + naming (run hygiene the validator checks)

```
sterling-run/runs/<YYYY-MM-DD>/
  tier0/    hunting_brief_<date>.md · tier0_research_pack_<date>.{json,md} · theme_map_<date>.json ·
            theme_health_<date>.md · _run_context.json
  tier1/    _batch_manifest.json · batch<N>.json · gapfill<N>.json · tier1_result_<date>.json
  tier1_5/  _batch_manifest.json · batch<N>.json · gapfill<N>.json · tier1_5_result_<date>.json ·
            CHECKPOINT_A_<date>.md
  tier2/    <TICKER>.json · tier2_result_<date>.json · tier3_queue.json
  tier2_5/  reconciled_queue_<date>.json            (only if a second pipeline ran)
  tier3/    <TICKER>/ evidence_pack.json · dossier.json · theme_space.json · geometry.json ·
            verdict.json · memo.md · decision_record.json
  tier4/    tier4_decision_<date>.md · decision_rows_<date>.json
  articles/ <ticker>-deep-dive.html · weekly-screening-<date>.html · notes files
```

Beyond the run dir, the weekly close **mirrors** each run (idempotent, append-only copies +
deterministic indexes) into the two findability views: `sterling-run/research/<TICKER>/`
(per-name: every memo/dossier/verdict/decision across runs + `index.json` with status
bought|held|passed|in-funnel) and `sterling-run/weeks/<YYYY-WNN>/` (per-week: newsletter, notes,
deep-dives/, `decisions.csv` ledger slice, `manifest.json`). Backfill mode:
`sterling_weekly_close <date> --mirror-only`.

**Each tier writes ONLY inside its own directory** (the 2026-06-08 run wrote tier1_5 outputs into
`tier1/` — the validator now flags it). One sanctioned exception: a tier may write its successor's
handoff queue in its own dir, named for the **consumer** (`tier2_queue.json` in `tier1_5/`,
`tier3_queue.json` in `tier2/`, `tier4_queue.json` in `tier3/`). Fan-out phases write
`_batch_manifest.json` **before** spawning; gapfills append to it. Readers (the weekly close, the
validator) accept pre-V9.1 aliases **for old runs only** — tier1_5: `triage_final_<date>.json` /
`triage_result_<date>.json`; tier4: `tier4_result_<date>.json` — **writers MUST emit the canonical
names above.**

## §5 Count-conservation manifests (truncation is detected, not noticed)

Before any fan-out the orchestrator writes the manifest:

```json
{ "phase": "tier1_5", "date": "YYYY-MM-DD",
  "batches": [ { "batch_id": "b1", "input_tickers": ["AAA","BBB","CCC"] } ] }
```

Rules: every manifest ticker receives exactly one verdict across the phase's batch files · the union
of batch outputs equals the manifest set (no missing, no extras, no duplicates) · the merged result
file covers the manifest set. Checked by `sterling_validate --check counts`; its `--json` output's
`missing` list is the auto-gapfill input (gapfill batches of ≤5, two rounds max, then STOP and
surface the residue at the checkpoint). **Never merge a short phase silently.**

**Merged-result minimal contract** (what the validator's result-covers-manifest sub-check parses):

```
tier1_5_result_<date>.json   { counts · tier2_queue: [ {ticker · arch · theme · pin-down · lineage} ]
                               · drop_log: [ {ticker · stage tier1|tier1_5 · reason_code · reason} ]
                               · tier1: [batch…] · tier15: [batch…] }
                             tier2_queue ∪ drop_log must cover BOTH phases' manifests.
tier2_result_<date>.json     { counts · advance: [card…] · drop: [ {ticker · reason_code · …} ] }
decision_rows_<date>.json    [ tier4 (d) rows: stage tier4 · decision · reason_code · … ]
```

## §W Workflow transport rules (platform lessons — do not relearn these)

1. **Interpolate, never `args`.** Write every input a workflow needs — ticker lists, file paths, the
   hunting-brief text, the carry digest — **literally into the workflow script/prompt text** before
   spawning. Workflow `args` can arrive `undefined` inside the script (the 2026-06-08 tier0 run
   silently fell back to cold discovery this way). Assert each interpolated value is non-empty before
   spawning; a missing expected input → **STOP and surface it**. Cold/bootstrap mode runs only when
   the operator explicitly asks for it — never as a fallback.
2. **Flat StructuredOutput schemas only.** Schemas in workflow `agent()` calls must be flat —
   top-level strings / numbers / arrays-of-strings. Nested object schemas fail validation. A nested
   payload (e.g. the lineage array) travels as a **JSON-encoded string field**; the merge step parses
   and re-validates it (§2 shape) before persisting.
3. **Effort reaches the workers (the M3 fix, structural).** Spawned sub-agents default to the
   *session* model/effort, NOT the skill's frontmatter. Before spawning: set the session
   (`/effort xhigh` or `ultracode`), **confirm via `/status`**, set per-agent effort explicitly in
   every `agent()` call, and record `effort_verified: true` in the tier's `_run_context.json`.
4. **Validate at every merge.** Run `sterling_validate` (counts + lineage) after each fan-out merge
   and before each checkpoint. A failed check means **fix the agent's output and re-run that unit**
   — never patch arrays or counts at persist time. Hand agents evidence and inputs, never pre-formed
   conclusions; operator priors live in a reconciliation note, not the spawn prompt.

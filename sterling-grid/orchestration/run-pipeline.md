# Sterling Grid — Running the pipeline (the V9 driver)

How to execute the skills and chain them. The skills are the *how* of each step; this is the
*operator* that runs the steps in order, isolates each unit of work, carries the lineage + the
persistent log, and passes the cards between them. Pair it with `weekend-run.md` (the detailed
sequence).

---

## 0. Install the skills (the ONE edit point is `sterling-grid/`, tracked in git)

- **Canonical source:** `sterling-grid/skills/sterling-grid-*` (the 16 skills) +
  `sterling-grid/shared/` (the 5 refs) + this `orchestration/` folder.
- **Install / update:** `sh sterling-grid/install.sh` — propagates the shared refs into each source
  skill's `references/`, then replaces the runtime copies in `.claude/skills/`. Start a new session;
  `/skills` to confirm. Invoke with `/sterling-grid-tier1` etc., or let the driver name it.
- **After ANY skill or shared-ref edit:** edit in `sterling-grid/`, run `sh sterling-grid/install.sh`.
  Never edit `.claude/skills/` directly — it is the gitignored runtime, overwritten on install.
- **Cowork / claude.ai:** zip a `sterling-grid/skills/sterling-grid-*` folder (folder at the ZIP
  root) and upload via Customize → Skills.

## 1. Set up a working folder (the state medium)

The chain passes files, not chat memory:

```
sterling-run/
├── signals/this-week.csv          # scanner output (the Tier-1 input)
├── log/                           # the carried-forward log (Tier 0 reads + rewrites weekly)
│   ├── theme_map.json             #   the scored theme map + theme-level lineage lines
│   ├── benchmark_set.json         #   off-list benchmarks we're waiting on
│   ├── regime_log.jsonl           #   0a's running macro read
│   └── discovery_log.jsonl        #   0b's running sweep
├── decisions.json                 # running log: BUY / DO NOT BUY / technical SELL / DROP
├── portfolio.csv                  # positions + prices; SOLE price source for the newsletter
└── runs/<YYYY-MM-DD>/             # this week's cards
    ├── tier0/                     #   hunting brief + scored map
    ├── tier1/   tier1_5/          #   one file per batch
    ├── tier2/   tier2_5/          #   gate cards / the reconciled DD queue
    ├── tier3/                     #   3a dossier · 3b geometry · 3c memo + record, per name
    ├── tier4/                     #   buy list + decision rows
    └── articles/                  #   3d deep-dive HTML per BUY; the newsletter; the notes
```

## 1b. Canonical paths & run hygiene (non-negotiable)

The 2026-06-06 run picked well but bypassed the harness; hold these or calibration and next-week
carry-forward break:
- **Read signals from `sterling-run/signals/this-week.csv`** — and use its `sector` and
  `signal_strength` columns (Tier 1 inputs), not a bare ticker dump.
- **Write every tier's cards to `sterling-run/runs/<YYYY-MM-DD>/<tier>/`** — not to `log/`, not scattered.
- **`sterling-run/decisions.json` is the single decision ledger.** Every DROP / DO NOT BUY / BUY is
  appended there with the V9 forward-snapshot schema by **calibration Part A as the sole writer** — no
  parallel ad-hoc logs, no double-logging.
- **The carried-forward log stays in `sterling-run/log/`** (`theme_map.json`, `benchmark_set`,
  `regime_log`, `discovery_log`); Tier 0 reads + updates it. (This part the run did correctly.)
- **Populate `sterling-run/portfolio.csv` via `python3 -m scripts.sterling_price_refresh` before the
  newsletter** — it rewrites only the Current/P&L% columns (the newsletter's sole price source);
  fetch failures keep old values and warn, never blank.
- **One growing `lineage` array per name, carried whole** (copy → append one → forward), encoded as
  the canonical `[{stage, line}]` array (`shared/handoff-card-spec.md` §2 — never a dict, never a
  `lineage_complete` flag); assert all eight elements at 3c. A card with fewer lineage elements than
  its input dropped inherited context. **Run `python3 -m scripts.sterling_validate <date> --check all`
  after every merge and before each checkpoint** — a failed check means fix the agent's output and
  re-run that unit, never patch arrays or counts at persist time.
- **Effort reaches the workers (STEP 0 in every workflow skill):** a workflow's spawned sub-agents
  default to the session model — set the session to the tier's declared effort (`/effort xhigh` for
  the deep dives), **confirm via `/status`**, and set per-agent effort in every spawn, so xhigh
  actually applies to the analysis, not just the orchestration context.
- **Interpolate workflow inputs — never `args`:** continuity and inputs (the Tier-0 carry digest,
  ticker lists, card text) are pasted **literally into the workflow script text**; workflow `args` can
  arrive undefined (the 2026-06-08 tier0 silently ran cold discovery this way). A missing expected
  input → STOP and surface; cold/bootstrap mode only when explicitly requested. StructuredOutput
  schemas in `agent()` calls stay **flat** (spec §W).
- **Agents reach verdicts unled:** hand each sub-agent the evidence and inputs, **not** your pre-formed
  conclusions; keep operator priors (known false-matches, "expect to decline") in a separate
  reconciliation note rather than seeding the agent's prompt.

## 2. Levels of automation

- **Level 0 — manual:** run one skill per chat turn, copy each card into the next step. Best for the
  first validation run. No setup.
- **Level 1 — delegated:** paste the operator prompt below into one Claude Code session (or a Cowork
  task). Claude orchestrates the whole run; the human checkpoints are approval gates.
- **Level 2 — scheduled:** wrap the operator prompt as a Claude Code Routine / scheduled task to run
  it on a cadence; the checkpoints become explicit approve-to-continue gates.

---

## 3. The operator prompt (Level 1 / Level 2)

> Paste into a Claude Code session (or Cowork task) **with the Sterling Grid skills installed** and a
> `sterling-run/` folder present. It invokes each skill **explicitly** (not by keyword auto-load), per
> the "looked up each time" model.

```
You are the ORCHESTRATOR for the Sterling Grid V9 weekend run. Your job is sequencing, context
isolation, merging, and carrying the lineage + the persistent log — NOT analysis. Do not triage,
value, or judge any name yourself; invoke the tier skills to do that. Read orchestration/weekend-run.md
first and follow it exactly. There is NO position sizing in V9 — every decision is ADVANCE/DROP in the
funnel and BUY/DO NOT BUY at the buy gate.

PRECONDITIONS & MANDATORY CHECKS (real 2026-06 failures sit behind every one — enforce them):
- Set `/effort xhigh` NOW and CONFIRM via `/status`. When you delegate a tier to a workflow, set each
  analysis agent's effort explicitly too — a skill's frontmatter effort does NOT reach spawned
  sub-agents (the repeated Critical finding; every workflow skill's STEP 0 governs).
- Batch ceilings, stage ids, reason codes, the card envelope, and the lineage JSON encoding live in
  `sterling-grid/shared/handoff-card-spec.md` §0–§2 — THAT FILE GOVERNS; do not restate numbers here.
  One growing `lineage` array per name (the §2 [{stage, line}] array), carried ON the card; at every
  handoff `len(out) == len(in)+1` (Tier 1.5 edits Triage in place). If it shrank, FIX THE AGENT — do
  not patch the array externally at persist time.
- After every merge and before each checkpoint, run
  `python3 -m scripts.sterling_validate <today> --check all` and act on FAILs by re-running the
  failing unit. Fan-out phases write `_batch_manifest.json` BEFORE spawning; the validator's
  `missing` list drives auto-gapfill (≤5 per batch, two rounds, then surface the residue).
- Workflow inputs are INTERPOLATED into the script text, never passed as `args` (they can arrive
  undefined — the 2026-06-08 cold-discovery failure). Missing input → STOP; cold mode only on explicit
  request. StructuredOutput schemas flat (spec §W).
- Decisions go to `sterling-run/decisions.json` ONLY, via the calibration schema WITH `stage`,
  `reason_code`, and the `forward`/`price_at_decision` block — no `.jsonl` side-logs, no
  double-logging. Calibration Part A is the sole writer.
- Invoke the skills; do not re-derive them loosely. If you author a workflow, each agent reads the
  tier's SKILL.md and obeys it verbatim (schema, lineage array, effort).

Setup: create runs/<today>. Read signals/this-week.csv, log/ (the carried-forward log), portfolio.csv.

Run, in order, invoking each skill BY NAME (re-read each skill from disk on use):

① THEME MAP — run `sterling-grid-tier0` as FOUR sessions, each its own subagent for its own attention
   budget: 0a Regime and 0b Discovery in PARALLEL (run as the `sterling-grid-tier0-research` deep-research
   workflow — parallel cross-checked web fan-out; BUILD THE CARRY DIGEST from log/ first and paste it
   verbatim into the workflow text per that skill's STEP 0 — never via args), then 0c Qualification &
   Scoring (incl. the regime-shift re-tag + the stage/precursor/window read), then 0d Vehicle Mapping
   (proxy rubric + mapping confidence + false_matches + BOTTLENECK WATCH). Inputs: log/ +
   signals/this-week.csv + last week's NEW-CLUSTER notes + holdings. Write the hunting brief + scored
   map to runs/<today>/tier0/ and UPDATE log/ (theme_map.json, benchmark_set, regime_log,
   discovery_log). The hunting brief (carrying the three theme-level lineage lines per theme) feeds
   Tier 1.

①b THEME HEALTH — after Tier 0, in parallel with ②: spawn one cheap subagent running
   `sterling-grid-theme-health` over portfolio.csv + the fresh theme_map. It emits the GREEN/AMBER/RED
   note per held theme (runs/<today>/tier0/theme_health_<date>.md) + appends log/theme_health.jsonl.
   INFORMATIONAL ONLY — never a sell (exits are the scanner's); RED/AMBER feed next week's 0c.

②③ TRIAGE + VERIFY — invoke `sterling-grid-triage` (the fan-out workflow). It runs the full STEP
   structure: manifest (tier1 batches ≤10) → tier1 fan-out → validate + auto-gapfill
   (sterling_validate --check counts --json; gapfill ≤5, two rounds) → merge → tier1_5 manifest (≤8)
   → tier1_5 fan-out → validate + auto-gapfill → RECALL AUDIT (one reviewer agent flags possible
   false-drops R1–R6 from the merged DROP log — reinstatement-only) → Checkpoint-A assembly.
   Write to tier1/ and tier1_5/. MERGE: ADVANCE → tier2 queue; DROP → decisions.json; NEW-CLUSTER →
   note for next week's Tier 0.
   (Optional: pre-tag obvious ticker→theme matches in code; send only ambiguous names to the skill.
   Fallback without workflows: run the same steps one batch at a time at the same ceilings.)

   ⏸ CHECKPOINT A — show me the merged ADVANCE list + the possible-false-drops block (R1–R6 flags)
   + the validator summary, and WAIT for approval before the expensive per-name work. Trim or
   reinstate on my instruction (approved reinstatements re-enter as a gapfill batch, Triage line
   annotated).

④ GATE — for EACH approved name, spawn an isolated subagent running `sterling-grid-tier2` on that
   name's card (+ theme map + holdings). Strong model, extended thinking ON. Write to tier2/. MERGE:
   ADVANCE cards (+ provisional type) → the Tier-3 DD queue; DROP → decisions.json. No sizing.

⑤ RECONCILE — IF a second selection pipeline also ran this week, spawn one subagent running
   `sterling-grid-tier2_5` with both pipelines' DD-progressed + dropped lists; it returns one ranked
   DD queue + a divergence log (→ decisions.json). IF only one pipeline ran, SKIP this step.
   (When to run a second pipeline at all: the trigger policy in the tier2_5 skill — default NO.)

⑥ DEEP DD — ONE name in the (reconciled) DD queue: run `sterling-grid-tier3` as FOUR SEQUENTIAL
   subagent sessions — 3a, then 3a-T (The Space: theme/space trajectory), then 3b, then 3c — each its own
   session, passing the typed handoff forward (3a dossier → 3a-T Theme/Space block → 3b geometry read →
   3c verdict + memo). TWO OR MORE names: invoke `sterling-grid-tier3-batch <TICKERS>` — the
   parallel-branch workflow that runs the same single-sourced logic, one isolated branch per ticker.
   The deep-research 3a sweep runs as `sterling-grid-tier3a-research` (which also carries the
   theme/space dimension that feeds 3a-T). Strong model, extended thinking ON, full web/deep-research
   on 3a AND 3a-T. 3a-T enriches the Evidence lineage line (no ninth element). Write the dossier, the
   theme/space block, geometry, memo, and decision record to tier3/<TICKER>/; validate lineage per
   branch (sterling_validate --check lineage). Names run in parallel ACROSS names.

⑦ BUY DECISION — spawn one subagent running `sterling-grid-tier4` on the WHOLE deep-dived batch (each
   3c dossier + lineage) + the held book + the Tier-0 map. It decides BUY / DO NOT BUY against the
   opportunity bar, full equal-weight, diversification at selection. Write the buy list + decision rows
   to tier4/.

   ⏸ CHECKPOINT B — show me the Tier-4 buy list and WAIT for approval before anything reaches the
   portfolio or the newsletter.

⑧ PUBLISH — for EACH confirmed BUY, run `sterling-grid-tier3d` to write its deep-dive article to
   articles/. Then run `python3 -m scripts.sterling_price_refresh` (rewrites Current/P&L% in
   portfolio.csv — the newsletter's only price source) and run
   `sterling-grid-newsletter` once for the week, then `sterling-grid-notes`.
   [If the newsletter / notes skills are not yet installed: write the 3d articles, then pause and tell
   me — I'll run the newsletter step manually.]

⑨ CLOSE — run `sterling-grid-calibration`. **Part A:** append every decision (buys + rejects + any
   technical SELL) to decisions.json WITH stage, reason_code, and the forward-snapshot block (the sole
   ledger; consolidate any stray side-logs into it), then run
   `python3 -m scripts.sterling_validate <date> --check decisions` — Part A owns ledger validity.
   **Part C (runs last):** `python -m scripts.sterling_weekly_close <date>` to
   build the operator report + the two tracking CSVs and write new buys / DD'd sells into portfolio.csv
   — the close ALSO MIRRORS the run into `research/<TICKER>/` (per-name view, status + decision
   history) and `weeks/<YYYY-WNN>/` (per-week view: newsletter, notes, deep-dives, decisions.csv) —
   idempotent, append-only.
   SAVE log/ (theme_map.json, benchmark_set, regime_log, discovery_log, theme_health.jsonl) for next
   week; check held names for the scanner's technical exit and flag any to sell in full.

Pacing: cap concurrent subagents so the run doesn't hit usage rate limits — a throughput limit, not a
reason to merge work into one context. Keep facts sourced in-session; never fill from memory. The
lineage block travels in every card — never let a tier re-derive an upstream line. Report a short
summary at each checkpoint, not a wall of text.
```

---

## 4. Recommended path

1. **Level 0 validation** — run a handful of this week's signals through Tier 0 → 1 → 1.5 → 2 → 3 → 4
   by hand. Confirm the cards hand off cleanly, the lineage accumulates, and a BUY / DO NOT BUY comes
   out the far end with a comprehensive memo.
2. **Level 1** — once the manual run looks right, drive the whole thing with the operator prompt.
   Claude Code suits the heaviest parallel fan-out and the scanner-script integration; Cowork suits
   the research connectors + checkpoints.
3. **Finish the publishing + calibration layer** — build `sterling-grid-newsletter`,
   `sterling-grid-notes`, and `sterling-grid-calibration` so steps ⑧ and the quarterly K.1 stop being
   manual — then **Level 2 schedule** the run.
```

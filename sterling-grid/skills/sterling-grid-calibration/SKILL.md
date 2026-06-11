---
name: sterling-grid-calibration
description: >-
  Sterling Grid Calibration Layer (V9) — the self-correcting loop and the last component. PART A
  (weekly) appends a normalized record for EVERY decision across all tiers to decisions.json — buys,
  DO-NOT-BUYs, and DROPs — with forward price snapshots; logging the rejects matters as much as the
  buys, since the reject cohort is how we measure whether we're too strict. PART B (quarterly, K.1)
  reads the matured log + forward prices and answers the governing question — are we catching the tail,
  holding winners, and containing losers, and are we too strict or too loose — proposing threshold
  changes as operator proposals, never auto-applied. The cardinal rule throughout: measure TAIL-
  CATCHING, NOT HIT-RATE. Never fabricate a price or date — pull it or leave it null.
  INVOCATION: invoked deliberately — Part A after each weekend session, Part B quarterly — by the
  pipeline orchestrator or the operator. NOT a keyword-triggered skill. On EVERY invocation, re-read
  this file and its reference files from disk; never run it from memory.
disable-model-invocation: true
allowed-tools: Read Write Bash WebSearch WebFetch
---

# Sterling Grid — Calibration Layer (V9): the log + K.1

## How this skill is invoked

Explicitly-invoked, looked-up-each-time. **Part A runs after each weekend session** (append the week's
decisions); **Part C runs LAST each weekend** (the weekly close: the operator report + the two tracking
CSVs + the portfolio buy/sell writes); **Part B (K.1) runs quarterly** on the matured log. On every run,
re-read this file and `references/` fresh from disk. Don't run it from topic keywords. Most of Part A and
all of Part C's numbers are mechanical and best done in **code** (`scripts/sterling_weekly_close.py` over
`runs/<date>/` + `decisions.json`).

## Read first — load the DNA

Load **`references/shared-context-dna.md`** (the §11 closing discipline — *tail-catching, not
hit-rate*; a high per-name failure rate is expected). The record schema and the K.1 output structure
are in **`references/card-schemas.md`**.

## The cardinal discipline (governs everything here)
**Measure tail-catching, not hit-rate.** In a concentrated venture book most names disappoint; the book
lives on the few 4–10x. A low win-rate with the tail captured is *working as designed* — never tighten
on it. The failure mode to fear is a **captured tail drifting into the reject cohort.**

---

## Part A — `decisions.json` (the log), after each weekend session
Append a normalized record for **every** decision across all tiers (schema in `card-schemas.md`;
enums in `references/handoff-card-spec.md` §0). **`sterling-run/decisions.json` is the canonical,
single ledger and Part A is its sole writer** — append here, never to parallel ad-hoc logs, and never
double-log a decision (exactly one record per decision). **Every record carries `stage` (the §0 id)
and `reason_code` (the §0 closed enum) plus the `forward` / `price_at_decision` block** — a
ticker-and-reason drop with no stage/code/forward fields is incomplete and defeats both the
newsletter's rejection-stage tagging and the whole calibration loop. If a run left stray side-logs
(e.g. `decisions_v9.jsonl`, `tier1_decision_log.jsonl`), Part A's first act is to **consolidate them
into `decisions.json` with the full schema and delete the strays.** **Part A owns ledger validity:**
run `python3 -m scripts.sterling_validate <date> --check decisions` before and after appending; fix
records at the source, never by hand-editing history.

- **Safety rule (read first):** output **valid JSON only**; **never fabricate a price, date, or figure**
  — pull it or leave it `null`. A wrong number here poisons every future calibration.
- **What to log, at what detail:** **BUY** → full record (type, conviction, the expected path). **DO NOT
  BUY** (deep-dived, not bought) → medium record (identity, price, reason, theme, bull-multiple if
  assessed); for close calls (a near-miss on path or catalyst timing) also enable forward tracking.
  **DROP** (cut before the deep dive, at Tier 1/1.5/2/2.5) → light record (ticker, date, price, reason);
  for close-call DROPs (a Tier-1 `4x? = MAYBE`) also enable forward tracking; obvious wrong-instrument
  DROPs need only the reason for the audit.
- **Forward snapshots:** capture `price_at_decision`, then fill `+3 / +6 / +12 / +18 / +24 / +36 mo` as
  each comes due — the longer points matter most (a 4x usually takes years). Track snapshots for all
  buys, all DO-NOT-BUYs, and close-call DROPs. `null` until due; **never back-fill from memory.**
- **`outcome` block** (exit price/date, reason, realized return) is written when the **scanner's
  technical exit** closes a position — that closes the loop and lets K.1 measure winner-holding and
  loser-containment.

---

## Part C — Weekly Close: the report + the tracking CSVs *(weekly, runs LAST — after notes)*

The final step of every weekend session. Part A logs the *decisions*; **Part C aggregates the whole week
into one operator report and two append-only tracking CSVs that build week over week**, then writes new
buys (and DD'd sells) into the portfolio. It introduces **no new analysis** — every number is parsed from
the week's `runs/<date>/` outputs + `decisions.json`; never fabricate a price.

**Canonical layout it assumes / enforces:**
```
sterling-run/runs/<YYYY-MM-DD>/
  tier0/ … tier4/   each tier's cards        articles/  3d · newsletter · notes · cards
  report/           the weekly report + this week's CSV slices
sterling-run/log/   cross-week STATE + the two master tracking CSVs
```
If a tier wrote outside its `runs/<date>/<tier>/` folder, flag it — clean layout is what keeps the CSVs
reproducible.

**Run the deterministic engine first (code, not the model):** `python -m scripts.sterling_weekly_close
<date>` — it parses the run, **appends** `log/theme_research_history.csv` and
`log/ticker_journey_history.csv` (+ the same rows as a that-week slice in `runs/<date>/report/`), saves a
dated `theme_map_<date>.json` snapshot, writes `runs/<date>/report/report_data.json`, **appends a
`portfolio.csv` row for any new Tier-4 BUY** (targets from the 3c geometry) and **marks the exit on any
DD'd Tier-4 sell**. Append-only: a new week only *adds* rows, never rewrites prior weeks. Outcomes come
from the run-dir tier outputs (authoritative for the week), never from same-dated ledger records of a
different run.

**Forward prices have ONE home — `decisions.json`.** The `px_*` columns on `ticker_journey_history.csv`
are **derived by this script from the decisions.json forward snapshots, never filled independently** — one
computation, written through to the CSV, so the ledger and the tracking sheet can't drift (the
single-ledger discipline extended to the tracking layer). Part B refreshes the snapshots *in
decisions.json*; the next weekly close re-derives the CSV columns from them.

**Then synthesise the narrative report** from `report_data.json` + the tier outputs →
`runs/<date>/report/weekly_report_<date>.md`: regime (0a) · the scored theme map by tier (0c) · the funnel
counts · each deep dive's verdict + the four scenarios/targets + prob-adjusted + catalyst window + decisive
bear (3c) · the Tier-4 capital decisions (BUY / DO-NOT-BUY / sell + opportunity-vs-RKLB) · rejections by
stage · the **portfolio snapshot from `portfolio.csv`** (held names + P&L + targets) · links to the
newsletter/notes. This is the operator's complete internal record, **distinct from the public newsletter**.
Schemas (report outline, the two CSV column sets, the `portfolio.csv` schema) live in
`references/card-schemas.md`.

---

## Part B — K.1 Calibration Retrospective (quarterly)
Reads the log + forward prices; proposes threshold changes as **operator proposals, never auto-applied.**

1. **Refresh snapshots** — update every open + tracked-reject record to its due interval; pull or mark
   stale, never fabricate.
2. **Cohort measurement (separate selection from execution):**
   - **Reject cohort** (DO NOT BUY / close-call DROP) — the **purest test of selection**, no execution
     noise. How many went on to ≥2x, ≥4x? **Tail in the rejects = too strict** — the single most
     important number in the system.
   - **Buy cohort** (BUY) — selection × execution: the return *distribution* (count the ≥2x and ≥4x, not
     just the average); **winner-holding** (did the scanner's exit let winners run, or did the trailing
     stop clip them early?); **loser-containment** (avg realized loss on failed buys — kept small?);
     **slugging / expectancy** (avg win × win-rate vs avg loss × loss-rate).
   - **Great-trade-typed buys** — the **one type where hit-rate matters** (the bar was "high
     confidence"): did the price reach ~3–4x (hit-rate should be *high*), average return, time-to-target;
     guard against **mislabeling** (great-trades behaving like coin-flips → the bar isn't being held →
     tighten it). (Type never affected size or slots — both uniform — so nothing to police there.)
   - **Name-level rubric calibration** (the V9.1 rubrics are starting placeholders — this is where they
     get evidence): **discriminator-mix tail-catching** — cohort the BUYs by scorecard mix (4-present /
     ≥1-partial / any-absent-where-needed) and compare forward distributions; the present-mix cohort
     should own the tail. **Conviction calibration** — Extremely Bullish vs Bullish forward
     distributions; indistinguishable → the 3c strike-count rubric isn't separating — propose a rubric
     tweak, not a threshold change. **Unresolved-binary cohort** — decisive_bear=unresolved-binary vs
     refuted/priced cohorts: are the binaries paying for their variance? **Concentration lens** —
     weeks Tier 4 flagged `heavy-tilt`: did marginal same-theme BUYs underperform the first BUY in
     that theme? (informational — no cap proposal, §5). **Recall-audit yield** — reinstated names
     (`recall_audit != null`) vs the drop cohort: is the audit catching real tails or noise?
   - **Theme-level calibration** (from `theme_research_history.csv` + the dated `theme_map_<date>.json`
     snapshots + `ticker_journey_history.csv`): the **axis-profile → outcome hit-table** (which 0c axis
     profiles at first-HUNT preceded ≥2x/≥4x names vs round-trippers — re-weights *attention*, never a
     numeric total); **lead-time validation** (realized precursor→re-rate leads vs the
     theme-intelligence §3 priors → propose prior updates, one at a time); **staging accuracy** (% of
     S1-tagged themes reaching S2 inside their stated `inflection_window` / stalled / died);
     **recognition-gate audit** (did STAND-DOWN cohorts stop producing ≥2x names — gate working — or
     keep producing — too early?); **proxy/mapping audit** (weak-proxy DROPs that went ≥2x = rubric too
     strict; VERIFIED-tag error rate; false-match recurrences prevented); the **cluster funnel** (born
     → promoted → Tier-2 survivor → buy; median weeks-to-promotion; **discarded clusters that later
     became real themes — the recall-miss number, the one that matters most**).
   - Break each down by **stage, archetype, and reason code.**
3. **Diagnosis** — per decision point + reason code, with a **minimum cohort size** (never tune on n=3):
   `WORKING / TOO-STRICT / TOO-LOOSE / INCONCLUSIVE`. *Too-strict:* multibaggers in the reject cohort; a
   reason code repeatedly cutting names that ran. *Too-loose:* a buy cohort full of dead money that never
   had a real shot; conviction not separating winners from losers. A timing lesson (stopped out, then it
   ran) is an **execution** finding (the stop layer), not a selection error — keep them separate.
4. **Recommendations (operator proposals)** — tie each to evidence; change thresholds **one at a time**,
   so the effect is attributable (e.g. "three `no-path` DO-NOT-BUYs are now ≥2x → loosen the Tier-2
   ≥4x-path bar"; "winners routinely exiting near 2x → revisit the scanner's exit rule — a system
   finding, not a selection one").
5. **Log health (the main job in the early quarters)** — until forward history matures (~the first 2–3
   quarters, longer for the ≥24mo points), K.1's primary output is verifying the log is **clean and
   complete**: every decision captured, rejects tracked, snapshots updating, nothing fabricated. Real
   tuning waits for matured cohorts; until then **bias to recall and keep logging.**

**Output:** the cohort tables (tail-focused) · the per-point diagnosis · the ranked recommendations
(proposals) · the refreshed log.

## Discipline (non-negotiable)
Tail-catching, not hit-rate · judge by cohort, never by survivors or anecdotes · minimum cohort size
before any conclusion · recommendations are proposals, thresholds move one at a time · never fabricate
prices (mark stale/missing) · separate selection errors from execution / timing errors.

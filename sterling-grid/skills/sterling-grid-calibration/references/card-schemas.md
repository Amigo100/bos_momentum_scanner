# Sterling Grid — Schemas (Calibration, V9)

> Part A appends one record per decision to `decisions.json`. Part B reads the matured log + forward
> prices and emits the K.1 retrospective. Never fabricate a value — pull it or leave it `null`.

## Part A — the `decisions.json` record (per decision)

Enums (stage ids · decision spellings · the closed reason-code list) live in
**`references/handoff-card-spec.md` §0** — that file governs. The machine check is
`python3 -m scripts.sterling_validate <date> --check decisions`.

```json
{
  "ticker": "",
  "date": "YYYY-MM-DD",
  "week_id": "YYYY-WNN",
  "stage": "tier1 | tier1_5 | tier2 | tier2_5 | tier3 | tier4 | exit",   // REQUIRED — spec §0 enum
  "tier": null,             // legacy field, kept for back-compat; `stage` governs
  "decision": "BUY | DO_NOT_BUY | DROP | SELL",   // canonical JSON spelling (prose may say "DO NOT BUY")
  "type": null,             // buys only: multibagger | great trade
  "conviction": null,       // buys only: Extremely Bullish | Bullish
  "reason": "",             // one line, calibration-checkable — the nuance
  "reason_code": "",        // REQUIRED on DO_NOT_BUY / DROP — the spec §0 closed enum
  "recall_audit": null,     // "R1".."R6" when the record was flagged/reinstated by the triage recall audit
  "concentration_flag": null, // BUYs only: Tier 4's heavy-tilt tag, copied by Part A
  "archetype": "V | G | N | ?",
  "theme": "",
  "price_at_decision": null,
  "thesis": {
    "bull_multiple": null,
    "bear": null, "base": null, "bull": null,
    "p_bear": null, "p_base": null, "p_bull": null,
    "target": null,
    "permanent_impairment_pct": null,
    "decisive_bear": ""     // refuted | priced | mispriced | unresolved-binary
  },
  "forward": { "p3": null, "p6": null, "p12": null, "p18": null, "p24": null, "p36": null },
  "outcome": {              // filled when the scanner's exit closes it
    "status": "open | closed | tracking-reject",
    "exit_price": null, "exit_date": null,
    "exit_reason": "",      // pivot-down | trailing-stop | hard-stop | still-open
    "realized_return_pct": null
  },
  "unverified": []
}
```
Detail by decision: **BUY** full · **DO_NOT_BUY** medium (+ forward tracking on close calls) · **DROP**
light (+ forward tracking on close-call `4x? = MAYBE`; obvious wrong-instrument needs only the reason).

**Backfill status (2026-06-11): DONE.** The 35 pre-V9.1 records were mechanically backfilled
(`stage` from legacy `tier`; spellings normalized; `price_at_decision`/`forward` added as null —
never fabricated; `reason_code` derived from unambiguous prefixes, else null — 5 rows carry an
acceptable null WARN). The original is preserved at `decisions.json.pre-backfill.bak`. **Two jobs
remain for Part A at the next run:** (1) consolidate the stray side-logs
(`log/decisions_v9.jsonl`, `log/tier1_decision_log.jsonl`) into the ledger and delete them;
(2) **known gap — the W23 (2026-06-07) SENS tier-3/tier-4 verdict rows were never appended**: append
them from `runs/2026-06-07/tier3/SENS/decision_record.json` + `runs/2026-06-07/tier4/decision_row_SENS.json`
(prices pulled-or-null, full V9.1 schema). Then this note retires.

## Part B — K.1 output structure
- **Cohort tables (tail-focused):** reject cohort (% → ≥2x / ≥4x — the purest selection read), buy
  cohort (return distribution, winner-holding, loser-containment, slugging), great-trade-typed
  (hit-rate, avg return, time-to-target), each broken down by stage / archetype / reason code.
- **Name-level calibration tables:** discriminator-mix tail-catching (4-present vs partial vs
  absent-where-needed cohorts → forward distributions) · conviction calibration (Extremely Bullish vs
  Bullish forward distributions) · unresolved-binary cohort vs refuted/priced cohorts · the
  concentration-lens read (marginal same-theme BUYs vs the first BUY in the theme) · recall-audit
  yield (reinstated `recall_audit != null` names vs the drop cohort).
- **Theme-level calibration tables** (from `theme_research_history.csv` + the dated
  `theme_map_<date>.json` snapshots + `ticker_journey_history.csv`): axis-profile → outcome hit-table ·
  §3 lead-time validation (realized precursor→re-rate leads vs the priors) · staging accuracy (S1 →
  S2 inside the stated window) · recognition-gate audit (did STAND-DOWN cohorts stop producing ≥2x?) ·
  proxy/mapping audit (weak-proxy DROPs that ran; VERIFIED error rate; false-match recurrences) ·
  the cluster funnel (born → promoted → Tier-2 survivor → buy; discarded clusters that later became
  real themes — the recall-miss number).
- **Per-point diagnosis:** `WORKING / TOO-STRICT / TOO-LOOSE / INCONCLUSIVE` (with a minimum cohort size).
- **Ranked recommendations:** operator proposals, evidence-tied, one threshold at a time.
- **Refreshed log:** every snapshot updated to its due interval (or marked stale).

## Part C — the weekly-close outputs *(align these with `scripts/sterling_weekly_close.py` — the script is the source of truth; this documents the intended shape)*

**`log/theme_research_history.csv`** (append-only; one row per theme assessed, per week):
`week_id, date, theme, sub_theme, tier_priority, stage, recognition, value_capture_grade, proxy_quality,
on_list_vehicles, surfaced_via, theme_score, verdict_note` — the week-over-week map of every theme we
scored and where it ranked.

**`log/ticker_journey_history.csv`** (append-only; one row per ticker per week it was touched):
`week_id, date, ticker, sector, theme, entered_at_tier, furthest_tier, decision (ADVANCE|DROP|BUY|DO_NOT_BUY),
reason_code, type, conviction, price_at_decision, target, px_3mo, px_6mo, px_12mo, px_18mo, px_24mo` — the
funnel journey + outcome for every name. **The `px_*` columns are DERIVED from `decisions.json` forward
snapshots by the weekly-close script, never filled independently** (forward prices live only in the
ledger; see Part C in `SKILL.md`).

**`sterling-run/portfolio.csv`** (THE single book — consolidated 2026-06-11; the newsletter's sole
price source AND the V10 scanner's exit-check anchor). 2 leading `#` comment lines + the real header:
`Ticker, Entry, Current, P&L%, Structural Force, Days Held, Type, Conviction, Bear, Base, Bull,
ProbAdjTarget, Catalyst Window, Entry Date` — a new Tier-4 BUY appends a row with its 3c targets and
`Entry Date` = the run anchor (written by the weekly close); a DD'd Tier-4 sell removes the row (the
exit lands in `decisions.json` as a SELL record with the outcome block). `Current`/`P&L%` are
refreshed by `scripts/sterling_price_refresh.py`; `Entry Date` drives the scanner's peak-close
derivation — never blank it.

**`runs/<date>/report/report_data.json`** — the machine-parsed numbers the narrative report renders.

**`weekly_report_<date>.md`** outline (operator's internal record, distinct from the public newsletter):
regime (0a) → scored theme map by tier (0c) → funnel counts → per deep-dive verdict + four scenarios/targets
+ prob-weighted + catalyst window + decisive bear (3c) → Tier-4 capital decisions (+ opportunity-vs-RKLB) →
rejections by stage → portfolio snapshot from `portfolio.csv` → links to newsletter/notes.

## Source
Part A reads each weekend's tier outputs (the DROP logs + the 3c/Tier-4 records). Part B reads the
matured `decisions.json` + refreshed forward prices (pulled, never fabricated).

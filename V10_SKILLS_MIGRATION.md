# V10 SKILLS MIGRATION — Claude Code Work Order

**Repo:** `bos_momentum_scanner` · **Date issued:** 2026-06-11
**Execute in order. One commit per phase. Run the acceptance check before ticking a task.**
**Do not invent doctrine: where a task says OPERATOR DECISION, stop and ask Alex.**

## Context (read once)

The scanner was rebuilt as **V10** (2026-06-11): entry = bare HMA(21) pivot low on a completed
weekly bar; exit = `tiered_initial_35` ONLY (−35% floor below +50% gain; trailing lock from peak
+50%→25% / +100%→20% / +200%→15%); **no HMA-down/pivot-down exit, no tiers T1–T6, no watchlist,
no sizing, no portfolio-manager writes**. New `signals_technical.json` schema: top-level
`scan_meta` (doctrine_version/asof/criteria), `stats`, `data_quality`, `buy_signals`,
`exit_flags` (replaces `sell_signals`). Prices pinned to **adjusted closes** (`auto_adjust=True`);
portfolio.csv entry prices must be on the adjusted basis; date-only rows get derived entries.
A **Track Record Standard v1.0** now governs the published record (Calls Ledger + Model NAV,
baseline restart, Monday-open entries, scanner-owned exits, DISCRETIONARY labels, append-only
corrections, generated tables).

The V9 skills bundle was reviewed in two halves. This work order encodes every finding.
A distribution **Roadmap** + a voice-grounded **`sterling-notes-generator`** skill (from a parallel
planning chat, June 2026) are integrated in Phase 6: the roadmap supersedes the GitHub-Actions
tweet pipelines and the 21-note card engine, and the generator's reference set becomes the single
voice layer for ALL published output.

---

## PHASE 0 — Inventory + audit of files not yet reviewed

- [ ] **0.1 Inventory.** List `.claude/skills/sterling-grid-*/` (SKILL.md + references) and
  `scripts/`. Confirm presence of: tier0 (main, 0a–0d), tier0-research, theme-health, triage,
  tier1, tier1_5, tier2, tier2_5, tier3 (main: 3a/3a-T/3b/3c), tier3a-research, tier3d, tier4,
  newsletter, notes, calibration, `scripts/sterling_validate.py`,
  `scripts/sterling_weekly_close.py`. Note anything missing or extra.
- [ ] **0.2 Audit the four never-reviewed components** with the same lens used on the rest:
  - **tier0 main (0c/0d):** does 0c implement the eligibility + recognition gates only (no extra
    gates)? does it derive `inflection_window` (see task 3.3)? does 0d emit the three theme-level
    lineage lines + mapping_confidence per vehicle?
  - **tier2_5:** confirm reconciliation is comparative ADVANCE-ranking only (no sizing, no new
    gates) and appends exactly one Consensus lineage element.
  - **tier3 main:** confirm 3a renders the discriminator scorecard with `absent (N/A: why)`
    handling; 3b produces decoupled floor/target + four scenarios + the §11 probability playbook
    with written shift rules; 3c asserts the 8-element lineage and emits the decision record with
    `stage/reason_code/price_at_decision/forward` fields; 3a-T enriches Evidence in place (no 9th
    element).
  - **the two scripts:** map every file/field each one reads or writes; this becomes the seam
    inventory used in Phases 1–2. Flag any read of `sell_signals`, `tier`, `position_size`,
    `quality_tier`, `signal_strength`.
- [ ] **0.3 Write `MIGRATION_AUDIT.md`** with 0.2's findings; add any new tasks it surfaces to
  this file before proceeding.
- [ ] **0.4 Console disposition** (`sterling-grid-v9_1-console.html`): move to `archive/` with a
  tombstone note — it predates the V9.1 enforcement layer and carries confirmed drift (pivot-down
  exit text AND a `pivot-down|trailing-stop|hard-stop` exit_reason enum in its decisions.json
  schema; legacy DD-1→DD-5 / 7-method football-field framing; a "benchmark set / watchlist"
  vocabulary slip). Tombstone maps its unique concepts to their new homes: CP-2A data refresh →
  weekly-close script (prices) + task 4.3 (per-holding thesis status); CP-1 chart prose → manual
  runbook input (5.2); "How to run each week" → RUNBOOK.md. Chat-mode fallback is documented as:
  attach the relevant SKILL.md + its references to the chat — never a second prompt copy.
  Also resolve the **frozen-library dangling pointer**: diagnostic-reference (and the console)
  defer the A–F return-driver taxonomy to a "frozen library" that exists in neither — locate the
  source document and check it into `references/frozen-library.md`, or strip the deferral
  sentence (V9 text already states the revenue-vs-catalyst split is all it needs). Optional,
  post-dry-run only: a thin doctrine-free cockpit (nav + checklist + commands, zero rules) if the
  dashboard is missed.

## PHASE 1 — The scanner→skills seam (blocking)

- [ ] **1.1 Build `scripts/make_week.py`** — the deterministic adapter:
  - Input: `signals_technical.json` (V10 schema). Output A: `sterling-run/signals/this-week.csv`
    with EXACTLY: `ticker, sector, last_price, week_date, uc, atr_rank, profile_confidence`.
    (`sector` + `profile_confidence` from enrichment; `signal_type`/`signal_strength` are
    RETIRED.) Output B: `sterling-run/signals/enrichment-cards/<TICKER>.json` — per signal:
    business_summary, market_cap, revenue + growth, cash, OCF, runway_months, dilution_yoy,
    flags, profile_confidence, plus the scanner's informational indicators (uc, rsi14,
    macd_cross_up, atr_rank/squeeze, momentum_4w, return_20d).
  - Acceptance: run on a real V10 output file; validator task 5.1 passes; no skill reads
    `signal_strength` anywhere (grep proves it).
- [ ] **1.2 Pipe enrichment into the funnel (the big efficiency win).**
  - tier1 SKILL.md: input gains the enrichment card; Method step 1 becomes "read the card first;
    search ONLY if `profile_confidence: low`, the card is stale, or the catalyst question is
    open." Batch subagent spawn text in triage SKILL.md updated to hand each batch its cards.
  - tier1_5 SKILL.md: fast-disqualifier scan consumes `runway_months`/`dilution_yoy`/flags from
    the card (KS-5 ≈ dilution_yoy); search budget drops 3–6 → **2–3 per name**.
  - Acceptance: both skills + triage reference the cards; budgets updated; no instruction to
    re-derive runway/dilution from filings when the card has them.
- [ ] **1.3 Retire `merge_decisions.py` / `saturday_workflow.py` + the GH-Actions tweet pipelines**
  (RESOLVED by Roadmap §2.5/§10 — no port needed): they read the dead V8 schema and their only
  live consumer (the tweet pipeline) is itself retired; X posts now come from the Sunday batch
  (Phase 6) into a scheduler. Move all to `archive/` with a tombstone note; disable the three
  persona GH-Actions workflows. The scanner's `twitter.signal_tracker` hooks stay (harmless
  try/except) until a later cleanup.
- [ ] **1.4 Pin yfinance** in requirements; add a README note: portfolio.csv entry prices live on
  the adjusted-close basis; after a split, blank the price and let the derived-entry fallback
  recompute from `entry_date`.

## PHASE 2 — V10 vocabulary + schema sync (mechanical sweep)

- [ ] **2.1 Grep sweep** across `.claude/skills/**` and `scripts/**` for:
  `pivot-down`, `pivot down`, `HMA exit`, `HMA-down`, `trend reversal`, `ExD`,
  `sell_signals`, `signal_strength`, `signal_type`, `quality_tier`, `tier_label`,
  `Tier [0-9] signal`, `position_size`, `watchlist`, `TIER_ALLOC`.
  Every hit is edited or justified in MIGRATION_AUDIT.md.
- [ ] **2.2 newsletter SKILL.md §3 Exits:** replace "a trend reversal or the trailing stop" with
  trailing-lock-only language (e.g. "the system's trailing lock or initial floor"). Keep
  indicator names out per voice rules.
- [ ] **2.3 calibration Part C:** "marks the exit on any DD'd Tier-4 sell" → "marks the exit on
  any scanner `exit_flags` entry executed at Monday open." Tier 4 never sells.
- [ ] **2.4 sterling_weekly_close.py:** read V10 `exit_flags` + `scan_meta` (not `sell_signals`);
  write portfolio.csv columns compatible with the scanner's read-only loader
  (`ticker,entry_date,entry_price,status[,exit_date,exit_price]`); adjusted basis throughout.
- [ ] **2.5 DNA:** add ONE line to §2 (mechanics-agnostic stays): "The current technical exit rule
  is the scanner's `tiered_initial_35`; the pipeline never needs its mechanics — see
  CHANGES_V10.md." Date the rule change (2026-06-11) so the reconciliation piece can cite it.

## PHASE 3 — Structural findings, part 1 (funnel layer)

- [ ] **3.1 §0 budget constants** in handoff-card-spec: `TIER2_MAX_PER_WEEK = 8`,
  `TIER3_MAX_PER_WEEK = 3`, new closed reason code `budget-overflow` (re-enters via a later scan
  like any DROP). tier2/tier3 queue writers enforce; triage Checkpoint A surfaces the overflow
  list for the operator's comparative cut. OPERATOR DECISION: who cuts when oversubscribed —
  default: operator at Checkpoint A, ranked by Tier-1.5 notes; never silently FIFO.
- [ ] **3.2 Move stray constants into §0:** the recall-audit R2 cap figure (`$1.5B`) out of triage
  SKILL.md; any others the 0.2 audit finds. §0 is the only home.
- [ ] **3.3 Inflection-window expiry rule** (tier0 main, 0c): window lapses with no precursor
  refresh → theme drops one priority tier automatically; two consecutive lapses → HOLD. Log the
  transition so K.1 can score the rule.
- [ ] **3.4 `price_at_decision` on every DROP row:** add to the §1 batch drop schema + tier1/1.5/2
  outputs (source: `this-week.csv last_price`); validator checks presence (task 5.1). The
  false-DROP cost ledger depends on this.
- [ ] **3.5 Tier-0 delta mode:** tier0-research gains an explicit weekly DELTA contract
  (constraint-chain re-checks + leading-indicator refresh on carried themes + NEW-CLUSTER intake);
  full three-stream discovery monthly or on `regime_shift: material`. Record
  `run_mode: delta|full|cold (explicit)` in `_run_context.json`.
- [ ] **3.6 tier3a-research fan-out cap:** cap parallel agents at the 7 evidence dimensions; note
  per-dimension search guidance (filings + comparable-winner are the costly ones).

## PHASE 4 — Structural findings, part 2 (publication layer)

- [ ] **4.1 Unify the voice layer into the notes-generator reference set** (target changed from a
  standalone voice-rules.md): `references/voice.md` = the house constraints (em-dash ban, no AI
  refs, no indicator names, structural forces, specific numbers, sentence variety,
  conviction/branding terms — "GREEN signal", "Extremely Bullish/Bullish" — tagline placement,
  British English) merged from the inline blocks in tier3d / newsletter / notes;
  `references/banned_patterns.md` = the anti-AI blocklist (port from the generator package). The
  three skills load these by reference; inline blocks shrink to "load voice.md +
  banned_patterns.md + skill-specific additions." Task 6.5 applies the adversarial pass.
- [ ] **4.2 Loss-language rule** (OPERATOR DECISION, recommended): in newsletter + notes, replace
  the ban on "loss/stopped out/down" with "state negative P&L plainly and factually; no
  melodrama, no euphemism." Rationale: credibility positioning post-reconciliation.
- [ ] **4.3 Holdings "under pressure" sourcing:** newsletter §3 renders ONLY (a) theme-health's
  dated per-holding row (status + finding) and (b) the BUY record's expected-path checkpoint from
  decisions.json. Add both to the newsletter's input list; no undated thesis claims.
- [ ] **4.4 Model-NAV weighting (OPERATOR DECISION, default proposed):** equal-weight across all
  open positions, rebalanced mechanically only at entry/exit events; N floats (no cap, matching
  Tier 4). Amend `track_record_standard_v1.md` wording (currently N=10) + the newsletter
  methodology footer. Alternative if rejected: fixed 10% slices + cash drag.
- [ ] **4.5 Monday-open entry fill:** weekly close writes new BUY rows with
  `entry_date = <Monday>` and `entry_price` blank; NEXT week's close fills the recorded Monday
  open from the same adjusted series. Scanner already tolerates date-only rows (derived-entry
  fallback covers the interim week). Document in the Standard's mechanics section.
- [ ] **4.6 Forward snapshots via yfinance, not web:** small script (or weekly-close flag) fills
  decisions.json `+3/+6/+12/...` snapshot prices from adjusted weekly closes — split-consistent
  with everything else. Calibration Part B's "pull it or leave it null" now means this script.
- [ ] **4.7 tier3d scenario cards:** delete the optional three-card (Bear/Base/Bull) parenthetical;
  the four-scenario render is the spec. Conditionalize the notes F3 "two parallel pipelines"
  example on a second pipeline actually running.

## PHASE 5 — Validator + runbook

- [ ] **5.1 Extend `sterling_validate`:** new checks — `--check seam` (this-week.csv column
  contract + enrichment card presence per signal), `--check budgets` (weekly T2/T3 counts vs §0),
  `--check drops` (every DROP row carries stage/reason_code/price_at_decision). Wire into the
  triage STEP 3 and weekly close call sites.
- [ ] **5.2 `RUNBOOK.md`** — one page, the weekly cadence end-to-end with the exact commands:
  Sat: scanner (`--asof <Fri>`) → make_week → tier0-research (delta) → tier0 main → theme-health
  ∥ triage → Checkpoint A → tier2 (≤8) → tier3a-research + tier3 (≤3) → tier4 → calibration Part A
  → weekly close → newsletter → notes → Part C report. Mark the two manual inputs (chart-analysis
  prose; Checkpoint-A review) and the Monday fill step.
- [ ] **5.3 Dry run:** execute the runbook on a frozen historical week (`--asof` a past Friday,
  tickers capped) end-to-end; fix what breaks; commit the run dir as the reference fixture.

## PHASE 6 — Distribution engine (Roadmap integration)

- [ ] **6.1 Install `sterling-notes-generator`** as a skill; port or scaffold its reference set —
  `references/voice.md` (from 4.1), `references/note_formats.md`, `references/banned_patterns.md`,
  `references/compliance.md`, `assets/output_template.md`, `config.yaml`. Copy any files Alex
  provides from the source chat; draft the rest and mark them DRAFT for his edit. `config.yaml`
  wiring: portfolio → `sterling-run/portfolio.csv` (**sole price source**; `decisions.json`
  accepted for theses/dates only), newsletter → newest `articles/weekly-screening-*.html`,
  archive → `articles/` + published exports, both seasonal slot tables (AEST/AEDT) carried.
- [ ] **6.2 Retire `sterling-grid-notes`** (the 21-note + per-note-card engine) → `archive/` with
  a tombstone; the generator (12 notes + 6 X posts + 3 article ideas + 4 reactive templates) is
  the weekly engine per Roadmap §4/§8. **OPERATOR DECISION — cards:** default NONE (the 90-min
  Sunday budget has no card step); option: keep ≤3/wk high-value templates (comparable-winner
  parallel, funnel) in an optional `references/cards.md`.
- [ ] **6.3 Voice corpus:** create `voice/corpus.md` seeded with 10–20 genuine Alex samples (the
  skill's hard gate — it must refuse below 10); add the monthly refresh rule (fold in the 2–3
  best-performing notes) to the runbook.
- [ ] **6.4 Compliance merge:** `compliance.md` carries the standing disclaimer text, the
  position-disclosure rule, no reader-directed buy/sell imperatives, and: **any performance claim
  must be reproducible from the Calls Ledger / `portfolio.csv`** (Track Record Standard tie-in).
  Paid-tier copy (when Stage 2 arrives) says "near-miss log + hunting brief," never "watchlist" —
  the doctrine has none.
- [ ] **6.5 Long-form anti-AI pass:** newsletter + tier3d load `voice.md` + `banned_patterns.md`
  and add a lightweight Step-4-style adversarial edit pass (blocklist scan + rhythm/variety check,
  rewrite-not-patch on failures) before output. This completes the humanization program.
- [ ] **6.6 Runbook additions (extends 5.2):** the Sunday distribution session — generate batch →
  30–40 min edit pass (hooks, ⚠ FACT-CHECK items) → schedule notes/X → mark the week's two
  ATTEND-LIVE slots → the 10-minute metrics check (net adds · source split · open rate ·
  restacks/note · rec referrals); newsletter send scheduled ~7–8am ET on publish day; seasonal
  slot-table switch noted for April/October.

## Done criteria
Grep sweep (2.1) returns zero unjustified hits · validator passes all checks on the dry run ·
the voice layer exists in exactly one reference set (voice.md + banned_patterns.md + corpus) ·
§0 contains every constant quoted anywhere · the dry-run week (5.3) also produces a passing
12-note batch from the generator · the OPERATOR DECISION tasks (3.1 overflow cut, 4.2 loss
language, 4.4 NAV weighting, 6.2 cards) have recorded answers in MIGRATION_AUDIT.md.

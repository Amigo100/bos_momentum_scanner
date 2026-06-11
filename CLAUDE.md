# CLAUDE.md — Sterling System

> Lean system documentation after the 2026-06-11 restructure.
> Everything retired lives under `archive/` (map in §3). Last updated: June 2026.

---

## 1. System identity

| Attribute | Value |
|-----------|-------|
| **Project** | Sterling System (scanner + sterling-grid skills pipeline) |
| **Purpose** | Weekly momentum scan → skills-driven research funnel → BUY / DO NOT BUY |
| **Newsletter** | [Sterling Signals](https://sterlingsignals.substack.com) |
| **Goal** | Catch early-lifecycle, high-growth themes at their inflection (RKLB-2024 / PLTR-2022 / Quantum-2024 pattern) and ride the best vehicles |

Three layers, strict division of labour:

1. **The V10 technical scanner** (`scanner/`) owns ENTRY and EXIT timing. Pure technical, $0 — no
   LLM. Entry: bare HMA(21) pivot low on a COMPLETED weekly bar (fires wide — the skills select).
   Exit: `tiered_initial_35` only (-35% hard floor below +50% gain; trailing locks from peak close:
   +50%→25%, +100%→20%, +200%→15%). The scanner READS the portfolio (never writes it) and flags
   exits; it supports `--asof YYYY-MM-DD` deterministic replay and `--tickers` ad-hoc checks.
2. **The sterling-grid skills** (canonical source `sterling-grid/skills/`, installed into
   `.claude/skills/` by `sh sterling-grid/install.sh`) own SELECTION — which flagged signal is a
   *real* buy. A 16-skill pipeline: Tier 0 theme research → triage → verification → deep-dive gate →
   deep DD → a binary, full-position **BUY / DO NOT BUY** (no sizing; V9 DNA in
   `sterling-grid/shared/shared-context-dna.md`).
3. **The state layer** (`sterling-run/`) holds everything the system knows: signals, runs, the
   decisions ledger, THE portfolio, per-ticker research, and per-week content.

## 2. The weekly cadence

```
FRIDAY after the close (LOCAL RUN — all automation removed 2026-06-12)
  python -m scanner.scanner --archive              # V10 scan: pivots + exit flags (read-only book)
  python -m scripts.sterling_signals_export        # → sterling-run/signals/this-week.csv
  → report prints to the terminal; email/WhatsApp summary only if §9 env vars set (--no-email skips)

WEEKEND (the skills run — sterling-grid/orchestration/run-pipeline.md, steps ①–⑨)
  ① Tier 0 theme map + hunting brief   ①b theme-health on held themes
  ②③ triage + verify (batched, validated, recall-audited)   ⏸ Checkpoint A
  ④ Tier 2 gate → ⑤ (reconcile) → ⑥ Tier 3 deep DD → ⑦ Tier 4 buy decision   ⏸ Checkpoint B
  ⑧ publish: 3d articles → python -m scripts.sterling_price_refresh → newsletter + notes skills
  ⑨ close: calibration Part A (ledger) → python -m scripts.sterling_weekly_close <date>
     — the close also MIRRORS the run into research/<TICKER>/ and weeks/<YYYY-WNN>/
     — exit flags from Friday's scan are acted on here (sell at next open; ledger SELL record)
```

Validation at every seam: `python -m scripts.sterling_validate <date> --check all`.

## 3. Repo layout

```
scanner/        scanner.py · sterling_indicators.py · enrichment.py · complete_tickers.txt · output/
scripts/        sterling_signals_export · sterling_validate · sterling_weekly_close · sterling_price_refresh
sterling-grid/  skills/ (the 16 CANONICAL skill sources) · shared/ (5 canonical refs) ·
                orchestration/ (run-pipeline, weekend-run) · install.sh (source → .claude/skills)
.claude/skills/ the installed runtime (gitignored; regenerate any time: sh sterling-grid/install.sh)
sterling-run/   THE STATE LAYER — see §6 (incl. THE portfolio.csv)
config/         output_paths.py · banned_terms.py
utils/          notifications.py (scan summary email/WhatsApp) · email_notifier.py
tests/          test_sterling_indicators.py (V10 suite) · test_integration.py (marketing-rule guard)
archive/        everything retired (see map below)
```

**Where did X go:**
2026-06-11 restructure — `archive/twitter-system/` (the tweet system; crons disabled) ·
`archive/workflows/` · `archive/dashboard-src/` ·
`archive/decision-loop-v8/` (saturday_workflow, merge_decisions, weekly_briefing, run_friday.sh) ·
`archive/substack_python_pipeline/` ·
`archive/scanner-output-history/` (pre-sterling weekly archives + the V8 analysis_log/signals) ·
`archive/content-history/` + `sterling-run/weeks/<id>/legacy/` (old content) ·
`archive/{docs,specs,logs,misc,portfolio-backups}/`. Rollback tag: `pre-restructure`.
2026-06-11 V10 consolidation — `archive/portfolio-v8/` (manager.py, backup_cleanup, the old second
book + equity/sheets/snapshot exports) · `archive/cowork-content-system/` (COWORK files,
settings.py, voice_rules.md, all of substack/) · `archive/docs/` (Sterling Prompt Library, handbook
v7, ARTICLE/VISUAL systems) · `archive/sterling-grid-bundle/` (superseded by sterling-grid/skills +
install.sh). Rollback tag: `pre-v10-integration`.
2026-06-12 local-only — ALL automation removed: every GitHub workflow disabled
(`friday_scan.yml` + `test_notifications.yml` YAMLs → `archive/workflows/`; `.github/` deleted) and
the 3 Claude scheduled tasks disabled (scanner-run, run-sterling-scanner, weekly-content-ideas).
The system runs only when you run it.

---

## 4. MARKETING LANGUAGE RULES (CRITICAL)

All public-facing content (newsletter, notes, posts) must follow these rules. The newsletter and
notes skills enforce them; `config/banned_terms.py` is the machine-readable registry
(tested by `tests/test_integration.py`).

### NEVER Reveal These Details (BANNED TERMS)

| Internal Term | Public Alternative |
|---------------|-------------------|
| "20% trailing stop" / "tiered stop" / "profit lock" | "Capital Preservation Protocol" |
| "HMA pivots" / "HMA slope" | "Structural Pivot Confirmation" |
| "Banker indicator" / "Banker rising" / "UC rising" / "Undercurrent" / "UC indicator" | "Institutional Accumulation Divergence" |
| "Beta >= 1.5" | "Volatility Expansion Criteria" |
| "Weekly BoS (Break of Structure)" / "ExD exit" | "Structural Trend Confirmation" |
| "Tier 1/2/3 classification" | "Conviction Rating" |
| "Gatekeeper" / "Investment Gate" | "The 5th Gate: Forensic Audit" |
| "Theme scoring" | "Sector Flow Analysis" |
| "Price cap" / "$25 cap" | "Universe filter" |
| "Gear shift" / "sizing gear" | "Position management" |
| "STRONG BUY" / "SPEC BUY" / "NO_GO" (verdicts) | "GREEN signal" / "GREEN signal (speculative)" |

**Also BANNED:** UK ISA, ISA account, GMT, BST, UK Time, RSI, MACD, KDJ, conviction 6-10 numeric values

### Approved Marketing Phrases

**System Description:**
- "Proprietary 5-gate screening system"
- "Filters 1,800 stocks to 3-5 actionable signals"
- "Institutional-grade momentum analysis"
- "Systematic approach that removes emotional bias"

**Signal Detection:**
- "Institutional Accumulation Divergence detected"
- "Structural Pivot Confirmation triggered"
- "Sector Flow Analysis alignment"
- "Forensic Audit cleared"

**Risk Management:**
- "Capital Preservation Protocol activated"
- "Systematic exit discipline"
- "Risk-defined position sizing"
- "The system protects capital so we live to fight another day"
- "No ego, just execution"

### US Audience Content Hooks

1. **Beat SPY** - Alpha over indexing, stop indexing start selecting
2. **Roth IRA** - Tax-free compounding, retirement account momentum
3. **PDT-Friendly** - No $25k requirement, weekly timeframe, 15 min/week
4. **Power Hour** - 15:30-16:00 ET market reaction, relative strength
5. **Sector Rotation** - Following institutional flows between themes

### Content Themes to Emphasize

1. **Following Smart Money** - Institutional flows, accumulation patterns
2. **Bottleneck Plays** - Infrastructure, supply chain, capacity constraints
3. **Theme Momentum** - Hot sectors, rotating capital, catalyst-driven
4. **Contrarian Opportunities** - Cold themes, oversold setups, patience plays
5. **Discipline Over FOMO** - Patience, systematic approach, no chasing

### Signal Color System

| Color | Emoji | Meaning | Public Name |
|-------|-------|---------|-------------|
| **GREEN** | 🟢 | BUY | GREEN Signal |
| **RED** | 🔴 | EXIT | Exit Alert |
| **CONSIDER** | 🟡 | WATCH | On Our Radar |

### Conviction Language

| Internal | Public Language |
|----------|-----------------|
| Extremely Bullish | Extremely Bullish (the only two conviction labels V9 emits) |
| Bullish | Bullish |
| Numeric conviction values | **NEVER** post publicly |

### Honesty Rules (Portfolio Transparency)

- Always show ALL positions — winners AND losers; show entry prices (full transparency)
- Frame losses positively: "Stop hit = system working as designed"
- When underwater: "Down but managing risk — disciplined exits in place"
- Celebrate big wins prominently (25%+, 50%+, 100%+); never hide or omit negative P&L

---

## 5. Command cheat sheet

```bash
# Friday (local run)
python -m scanner.scanner --archive              # full technical scan: pivots + exit flags
python -m scripts.sterling_signals_export        # → sterling-run/signals/this-week.csv
python -m scripts.sterling_signals_export --dry-run

# Weekend run helpers
python -m scripts.sterling_validate 2026-06-14 --check all      # lineage/counts/decisions/layout
python -m scripts.sterling_price_refresh [--dry-run]            # refresh sterling-run/portfolio.csv prices
python -m scripts.sterling_weekly_close 2026-06-14              # the close (+ research/weeks mirrors)
python -m scripts.sterling_weekly_close 2026-06-14 --mirror-only  # backfill mode (no history appends)

# Skills (edit in sterling-grid/, then install)
sh sterling-grid/install.sh                      # shared refs → sources → .claude/skills runtime

# Scanner extras
python -m scanner.scanner --asof 2026-06-05      # deterministic replay of any historical week
python -m scanner.scanner --tickers CRSP,TEM --no-email --no-enrich   # ad-hoc check

# Tests
python -m pytest tests/ -v
```

## 6. The sterling-run data layer

```
sterling-run/
├── signals/this-week.csv        # Tier-1 input — written by the Friday signals export (local run)
│   └── archive/                 # dated snapshots
├── log/                         # carried-forward state (Tier 0 reads + rewrites weekly):
│   theme_map.json · regime_log.jsonl · discovery_log.jsonl · benchmark_set.json ·
│   theme_health.jsonl · theme_research_history.csv · ticker_journey_history.csv
├── runs/<YYYY-MM-DD>/           # each run's tier0..tier4 cards + report/ + articles/
├── research/<TICKER>/           # ★ PER-TICKER VIEW (built by the weekly close, idempotent)
│   ├── index.json               #   status bought|held|passed|in-funnel + decision_history + runs
│   ├── runs/<date>/             #   memo.md · dossier · geometry · verdict · decision_record ·
│   │                            #   tier4_row · deep-dive.html (per deep-dived run)
│   └── deep-dive-legacy.html    #   pre-sterling DD article where one exists
├── weeks/<YYYY-WNN>/            # ★ PER-WEEK VIEW (built by the weekly close, idempotent)
│   ├── newsletter.html · notes.md · note-cards.html · deep-dives/ · report/
│   ├── decisions.csv            #   the week's ledger slice (ticker·stage·decision·reason_code…)
│   ├── manifest.json            #   week_id ↔ run_dates, buys/sells, what exists
│   └── legacy/                  #   pre-sterling content history (W04–W23 migrated)
├── decisions.json               # THE LEDGER — sole record of every decision (calibration Part A
│                                #   is its sole writer; V9.1 schema: stage + reason_code + forward)
├── portfolio.csv                # THE portfolio (see §7) — newsletter's SOLE price source AND the
│                                #   scanner's exit-check anchor (Entry Date, col 14)
└── fixtures/                    # synthetic plumbing fixtures for skill smoke tests
```

Seam contracts (batch ceilings, lineage encoding, file naming, workflow transport):
`sterling-grid/shared/handoff-card-spec.md`. Theme method (S0–S4 staging, P1–P4 precursors,
bottleneck migration, proxy rubric): `sterling-grid/shared/theme-intelligence.md`.

## 7. THE portfolio (one book)

`sterling-run/portfolio.csv` is the single book (consolidated 2026-06-11). 2 `#` comment lines +
14 columns: `Ticker, Entry, Current, P&L%, Structural Force, Days Held, Type, Conviction, Bear,
Base, Bull, ProbAdjTarget, Catalyst Window, Entry Date`.

- **The V10 scanner READS it** (never writes): `Entry` + `Entry Date` anchor the exit checks
  (peak-close derived from price history since entry — no mutable state).
- **`scripts/sterling_price_refresh.py`** rewrites only `Current`/`P&L%` (run before the newsletter).
- **The weekly close** appends a row for each Tier-4 BUY (3c targets + Entry Date = run anchor).
- ⚠ TEM and CRSP carry **defaulted** Entry Dates (2026-06-04, derived from Days Held) — correct them
  in the csv if the true entry dates differ.

## 8. Content system

Newsletter + notes are produced by the `sterling-grid-newsletter` and `sterling-grid-notes` skills
(self-contained; prices only from THE portfolio). The per-week record lands in
`sterling-run/weeks/<YYYY-WNN>/`. The old Cowork stack (COWORK files, prompt library, handbook,
article/visual systems, substack tools) is archived at `archive/cowork-content-system/` +
`archive/docs/`. The §4 marketing rules above remain binding on all published content.

## 9. Environment variables

```bash
# Notifications (optional — emailed scan summary when running locally)
export NOTIFICATION_EMAIL="alerts@yourdomain.com"
export SMTP_SERVER="smtp.gmail.com"; export SMTP_PORT="587"
export EMAIL_SENDER="you@gmail.com"; export EMAIL_PASSWORD="app-password"
export EMAIL_RECIPIENTS="you@gmail.com"

# Optional WhatsApp (Twilio)
export TWILIO_ACCOUNT_SID="AC..."; export TWILIO_AUTH_TOKEN="..."
export TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"; export WHATSAPP_TO="whatsapp:+1..."
```

No LLM API keys required — the scanner is pure technical; the skills run inside Claude Code.

## 10. Running it & troubleshooting

**No automation.** Every GitHub workflow is disabled (YAMLs in `archive/workflows/`; `.github/`
removed) and the Claude scheduled tasks are disabled — nothing runs unless you run it.

- **Friday scan** → run it yourself after the close: `python -m scanner.scanner --archive`, then
  `python -m scripts.sterling_signals_export`. The weekend run needs
  `sterling-run/signals/this-week.csv` — the export writes it.
- **Validator FAILs after a weekend run** → fix the failing agent's output and re-run that unit;
  never patch arrays/counts at persist time (handoff-card-spec §W).
- **yfinance rate limits** → wait 5–10 min or `--top 50`.
- **Where is anything old?** → `archive/` (see §3 map). Rollback point: git tag `pre-restructure`.

### Key indicator summary (internal — V10 doctrine)

Entry: bare HMA(21) pivot low on a COMPLETED weekly bar — fires wide, the skills select. Context
columns (RSI/MACD/UC/ATR) inform, never gate; the signals export tags strength from MACD cross-up /
UC rising. Exit: `tiered_initial_35` only — -35% hard floor from entry below +50% gain; above it, a
trailing lock from peak close (+50%→25%, +100%→20%, +200%→15%); decided on the weekly close, acted
at next open. No ExD, no HMA-down exit, no sizing. Formulas + thresholds live in
`scanner/sterling_indicators.py` (45 unit tests in `tests/test_sterling_indicators.py`).

*End of CLAUDE.md*

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

1. **The technical scanner** (`scanner/`) owns ENTRY and EXIT timing. Pure technical, $0 — no LLM.
   It flags ~30–60 weekly buy signals wide and checks held positions for technical exits.
2. **The sterling-grid skills** (`.claude/skills/sterling-grid-*`, master in `sterling-grid/`) own
   SELECTION — which flagged signal is a *real* buy. A 16-skill pipeline: Tier 0 theme research →
   triage → verification → deep-dive gate → deep DD → a binary, full-position **BUY / DO NOT BUY**
   (no sizing; V9 DNA in `sterling-grid/shared/shared-context-dna.md`).
3. **The state layer** (`sterling-run/`) holds everything the system knows: signals, runs, the
   decisions ledger, the portfolio, per-ticker research, and per-week content.

## 2. The weekly cadence

```
FRIDAY ~16:30 ET (automated — .github/workflows/friday_scan.yml)
  python -m scanner.scanner --archive          # signals + portfolio price/exit checks + sell email
  python -m scripts.sterling_signals_export    # → sterling-run/signals/this-week.csv (auto)

WEEKEND (the skills run — sterling-grid/orchestration/run-pipeline.md, steps ①–⑨)
  ① Tier 0 theme map + hunting brief   ①b theme-health on held themes
  ②③ triage + verify (batched, validated, recall-audited)   ⏸ Checkpoint A
  ④ Tier 2 gate → ⑤ (reconcile) → ⑥ Tier 3 deep DD → ⑦ Tier 4 buy decision   ⏸ Checkpoint B
  ⑧ publish: 3d articles → python -m scripts.sterling_price_refresh → newsletter + notes skills
  ⑨ close: calibration Part A (ledger) → python -m scripts.sterling_weekly_close <date>
     — the close also MIRRORS the run into research/<TICKER>/ and weeks/<YYYY-WNN>/
```

Validation at every seam: `python -m scripts.sterling_validate <date> --check all`.

## 3. Repo layout

```
scanner/        scanner.py · sterling_indicators.py · enrichment.py · complete_tickers.txt · output/
portfolio/      manager.py (canonical price/trade manager) · backup_cleanup.py · output/
scripts/        sterling_signals_export · sterling_validate · sterling_weekly_close · sterling_price_refresh
sterling-grid/  shared/ (5 canonical refs) · orchestration/ (run-pipeline, weekend-run) · sync-shared.sh
.claude/skills/ the 16 installed sterling-grid-* skills (gitignored — bundle is the tracked copy)
sterling-grid-bundle/  the distributable (skills + shared + orchestration + scripts + starter state)
sterling-run/   THE STATE LAYER — see §6
substack/       COWORK_INSTRUCTIONS.md · docs/ · tools/ (capture.py, carousel) · output/current/ (Cowork working area)
docs/           ARTICLE_SYSTEM_v2 · STERLING_VISUAL_SYSTEM_v2 · content_prompt_handbook_v7_0 · Sterling Prompt Library.html
config/         settings.py · output_paths.py · banned_terms.py · voice_rules.md
utils/          notifications.py (scan summary email/WhatsApp) · email_notifier.py
tests/          test_sterling_indicators.py · test_integration.py
.github/workflows/  friday_scan.yml · test_notifications.yml
archive/        everything retired (see map below)
```

**Where did X go (the 2026-06-11 restructure):**
`archive/twitter-system/` (the whole tweet system + its workflows' tests + state) ·
`archive/workflows/` (live_tweet, engagement-fetch, content_watchdog, saturday_workflow YAMLs — crons disabled) ·
`archive/dashboard-src/` (Next.js source; build artifacts deleted) ·
`archive/decision-loop-v8/` (saturday_workflow.py, merge_decisions.py, weekly_briefing.py, run_friday.sh — superseded by the skills pipeline) ·
`archive/substack_python_pipeline/` (constants, portfolio_visual, email/content scripts) ·
`archive/scanner-output-history/` (pre-sterling weekly archives) ·
`archive/content-history/` + `sterling-run/weeks/<id>/legacy/` (old content) ·
`archive/{docs,specs,logs,misc,portfolio-backups}/`. Rollback tag: `pre-restructure`.

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
# Friday (automated; manual equivalents)
python -m scanner.scanner --archive              # full technical scan + portfolio update
python -m scripts.sterling_signals_export        # → sterling-run/signals/this-week.csv
python -m scripts.sterling_signals_export --dry-run

# Weekend run helpers
python -m scripts.sterling_validate 2026-06-14 --check all      # lineage/counts/decisions/layout
python -m scripts.sterling_price_refresh [--dry-run]            # refresh sterling-run/portfolio.csv prices
python -m scripts.sterling_weekly_close 2026-06-14              # the close (+ research/weeks mirrors)
python -m scripts.sterling_weekly_close 2026-06-14 --mirror-only  # backfill mode (no history appends)

# Old BoS portfolio manager (still the canonical price fetcher)
python -m portfolio.manager --report             # view portfolio summary
python -m portfolio.manager --update             # refresh prices via yfinance
python -m portfolio.backup_cleanup --execute     # dedup backups (newest per week)

# Tests
python -m pytest tests/ -v
```

## 6. The sterling-run data layer

```
sterling-run/
├── signals/this-week.csv        # Tier-1 input — WRITTEN AUTOMATICALLY by the Friday workflow
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
├── portfolio.csv                # the sterling book — SOLE price source for the newsletter
│                                #   (refreshed by scripts/sterling_price_refresh.py)
└── fixtures/                    # synthetic plumbing fixtures for skill smoke tests
```

Seam contracts (batch ceilings, lineage encoding, file naming, workflow transport):
`sterling-grid/shared/handoff-card-spec.md`. Theme method (S0–S4 staging, P1–P4 precursors,
bottleneck migration, proxy rubric): `sterling-grid/shared/theme-intelligence.md`.

## 7. The two portfolios

| File | Owner | Role |
|------|-------|------|
| `portfolio/output/portfolio.csv` | `portfolio/manager.py` (via the Friday scan) | The technical book: prices, trailing stops/exits, Google-Sheets export, the Friday sell-signal email |
| `sterling-run/portfolio.csv` | the skills pipeline + `sterling_price_refresh` | The research book: held names + 3c targets; the newsletter's ONLY price source |

`portfolio/manager.py` stays whole — it is the canonical yfinance price fetcher
(`fetch_current_prices`) that `sterling_price_refresh` imports.

## 8. Content system (Cowork)

- `COWORK.md` (root) → `substack/COWORK_INSTRUCTIONS.md` — the Cowork session contract.
- Voice: `config/voice_rules.md` + §4 above. Current playbooks: `docs/ARTICLE_SYSTEM_v2.md`,
  `docs/STERLING_VISUAL_SYSTEM_v2.md`, `docs/content_prompt_handbook_v7_0.md`.
- Tools: `substack/tools/capture.py` (animated HTML → MP4), `substack/tools/carousel-template-v2.js`.
- Working area: `substack/output/current/` (posts/, notes/, diagrams/, carousels/, substack_posts/).
- The canonical published-content record per week: `sterling-run/weeks/<YYYY-WNN>/`.

## 9. Environment variables

```bash
# Notifications (Friday scan summary + failure alerts)
export NOTIFICATION_EMAIL="alerts@yourdomain.com"
export SMTP_SERVER="smtp.gmail.com"; export SMTP_PORT="587"
export EMAIL_SENDER="you@gmail.com"; export EMAIL_PASSWORD="app-password"
export EMAIL_RECIPIENTS="you@gmail.com"

# Optional WhatsApp (Twilio)
export TWILIO_ACCOUNT_SID="AC..."; export TWILIO_AUTH_TOKEN="..."
export TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"; export WHATSAPP_TO="whatsapp:+1..."
```

No LLM API keys required — the scanner is pure technical; the skills run inside Claude Code.

## 10. Workflows & troubleshooting

**Active workflows:** `friday_scan.yml` (Fri 21:30 UTC: scan → signals export → notify → commit)
and `test_notifications.yml` (manual dispatch). Everything else was disabled + archived.

- **Friday scan failed** → check the Actions run; the failure email fires automatically. Re-run via
  `workflow_dispatch`. The weekend run needs `sterling-run/signals/this-week.csv` — regenerate
  locally with `python -m scripts.sterling_signals_export` if needed.
- **Validator FAILs after a weekend run** → fix the failing agent's output and re-run that unit;
  never patch arrays/counts at persist time (handoff-card-spec §W).
- **yfinance rate limits** → wait 5–10 min or `--top 50`.
- **Where is anything old?** → `archive/` (see §3 map). Rollback point: git tag `pre-restructure`.

### Key indicator summary (internal)

Weekly entry: HMA(21) bare-pivot low on weekly bars; strength tags from UC rising / MACD cross-up /
V6 confluence. Exit: ExD signal or the tiered profit-lock trail (+200%→15%, +100%→20%, +50%→25%).
Full formulas live in `scanner/sterling_indicators.py` (63 unit tests in
`tests/test_sterling_indicators.py`).

*End of CLAUDE.md*

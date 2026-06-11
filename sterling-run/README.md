# sterling-run — the Sterling Grid working folder (state medium)

The pipeline passes FILES, not chat memory. This folder is that state. Drop it beside (or inside) the
repo where the `sterling-grid-*` skills are installed, and point the operator prompt at it.

```
sterling-run/
├── signals/this-week.csv     # the Tier-1 input — written by the Friday signals export (local run)
│   └── archive/              #   dated snapshots (this-week-<YYYY-MM-DD>.csv)
├── log/                      # the carried-forward log (Tier 0 reads + rewrites weekly)
│   ├── theme_map.json        #   {} on first run; Tier 0 fills it (+ theme-level lineage lines)
│   ├── benchmark_set.json    #   {} on first run
│   ├── regime_log.jsonl      #   empty on first run (0a appends)
│   ├── discovery_log.jsonl   #   empty on first run (0b appends; + cluster-candidate records)
│   ├── theme_health.jsonl    #   the weekly theme-health skill appends here
│   └── *_history.csv         #   theme_research / ticker_journey (the weekly close appends)
├── decisions.json            # THE LEDGER — every BUY / DO NOT BUY / SELL / DROP appends here
│                             #   (calibration Part A is the sole writer; V9.1 schema)
├── portfolio.csv             # held positions; SOLE price source for the newsletter
│                             #   (refresh: python -m scripts.sterling_price_refresh)
├── runs/<YYYY-MM-DD>/        # each run's cards (tier0..tier4, report/, articles/)
├── research/<TICKER>/        # ★ per-ticker view — every deep dive/verdict for a name across runs,
│   └── index.json            #   with status bought|held|passed|in-funnel (built by the close)
├── weeks/<YYYY-WNN>/         # ★ per-week view — newsletter, notes, deep-dives, decisions.csv,
│   └── legacy/               #   manifest; pre-sterling content history lives in legacy/
└── fixtures/                 # Phase-1 plumbing dry-run (synthetic; not investment data)
```

The weekly close (`python -m scripts.sterling_weekly_close <date>`) mirrors each run into
`research/` + `weeks/` idempotently; `--mirror-only` backfills without touching the append-only
history CSVs. See `FIRST-RUN.md` for the validation walkthrough.

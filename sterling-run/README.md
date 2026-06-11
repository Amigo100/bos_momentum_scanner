# sterling-run — the Sterling Grid working folder (state medium)

The pipeline passes FILES, not chat memory. This folder is that state. Drop it beside (or inside) the
repo where the `sterling-grid-*` skills are installed, and point the operator prompt at it.

```
sterling-run/
├── signals/this-week.csv     # scanner output — the Tier-1 input (replace the template)
├── log/                      # the carried-forward log (Tier 0 reads + rewrites weekly)
│   ├── theme_map.json        #   {} on first run; Tier 0 fills it (+ theme-level lineage lines)
│   ├── benchmark_set.json    #   {} on first run
│   ├── regime_log.jsonl      #   empty on first run (0a appends)
│   └── discovery_log.jsonl   #   empty on first run (0b appends)
├── decisions.json            # [] on first run; every BUY / DO NOT BUY / SELL / DROP appends here
├── portfolio.csv             # held positions; SOLE price source for the newsletter
├── runs/<YYYY-MM-DD>/        # this week's cards (tier0..tier4, articles) — created per run
└── fixtures/                 # Phase-1 plumbing dry-run (synthetic; not investment data)
```

See `FIRST-RUN.md` for the validation walkthrough.

# Sterling Grid — Skills (V9.1)

The Sterling Grid pipeline packaged as **16 explicitly-invoked, looked-up-each-time Claude Code
skills** plus the orchestration docs that sequence them. The funnel: ~30–60 weekly technical buy
signals → theme-aware triage → verification → the deep-dive gate → full deep DD → a comparative
**BUY / DO NOT BUY** capital decision (binary, full equal-weight positions, **no sizing** — entries
and exits both belong to the technical scanner).

## What's here

```
sterling-grid-skills/
├── README.md                       ← you are here
├── shared/                         ← the 5 CANONICAL refs (single source of truth — edit HERE):
│   ├── shared-context-dna.md       ←   the decision DNA (V9: binary, no sizing, recall→precision)
│   ├── lineage-block.md            ←   the report-handoff spine (the growing lineage array)
│   ├── diagnostic-reference.md     ←   the optional per-name toolkit (+ scenario playbook §11)
│   ├── handoff-card-spec.md        ←   seam contract: constants · envelope · lineage encoding ·
│   │                                   file layout · manifests · workflow transport (§W)
│   └── theme-intelligence.md       ←   the prospective wave method: S0–S4 staging · P1–P4
│                                       precursors (RKLB/PLTR/Quantum anchors) · lead-time priors ·
│                                       bottleneck migration · cluster lifecycle · proxy rubric
├── sync-shared.sh                  ← copies shared/* into every skill's references/ after an edit
├── skills/sterling-grid-*/         ← the 16 skills, each with SKILL.md + references/:
│     tier0 · tier0-research · theme-health · triage · tier1 · tier1_5 · tier2 · tier2_5 ·
│     tier3 · tier3a-research · tier3-batch · tier3d · tier4 · newsletter · notes · calibration
└── orchestration/
    ├── weekend-run.md              ← the weekend sequence (fan-out, isolation, merge, checkpoints)
    └── run-pipeline.md             ← the operator prompt + run hygiene (the V9 driver)
```

The deterministic helpers ship at the bundle root (`scripts/`): **sterling_validate** (lineage /
counts / decisions / layout checks at every merge), **sterling_weekly_close** (calibration Part C),
**sterling_price_refresh** (the pre-newsletter portfolio price refresh).

Each skill is **self-contained** — it carries its own copy of the shared references, so it stays
portable. To avoid drift, the canonical copies live in `shared/` and `sync-shared.sh` propagates
them: **edit once in `shared/`, run `./sync-shared.sh`, every tier inherits the change.**

## The invocation model — "looked up each time, not keyworded"

These skills are **not** auto-triggered. They are invoked **deliberately, one unit of work at a
time, by the orchestrator** (or by you explicitly running a stage). On every invocation the worker
**re-reads the skill's `SKILL.md` and its `references/` from disk** before acting — a tuned
framework is always applied from source, never from memory. The pipeline is stateless with fixed
handoff cards (the lineage array travels on every card; `sterling_validate` proves nothing was
dropped), so each step is a clean, isolated unit with undiluted attention and web budget.

## Running it

Follow `orchestration/weekend-run.md` (the sequence) and `orchestration/run-pipeline.md` (the
operator prompt + the non-negotiable run hygiene: batch ceilings and the lineage encoding live in
`shared/handoff-card-spec.md`; workflow inputs are interpolated, never passed as args; effort is set
and confirmed before any workflow spawns). First run: see `sterling-run/FIRST-RUN.md` and the
synthetic fixtures in `sterling-run/fixtures/` for a plumbing-only validation pass.

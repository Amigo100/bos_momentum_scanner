# Sterling Grid V9.1 — Start Here

Your systematic small-cap research pipeline, packaged as **16 explicitly-invoked Claude Code skills**
that chain together each week (incl. the weekly `sterling-grid-theme-health` TD sweep on held themes),
plus the state folder they read and write, the deterministic helper scripts (validator · weekly close
· price refresh), and a one-shot installer.

The skills come **pre-hardened**: each is manual-only (so Claude never auto-fires a stage), the
heavy-reasoning tiers carry effort overrides (Tier 3 runs at `xhigh`), and each has a scoped
`allowed-tools` set so it won't prompt you on every web search or file write.

---

## What's in this bundle

```
sterling-grid-bundle/
├── START-HERE.md                 # this file
├── setup.sh                      # one-shot installer
├── sterling-grid-skills/         # the 16 skills + editable master
│   ├── skills/sterling-grid-*/   #   the tiers (each with its own references/)
│   ├── shared/                   #   canonical DNA · lineage spec · diagnostic toolkit ·
│   │                             #   handoff-card-spec · theme-intelligence (5 files)
│   ├── orchestration/            #   weekend-run.md, run-pipeline.md
│   └── sync-shared.sh
├── scripts/                      # deterministic helpers, invoked as `python3 -m scripts.<name>`:
│                                 #   sterling_validate · sterling_weekly_close · sterling_price_refresh
└── sterling-run/                 # the working state folder
    ├── FIRST-RUN.md              #   the detailed validation runbook (per-step assertions)
    ├── signals/  log/  runs/  fixtures/
    ├── decisions.json  portfolio.csv
```

---

## Prerequisites

- **Claude Code** — the desktop app, an IDE extension, or the CLI (v2.1.154+ for Opus 4.8 + Dynamic
  Workflows). **No terminal required:** the app's own Bash tool runs the installer for you. Docs:
  https://docs.claude.com/en/docs/claude-code/overview.
- Your **`bos_momentum_scanner`** repo on disk.

---

## 1. Install (no terminal needed)

Save `sterling-grid-bundle.zip` and, using your file manager, drop it into your `bos_momentum_scanner`
repo folder. Then open that folder as your workspace in Claude Code and paste:

> Unzip `sterling-grid-bundle.zip` here, then run its installer against this repo
> (`sh sterling-grid-bundle/setup.sh .`). Show me the output, and confirm the 16 sterling-grid-* skills
> landed in `.claude/skills/` and that `.claude/settings.json` has `effortLevel: xhigh`.

Claude Code runs it with its Bash tool. The installer copies the 16 skills into `.claude/skills/`, the
editable master (`shared/` + `orchestration/` + `sync-shared.sh`) into `sterling-grid/`, the helper
scripts into `scripts/`, the working
folder into `sterling-run/`, and sets `effortLevel: xhigh` in `.claude/settings.json`. It skips files
that already exist, so it's safe to re-run. *(To refresh the skills outright on an update, ask it to
first delete `.claude/skills/sterling-grid-*` and `sterling-grid/` — that leaves `sterling-run` and any
other skills untouched — then run the installer.)*

*(Prefer a terminal? `unzip sterling-grid-bundle.zip && sh sterling-grid-bundle/setup.sh /path/to/bos_momentum_scanner` does the same.)*

---

## 2. Open and verify

Open the `bos_momentum_scanner` folder as your workspace in Claude Code and accept the
**workspace-trust dialog** — that's what activates the skills' `allowed-tools`. Then:

```
/skills
```

You should see all 15 `sterling-grid-*` skills. (Or just ask: "What skills are available?") If any are
missing, run `/doctor` to check the skill-listing budget.

**Effort is already handled.** `setup.sh` set `effortLevel: xhigh` in `.claude/settings.json`, so every
session in this repo — and every workflow sub-agent it spawns — runs at `xhigh` without you touching
`/effort`. Confirm it by the indicator next to the spinner ("with xhigh effort"). *(To set it manually
instead: type `/effort xhigh` once — the level is part of the command, there's no menu to wait for, and
on Opus 4.8 it persists across sessions.)*

---

## 3. Trial run, Phase 1 — synthetic plumbing

This proves the cards hand off cleanly and the lineage accumulates end to end, **without** spending
deep-research budget. It uses the synthetic fixture shipped in `sterling-run/fixtures/`. Run each tier
in its own turn, reading the card before the next:

```
/sterling-grid-tier1        → point it at sterling-run/fixtures/synthetic-signals.csv
                              and sterling-run/fixtures/synthetic-hunting-brief.md
/sterling-grid-tier1_5
/sterling-grid-tier2
/sterling-grid-tier3        → run 3a, then 3b, then 3c as separate invocations
/sterling-grid-tier4
```

You can pass a ticker as an argument, e.g. `/sterling-grid-tier3 TESTA`. After each step, check the one
handoff/lineage assertion listed in **`sterling-run/FIRST-RUN.md`**.

**Phase 1 passes when** the lineage block at 3c carries all eight lines — Macro, Theme, Mapping,
Triage, Gate, Evidence, Geometry, Verdict — and the 3c memo opens with the Macro -> Theme -> Mapping
framing.

---

## 4. Trial run, Phase 2 — real, small

Export this week's scanner output to `sterling-run/signals/this-week.csv` (columns below), then:

```
/sterling-grid-tier0        → run 0a, 0b, 0c, 0d as four turns; this bootstraps log/
                              and writes the hunting brief
```

Then take **one** ~10–15 batch through the chain: `tier1` -> `tier1_5` -> look at the ADVANCE list ->
`tier2` -> pick 1–2 -> `tier3` -> `tier4` -> `tier3d` on any BUY.

> **Batching on a full week.** The trial deliberately uses a single batch. A real week of ~30–60
> signals is split into **batches of ~10–15** at Tier 1 and Tier 1.5, each batch run in its own
> isolated context (in parallel), then merged by concatenation — never all 50 in one pass. Tier 1 and
> Tier 1.5 now refuse an oversized pass and split it themselves, and the orchestrator
> (`sterling-grid/orchestration/run-pipeline.md`) drives the split + parallel fan-out + merge. Tier 2
> is one or two names per session, Tier 3 one name per session, Tier 4 the whole deep-dived batch in one
> session. The batch fan-out is also a natural fit for a saved dynamic workflow if you want it automated.

> Run each tier in its **own session/turn**. A skill's content stays loaded for the rest of a session,
> so fresh sessions are how you get the clean per-name context the pipeline assumes — don't run a whole
> weekend in one ever-growing chat.

---

## The 15 commands

| Command | What it does |
|---|---|
| `/sterling-grid-tier0` | Theme & benchmark engine — four passes (regime, discovery, scoring, vehicle mapping); writes the hunting brief |
| `/sterling-grid-tier1` | Shape triage — ADVANCE / DROP |
| `/sterling-grid-tier1_5` | Batch verification — ADVANCE / DROP |
| `/sterling-grid-tier2` | Deep-dive gate — ADVANCE / DROP + provisional type |
| `/sterling-grid-tier2_5` | Cross-pipeline reconciliation (only if a second pipeline ran) |
| `/sterling-grid-tier3` | Deep due diligence — 3a evidence -> 3b geometry -> 3c verdict; **BUY / DO NOT BUY** + comprehensive memo |
| `/sterling-grid-tier4` | Comparative buy decision against the opportunity bar |
| `/sterling-grid-tier3d` | The Sterling Signals deep-dive article (self-contained HTML) |
| `/sterling-grid-newsletter` | "The Weekly Screening" (self-contained HTML) |
| `/sterling-grid-notes` | The week of Substack notes + image cards |
| `/sterling-grid-calibration` | Part A logs every decision; Part B is the quarterly K.1 retrospective |
| `/sterling-grid-tier0-research` | **Deep-research workflow** for Tier 0's macro (0a) + theme discovery (0b) — parallel, cross-checked |
| `/sterling-grid-tier3a-research` | **Deep-research workflow** for Tier 3a's single-name evidence sweep — parallel, adversarially cross-checked |
| `/sterling-grid-triage` | **Batch fan-out workflow** — splits the week's signals into batches of ~10–15, runs Tier 1 + Tier 1.5 as parallel subagents, returns the merged ADVANCE list (Checkpoint A) |
| `/sterling-grid-tier3-batch` | **Deep-dive orchestrator workflow** — runs a full Tier-3 deep dive (research-mode 3a → 3b → 3c) on each chosen survivor in its own isolated parallel branch; returns one verdict card per name for Tier 4 |

## Deep research (the depth, not a plain web search)

Tier 0's macro/theme discovery and Tier 3a's evidence sweep are the breadth-heavy passes. They run as
**dynamic workflows** — Claude orchestrates parallel subagents that fan search across angles, fetch and
cross-check sources, vote on claims, and return one cited result — the same shape as the chat's
Research mode, but codified and rerunnable. The two `*-research` skills above are the orchestration
specs; `/sterling-grid-tier0` and `/sterling-grid-tier3` delegate their research step to them.

To use them:
- **Enable workflows once:** `/config` → turn on **Dynamic workflows** (Claude Code v2.1.154+, any paid plan).
- **Trigger as a workflow:** with Dynamic Workflows on, the `*-research`, `triage`, and `tier3-batch` skills orchestrate automatically. If one runs in a single pass instead of fanning out into parallel agents, prefix *that* call with `ultracode` (e.g. `ultracode /sterling-grid-triage`) to force it — but don't leave `ultracode` on session-wide, or every command becomes a workflow. (Effort is already `xhigh` from settings; `ultracode` only adds the auto-orchestration on top.)
- **Watch it:** `/workflows` shows phases, agent counts, and tokens; you can pause or stop without losing completed work.
- **Save it for the weekly cadence:** in `/workflows`, select the run and press `s` to save it as a reusable `/command`.
- A workflow spawns many agents, so it costs more tokens than a chat turn — gauge on a narrow question first. With workflows off, both skills fall back to running inline at `xhigh` effort.

The same workflow machinery powers **`/sterling-grid-triage`**: it splits the week's signal list into
batches of ~10–15 and runs Tier 1 + Tier 1.5 as parallel subagents, handing back one merged ADVANCE
list (Checkpoint A) — so a 50-ticker week is never run in a single pass. Trigger and save it the same
way (`ultracode /sterling-grid-triage`, then `/workflows` → `s`).

---

## The two integration points you own

- **Signals in:** have `scanner/` write `sterling-run/signals/this-week.csv` with columns
  `ticker,sector,last_price,signal_type,signal_strength`.
- **Prices in:** a price-refresh must update the `Current` column in `sterling-run/portfolio.csv`
  before the newsletter runs — that file is the newsletter's only price source.

---

## Editing the shared logic later

The DNA, the lineage spec, and the diagnostic toolkit live once in `sterling-grid/shared/`. Edit there,
then propagate into every skill's `references/`:

```
sh sterling-grid/sync-shared.sh
```

---

## When the trial passes — automating

- **Level 1:** paste the operator prompt from `sterling-grid/orchestration/run-pipeline.md` and let
  Claude drive the whole chain (a subagent per batch and per name for the fan-out), pausing at the two
  human checkpoints.
- **Level 2:** wrap that prompt as a Claude Code scheduled task to run weekly.
- The full weekend sequence and the data-layer contract are documented in
  `sterling-grid/orchestration/weekend-run.md`.

One note on the manual-only setting: because each skill is `disable-model-invocation: true`, it won't
auto-preload into a subagent. That's correct for the manual trial. For Level 1 automation, the
orchestrator invokes the skill inside each forked subagent, or you preload it via a custom agent's
`skills` field.

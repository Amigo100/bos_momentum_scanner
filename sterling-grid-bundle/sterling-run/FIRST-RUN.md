# Sterling Grid — First Validated Run

Goal: prove the pipeline **plumbing** (every card hands off cleanly and the **lineage accumulates end
to end**) before you trust it with real capital decisions or schedule it. Two phases:

- **Phase 1 — synthetic plumbing dry-run** (fast, cheap, deterministic): validate the Tier 1 → Tier 4
  handoffs + lineage on a synthetic fixture, skipping Tier 0's deep research. Proves the *wiring*.
- **Phase 2 — real small run**: run Tier 0 on this week's real signals, take ONE batch through to a
  BUY / DO NOT BUY. Proves the *analysis* on real data.

Run it **Level 0 (manual)** — one skill at a time, reading each output before the next. This is the run
where your eyes are on every handoff; automation comes after it passes.

---

## Phase 0 — install + point at the state folder

1. **Install the skills (Claude Code).** Copy each `sterling-grid-*` folder into `~/.claude/skills/`
   (all projects) or `.claude/skills/` (this project). New session → `/skills` should list all 11.
2. **Place this folder.** Put `sterling-run/` beside (or inside) that repo. The chain reads/writes the
   files here.
3. **How a skill runs.** In Claude Code you invoke the skill (e.g. `/sterling-grid-tier1`) and give it
   the inputs; it loads its own `SKILL.md` + `references/` (the DNA, the lineage spec, the card schemas)
   from disk — you do **not** paste the Shared Context separately. *(In a plain chat you would paste
   `shared/shared-context-dna.md` first, then the skill, then the inputs.)*

---

## Phase 1 — synthetic plumbing dry-run (Tier 1 → Tier 4)

Inputs: `fixtures/synthetic-signals.csv` (TESTA/TESTB/TESTC) + `fixtures/synthetic-hunting-brief.md`
(one synthetic theme carrying the three theme-level lineage lines). **Tell each step: "synthetic
fixture — validate card shape + lineage only; skip live web grounding."**

Run each step, then check the assertion before moving on. ✅ = pass.

**1) Tier 1 (`/sterling-grid-tier1`)** — give it the synthetic signals + the synthetic hunting brief.
- Expect: a triage table (ADVANCE/DROP) + an ADVANCE payload per advanced ticker.
- ✅ Each ADVANCE card carries the **inherited Macro / Theme / Mapping lines copied verbatim** from the
  brief, **plus an appended `Triage` line** and a verify-first note. (No PURSUE/PARK; no sizing.)

**2) Tier 1.5 (`/sterling-grid-tier1_5`)** — give it the Tier-1 ADVANCE payload.
- Expect: a verification table sorting ADVANCE/DROP.
- ✅ The `Triage` line now reads `→ T1.5 ADVANCE · verify-question answered`. **No WATCH bucket.**

**3) Tier 2 (`/sterling-grid-tier2`)** — give it one ADVANCE card.
- Expect: ADVANCE (+ provisional type) or DROP.
- ✅ The ADVANCE card matches the **Tier-3a input schema** (provisional type multibagger/great-trade,
  rough path/asymmetry/survival, **open questions**, lineage) with an appended **`Gate` line**. **No
  band, no size.**

**4) Tier 3 — run as THREE sessions (`/sterling-grid-tier3`, phases 3a → 3b → 3c):**
- **3a** (give it the Tier-2 card): an evidence dossier. ✅ **`Evidence` line appended** (discriminator
  scorecard + survival/accounting reads + comparable anchor).
- **3b** (give it the 3a dossier): floor/target, four scenarios, velocity, **catalyst window**, type.
  ✅ **`Geometry` line appended** and the catalyst window is present.
- **3c** (give it the 3a dossier + 3b geometry): a **BUY / DO NOT BUY** verdict + the memo + the
  decision record. ✅ The **memo opens with the Macro → Theme → Mapping framing** (the comprehensive
  report, not a name note); **`Verdict` line appended** (with the catalyst window); the decision record
  uses the V9 schema — `decision`, `type`, `conviction`, `catalyst_window`, four scenarios, velocity,
  positioning, overshoot_anchor, and **no `size_pct` / `exit_regime` / `kill_criteria`**.

**5) Tier 4 (`/sterling-grid-tier4`)** — give it the 3c card(s) + an empty held book +
`fixtures/synthetic-hunting-brief.md` as the theme map.
- Expect: BUY / DO NOT BUY + the opportunity read (five dimensions, vs RKLB-2024).
- ✅ It reads the **catalyst window** for dimension 3; **`Decision` line appended**; a decision row in
  the `date,week_id,ticker,decision,type,conviction,opportunity_vs_RKLB,catalyst_window,reason` shape.

**6) (optional) Tier 3d on a BUY (`/sterling-grid-tier3d`)** — give it the 3a/3b/3c work.
- ✅ Self-contained HTML that **opens on the structural force** (from the lineage), renders **3a's
  discriminator scorecard** (not a 5-metric forensic battery) + **3b's methods-used valuation** + the
  four scenario cards, with **zero em dashes**.

**Phase 1 passes when** the lineage block at 3c contains all of: **Macro · Theme · Mapping · Triage ·
Gate · Evidence · Geometry · Verdict**, and the 3c memo renders Macro → Theme → Mapping → selection →
deep-dive → verdict. (Tier 2.5's `Consensus` line only appears when a second pipeline runs — skip it.)

---

## Phase 2 — real small run (Tier 0 → Tier 4)

1. **Export this week's scanner output** to `signals/this-week.csv` (replace the template; 30–60 rows).
2. **Tier 0 (`/sterling-grid-tier0`), four sessions:** 0a Regime ∥ 0b Discovery → 0c Qualification &
   Scoring → 0d Vehicle Mapping, off `log/` (empty on first run = bootstrap). Output: the scored map +
   the **hunting brief**. ✅ The hunting brief carries the **three theme-level lineage lines per HUNT
   theme**; `log/theme_map.json` is now populated for next week.
3. **One batch only.** Take ~10–15 real signals (one Tier-1 batch) and run **Tier 1 → 1.5**. ⏸ At the
   merged ADVANCE list, do **Checkpoint A** (eyeball it).
4. **Tier 2** on each ADVANCE name → pick **1–2** that ADVANCE to the DD queue. (**Skip Tier 2.5** — a
   single pipeline.)
5. **Tier 3** (3a → 3b → 3c as sessions) on those 1–2 names → the verdict + comprehensive memo.
6. **Tier 4** on the batch → BUY / DO NOT BUY. ⏸ **Checkpoint B** before anything is "real."
7. **Tier 3d** on any BUY → the article. *(Newsletter/notes are weekly aggregations — exercise them
   once you have a few weeks of `decisions.json` + a populated `portfolio.csv`.)*
8. **Close:** confirm every decision appended to `decisions.json` and `log/` saved for next week.

Run the **same assertions** from Phase 1 at each real handoff — plus, on real data, sanity-check that
3a pulled **primary sources** (not memory) and flagged unverifiable items `[UNVERIFIED]`.

---

## The validation checklist (what "passing" means)

- [ ] All 11 skills load (`/skills`).
- [ ] The chain reads/writes `sterling-run/` (signals in, cards in `runs/<date>/`, decisions appended).
- [ ] **Lineage inheritance:** a mapped name carries Macro/Theme/Mapping verbatim from the hunting brief.
- [ ] **Lineage accumulation:** by 3c the block holds Macro·Theme·Mapping·Triage·Gate·Evidence·Geometry·Verdict (·Decision after Tier 4).
- [ ] **No sizing anywhere:** funnel is ADVANCE/DROP; the buy gate is BUY/DO NOT BUY; type/conviction are labels; no `size_pct`/bands/caps/kill-criteria.
- [ ] **The 3c memo is the comprehensive report** (opens Macro → Theme → Mapping → … → verdict).
- [ ] **Catalyst window** travels 3b → 3c record → Tier 4's dimension 3.
- [ ] **3d adapts** (discriminator scorecard + methods-used valuation, not the legacy battery/football-field); zero em dashes; self-contained HTML.
- [ ] **decisions.json** records buys AND rejects (DROP/DO-NOT-BUY) with forward-snapshot fields ready.

If any assertion fails, it's a card-schema mismatch at that one handoff — fix that skill's
`card-schemas.md` (or its output section) and re-run that step; the isolation makes it easy to localise.

---

## After it passes
- Move to **Level 1**: paste the operator prompt from `sterling-grid-skills/orchestration/run-pipeline.md`
  and let it drive the full run, with Checkpoints A and B as approve-to-continue gates.
- Then **Level 2**: wrap that prompt as a Claude Code Routine to run weekly.
- Keep the early-quarter discipline: **bias to recall, log cleanly**; real K.1 tuning waits for matured
  cohorts.

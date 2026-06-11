---
name: sterling-grid-theme-health
description: >-
  Sterling Grid Theme Health (V9) — the weekly health check on HELD positions' themes. A cheap,
  bounded sweep (≤2 searches per theme, ~10–15 minutes total) that runs the TD-1…5 theme-death
  triggers against every theme the book currently holds and emits a GREEN / AMBER / RED note per held
  name. Purely informational: it is NEVER a sell trigger (exits are exclusively the technical
  scanner's), it never edits the theme map, and it adds no gate anywhere — a RED finding is an input
  to next week's Tier-0 0c, which may downgrade the theme (downgrades stop hunting NEW names only).
  It exists because TD triggers were previously checked only deep inside Tier-3a-T for names under
  DD, never weekly against what we already hold.
  INVOCATION: invoked deliberately, weekly, by the pipeline orchestrator AFTER Tier 0 writes the
  fresh map (it can run in parallel with Tier 1 — it feeds the operator, not the funnel). NOT a
  keyword-triggered skill. On EVERY invocation, re-read this file and its reference files from disk;
  never run it from memory.
disable-model-invocation: true
effort: medium
allowed-tools: WebSearch WebFetch Read Write Bash
---

# Sterling Grid — Theme Health (V9): the weekly TD sweep on held themes

## How this skill is invoked

Explicitly-invoked, looked-up-each-time, weekly — **after Tier 0** (it needs the freshly-updated
theme map), in parallel with Tier 1. One short session; this is deliberately the cheapest skill in
the system. On every invocation, re-read this file and `references/` fresh from disk.

## Read first — load the DNA and the vocabulary

Load **`references/shared-context-dna.md`** (§2 — exits are the scanner's, a theme downgrade is
never a sell; §9 current-info-only) · **`references/diagnostic-reference.md`** §6 (TD-1…5) ·
**`references/theme-intelligence.md`** §1/§5 (S-stage and recognition vocabulary this note speaks).

## Hard rules (the reason this skill is safe to run weekly)

1. **Never a sell trigger.** The output contains zero sell language and zero position
   recommendations. Sell only when the technical scanner flags an exit — no exceptions, no
   "consider trimming," no urgency framing.
2. **Never edits the theme map.** A RED is an *input* to next week's 0c, which may downgrade
   (downgrade = stop hunting new names, nothing more).
3. **Current sources only** (§9). Every finding carries a dated source or an explicit
   `no adverse evidence found`.
4. **Bounded budget.** ≤2 targeted searches per held theme; ~10–15 minutes total. This is a smoke
   detector, not a deep dive — anything that smells is escalated to 0c, not investigated here.

## Input

- `sterling-run/portfolio.csv` — the held rows (ticker + the **Structural Force** column = the theme).
- `sterling-run/log/theme_map.json` — the post-Tier-0 map (stage, recognition, capital momentum,
  regime_fit, Δ vs last week, value_chain, false_matches).
- `sterling-run/log/theme_health.jsonl` — last week's statuses (the carried baseline; first run: none).

## Method

1. **Map every held name → a tracked theme** via its Structural Force + the map's held/flagged
   lists. A holding that maps to no tracked theme is itself a finding —
   `ORPHAN — theme not tracked` — routed to next week's 0b as a discovery item (the book should
   never hold a theme the map can't see).
2. **Per unique held theme, run the TD sweep** — one targeted check each, from current sources,
   cross-read against the map's weekly Δ:
   - **TD-1 mechanism-class abandonment** — anchor buyers cancelling/pivoting off the mechanism
     class (not one lost deal: the *class*).
   - **TD-2 regulatory disqualification** — fresh regulatory action against the class.
   - **TD-3 capital-flow reversal** — the map's capital-momentum Δ turning + funding/raise
     headlines confirming capital leaving.
   - **TD-4 superior investable liquid proxy** — the strict three-condition test against the map's
     vehicle set (never fires against the category leader itself).
   - **TD-5 secondary-ticker crowding** — issuance/secondary wave across the cohort.
3. **Status per theme:** **GREEN** — nothing firing. **AMBER** — partial or unconfirmed evidence on
   any TD, or ≥2 adverse map Δs this week (e.g. capital momentum weakening + recognition jumped a
   stage). **RED** — ≥1 TD firing on primary-source evidence. Note the week-over-week transition
   (GREEN→AMBER is the news, not AMBER itself).

## Output

**(a) The health note** → `sterling-run/runs/<date>/tier0/theme_health_<date>.md`:

```
THEME HEALTH — <date>   (informational; exits remain the scanner's)
| Ticker | Theme | Status (Δ vs last wk) | Finding (dated) | What would escalate it |
one row per held name; themes shared by several names get one finding block.
ORPHANS: [names whose theme the map doesn't track → 0b]
```

**(b) The carried log** — append one record per held theme to `sterling-run/log/theme_health.jsonl`:

```json
{"date": "YYYY-MM-DD", "week_id": "YYYY-WNN", "theme": "...", "held_tickers": ["..."],
 "status": "GREEN|AMBER|RED", "delta": "GREEN->AMBER", "td_flags": ["TD-3 partial"],
 "basis": "one line, dated", "sources": ["url"]}
```

**(c) Escalations** — RED/AMBER themes listed in one line each for next week's 0c step-1 refresh
(and, if a holding is an ORPHAN, for 0b discovery). Nothing else moves.

## Self-check
- Every held name mapped to a tracked theme or flagged ORPHAN?
- Every held theme: all five TDs checked, each with a dated source or an explicit no-evidence line?
- Zero sell language, zero map edits, budget respected?
- `theme_health.jsonl` appended with this week's record per theme?

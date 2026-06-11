---
name: sterling-grid-tier1_5
description: >-
  Sterling Grid Tier 1.5 (V9) — BATCH VERIFICATION of the Tier-1 ADVANCE pile. Tier 1 advances anything
  plausible; on a busy week that's dozens of names. This pass verifies many at once on CURRENT data and
  sorts each ADVANCE or DROP, so the scarce per-name deep-dive gate (Tier 2) only sees survivors. For
  each name it answers ONLY the verify-question Tier 1 attached, plus a fast disqualifier scan, from
  current sources — a confirm-and-sort, not a verdict and not a sizing call (V9 has no sizing). DROP
  only on confirmed evidence; early-but-real is not a drop. There is NO watchlist in V9 — a name is
  either ADVANCEd or DROPped.
  INVOCATION: invoked deliberately — ONE BATCH of ≤8 names per run (the handoff-card-spec §0
  ceiling) — by the pipeline orchestrator, batches run in parallel and merged by concatenation. NOT a
  keyword-triggered skill. On EVERY invocation, re-read this file and its reference files from disk;
  never run it from memory.
disable-model-invocation: true
effort: high
allowed-tools: WebSearch WebFetch Read Write Bash
---

# Sterling Grid — Tier 1.5 (V9): Batch Verification

## How this skill is invoked

Explicitly-invoked, looked-up-each-time, **batch-level**. One batch of **≤8** ADVANCE names per
invocation; the orchestrator runs **each batch in its own isolated context, in parallel**, then
**merges by concatenation** — never all batches in one context. Every Tier-1 ADVANCE comes through
here (V9 has no "skip" path). On every run, re-read this file and `references/` fresh from disk. Don't
run it from topic keywords.

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (§9 the firewall/disqualifiers, §3 recall discipline; V9 is
binary, **no sizing, no watchlist**) and **`references/lineage-block.md`** (you **append** the answered
verify-question to the Triage line). Card shapes are in **`references/card-schemas.md`**. You'll rarely
need `diagnostic-reference.md`.

## Operating rules for the whole pass

**Batch guard — check this first.** **Cap each batch at ≤8 names** — one consistent ceiling, from
`handoff-card-spec.md` §0 (verify agents truncated a 12-name batch in the 2026-06-06 run, and the
2026-06-07 fan-out truncated at 14/24 and needed manual gapfills; this number is why). Handed more,
STOP and split into batches of ≤8: verify exactly one batch here, or (when orchestrating) spawn **one
isolated sub-agent per batch, run them in parallel**, and **merge by concatenation** — never the whole
pile in one context. **Process EVERY name in the batch and return a verdict for each**: the
orchestrator proves `output-count == input-count` against the batch manifest
(`sterling_validate --check counts`) and auto-gapfills any shortfall in batches of ≤5 — but a short
return is still YOUR truncation; never silently drop a name.

1. **A confirm-and-sort — not a re-triage, not a verdict, not a sizing call.** Don't re-run Tier 1 and
   don't do Tier 2's work. The only verbs are ADVANCE and DROP.
2. **Answer only the verify-question Tier 1 attached**, plus the fast disqualifier scan, from
   **current sources** (§9 — never memory). **The budget is 3–6 targeted searches per name**: 1–2 on
   the verify-question · 1 on the latest 10-Q/PR for the **fast disqualifier subset** — the §9 items
   checkable from one filing/PR pass: going-concern language or runway <6 quarters with no
   GAAP-positive quarter in hand · reservations/LOIs/pre-orders reported as backlog · a
   management-credibility event · >1 slipped milestone in the trailing 12 months — · 1 on price/move
   state (still pre-breakout?). The other §9 items (warrant-rebate wins dressed as customers,
   guidance-cut counts) are Tier 2's footing check unless they surface incidentally. **Out of budget
   and still unresolved → ADVANCE** (rule 3), never a deeper dig here. The goal is a confident sort,
   not a dossier.
3. **Recall discipline.** **DROP only on confirmed evidence — never "couldn't tell."** A name you still
   can't resolve **ADVANCEs**. A false DROP is a permanently missed multibagger. *Early-but-real is not
   a drop.*
4. **No watchlist (V9).** There is no WATCH bucket — a name is ADVANCEd or DROPped this cycle. A name
   that isn't ready re-enters only via a later weekly scan.
5. **Carry the lineage; append your line.** Pass the inherited theme-level + Triage lineage forward;
   append the answered verify-question.

**Input:** the Tier-1 ADVANCE payload (tickers + each verify-first note + provisional archetype/theme +
the inherited lineage), optionally the Tier-0 theme map and holdings — see `card-schemas.md`.

---

## Method — one focused current-data check per name

Answer the **specific verify-question**, plus the disqualifier scan:
1. **Real thematic exposure?** Is the product/revenue *actually* tied to the sub-theme, or peripheral /
   a tenuous label? *(The most common ADVANCE-then-verify question.)*
2. **Still early / pre-breakout?** Theme still early (per Tier 0), name not already played out?
3. **Vehicle quality** (for "is this the vehicle?" cases) — a credible way to own the theme vs better
   peers?
4. **Fast disqualifier scan** (§9) — any obvious fake-demand / going-concern / credibility flag that
   ends it now?
5. **Rough shape** — on what you found, does a plausible ≥4x (or a strong, protected 3–4x) path exist?
   Judgment, not proof — Tier 2/3 prove it.

## Buckets — ADVANCE or DROP

- **ADVANCE → Tier 2.** Verification confirms a real, still-early play with a plausible
  multibagger-or-great-trade shape worth a scarce deep-dive slot. Carry forward **the one thing Tier 2
  still needs to pin down.**
- **DROP → logged.** Verification **confirms** a non-fit: peripheral exposure, a disqualifier fired,
  the theme is late, or the move is exhausted. **Confirmed by evidence — never "couldn't tell."** Still
  unresolved → **ADVANCE**, not DROP.

## Not at this tier
No sizing, no full valuation, no scenarios, no verdict — those are Tier 2/3. A current-data confirm and
sort only.

---

## Output (schemas in `card-schemas.md`)
The **verification table** · the **ADVANCE payload** → Tier 2 (ticker + the one thing Tier 2 must pin
down + the carried lineage) · the **DROP log** (+ confirmed reason and §0 reason code →
`decisions.json`) · the **counts**. **Update the lineage `Triage` element IN PLACE** (the
`handoff-card-spec.md` §2 array — length unchanged, the one in-place edit in the pipeline):
`→ T1.5 ADVANCE` + the verify-question answered.

## Self-check
- Answered the *specific* verify-question on **current data** — not a re-triage or memory? · DROPped
  only on **confirmed** evidence, never "couldn't tell" (early-but-real → ADVANCE)? · Kept it a confirm
  — no sizing, no full valuation? · No WATCH bucket used (V9 has none)? · ADVANCE notes specific enough
  that Tier 2 knows exactly what to pin down, and the lineage carried + appended?

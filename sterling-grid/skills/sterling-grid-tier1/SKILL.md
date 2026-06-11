---
name: sterling-grid-tier1
description: >-
  Sterling Grid Tier 1 (V9) — fast, recall-biased SHAPE TRIAGE of a batch of ≤10 tickers from the
  week's technical signal list, grounded in current facts via a quick targeted web check. For each
  name: ground it in current facts, make the bull case in its own terms, map it to a theme (inheriting
  that theme's lineage, or flagging a NEW-CLUSTER), tag a provisional V/G/N archetype, judge whether a
  credible ≥4x path could plausibly exist, and bucket it ADVANCE or DROP. Not a buy decision and not a
  sizing call (V9 has no sizing) — it decides what deserves a closer look, losing nothing asymmetric.
  ADVANCE → Tier 1.5 batch verification; DROP only on a staleness-proof structural fact or what a
  search actually showed.
  INVOCATION: invoked deliberately — ONE BATCH of ≤10 tickers per run (the handoff-card-spec §0
  ceiling) — by the pipeline orchestrator, batches run in parallel and merged by concatenation. NOT a
  keyword-triggered skill. On EVERY invocation, re-read this file and its reference files from disk;
  never run it from memory.
disable-model-invocation: true
effort: high
allowed-tools: WebSearch WebFetch Read Write Bash
---

# Sterling Grid — Tier 1 (V9): Shape Triage

## How this skill is invoked

Explicitly-invoked, looked-up-each-time, **batch-level**. One batch of **≤10** tickers per invocation
(the `handoff-card-spec.md` §0 ceiling — a 12-name batch content-truncated a card in the 2026-06-07
run; drop the size further if a week's list needs heavy searching). The orchestrator splits the week's
signals into batches and runs **each batch in its own isolated context, in parallel**, then **merges
by concatenation** — never all batches in one context (that reintroduces the dilution batching
avoids). ≤10 is small enough that each name gets a real bull-case-in-its-own-terms, not a rushed skim.
On every run, re-read this file and `references/` fresh from disk. Don't run it from topic keywords.

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (V9 — §3 recall at discovery, §6 the V/G/N lens, §8 themes
top-down + bottom-up; the model is binary BUY / DO NOT BUY with **no sizing**) and
**`references/lineage-block.md`** (you **inherit** a name's theme-level lineage and **append** the
Triage contribution). Card shapes are in **`references/card-schemas.md`**. You'll rarely need
`diagnostic-reference.md` here — Tier 1 is fast triage, not depth.

## Operating rules for the whole pass

**Batch guard — check this first.** Never triage more than **10** names in one pass (handoff-card-spec
§0). Handed more, STOP and split into batches of ≤10: process exactly one batch in this pass, or (when
orchestrating) spawn **one isolated sub-agent per batch, run them in parallel**, and **merge by
concatenation**. ≤10 keeps each name's bull-case real rather than a rushed skim; a single 40–50-name
pass is precisely the dilution batching exists to prevent. Drop the batch size further if the week's
list needs heavy searching — and **return a verdict for EVERY ticker handed to you** (ADVANCE / DROP /
HELD, never silence; the orchestrator proves coverage against the batch manifest).

1. **Recall at discovery — you are not deciding to buy or to size.** You decide what deserves a closer
   look. A false ADVANCE dies cheaply at Tier 1.5 / Tier 2; a false DROP is a permanently missed
   multibagger. Cheap and high-recall by design. There is no sizing anywhere — the only verbs here are
   ADVANCE and DROP.
2. **Ground every judgment in current facts, never stale memory** (§9). The screener flagged these on
   *recent* action, so the catalyst that matters is often newer than training data.
3. **Bull case before checklist.** Make the strongest honest case for each name *in its own terms*
   before judging it. Frameworks challenge a thesis; they never license rejecting a name for not
   ticking boxes.
4. **Confirm before you cut.** A DROP must rest on a staleness-proof structural fact or on what a quick
   search *actually showed* — never an untested prior. Didn't check and not structurally ruled out →
   you cannot DROP it.
5. **Web here is identity + thematic fit only** — what it does now and whether there's a live angle.
   Not the Tier-2 conviction pull or a Tier-3 deep dive.
6. **Inherit the theme-level lineage; append your element.** When you map a name to a theme, copy that
   theme's Macro / Theme / Mapping lineage lines from the Tier-0 hunting brief **verbatim** (don't
   re-derive macro/theme) — emitted as the canonical ordered array of `{stage, line}` objects
   (`handoff-card-spec.md` §2; a dict-keyed lineage entered the 2026-06-07 cards here and broke the
   downstream length checks). Carry the vehicle's **mapping-confidence tag** with the Mapping line;
   your identity check (method step 1) upgrades an UNVERIFIED mapping to VERIFIED — or exposes a
   false match (a confirmed false match is a valid DROP, reason `false-match`, and feeds the theme's
   `false_matches` list via the batch summary). For a NEW-CLUSTER name the top-down map hasn't named,
   carry the cluster as the provisional theme and flag it for Tier 0 (the theme-intelligence §6
   ledger: ≥2 names on one mechanism births a tracked cluster-candidate with promotion criteria).
   Append the Triage element.

**Input:** a batch of ≤10 tickers from the canonical signal list
**`sterling-run/signals/this-week.csv`** (columns `ticker, sector, last_price, signal_type,
signal_strength`) — read **this file**, not a bare ticker dump, and actually **use `sector` in the
identity/fit read and `signal_strength` in the recall tilt; do not discard them** — plus the **Tier-0
hunting brief** (carrying, per theme, the three theme-level lineage lines), optionally holdings — see
`card-schemas.md`.

---

## Method — for each name, in this exact order

1. **Ground it in current facts.** For any name you can't confidently place *as of today* — and
   **always before you would DROP one** — run a quick search: what does it do *now*, and what's its
   most recent material catalyst/news (last ~3 months)? A current-identity-and-catalyst check is
   enough; the deep pull is Tier 2/3's job.
2. **Bull case in the name's own terms — on those current facts.** One or two lines: what *shape*
   (early/pre-revenue, growth compounder, re-rating/turnaround), what *inflection* could re-rate it,
   and *why now*?
3. **Map the theme.** Which live theme/sub-theme (from the hunting brief) does it sit in? **Inherit
   that theme's Macro/Theme/Mapping lineage lines.** If none fits but it's a credible standalone, a
   **Monster-shape**; if two or more names in this batch point at the *same* emerging mechanism, flag a
   **NEW-CLUSTER** (a bottom-up theme-birth signal for Tier 0) and carry it as the provisional theme.
4. **Tag a provisional archetype** (V / G / N) — the lens, not a verdict. `?` if unclear.
5. **Judge plausibility of ≥4x.** *Could* this plausibly reach ≥4x over 2–4 years if the bull case
   plays out? Judging whether a credible path *could* exist — not proving it. `YES / MAYBE / NO`.
6. **Bucket it** (below). `Fam` records how confidently you placed it *after* the check
   (`KNOWN / PARTIAL / UNKNOWN`).

## Buckets — ADVANCE or DROP

- **ADVANCE → Tier 1.5.** Any plausible shape worth verifying (4x? = `YES`, or `MAYBE` with a clear
  inflection). Attach a **verify-first note** — the one thing Tier 1.5 should confirm on current data
  (real thematic exposure, still-early, theme still alive). **ADVANCE is the recall setting: when torn
  between ADVANCE and DROP, ADVANCE** — Tier 1.5 is the cheap filter that catches the false positives.
- **DROP.** You can confidently say this isn't even a closer-look candidate, and that rests on a
  **staleness-proof structural fact** (a size class that can't 4x, not a real operating company, the
  wrong instrument — a stable large-cap or low-growth dividend payer) **or** on **current evidence
  from your search** (no live thematic angle / a confirmed non-fit) — **never a stale prior about a
  name you didn't check.** Every DROP needs a one-line, calibration-checkable reason.
- **HELD** — already in the book: route out (`HELD — position review`), don't re-triage as a candidate.

## Recall rules — do not violate
- **Never DROP a name only for failing a predefined shape or box.** Pre-revenue, "mature-looking
  theme," and unfamiliar are *not* drop reasons on their own.
- **Confirm before you cut** (rule 4).
- **A name you can't place stays an ADVANCE.** Search to identify it; still unclear after a quick
  check → ADVANCE, never DROP.

## Not at this tier
No valuation, scenarios, verdicts, or sizing (there is none) — speed and recall only.

---

## Output (schemas in `card-schemas.md`)
The **triage table** · the **ADVANCE payload** (each with the bull case, provisional archetype,
theme + the inherited theme-level lineage, the verify-first note → Tier 1.5) · the **DROP log** (each
with a checkable reason → `decisions.json`) · **NEW-CLUSTER signals** → Tier 0 · the **batch summary**
(counts; ADVANCE payload; clusters; theme-map gaps; confirmed false-matches → the theme's
`false_matches` list). **Append the lineage `Triage` element** (the §2 array — copy whole, append
one): `T1 ADVANCE` + the verify-question carried to 1.5.

## Worked anchors
- Pre-revenue quantum/space name, KNOWN, clear theme inflection → **ADVANCE (N)**. Pre-revenue is not
  a drop reason.
- Unrecognised small-cap semi in a week AI-memory is hot → **search it**: a real sub-theme play →
  ADVANCE; a peripheral non-player (confirmed) → a *valid* DROP.
- Stable regional utility / mature dividend large-cap → **DROP** ("wrong instrument — no ≥4x path").
- Three unrelated-looking names all exposed to grid-scale power for AI datacentres → ADVANCE each +
  flag `NEW-CLUSTER: AI-power` for Tier 0.

## Self-check
- Bull case made *before* judging, on current facts not stale memory? · Confirmed with a search before
  any DROP, and dropped only on a structural fact or what the search showed? · Did I DROP anything only
  for failing a box, being pre-revenue, or being unfamiliar (→ move to ADVANCE)? · Every DROP carries a
  calibration-checkable reason? · Theme-level lineage inherited for each ADVANCE, the Triage line
  appended, clusters + map-gaps surfaced for Tier 0?

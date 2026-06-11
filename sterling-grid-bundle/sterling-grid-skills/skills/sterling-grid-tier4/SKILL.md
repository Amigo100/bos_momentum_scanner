---
name: sterling-grid-tier4
description: >-
  Sterling Grid Tier 4 (V9) — the final gate before capital. Takes the whole batch of names that
  cleared the Tier-3 deep dive (each with a 3c verdict, scenarios, catalyst, bear classification, memo,
  and decision record) and decides COMPARATIVELY and at the BOOK level which we actually buy: BUY or DO
  NOT BUY. Tier 3 judged each name on its own; this tier judges them against each other, against the
  held book, and against one sharpened bar — is this a *great* opportunity, the RKLB-early-2024 setup
  (early high-growth macro-tailwind theme · a present operational inflection · a near-term catalyst so
  the payoff begins soon) — not a slow burn and not a lottery ticket. Every BUY is one full,
  equal-weight position at the scanner's entry; there is NO sizing, NO slot or position cap, NO
  watchlist, and NO kill criteria (exits are the scanner's). Output: a ranked buy list, a DO-NOT-BUY
  log, the portfolio impact, and append-ready decision rows.
  INVOCATION: invoked deliberately — once per week, on the whole deep-dived batch in one session — by
  the pipeline orchestrator or the operator running the buy decision. NOT a keyword-triggered skill. On
  EVERY invocation, re-read this file and its reference files from disk; never run it from memory.
disable-model-invocation: true
effort: high
allowed-tools: WebSearch WebFetch Read Write Bash
---

# Sterling Grid — Tier 4 (V9): Deep-Dive Review & Buy Decision

## How this skill is invoked

Explicitly-invoked, looked-up-each-time. Run **once per week on the whole deep-dived batch in a single
session** — this tier is comparative, so it needs every survivor in front of it at once (unlike Tiers
2/3, which run per name). On every run, re-read this file and `references/` fresh from disk. Do not run
it from topic keywords.

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (V9 — binary BUY / DO NOT BUY, no sizing; you apply §4
spine, §5 the binary decision, §9 firewall) and **`references/lineage-block.md`** (you append the
final **Decision** line, and you read the inherited lineage to score the opportunity bar — Macro/Theme
for the theme read, Evidence for the inflection, Geometry for the catalyst window, Verdict for type/
conviction/path). `references/diagnostic-reference.md` is rarely needed here. Card shapes are in
**`references/card-schemas.md`**.

## Operating rules for the whole pass

1. **The final gate — comparative and book-level.** Tier 3 cleared each name on its own merits; you
   re-judge them *against each other, against the held book, and against the opportunity bar.* A name
   can have a clean 3c BUY and still be a DO NOT BUY here (outclassed, redundant with the book, or the
   moment isn't right).
2. **Same spine (§4), same firewall (§9) — plus the opportunity profile on top.** This tier is
   deliberately selective because the bar is a *great* setup, not a passable one. **Selectivity is the
   quality bar.** There is **no slot or capital scarcity to ration — no position cap (§5)** — so
   nothing pressures you to fill a quota. **Better to hold cash than to buy a merely-passable setup.**
3. **Binary, full positions.** Every BUY is one full, equal-weight position at the scanner's entry —
   **no sizing, no scaling, no tranches.** Type (multibagger / great trade) and conviction (Extremely
   Bullish / Bullish) are *labels carried from 3c*, never a size.
4. **Entry and exit belong to the scanner.** Set **no** size and **no** sell rules or kill criteria
   (§2 / §5). The only thing carried forward on a BUY is the **expected-path checkpoint** — the next
   print/event we watch the thesis against, *informational, not a sell trigger.*
5. **No new thesis work.** Thinking + *light* web only — to refresh prices and confirm the scanner
   entry is still live, and to catch anything that landed since the deep dive. The analysis is done;
   you are deciding, not re-deriving.
6. **No watchlist.** A DO NOT BUY (whether it fails the bar or is a sound thesis at the wrong moment)
   re-enters only if a later scan re-flags it and it clears the bar then.
7. **Append the Decision lineage line; don't re-derive the chain.**

---

## What we're buying — the opportunity bar

We want **higher-risk / higher-reward, substance-backed** — not slow compounders, and **not
pie-in-the-sky lottery tickets.** The exemplar is **RKLB in early 2024**: an early-commercial name in a
high-growth theme (space / defence) with real macro tailwinds, at a genuine operational inflection
(launch cadence ramping, milestones, revenue accelerating, backlog building), positioned to re-rate
*soon* on near-dated catalysts — and it ran hard within the year. Judge every candidate against that
on five dimensions:

1. **Theme — early, high-growth, macro-backed.** Genuinely *early* (rising capex / adoption / capital
   flows, §8), structurally high-growth, carried by a real macro tailwind. **Reject** late or crowded
   themes, and "themes" that are narrative with no demand mechanism or capital behind them.
2. **Inflection — now, and operational.** *At* the inflection, evidenced by the discriminators (§7) —
   backlog converting, a milestone hit on its original date, a firm cash contract, a margin/cash
   inflection — **present, not merely asserted.** **Reject** pre-inflection (still a story) and
   post-inflection (already re-rated; the geometry is gone).
3. **Catalyst proximity & payoff velocity.** The catalyst that drives the re-rating lands **within
   ~6–18 months**, so the move *begins soon.* *(The hold can still run for years if it keeps working —
   RKLB did; what we screen here is when the payoff **starts**.)* **Do not buy** a sound thesis whose
   catalyst is years out with no near-term driver — it re-enters via the scan when the catalyst nears.
4. **Reward vs substance — opportunity, not lottery.** Upside large *and* evidence-backed: a real
   mechanism, the discriminators live, a non-trivial probability of the favourable scenario. **Reject**
   huge theoretical upside resting on narrative or a low-odds binary with no operational evidence.
5. **Risk — large but survivable.** Higher risk is welcome where the tail justifies it, provided the
   downside is a survivable drawdown, not permanent impairment (§5) — every position is full equal
   weight, so survival is about the *name*, not a size. **Reject** ruin (§9), however attractive the
   upside.

The bar is comparative: *is this as good an opportunity as RKLB was in early 2024?* Great setups are a
BUY; everything short of great is a DO NOT BUY.

## Inputs

- **The deep-dived batch** — each name's **Tier-3c dossier:** verdict (type + conviction + expected
  path), the path + scenarios, the catalyst + its window, the bear classification, the memo, the
  decision record, and the accumulated lineage. *(The 3a scorecard and 3b geometry sit behind it if you
  need to check a claim.)*
- **The held book** — current positions + their themes (to avoid double-buying and to spot
  inferior-expression overlaps).
- **The theme map (Tier 0)** — to confirm each candidate's theme is early / strong and to read book
  concentration.
- **No slot or position cap (§5)** — every name that clears the bar is a full, equal-weight buy.

## Step 1 — Firewall backstop (per name)

Re-run the §9 disqualifiers and the ruin test against the 3c dossier one last time — a slipped
milestone, a financing, a credibility event, or a runway problem that landed *since* the deep dive.
**Any hit → DO NOT BUY** (log it). Nothing buys past a live firewall trip.

## Step 2 — Opportunity read (per name)

Score each survivor on the five dimensions — a structured judgment, not a number. For each, state
where it sits and the evidence (read from the lineage where you can — Theme/Macro, Evidence,
Geometry):
- **Theme:** early / mid / late · the macro tailwind named · capital-flow direction.
- **Inflection:** which discriminators are *present* (not asserted) · is the inflection now, pre, or post?
- **Catalyst:** the specific near-term catalyst + its expected window (the 3c catalyst window) · is the
  payoff imminent or years out?
- **Reward vs substance:** the upside multiple · and the evidence that makes it live (not a lottery).
- **Risk:** the permanent-impairment downside · survives it? (full equal weight — about the name, not a size)

Then place it against the exemplar: **stronger than / comparable to / weaker than RKLB-early-2024**, and why.

## Step 3 — Cross-check against the book

No slot budget and no position cap to ration — the only book-level check is **diversification, enforced
at selection (§5):**
- **Inferior-expression overlap:** if two candidates are the same wave, only the better vehicle clears —
  the weaker expression is a DO NOT BUY (inferior expression, §7). Read this against the *held* book
  too, not just the batch.
- **Concentration (the CONCENTRATION LENS — qualitative by design, never a cap, §5):** *note* (don't
  cap) how far the new buys tilt the book toward one theme; a heavy tilt is a reason to hold the bar
  *especially high* on the marginal same-theme names — never a reason to size anything down or to
  decline an otherwise-great setup. Emit it as a structured `concentration_read` (per theme: held +
  new counts; ≥3 same-theme positions → tag `heavy-tilt`, informational) so K.1 can later measure
  whether marginal same-theme buys underperform — the lens is tracked, not enforced.

## Step 4 — Decide (per name)

- **BUY** — clears the bar. One full, equal-weight position at the scanner's signal: **no size to set,
  no scaling, no kill criteria** (exits are the scanner's technical rule). Carry only the
  **expected-path checkpoint** — the next print/event to watch the thesis against (informational, not a
  sell trigger).
- **DO NOT BUY** — anything short of a clear BUY: it fails the bar (late/narrative theme, no near-term
  catalyst, lottery-ticket upside, ruin, inferior expression) *or* is a sound thesis at the wrong
  moment (catalyst too distant, inflection not yet evidenced). Either way it is not today's buy, **no
  watchlist** — it re-enters only via a later scan. Log the reason **+ its §0 reason_code** (the
  prose→code legend is in `card-schemas.md`).

---

## Output

### Buy list (ranked → execution + book)
Per BUY:
- **TICKER — BUY · type [multibagger / great trade] · [Extremely Bullish / Bullish] · [V/G/N]**
- **Opportunity read:** theme [early + tailwind] · inflection [discriminators present] · catalyst [+ window]
  · reward-vs-substance · risk — and **vs RKLB-2024: [stronger / comparable / weaker].**
- **Why it clears the bar:** one or two lines.
- **Entry:** the scanner's signal — one full, equal-weight position. **Expected-path checkpoint:** the
  next proof point (informational, not a sell trigger).

### Do not buy
- **TICKER** — reason_code (spec §0; the card-schemas legend maps the prose: late theme→theme-posture ·
  unproven inflection→pre-inflection · no near-term/distant catalyst→distant-catalyst · the rest
  literal) + one line. Re-enters only via a later scan.

### Portfolio impact
- Resulting book: the new full, equal-weight positions added and the **`concentration_read`** (per
  theme: held + new counts; `heavy-tilt` tags — informational, no cap), plus any inferior-expression
  overlaps avoided. No slot or position cap. Calibration Part A copies each BUY's tilt tag onto its
  ledger row as `concentration_flag`.

### Decision log (append-ready → `decisions.json`)
One row per name: `date, week_id, ticker, stage: "tier4", decision, reason_code (handoff-card-spec
§0), type, conviction, opportunity_vs_RKLB, catalyst_window, reason, concentration_flag`. This is the
**binding capital decision** — where it differs from the 3c verdict (a 3c BUY declined here for
diversification or timing), this row governs. Feeds calibration: over time, did the BUYs scoring
*comparable-or-stronger than RKLB-2024* deliver the fast, large move, and did the DO-NOT-BUYs run
without us?

### Lineage — append, then pass forward
```
· Decision   BUY / DO NOT BUY (capital) · opportunity-vs-RKLB-2024 · reason                ← Tier 4
```

### Handoff
BUYs → execution at the scanner-timed entry (one full, equal-weight position each), then into the held
book; each BUY's dossier + lineage also feeds **Tier 3d** (the deep-dive article); the week's BUYs + the
DO-NOT-BUY log feed the **weekly newsletter**. No watchlist — DO-NOT-BUYs re-enter only via a later scan.

## Self-check
- Did I **rule out the lottery tickets** — large upside with no operational evidence or no near-term
  catalyst — rather than rationalise a marginal buy?
- Did I make the **slow burns** (sound thesis, distant catalyst) a DO NOT BUY for now, not a buy today?
- Does every BUY have all of: an early, high-growth, **macro-tailwind theme**; a **present** (not
  asserted) inflection; and a **near-term catalyst** so the payoff begins soon?
- Did I hold the bar against **RKLB-early-2024**, knowing a clean DO NOT BUY beats a marginal buy?
- Did I avoid **inferior-expression overlaps** and flag **theme concentration** across the *held* book —
  without inventing a slot or position cap (there is none, §5)?
- Did a firewall hit (§9) make it a DO NOT BUY regardless of upside?
- Did I keep entry to the **scanner's timing** and exits with the scanner — no size, no sell rules, only
  an informational expected-path checkpoint?
- Did I append the Decision lineage line and log every decision?

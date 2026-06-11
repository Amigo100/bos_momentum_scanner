---
name: sterling-grid-notes
description: >-
  Sterling Grid Substack Notes (V9) — the downstream publishing step, run after the weekly newsletter:
  turn the newsletter into a week of Substack Notes (21 base + up to 3 bonus, across 7 content
  categories), each with a complementary 1200×630 HTML image card. CONTENT GENERATION, not a new
  analytical pass: prices and facts come only from portfolio.csv and the newsletter. The cardinal card
  rule is COMPLEMENT NOT REPEAT — a card must add visual information the text alone can't convey.
  Outputs two files: a markdown file of all note text (ready to paste, with [LINK] placeholders) and a
  single HTML file of all cards (stacked for screenshotting). Multi-newsletter: Sterling Signals
  (small-cap) / Ground Floor Investing (micro-cap) / Inflection Point Investing (mid-cap).
  INVOCATION: invoked deliberately — once per week, after the newsletter — by the pipeline orchestrator
  or the operator. NOT a keyword-triggered skill. On EVERY invocation, re-read this file and its
  reference files from disk; never run it from memory.
disable-model-invocation: true
allowed-tools: Read Write Bash
---

# Sterling Grid — Substack Notes (V9): Weekly Content Production

## How this skill is invoked

Explicitly-invoked, looked-up-each-time. **Once per week, after the weekly newsletter.** On every run,
re-read this file and `references/` fresh from disk. Don't run it from topic keywords. This skill
**writes two files** (notes markdown + cards HTML).

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (the house voice + the V9 model — binary, full positions,
exits owned by the scanner, no sizing) and **`references/lineage-block.md`** (the forces and theses you
reference trace to the Theme lines and the 3c memos via the newsletter). The input→note map is in
**`references/card-schemas.md`**.

## Operating rules

1. **Content generation only. Introduce nothing new.** Prices and facts come **only** from
   `portfolio.csv` and the weekly newsletter (and the Tier-3d articles / chart prose for signal
   companions). No web search for prices, no new analysis.
2. **COMPLEMENT, NOT REPEAT — the most important rule.** A card must add visual information the text
   alone can't convey. Test each: *would the card still be informative if the reader couldn't see the
   note text?* If no, it's a repeat — redesign it. Valid complements: data viz (chart/histogram/
   heatmap/timeline), process diagram, comparison structure, reference/concept visual, pattern overlay.
3. **Adapt to the V9 chain (our standing rule).** The newsletter is the source; legacy terms map onto
   V9: **structural forces** = Tier-0 themes; **signal thesis** = the 3c memo / 3d article;
   **comparable-winner archetype** = the 3a read; rejection tags map to the **V9 stage** each name
   failed at (Tier-1/1.5 exposure · Tier-2 gate · Tier-2.5 reconciliation · Tier-3 deep-dive); the
   **funnel** is the V9 stages. **No sizing** anywhere — thesis-risk notes give *informational*
   expected-path checkpoints, never scale-up triggers and never sell rules.
4. **Honest on losses** — never frame negative P&L as "loss," "stopped out," or "down."

**Input:** `portfolio.csv` (sole price source) · the **weekly newsletter HTML** (primary structured
source) · optionally the **Tier-3d articles** + the **chart-analysis prose** for new signals — see
`card-schemas.md`. Set the **newsletter identity** first: name · Substack URL · market-cap focus ·
tagline · palette (below).

## Voice (non-negotiable)
Data-first; a specific number in every note; no hedging ("might / could potentially"); honest on
losses; forward-looking. **No em dashes** (colons, semicolons, periods). **No AI / LLM references** —
"our screening system." Vary sentence length. **"GREEN signal" only** (never TEAL/PASS/VIOLET/AMBER).
Conviction: **"Extremely Bullish" / "Bullish"** (never numbers). Tagline on notes **A1, D1, E2, F3**.

---

## Task — 21 base notes + up to 3 bonus (target 3–4/day across 7 days)

Each note = **(a) text, 80–200 words**, paste-ready, with a `[LINK]` placeholder where a URL goes (not
every note has a link); **(b) a complement card, 1200×630.** Produce the counts per category:

### A — Portfolio performance (3) · source: portfolio.csv + newsletter §3
- **A1 Portfolio snapshot** — full portfolio P&L, lead with the strongest, note any doublers, honest on
  negatives, recent exits, tease new signals, tagline, [LINK]. *Card:* P&L **distribution histogram**
  (uniform-width bars — one equal weight each — colour-coded by force). Not a list of numbers.
- **A2 Winner spotlight** — the 1–2 best, the story (entry thesis, force, journey, dates/prices), [LINK]
  to the deep dive. *Card:* **price-journey chart** from entry to now, entry + catalysts + current marked.
- **A3 Under pressure / honest update** — any negative P&L: state it factually, thesis intact/weakening/
  broken, the data point that would change the view, the downside floor. *Card:* **thesis-tracker grid**
  (the 3–5 thesis components as rows with ✓/~/✗/? status). Audited honestly, not just a P&L number.

### B — Market context (3) · source: newsletter §1 + §6 + macro
- **B1 Market snapshot** — index levels + weekly change + a one-sentence read for our 3–18mo horizon (no
  predictions). Benchmarks only if in portfolio.csv, else say so and skip values. *Card:* **regime gauge
  / 2D macro positioning** with the current point + historical analogues.
- **B2 The macro argument** — the single most important macro data point as a 150-word mini-editorial,
  one number as the anchor. *Card:* **big number + historical sparkline** (where today sits in 5y history).
- **B3 What moved this week and why** — the 2–3 biggest stories, 1–2 sentences each, connect to the
  portfolio. *Card:* **cause→effect arrow diagram** (events → affected positions/forces).

### C — Sector & force analysis (4) · source: newsletter §2 + Tier-0 themes
- **C1 The force map** — every force with status (DEPLOYED / BENCHMARKED / APPROACHING / NOT READY) + the
  tickers. *Card:* **deployment matrix** (forces × status, tickers in cells).
- **C2 Strongest force deep dive** — the force with most exposure / strongest convergence, 200 words
  (what it is, what drives it with $ amounts, why it matters for the cap range, which positions ride it).
  *Card:* **force-flow diagram** (capital sources → mechanism → benefiting companies, our tickers
  highlighted) or a stat-block if data-defined.
- **C3 Emerging / approaching force** — an APPROACHING force or signals that didn't advance; what we
  watch for, the trigger, why patience. *Card:* **leading-indicator timeline** with the trigger threshold.
- **C4 Scanner convergence** (or skip → a bonus note) — if multiple signals fired in one force, what
  convergence means. *Card:* **signal-cluster diagram** (tickers as dots, grouped by force).

### D — New signals & deep-dive companions (3–4) · source: newsletter §3 NEW ENTRIES + Tier-3d + chart prose
- **D1 Weekly newsletter companion** — introduce the newsletter, steer to the rejection stories first,
  tagline, [LINK]. *Card:* **teaser visual** (the single most striking number/funnel), a hook not a menu.
- **D2 New signal companion** (one per new signal, max 2) — hook with the most compelling data point, the
  thesis in 150 words, the bear in one sentence, [LINK] to the deep dive (do NOT give away the
  valuation/target). Include the **comparable-winner archetype** if one exists. *Card:* **comparable-
  winner parallel chart** (the historical winner's chart beside our current chart to the entry point) +
  a 3-cell metric grid. Not a GREEN-signal badge.
- **D3 Thesis risks & what we're watching** (per new signal with notable open risks, else skip) — every
  buy is one full equal-weight position; name the unresolved-binary / conviction strike honestly, then
  the **expected-path proof points** (informational checkpoints, never scale-up, never sell rules).
  *Card:* **expected-path checklist** (3–5 proof points as checkbox rows).

### E — Rejections & discipline (2) · source: newsletter §4 + the DROP log
- **E1 What we rejected** — the 2 most interesting rejections: what looked good, what killed it, **tagged
  to the V9 stage** (Tier-1/1.5 exposure-proxy · Tier-2 gate · Tier-2.5 reconciliation · Tier-3 deep-dive
  disqualifier/no-path/ruin/bear), framed as investing lessons + the discipline message. *Card:*
  **rejection-autopsy visual** (dilution → share-count chart; deterioration → peer-gap chart; Tier-2.5 →
  "Pipeline A vs B" boxes with the disagreement highlighted).
- **E2 The screening funnel** — the full V9 funnel (scanned → Tier 1/1.5 → Tier 2[/2.5] → Tier 3 → Tier 4
  GREEN) + the elimination rate ("99.X% eliminated"), tagline. *Card:* **multi-stage funnel diagram**
  with counts + drop-off labels + the elimination rate as the focal number.

### F — Investor education (4) · standalone, topic from the week
- **F1 Concept explainer** — a concept from the week in 150 words for non-pros, specific to a holding,
  [LINK]. *Card:* **concept diagram** (visualise the concept itself).
- **F2 Historical parallel / pattern** — connect a holding to a historical example, specific
  dates/prices/outcomes. *Card:* **pattern overlay** (historical chart aligned with ours at the entry).
- **F3 System methodology** — one aspect of how the system works (no proprietary detail): structural
  forces vs sectors / two parallel pipelines / scanner convergence / why we reject above our cap range;
  tagline. *Card:* **process diagram** of that methodology component.
- **F4 Metric or term spotlight** — one metric/term from the week in 100–150 words, specific to a ticker
  (e.g. days-to-cover, asset–EBITDA gap, value-capture grade, comparable-winner archetype). *Card:*
  **formula / component diagram** with the ticker's value on a healthy/borderline/concerning scale.

### G — Week ahead & catalysts (2) · source: newsletter §5
- **G1 The week-ahead calendar** — next week's data releases, Fed speakers, portfolio events
  (earnings/FDA/conferences), chronological, portfolio-affecting flagged. *Card:* **portfolio-event
  mapping** (timeline of events ↔ affected tickers).
- **G2 Catalyst watch** — the single most important coming catalyst: the event, the outcome we watch
  for, "if X then Y / if Z then W." *Card:* **binary-outcome decision tree** (catalyst node → two
  branches → the response on each).

### Bonus (0–3, only if the week is exceptional) — multi-signal convergence, a 200%+/500%+ position, a
stark rejection, or a catalog-gap signal. Any category. Mark "BONUS." **Cap total at 24.**

---

## HTML card design system
All cards in one HTML file, each: aspect-ratio 1200/630, max-width 640px in the preview (scales to
1200px on screenshot), border-radius 12px, box-shadow for separation, a monospace **label above each
card** (category + note ID). **Fonts:** DM Serif Display (headlines) · DM Sans (body) · JetBrains Mono
(data/tickers/labels). **Palette — by newsletter:** Sterling Signals (navy `#0a1628`/`#0f2440`/`#1a3a5c`
· blue `#2563eb`/`#3b82f6`/`#60a5fa`/`#dbeafe` · slate `#0f172a`/`#334155`/`#64748b`) · Ground Floor
(copper `#92400e`/`#b45309`/`#d97706` · charcoal `#1c1917`/`#292524`/`#44403c` · stone `#78716c`/
`#a8a29e`) · Inflection Point (teal `#0d9488`/`#14b8a6`/`#2dd4bf` · deep navy `#0c1220`/`#0f172a`/
`#1e293b`). All three share green `#16a34a` (positive/deployed/GREEN) · red `#dc2626` (negative/
rejections) · amber `#d97706` (warnings/approaching). **Card templates:** DARK (portfolio/signals/
system) · LIGHT (market data/calendars/force maps) · GRADIENT (big-number) · ACCENT (green/red/amber
left border). **Visual variety is mandatory** — do not produce 21 same-looking cards.

## Scheduling (3–4/day, anchored to: newsletter Sun PM · deep dives Tue · education Thu)
Sun PM D1 · Mon A1/B1/B2 · Tue D2(+D2#2 or F4)/C2/A2 · Wed C1/D3(or C4)/E1 · Thu F1/F4/B3 · Fri
F2/G1/A3 · Sat G2/E2/F3 · bonus slotted off-peak. Adjust to operator timezone.

## Output — TWO files
- **FILE 1 — notes markdown** (`[NOTES MARKDOWN — {YYYY-MM-DD}]`): each note separated by `---`,
  labelled ID + title + suggested day/time, text paste-ready, `[LINK]` placeholders, BONUS marked.
- **FILE 2 — cards HTML** (`[CARDS HTML — {YYYY-MM-DD}]`): all cards stacked vertically, each labelled
  with its note ID, styling inline or one `<style>` block, Google Fonts imported.

## Quality checks
**Text:** a specific number in every note · zero em dashes · no AI/LLM refs · no hedging · negatives
honest (never "loss"/"down") · 80–200 words each · tagline on A1/D1/E2/F3 · "GREEN signal" only ·
conviction words only · no price absent from portfolio.csv/newsletter · E1 tags the V9 stage · D2
references the comparable-winner archetype where one exists. **Cards:** every note has a card · 1200:630
· correct palette · the three fonts · numbers match the text · green/red/amber correct · **each card a
complement, re-checked against the rule** · visually distinct · labelled with its note ID.

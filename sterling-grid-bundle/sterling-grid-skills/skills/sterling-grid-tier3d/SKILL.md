---
name: sterling-grid-tier3d
description: >-
  Sterling Grid Tier 3d (V9) — the publication step for a single CONFIRMED BUY: turn its completed
  deep-dive work into the published Sterling Signals deep-dive article, a 2,500–3,500-word analyst
  write-up as a self-contained HTML document in the house design system. CONTENT GENERATION, not a new
  analytical pass: every number, scenario, and judgment comes from the work already done (the Tier-3a
  dossier, the Tier-3b geometry, the Tier-3c verdict + memo) and the lineage; introduce nothing new. It
  ADAPTS to what the analytical tiers actually produced — it renders 3a's discriminator scorecard and
  3b's methods-used valuation, NOT a forensic battery or a 7-method field the deep dive didn't compute.
  Runs after Tier 4 confirms the BUY. Output: the article HTML; it is the newsletter's deep-dive and
  the source for the notes' signal companions.
  INVOCATION: invoked deliberately — one confirmed BUY per run — by the pipeline orchestrator or the
  operator, after the buy decision. NOT a keyword-triggered skill. On EVERY invocation, re-read this
  file and its reference files from disk; never run it from memory.
disable-model-invocation: true
allowed-tools: Read Write Bash
---

# Sterling Grid — Tier 3d (V9): Deep-Dive Article

## How this skill is invoked

Explicitly-invoked, looked-up-each-time. **One confirmed BUY per run**, after Tier 4 confirms it.
Parallel across confirmed BUYs. On every run, re-read this file and `references/` fresh from disk.
Don't run it from topic keywords. This skill **writes a file** — the complete article HTML — which then
feeds the weekly newsletter and the notes.

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (the house discipline + the V9 model the article describes —
binary BUY, type as a label not a size, exits owned by the scanner) and **`references/lineage-block.md`**
(you draw the article's **upstream framing — Macro → Theme → Mapping → verdict — from the lineage**;
the article renders what the analytical tiers produced, never demands more). The input→section map is
in **`references/card-schemas.md`**.

## Operating rules

1. **Content generation, not analysis. Introduce nothing new.** Every number, scenario, and judgment
   traces to the **3a dossier**, the **3b geometry**, or the **3c verdict + memo**. A fact that's
   missing is an *open question to name*, never something to fill from memory. No new web, no new model.
2. **Adapt to the analytical output (our standing rule).** Render what the deep dive actually produced:
   - the **scorecard** section renders **3a's discriminator scorecard** (the four leading signals:
     present / partial / absent) plus any **survival/accounting reads 3a computed** where the name
     warranted them (KS-3 accounting quality, Yartseva asset–EBITDA). Do **not** fabricate a 5-metric
     Altman/Piotroski/Beneish battery the deep dive didn't run.
   - the **valuation** section renders **3b's decoupled floor + the methods-used range + the four
     scenarios** (bear / base / re-rate / overshoot). Do **not** manufacture a 7-method football field.
3. **Draw the upstream framing from the lineage.** The **structural force** = the Theme line (Tier-0
   theme + benchmark); the **macro tailwind** = the Macro line; the **value-capture grade** = the
   Mapping line (proxy quality + archetype); the **comparable-winner** and **type** = the
   Evidence/Geometry lines. Open the article on this top-to-bottom framing, exactly as the 3c memo does.
4. **2,500–3,500 words of the highest-quality analytical writing.** Use extended thinking to plan the
   narrative arc before writing.
5. **Obey the voice rules and the design system below — both non-negotiable.**

**Input:** the confirmed-BUY name's **3a dossier + 3b geometry + 3c verdict/memo + the full lineage**,
and the **Tier-4 decision** (confirmed BUY + the opportunity read) — see `card-schemas.md`.

## Upstream context to weave in (all from the lineage / dossiers — render, don't re-derive)
- **Structural force** — the name's Tier-0 theme + benchmark, in newsletter voice; theme strength from
  the Tier-0 cues.
- **Value-capture grade** — Direct / Adjacent / Peripheral / R&D-stage (from Mapping); frames the
  conviction and risk discussion. *Never a position size — sizing doesn't exist in this model.*
- **Theme-confirmation read** — **dual-confirmed** (on the Tier-0 top-down map *and* surfaced bottom-up
  as a Tier-1 NEW-CLUSTER / confirmed by Tier-2.5 consensus) · **catalog-gap** (a Tier-1 NEW-CLUSTER the
  top-down map hadn't named yet — the Sandisk-as-AI-memory shape) · **top-down-only** (on the map, with
  adjacent / peripheral exposure). Frames the "why now."
- **Type + comparable winner** — the type (multibagger = open-ended ≥4x / great trade = protected 3–4x)
  from 3b/3c, and the comparable-winner archetype from the 3a read (e.g. "this setup most resembles
  RKLB 2024 / PLTR 2023 / SNDK 2025"). Closes the "why now."

---

## Voice & style rules (non-negotiable)
1. **NO EM DASHES.** Colons, periods, semicolons.
2. **NO AI / LLM references.** Human-written analyst voice ("our screening system," never the model).
3. **NO technical indicator names** (RSI, MACD, HMA, Banker, UC, MCDX, KDJ).
4. **STRUCTURAL FORCES over micro themes** — the validated canonical theme is "the structural force."
5. **SPECIFIC NUMBERS for every claim.** Never "strong growth"; always "23% revenue growth across the
   last four quarters."
6. **VARY SENTENCE LENGTH** deliberately. No triple parallel constructions.
7. **Write with CONVICTION.** The deep dive produced a verdict; write like an analyst who did the work.
8. **The BEAR CASE reads like a short-seller wrote it** — a genuine adversarial argument, not a hedge.

## Output — the article (complete, self-contained HTML)

**Sterling Signals design system:**
- Google Fonts: **DM Serif Display** (headings), **DM Sans** (body), **JetBrains Mono** (data).
- Container: max-width **780px**, padding **40px 24px**, centred. Mobile responsive.
- Palette: navy `#0a1628` · blue `#1a3a5c` / `#2563eb` · slate `#334155` / `#64748b` · green `#16a34a`
  · red `#dc2626` · gold `#d97706`.
- **Stat grid** — 4 cards: **Entry Price** · **Structural Force** · **Type** (multibagger / great trade)
  · **Next Catalyst**.
- **Tables**: `#0f2440` header, white text, alternating rows, JetBrains Mono numbers.
- **Price-target cards**: render the four V9 scenarios — **Bear** (red) · **Base** (blue) · **Re-rate**
  (green) · **Overshoot** (gold) — coloured left borders, each with its price level and probability.
  *(If a simpler three-card Bear/Base/Bull layout is preferred, collapse re-rate + overshoot into Bull;
  the four-scenario version is the faithful V9 render.)*
- **Scorecard**: render **3a's discriminator scorecard** (Backlog converting · Milestone on date · Firm
  cash contract · Margin/CF inflection — present / partial / absent) and any accounting/solvency reads
  3a computed. *(This replaces the legacy Altman/Piotroski/Beneish/Cash-Conversion/Asset–EBITDA card,
  per the adapt-to-the-analytical-output rule — show the metrics the deep dive actually produced.)*
  **Consistency rule:** every article's scorecard renders **all four** discriminators, one row each; a
  structurally-N/A signal (e.g. backlog for a pre-revenue biotech) renders
  `absent (N/A: <one-line why>)` per diagnostic-reference §2 — articles stay structurally comparable
  week to week, and an N/A never reads as a red flag.

### Sections
- **PREVIEW LINE** — 1–2 sentences with a specific number that compels the open (the first thing
  subscribers see in their email).
- **TABLE OF CONTENTS** — linked sections.
- **1. The thesis in one sentence** — from the 3c verdict; then 2–3 sentences of context.
- **2. What this company does** (200–300 words) — plain language: revenue model, key segments, key
  metrics, competitive position. From the 3a dossier.
- **3. Why now** (300–400 words) — the **structural force**: the Tier-0 theme and its macro tailwind
  (the Macro line), the theme-confirmation read, and why the operational inflection is *now*; close on
  the comparable-winner archetype and the type.
- **4. The Space** (300–400 words) — render **3a-T's Theme/Space Trajectory**: the **live competitive
  field** (who this name competes with in its segment and who is gaining vs losing share), the **theme
  lifecycle & growth** (where the space sits on its arc and where this name sits within it), **capex &
  demand** (the money funding the space and the name's addressable slice, with specific numbers), the
  **moat** (whether the name holds its value-capture as the space matures), and the **theme catalysts and
  risks**; close on **how the space's trajectory drives this stock's price** (the multiple-ceiling read and
  the theme catalyst-window). Distinct from "Why now" (which is the *inflection timing*); The Space is the
  *competitive / lifecycle / capex arc* of the structural force. Render only what 3a-T produced; a missing
  figure is an open question, not memory-filled.
- **5. The evidence** — render 3a's **discriminator scorecard** (which of the four signals are present
  vs absent-where-needed) and the verified ≥4x drivers, with specific numbers and the scorecard table.
- **6. Valuation and the path** — 3b's decoupled **floor** (method) and **target** (the methods-used
  range), the four **scenarios** as price-target cards with probabilities, the **re-rating velocity**
  (expected time-to-re-rate, P(≥2x within 6/12/18 months)), and what the current price already prices
  in (the one-line steelman).
- **7. The bear case** — the strongest documented bears (from 3a) with the 3b classification (refuted /
  real-but-priced / real-and-mispriced / unresolved-binary). Reads like a short-seller wrote it.
- **8. The call** — type, conviction, and the **expected path + target + horizon + driver + catalyst
  window**; the expected-path checkpoint (the next proof point). State plainly that entry and exit are
  the screening system's, and the target is the thesis, not a sell trigger.
- **9. How we'd be wrong** — the pre-mortem causes and the unresolved-binary risks; what would
  invalidate the thesis.

**Write the article to** the deep-dive output path (e.g. `articles/<ticker>-deep-dive.html`); it is the
newsletter's deep-dive and the source for the notes' signal companions.

## Self-check
- Introduced **nothing new** — every number/scenario/judgment traces to 3a / 3b / 3c (a missing fact
  named as an open question, not filled from memory)?
- **Adapted** the scorecard and valuation sections to what the analytical tiers actually produced (3a's
  discriminator scorecard; 3b's methods-used range + four scenarios) — no invented forensic battery or
  7-method field?
- Scorecard has **all four discriminator rows**, with any structurally-N/A signal rendered
  `absent (N/A: …)` rather than omitted or red-flagged?
- Opened on the lineage's upstream framing (structural force · macro · theme-confirmation), exactly as
  the 3c memo does?
- **The Space** section present — renders 3a-T's theme→price read (competitive field · lifecycle/growth ·
  capex/demand · moat · theme catalysts/risks), distinct from Why-Now, with specific numbers?
- All eight voice rules obeyed — especially **no em dashes**, no indicator names, specific numbers for
  every claim, and a short-seller-grade bear case?
- Self-contained HTML in the house design system (fonts, palette, stat grid, scenario cards, scorecard,
  mobile responsive), 2,500–3,500 words?

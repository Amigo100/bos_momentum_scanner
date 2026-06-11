---
name: sterling-grid-newsletter
description: >-
  Sterling Grid Weekly Newsletter (V9) — "The Weekly Screening": turn the week's pipeline output into a
  3,000–3,500-word investor briefing as a self-contained HTML document in the house design system. Run
  once weekly, after the Tier-4 buy decision. CONTENT GENERATION, not a new analytical pass: every
  number comes from the work already done; prices come ONLY from portfolio.csv (introduce none that
  weren't there). Structural forces first (the Tier-0 themes), honest on every position, and the
  rejection stories tagged to the V9 stage each name failed at. It aggregates the whole week — new BUYs,
  technical sells, rejections, the structural forces, the portfolio — and hands off to the Substack
  notes.
  INVOCATION: invoked deliberately — once per week, after Tier 4 — by the pipeline orchestrator or the
  operator. NOT a keyword-triggered skill. On EVERY invocation, re-read this file and its reference
  files from disk; never run it from memory.
disable-model-invocation: true
allowed-tools: Read Write Bash
---

# Sterling Grid — Weekly Newsletter (V9): The Weekly Screening

## How this skill is invoked

Explicitly-invoked, looked-up-each-time. **Once per week, after Tier 4.** On every run, re-read this
file and `references/` fresh from disk. Don't run it from topic keywords. This skill **writes a file** —
the newsletter HTML — and is the source the Substack notes spin out of.

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (the house discipline + the V9 model — binary, full
positions, exits owned by the scanner, no sizing) and **`references/lineage-block.md`** (the structural
forces and theses you render are the **Theme lines** and the **3c memos**; this is content generation —
the article renders what the pipeline produced). The input→section map is in
**`references/card-schemas.md`**.

## Operating rules

1. **Content generation, not analysis. Introduce nothing new.** Every number comes from the week's
   pipeline work and `portfolio.csv`. No new web, no new model, no re-judging.
2. **Prices come ONLY from `portfolio.csv`.** Do not introduce any price that isn't in it. This is the
   single hard data rule of the newsletter (run a price-refresh that writes `portfolio.csv` before this
   step). **Scope:** this binds the **portfolio table** (held positions). A **new entry's** thesis
   levels — its entry price and the 3c scenario prices (bear-floor, base, target) — come from that
   name's 3c verdict/geometry and are the **named exception**; present them explicitly as the announced
   new-signal levels, not as portfolio prices.
3. **Adapt to the V9 chain (our standing rule).** The legacy prompt's stage names map onto V9:
   - **structural forces** = the week's **Tier-0 themes** (the Theme lineage lines).
   - a new entry's **fundamental thesis** = its **Tier-3c memo** + **Tier-3d article**.
   - a new entry's **technical overview** = operator-supplied **chart-analysis prose** (the screener
     owns technicals; V9 generates none — fill from the screener's note or leave the placeholder).
   - the **funnel** = screener signals → Tier 1 / 1.5 → Tier 2 → Tier 2.5 (if a 2nd pipeline ran) →
     Tier 3 → Tier 4 BUY.
   - **rejection stories** tag to the **V9 stage** each name failed at — read the structured `stage`
     + `reason_code` fields on the `decisions.json` records (never inferred from the reason prose): a
     Tier-1/1.5 exposure/shape drop · a **Tier-2 deep-dive-gate** drop · a **Tier-2.5 reconciliation**
     drop (only if a 2nd pipeline ran) · a **Tier-3** deep-dive drop (re-validation break, a §9
     disqualifier, no credible path, ruin, or a bear that bites).
   - **near-misses** = this week's **DO NOT BUY** names (no watchlist; they re-enter only via a future scan).
4. **2,500–3,500 words**; use extended thinking to plan the narrative arc. Lead with the single most
   important thing for the week ahead, opening on a data point (never "This week" or "Welcome back").

**Input:** the week's pipeline outputs (Tier-0 theme map · the Tier 1/2/2.5 funnel + DROP log · the
Tier-3 memos · the Tier-4 buy list + DO-NOT-BUY log) · **`portfolio.csv`** (P&L) · the **market
calendar** for the week ahead · the per-ticker **chart-analysis prose** for any new entries — see
`card-schemas.md`.

---

## Voice rules (non-negotiable)
- **No em dashes** anywhere. Colons, periods, semicolons.
- **No AI / LLM references.** This is "our screening system."
- **No technical indicator names** (HMA, MACD, RSI, Banker, UC, MCDX, KDJ).
- **Structural forces** (the validated Tier-0 themes), NOT micro themes from the scanner.
- **Specific numbers** for every claim. Never "strong growth."
- **Vary sentence length.** No triple parallel constructions.

**Signal branding:** "GREEN signal" only. NEVER TEAL / PASS / VIOLET / AMBER.
**Conviction:** "Extremely Bullish" / "Bullish." NEVER numbers.
**Approved terms:** "our screening system," "momentum confirmed," "structural pivot confirmation,"
"institutional accumulation patterns," "systematic exit discipline," "GREEN signal" (buys), "system
exit" (sells).

**Portfolio display rules (honest transparency):**
- 15%+ gain: showcase with entry price and P&L %.
- Under 15%: include in the table, no spotlight.
- Negative P&L: acknowledge honestly, state facts. **NEVER** frame as "loss," "stopped out," or "down."
- Show ALL positions in the table.

---

## Structure — "The Weekly Screening" (3,000–3,500 words)

Before writing, decide **the most important thing a reader needs heading into next week** and lead with it.

**TITLE:** `The Weekly Screening — Week [N]: [2–4 word forward-looking hook]`
(e.g. "Week 12: CPI Tuesday, Eyes on Defence" · "Week 12: New Signal in Nuclear Memory")

**PREVIEW LINE** — 1–2 sentences with a specific number (the first thing subscribers see before opening).

**TABLE OF CONTENTS** — linked section list.

**SECTION 1 — THE HEADLINE** (100–150 words). What mattered most; a one-sentence performance snapshot;
the stakes for the week. Open with a data point.

**SECTION 2 — THE FORCES AT WORK** (500–700 words — the analytical core). Cover **all** the week's
structural forces (Tier-0 themes). Per force: current status + the week's key data point · which
portfolio positions are exposed (name them with current P&L from `portfolio.csv`) · any catalyst update
or status change · macro woven *through* the force, not as a separate section. Forces with no exposure
get a 2–3 sentence status + what would need to change. **Where a force is a catalog-gap** (a Tier-1
NEW-CLUSTER the top-down map hadn't named yet — the Sandisk-as-AI-memory shape), say so explicitly:
"our bottom-up screen surfaced this structural force before our top-down catalog crystallised it" — a
unique-to-Sterling-Signals editorial moment.

**SECTION 3 — THE PORTFOLIO** (400–500 words). Full P&L table (prices from `portfolio.csv`):
`Ticker | Entry | Current | P&L% | Structural Force | Days Held`. Then: **Winners** (2–3 sentences each,
what's driving gains) · **Under pressure** (honest read of any negative P&L: original thesis, whether
intact, what data point would change the view, and the portfolio-level impact — each holding is one
equal-weight position) · **New entries** (per GREEN signal: ticker, entry price, structural force,
conviction; a 2–3 sentence fundamental thesis from the 3c memo; a 2–3 sentence technical overview from
the chart prose; end "Full deep dive on Tuesday.") · **Exits** (if the scanner's technical exit fired:
ticker, exit price, original thesis, that systematic exit discipline triggered — a trend reversal or
the trailing stop, not a thesis call — and final P&L). End: *"Every position tracked from entry date.
No revisions."* Include the `[WINNERS_TABLE]` placeholder.

**SECTION 4 — THE SCREENING** (500–700 words — the most valuable section). Educate through the
rejections. **Funnel visualisation:**
```
[N] scanned (weekly signals)
→ [N] cleared shape triage + verification (Tier 1 / 1.5)
→ [N] cleared the deep-dive gate (Tier 2)[ + reconciliation (Tier 2.5)]
→ [N] completed deep due diligence (Tier 3)
→ [N] GREEN signal(s) (Tier 4 BUY)
```
State the rejection rate ("99.X% eliminated"). **Rejection stories (2–3 narrative paragraphs)**, each
tagged to the V9 stage it failed at — what looked good on the surface, what the deep analysis
uncovered, why the system said no, read as an investing lesson:
- **Exposure / proxy cut (Tier 1/1.5 or Tier 2):** "looked like a play on [force], but the revenue mix
  was only ~20% direct exposure; we do not buy peripheral exposure to a hot theme."
- **Reconciliation cut (Tier 2.5, only if a 2nd pipeline ran):** "the top-down map flagged it; the
  bottom-up screen disagreed on the revenue mix; when the two disagree, the operational read usually
  wins. We passed."
- **Deep-dive-gate cut (Tier 2):** a thin path / weak proxy / marginal asymmetry that didn't earn a
  scarce deep-dive slot.
- **Deep-dive cut (Tier 3):** a §9 disqualifier (dilution death-spiral, reservations-as-backlog,
  credibility event), no credible ≥4x path, ruin, the comparable-winner pattern not matching, or a bear
  that survived classification.
**Near-misses:** notable DO-NOT-BUY names this week and why (no watchlist; they re-enter only via a
future scan). Include the `[SCAN_FUNNEL]` placeholder.

**SECTION 5 — THE WEEK AHEAD** (300–400 words). The market calendar. Per event affecting the portfolio
or the forces: exact date + time (ET) · what it is + consensus · which holdings are affected · what
outcome would change positioning. Styled HTML cards with date badges (general `#f4f7fa`/`#3d5a80`;
portfolio-affecting `#fdf6f4`/`#dc2626`; held-position earnings `#f4faf5`/`#16a34a`). Flag held-position
earnings prominently: `⚡ $TICKER reports [day] [pre/post]. Consensus: $X. Our thesis depends on
[metric]. We are watching for [outcome].`

**SECTION 6 — THE BOTTOM LINE** (100–150 words). Synthesis: what the portfolio's structural positioning
means now, the primary risk this week, the regime stance. End with a content preview: *"Tuesday: [deep
dive topic]. Thursday: [education topic]."*

**SECTION 7 — FOOTER.**
> Every screening result. Every entry. Every exit.
> sterlingsignals.substack.com
> Not financial advice. Informational and educational content only. Past performance does not guarantee
> future results.

---

## HTML — Sterling Signals design system
Complete self-contained HTML (styles inline or in a `<style>` block).
- **Fonts:** DM Serif Display (headings) · DM Sans (body, 400/500/600/700) · JetBrains Mono (data, tickers).
- **Layout:** `max-width: 780px; margin: 0 auto; padding: 40px 24px`. Mobile responsive.
- **Palette:** navy `#0a1628` / `#0f2440` / `#1a3a5c` · blue `#2563eb` / `#3b82f6` / `#60a5fa` /
  `#dbeafe` · slate `#0f172a` / `#334155` / `#64748b` · green `#16a34a` · red `#dc2626` · amber `#d97706`.
- **Type:** h1 DM Serif 42px `#0f172a` · h2 DM Serif 28px `#0f2440` border-bottom 2px `#dbeafe` · h3 DM
  Sans 20px/700 `#1a3a5c` · body DM Sans 17px/1.7 `#334155`.
- **Components:** stat grid (flex row, `#f1f5f9`, radius 8px; numbers 24px/700, labels 12px uppercase
  `#64748b`) · portfolio table (`#0f2440` header white text, alternating `#fff`/`#f8fafc`, JetBrains
  Mono tickers/numbers, green/red P&L) · screening funnel (stepped bars, green→amber→red left borders) ·
  force cards (left border by status — READY `#16a34a`, APPROACHING `#d97706`; force name, status badge,
  key metric, mapped positions) · week-ahead cards (date badges, colour-coded borders) · signal
  announcement (`#f4faf5` bg, `#16a34a` left border; ticker, entry, force, fundamental thesis, technical
  overview, "Full deep dive Tuesday").

## Quality check (verify before outputting)
- [ ] 3,000–3,500 words?
- [ ] Every structural force (Tier-0 theme) appears in Section 2?
- [ ] Portfolio table uses ONLY `portfolio.csv` prices — zero prices not in it?
- [ ] New entries announced with ticker, price, force, fundamental thesis (3c memo) AND technical overview?
- [ ] Section 4 has ≥2 rejection narratives tagged to specific V9 stages (Tier 1/1.5 / Tier 2 / Tier 2.5
      / Tier 3)?
- [ ] Funnel shows the V9 stages (incl. Tier 2.5 only if a 2nd pipeline ran)?
- [ ] ZERO em dashes? ZERO technical indicator names?
- [ ] Week Ahead uses specific dates from the supplied calendar?
- [ ] Bottom Line previews Tuesday + Thursday content?

Write the newsletter to `articles/weekly-screening-<YYYY-MM-DD>.html`, labelled
`[NEWSLETTER HTML — {YYYY-MM-DD}]`. It is the source the Substack notes spin out of.

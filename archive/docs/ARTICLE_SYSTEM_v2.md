# Sterling Signals — Long-Form Article Production System

> **Version:** 2.0 · March 2026
> **Purpose:** Master reference for producing long-form Substack articles as complete HTML files with embedded visual elements. The output is a single `.html` file containing all text and visuals. You read through it, copy-paste text into Substack's editor, and screenshot each visual block as you encounter it.
>
> **Companion documents:**
> - `STERLING_VISUAL_SYSTEM_v2.md` — carousel/Notes visual production (540×675 slides)
> - `voice_rules.md` — voice, tone, banned terms (canonical source of truth)

---

# PART 1: THE PROMPT

> Paste at the end of any research conversation to generate a complete article.

---

## PROMPT — COPY FROM HERE

Using all the research and analysis from this conversation, produce a complete Sterling Signals long-form article as a **single HTML file**.

The HTML file contains the full article text AND all visual elements (stat grids, diagrams, tables, callout boxes, price target cards, etc.) embedded inline at the correct positions. The output is one continuous document that I will read top-to-bottom, copy-pasting text sections into Substack's editor and screenshotting each visual block as I encounter it.

**Follow the Sterling Signals Article Production System exactly:**

**Format:**
- Single self-contained `.html` file
- Dark navy background (#0a1628) matching Substack dark mode
- Max-width 720px article container
- DM Serif Display for headings, DM Sans for body, JetBrains Mono for data/numbers
- Google Fonts imported in the `<head>`
- All CSS in a single `<style>` block using CSS custom properties

**Visual elements to embed inline (choose what's appropriate for the content):**
1. **Hero Stat Grid** — 3–5 key metrics. Always include. Place after the title/reveal.
2. **Pull Stats** — Large dramatic numbers as section transitions. Use 1–3 per article.
3. **Thesis Box** — One-sentence thesis, blue left accent. Always include for deep dives.
4. **Pipeline / Flow Diagrams** — Horizontal progress bars or vertical card flows for business models, product stages, revenue architecture.
5. **Catalyst Map** — Vertical timeline with coloured dots for upcoming events.
6. **Data Tables** — Dark-header tables for quarterly financials, peer comparisons.
7. **Peer Comparison Bars** — Horizontal bar chart for market cap / valuation comparisons.
8. **Price Target Cards** — Bear/base/bull in a 3-column grid with probability bars.
9. **EV Summary Row** — Compact stat row for expected value, return, risk/reward.
10. **Risk/Reward Bar** — Horizontal bar showing downside vs upside proportionally.
11. **Callout Boxes** — Warning (red), Insight (blue), Key Insight (amber). Use for kill switches, confirms/disconfirms, structural observations.
12. **Case Study Cards** — For educational articles with multiple stock examples.

**Visual density rule:** Break up every 400–600 words of continuous text with a visual element. A deep dive should have 8–12 visual elements across ~3,000–4,000 words. No section should exceed 600 words without a visual break.

**Each visual block** should be wrapped in a `<div class="visual">` container so I can identify what to screenshot vs what to copy-paste as text. Include a `data-label` attribute describing the component (e.g., `data-label="Screenshot: Pipeline diagram"`).

**Voice rules:** Follow the Sterling Signals voice rules exactly. Key points: open with data, $TICKER at $PRICE format, no em dashes (use colons and periods), no hype language, no AI/LLM references, no technical indicator names, end with forward look. See Part 4 of this document for the full quick reference.

**Structure the article** using the appropriate template from Part 5 (Deep Dive, Educational, Weekly Briefing). Extract all data from this conversation. Do not hallucinate figures. Match the company's reporting currency throughout.

## END OF PROMPT

---

# PART 2: HTML SCAFFOLD & CSS REFERENCE

Every article uses this exact HTML structure and CSS stylesheet. Claude should reproduce this scaffold for every article, swapping only the content.

## 2.1 HTML Shell

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>[Article Title] | Sterling Signals</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=DM+Serif+Display&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  /* Full stylesheet — see Section 2.2 */
</style>
</head>
<body>
<div class="article">
  <!-- Article content here -->
</div>
</body>
</html>
```

## 2.2 Complete CSS Stylesheet

Copy this stylesheet verbatim into every article. Do not modify the CSS custom properties, font sizes, or spacing values. The only things that change between articles are the content and which visual components are used.

```css
:root {
  --navy: #0a1628;
  --navy-light: #0f2440;
  --navy-mid: #132d52;
  --blue: #1a3a5c;
  --blue-accent: #2563eb;
  --slate-light: #64748b;
  --green: #16a34a;
  --red: #dc2626;
  --amber: #d97706;
  --text: #e2e8f0;
  --text-sec: #94a3b8;
  --text-muted: #64748b;
  --border: rgba(255,255,255,0.08);
  --border-accent: rgba(37,99,235,0.3);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'DM Sans', sans-serif;
  color: var(--text);
  background: var(--navy);
  line-height: 1.75;
  font-size: 17px;
  -webkit-font-smoothing: antialiased;
}

.article {
  max-width: 720px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}

/* ── TEXT ── */
.brand {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; font-weight: 600;
  letter-spacing: 2.5px; text-transform: uppercase;
  color: var(--blue-accent); margin-bottom: 6px;
}
.alert-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; font-weight: 600;
  letter-spacing: 2px; text-transform: uppercase;
  color: var(--green); margin-bottom: 4px;
}
h1 {
  font-family: 'DM Serif Display', serif;
  font-size: 38px; line-height: 1.15;
  color: #fff; margin-bottom: 20px; font-weight: 400;
}
.preview {
  font-size: 18px; line-height: 1.65;
  color: var(--text-sec);
  border-left: 3px solid var(--blue-accent);
  padding-left: 20px; margin-bottom: 32px;
}
h2 {
  font-family: 'DM Serif Display', serif;
  font-size: 26px; color: #fff;
  margin: 56px 0 18px; padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
h3 {
  font-size: 18px; font-weight: 700;
  color: var(--text); margin: 28px 0 10px;
}
p { margin-bottom: 18px; color: var(--text); }
em { color: var(--text-sec); }
strong { color: #fff; font-weight: 600; }

.ticker-badge {
  display: inline-block; background: var(--blue-accent);
  color: #fff; font-family: 'JetBrains Mono', monospace;
  font-size: 14px; font-weight: 600;
  padding: 5px 14px; border-radius: 4px; margin-bottom: 16px;
}

.reveal-line {
  border: none; border-top: 2px solid var(--border); margin: 40px 0 28px;
}
.reveal-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: 2.5px;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px;
}

/* ── TOC ── */
.toc {
  background: var(--navy-light); border-radius: 8px;
  padding: 20px 24px; margin: 8px 0 40px;
  border: 1px solid var(--border);
}
.toc-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: 2px;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 12px;
}
.toc ol { list-style: none; counter-reset: toc; padding: 0; }
.toc li { counter-increment: toc; margin-bottom: 6px; }
.toc li::before {
  content: counter(toc, decimal-leading-zero) " ";
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px; color: var(--text-muted);
}
.toc a {
  color: var(--text-sec); text-decoration: none;
  font-size: 15px; font-weight: 500;
}

/* ── VISUAL BLOCK WRAPPER ── */
.visual { margin: 36px 0; position: relative; }
.visual::before {
  content: attr(data-label);
  position: absolute; top: -18px; left: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px; letter-spacing: 2px;
  text-transform: uppercase; color: #334155;
}

/* ── SECTION LABEL (inside visuals) ── */
.section-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; letter-spacing: 2px;
  text-transform: uppercase; color: var(--text-muted);
  margin-bottom: 16px;
}

/* ── STAT GRID ── */
.stat-grid {
  display: flex; gap: 1px; background: var(--border);
  overflow: hidden;
}
.stat-cell {
  flex: 1; background: var(--navy-light);
  padding: 20px 16px; text-align: center;
}
.stat-value {
  font-family: 'DM Sans', sans-serif;
  font-size: 22px; font-weight: 700; color: #fff; line-height: 1.2;
}
.stat-value.green { color: var(--green); }
.stat-value.amber { color: var(--amber); }
.stat-value.blue { color: var(--blue-accent); }
.stat-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9.5px; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-muted); margin-top: 6px;
}

/* ── PULL STAT ── */
.pull-stat {
  padding: 44px 32px; text-align: center;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.pull-stat .big {
  font-family: 'JetBrains Mono', monospace;
  font-size: 48px; font-weight: 700;
  color: #fff; letter-spacing: -1px; line-height: 1;
}
.pull-stat .big.blue { color: var(--blue-accent); }
.pull-stat .big.green { color: var(--green); }
.pull-stat .big.red { color: var(--red); }
.pull-stat .context {
  font-size: 16px; color: var(--text-sec);
  margin-top: 12px; line-height: 1.5;
}

/* ── THESIS BOX ── */
.thesis-box {
  padding: 28px 32px; border-left: 3px solid var(--blue-accent);
  background: var(--navy-light);
}
.thesis-box .label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; letter-spacing: 2px;
  text-transform: uppercase; color: var(--blue-accent); margin-bottom: 12px;
}
.thesis-box .text {
  font-family: 'DM Serif Display', serif;
  font-size: 19px; color: #fff; line-height: 1.55;
}

/* ── PIPELINE DIAGRAM ── */
.pipeline { padding: 24px 0; }
.pipeline-phases {
  display: flex; margin-bottom: 8px; padding-left: 150px;
}
.pipeline-phases span {
  flex: 1; text-align: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 8px; color: var(--text-muted);
}
.pipeline-row {
  display: flex; align-items: center; margin-bottom: 6px; position: relative;
}
.pipeline-row .prog-label { width: 150px; flex-shrink: 0; padding-right: 12px; }
.pipeline-row .prog-name { font-size: 12px; font-weight: 700; color: #fff; }
.pipeline-row .prog-desc { font-size: 9px; color: var(--text-muted); margin-top: 1px; }
.pipeline-row .prog-bar-area { flex: 1; position: relative; height: 28px; }
.pipeline-row .prog-bar-fill {
  position: absolute; left: 0; top: 2px; bottom: 2px; border-radius: 4px; opacity: 0.25;
}
.pipeline-row .prog-bar-border {
  position: absolute; left: 0; top: 2px; bottom: 2px; border-radius: 4px;
  border: 1.5px solid; display: flex; align-items: center; padding-left: 8px;
}
.pipeline-row .prog-bar-border span {
  font-family: 'JetBrains Mono', monospace; font-size: 8.5px; font-weight: 600;
}
.pipeline-row .prog-partner {
  width: 80px; flex-shrink: 0; text-align: right;
  font-family: 'JetBrains Mono', monospace;
  font-size: 8px; padding-left: 8px;
}
.pipeline-grid-lines {
  position: absolute; top: 0; bottom: 0; left: 150px; right: 80px;
  display: flex; pointer-events: none;
}
.pipeline-grid-lines div { flex: 1; border-left: 1px solid var(--border); }
.pipeline-legend { display: flex; gap: 16px; margin-top: 14px; padding-left: 150px; }
.pipeline-legend .leg { display: flex; align-items: center; gap: 5px; }
.pipeline-legend .dot { width: 8px; height: 8px; border-radius: 2px; opacity: 0.6; }
.pipeline-legend span { font-size: 9px; color: var(--text-muted); }

/* ── CATALYST MAP ── */
.cat-map { padding: 24px 0; }
.cat-timeline { padding-left: 80px; position: relative; }
.cat-line {
  position: absolute; left: 72px; top: 4px; bottom: 4px; width: 2px;
  border-radius: 1px; opacity: 0.6;
  background: linear-gradient(to bottom, rgba(255,255,255,0.3), rgba(22,163,74,0.4));
}
.cat-event { display: flex; align-items: flex-start; margin-bottom: 12px; position: relative; }
.cat-event .cat-date {
  position: absolute; left: -80px; width: 68px; text-align: right; padding-top: 3px;
  font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; color: #fff;
}
.cat-event .cat-dot {
  position: absolute; top: 5px; border-radius: 50%;
  border: 2px solid var(--navy); z-index: 2;
}
.cat-event .cat-card { margin-left: 12px; padding: 6px 12px; border-radius: 5px; flex: 1; }
.cat-event .cat-title { font-size: 13px; font-weight: 700; color: #fff; }
.cat-event .cat-detail {
  font-size: 11px; color: var(--text-sec); margin-top: 2px; line-height: 1.4;
}

/* ── DATA TABLE ── */
.data-table {
  overflow: hidden; border-radius: 8px; border: 1px solid var(--border);
}
.data-table table {
  width: 100%; border-collapse: collapse;
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px;
}
.data-table thead th {
  background: var(--navy-light); color: #fff;
  padding: 12px 14px; text-align: left;
  font-size: 11px; font-weight: 600; letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border);
}
.data-table thead th.r { text-align: right; }
.data-table tbody td {
  padding: 10px 14px; border-bottom: 1px solid var(--border); color: var(--text);
}
.data-table tbody td.r { text-align: right; }
.data-table tbody td.sec { color: var(--text-sec); }
.data-table tbody td.neg { color: var(--red); text-align: right; }
.data-table tbody td.pos { color: var(--green); text-align: right; }
.data-table tbody td.hl { background: var(--navy-mid); }
.data-table tbody tr:nth-child(odd) { background: var(--navy); }
.data-table tbody tr:nth-child(even) { background: rgba(255,255,255,0.015); }

/* ── PEER COMPARISON BARS ── */
.peer-bars { padding: 24px 0; }
.peer-row { display: flex; align-items: center; margin-bottom: 8px; }
.peer-row .peer-name {
  width: 110px; flex-shrink: 0; text-align: right;
  padding-right: 12px; font-size: 12px; color: var(--text);
}
.peer-row .peer-name.hl { color: var(--green); font-weight: 700; }
.peer-row .peer-name.acq { color: var(--text-muted); font-style: italic; }
.peer-row .peer-bar-area { flex: 1; position: relative; height: 28px; }
.peer-row .peer-bar-bg {
  position: absolute; top: 0; left: 0; height: 100%; border-radius: 4px;
}
.peer-row .peer-bar-border {
  position: absolute; top: 0; left: 0; height: 100%;
  border-radius: 4px; border: 1.5px solid;
  display: flex; align-items: center; padding-left: 10px;
}
.peer-row .peer-bar-border span {
  font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600;
}
.peer-insight {
  margin-top: 12px; padding: 10px 14px; border-radius: 5px;
  background: rgba(37,99,235,0.08);
  border-left: 2px solid rgba(37,99,235,0.3);
  font-size: 11px; color: var(--text-sec); line-height: 1.5;
}

/* ── PRICE TARGET CARDS ── */
.targets { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.target-card { border-radius: 8px; overflow: hidden; background: var(--navy-light); }
.target-header { padding: 8px 0; text-align: center; }
.target-header span {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; font-weight: 600;
  letter-spacing: 2px; text-transform: uppercase;
}
.target-body { padding: 16px 14px; }
.target-body .price {
  font-family: 'DM Serif Display', serif;
  font-size: 32px; color: #fff; text-align: center;
}
.target-body .prob {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; color: var(--text-muted); text-align: center; margin-top: 2px;
}
.target-body .prob-bar {
  height: 4px; background: rgba(255,255,255,0.04);
  border-radius: 2px; margin-top: 10px; overflow: hidden;
}
.target-body .prob-fill { height: 100%; border-radius: 2px; }
.target-body .desc {
  font-size: 12px; color: var(--text-sec); margin-top: 10px; line-height: 1.5;
}

/* ── EV SUMMARY ROW ── */
.ev-row {
  display: flex; gap: 1px; background: var(--border);
  border-radius: 8px; overflow: hidden;
}
.ev-cell {
  flex: 1; background: var(--navy-light);
  padding: 18px 16px; text-align: center;
}
.ev-cell .ev-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;
}
.ev-cell .ev-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px; font-weight: 700;
}

/* ── RISK/REWARD BAR ── */
.rr-bar-wrap { padding: 20px 0; }
.rr-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px;
}
.rr-bar { display: flex; height: 36px; border-radius: 6px; overflow: hidden; }
.rr-bar .rr-down {
  display: flex; align-items: center; justify-content: center;
  background: rgba(220,38,38,0.2); border-right: 2px solid #fff;
}
.rr-bar .rr-up {
  flex: 1; display: flex; align-items: center; justify-content: center;
  background: rgba(22,163,74,0.15);
}
.rr-bar span {
  font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600;
}
.rr-labels { display: flex; justify-content: space-between; margin-top: 6px; }
.rr-labels span { font-family: 'JetBrains Mono', monospace; font-size: 9px; }

/* ── CALLOUT BOXES ── */
.callout-box {
  padding: 16px 20px; border-radius: 0 6px 6px 0; border-left: 3px solid;
}
.callout-box.warning { border-color: var(--red); background: rgba(220,38,38,0.08); }
.callout-box.insight { border-color: var(--blue-accent); background: rgba(37,99,235,0.08); }
.callout-box.key-insight { border-color: var(--amber); background: rgba(217,119,6,0.08); }
.callout-box .cb-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; letter-spacing: 1.5px;
  text-transform: uppercase; font-weight: 600; margin-bottom: 8px;
}
.callout-box.warning .cb-label { color: var(--red); }
.callout-box.insight .cb-label { color: var(--blue-accent); }
.callout-box.key-insight .cb-label { color: var(--amber); }
.callout-box .cb-text { font-size: 14px; line-height: 1.6; color: var(--text); }
.callout-box .divider { height: 1px; background: var(--border); margin: 14px 0; }
.callout-box .cb-sublabel {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; letter-spacing: 1.5px;
  text-transform: uppercase; font-weight: 600; margin-bottom: 6px;
}

/* ── CASE STUDY CARDS ── */
.case-study {
  background: var(--navy-light); border: 1px solid var(--border);
  border-radius: 8px; padding: 24px; margin: 24px 0;
}
.case-study .cs-header {
  display: flex; justify-content: space-between;
  align-items: baseline; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;
}
.case-study .cs-ticker { font-size: 20px; font-weight: 700; color: #fff; }
.case-study .cs-return {
  font-size: 16px; font-weight: 700; color: var(--green);
  background: rgba(22,163,74,0.12); padding: 3px 12px; border-radius: 4px;
}
.case-study .cs-meta { font-size: 14px; color: var(--text-muted); margin-bottom: 16px; }
.case-study .cs-tags { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
.case-study .cs-tag {
  font-size: 11px; font-weight: 600; letter-spacing: 1px;
  text-transform: uppercase; padding: 4px 10px; border-radius: 4px;
}
.case-study .cs-tag.green { background: rgba(22,163,74,0.12); color: var(--green); }
.case-study .cs-tag.blue { background: rgba(37,99,235,0.12); color: var(--blue-accent); }
.case-study .cs-tag.amber { background: rgba(217,119,6,0.12); color: var(--amber); }

/* ── FOOTER ── */
.footer {
  margin-top: 56px; padding-top: 28px;
  border-top: 1px solid var(--border); text-align: center;
}
.footer-cta {
  font-family: 'DM Serif Display', serif;
  font-size: 18px; color: #fff; margin-bottom: 6px;
}
.footer-link {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px; color: var(--blue-accent); text-decoration: none;
}
.disclaimer {
  margin-top: 20px; font-size: 12px;
  color: var(--text-muted); line-height: 1.6;
}
```

---

# PART 3: COMPONENT HTML PATTERNS

These are the actual HTML markup patterns for each visual component. Claude should reproduce these exactly, changing only the data content.

## 3.1 Hero Stat Grid

```html
<div class="visual" data-label="Screenshot: Stat grid">
  <div class="stat-grid">
    <div class="stat-cell">
      <div class="stat-value">$4.45</div>
      <div class="stat-label">Entry Price</div>
    </div>
    <div class="stat-cell">
      <div class="stat-value amber">BBB Gene Therapy</div>
      <div class="stat-label">Structural Force</div>
    </div>
    <!-- 2-3 more cells -->
  </div>
</div>
```

Use 3–5 cells. Add class `green`, `amber`, or `blue` to `.stat-value` for semantic colouring.

## 3.2 Pull Stat

```html
<div class="visual" data-label="Screenshot: Pull stat">
  <div class="pull-stat">
    <div class="big">$6.8 billion</div>
    <div class="context">in milestone commitments across four pharma partnerships.<br>
    The public market values the entire platform at $63 million.</div>
  </div>
</div>
```

Add class `blue`, `green`, or `red` to `.big` for colour variants. Use 1–3 per article at section transitions.

## 3.3 Thesis Box

```html
<div class="visual" data-label="Screenshot: Thesis box">
  <div class="thesis-box">
    <div class="label">The Thesis</div>
    <div class="text">[One-sentence thesis statement]</div>
  </div>
</div>
```

## 3.4 Pipeline / Progress Diagram

See the VYGR article for the complete pattern. Key structure:

```html
<div class="visual" data-label="Screenshot: Pipeline diagram">
  <div class="pipeline">
    <div class="section-label">Development Pipeline</div>
    <div class="pipeline-phases">
      <span>Phase 1</span><span>Phase 2</span><!-- etc -->
    </div>
    <div style="position:relative">
      <div class="pipeline-grid-lines"><div></div><!-- one div per phase --></div>
      <!-- One .pipeline-row per program -->
      <div class="pipeline-row">
        <div class="prog-label">
          <div class="prog-name">Program Name</div>
          <div class="prog-desc">Description</div>
        </div>
        <div class="prog-bar-area">
          <div class="prog-bar-fill" style="width:64%; background:var(--green);"></div>
          <div class="prog-bar-border" style="width:64%; border-color:rgba(22,163,74,0.4);">
            <span style="color:var(--green)">Status note</span>
          </div>
        </div>
        <div class="prog-partner" style="color:var(--green)">Owner</div>
      </div>
    </div>
    <div class="pipeline-legend"><!-- legend items --></div>
  </div>
</div>
```

Bar width is a percentage representing progress through the phases. Colour indicates ownership (green = owned, blue = partnered, amber = platform/early).

**Adaptation:** This pattern works for any horizontal progress visualization: product pipelines, project milestones, feature roadmaps, regulatory approval stages.

## 3.5 Catalyst Map (Timeline)

```html
<div class="visual" data-label="Screenshot: Catalyst timeline">
  <div class="cat-map">
    <div class="section-label">Catalyst Calendar</div>
    <div class="cat-timeline">
      <div class="cat-line"></div>
      <!-- One .cat-event per milestone -->
      <div class="cat-event">
        <div class="cat-date">Mar 18</div>
        <div class="cat-dot" style="left:-7px; width:12px; height:12px;
          background:#fff; box-shadow:0 0 8px rgba(255,255,255,0.3);"></div>
        <div class="cat-card" style="background:rgba(255,255,255,0.03);
          border-left:2px solid rgba(255,255,255,0.2);">
          <div class="cat-title">Event Name</div>
          <div class="cat-detail">What to watch for.</div>
        </div>
      </div>
    </div>
  </div>
</div>
```

**Dot sizing by importance:**
- Standard events: `width:8px; height:8px; background:var(--text-muted);`
- Important events: `width:10px; height:10px; background:var(--blue-accent); box-shadow:0 0 6px rgba(37,99,235,0.4);`
- Imminent events: `width:12px; height:12px; background:#fff; box-shadow:0 0 8px rgba(255,255,255,0.3);`
- Binary/critical events: `width:14px; height:14px; background:var(--green); box-shadow:0 0 10px rgba(22,163,74,0.4);`

Adjust dot `left` position to compensate for size: -5px for 8px dots, -6px for 10px, -7px for 12px, -8px for 14px.

## 3.6 Peer Comparison Bars

```html
<div class="visual" data-label="Screenshot: Peer comparison">
  <div class="peer-bars">
    <div class="section-label">Market Cap Comparison</div>
    <!-- One .peer-row per company, sorted largest to smallest -->
    <div class="peer-row">
      <div class="peer-name hl">&#9656; VOYAGER</div>
      <div class="peer-bar-area">
        <div class="peer-bar-bg" style="width:18%; background:var(--green); opacity:0.25;"></div>
        <div class="peer-bar-border" style="width:18%; border-color:rgba(22,163,74,0.5);">
          <span style="color:var(--green)">$265M</span>
        </div>
      </div>
    </div>
    <div class="peer-insight">Key takeaway sentence.</div>
  </div>
</div>
```

Use class `hl` on `.peer-name` for the subject company (green, bold, with ▸ prefix). Use class `acq` for acquired companies (italic, muted). Bar width as percentage of the largest company (which gets ~93%).

## 3.7 Price Target Cards + EV Summary + Risk/Reward

These three components typically appear together. See the VYGR article for the complete markup. The price target cards use a 3-column CSS grid. Bear = red, Base = blue, Bull = green. Probability bars use inline width percentages matching the probability.

The risk/reward bar renders downside and upside as proportional segments of a horizontal bar. Downside width should roughly reflect the loss percentage relative to the total range. Labels below mark Stop, Entry, Base, and Bull prices.

## 3.8 Callout Boxes

Three variants:

```html
<!-- Warning (red) — for kill switches, key risks -->
<div class="visual" data-label="Screenshot: Kill switch">
  <div class="callout-box warning">
    <div class="cb-label">Kill Switch</div>
    <div class="cb-text">Conditions that kill the thesis...</div>
  </div>
</div>

<!-- Insight (blue) — for confirms/disconfirms, methodology -->
<div class="visual" data-label="Screenshot: Confirms/disconfirms">
  <div class="callout-box insight">
    <div class="cb-sublabel" style="color:var(--green)">Confirms the Thesis</div>
    <div class="cb-text">What validates the position...</div>
    <div class="divider"></div>
    <div class="cb-sublabel" style="color:var(--red)">Disconfirms the Thesis</div>
    <div class="cb-text">What breaks the thesis...</div>
  </div>
</div>

<!-- Key Insight (amber) — for structural observations -->
<div class="visual" data-label="Screenshot: Key insight">
  <div class="callout-box key-insight">
    <div class="cb-label">Key Insight</div>
    <div class="cb-text">The thing most people miss...</div>
  </div>
</div>
```

---

# PART 4: VOICE RULES (QUICK REFERENCE)

> Canonical source: `voice_rules.md`. This is an abbreviated reference.

1. Open with data or a concrete statement
2. $TICKER at $PRICE format always
3. Specific numbers on every claim
4. "Our system" / "the screening" as authority
5. No AI/LLM references
6. Never reveal technical indicators (HMA, MACD, RSI, KDJ, Banker)
7. Reference structural forces, not micro themes
8. Show rejected stocks and explain why
9. Show losses alongside wins
10. No exclamation marks
11. No hype language
12. Colons and periods, not em dashes
13. Vary sentence length deliberately
14. Table of contents for posts >1,000 words
15. End with what happens next

---

# PART 5: ARTICLE TEMPLATES

## Template A: Deep Dive / Trade Alert

```
HEADER
  .brand "Sterling Signals · Deep Dive"
  .alert-label "Trade Alert #N"
  h1 "[Thesis Hook Title]"
  .preview [1-2 sentence preview for email/feed]

INTRO (400-600 words, no ticker named)
  Build the structural theme. Why this sector matters.
  What large players are already doing.

  [VISUAL: pull-stat] ← most dramatic number from the intro

REVEAL
  hr.reveal-line
  .reveal-label "The Stock"
  .ticker-badge "EXCHANGE: TICKER"
  h1 (smaller) "[Company Name]: [Core Tension in Numbers]"

  [VISUAL: stat-grid] ← entry price, force, conviction, next catalyst

TOC
  .toc with numbered links to each section

SECTION 1: The Thesis (short)
  [VISUAL: thesis-box]

SECTION 2: What This Company Does (400-600 words)
  Plain language business description.
  [VISUAL: pipeline-diagram or flow-diagram]

SECTION 3: Why Now (400-600 words)
  Catalyst window, entry timing rationale.
  [VISUAL: catalyst-map]
  Price dislocation narrative.
  Institutional accumulation evidence.

SECTION 4: The Numbers (400-800 words)
  Revenue trajectory text.
  [VISUAL: data-table (quarterly)]
  Balance sheet text.
  Peer comparison text.
  [VISUAL: peer-comparison-bars]
  Disparity analysis text.

  [VISUAL: pull-stat] ← transition to valuation (e.g., EV number)

SECTION 5: What We Think It's Worth (300-500 words)
  Methodology text.
  [VISUAL: price-target-cards]
  [VISUAL: ev-summary + risk-reward-bar]
  Probability assignment text.

SECTION 6: The Bear Case (300-500 words)
  Steelman the opposition.
  [VISUAL: callout-box warning] ← kill switch

SECTION 7: How We Are Playing It (200-300 words)
  Position sizing, stop, conviction.
  [VISUAL: callout-box insight] ← confirms/disconfirms

SECTION 8: What Happens Next (200-300 words)
  Next catalyst, timeline, what to watch.

FOOTER
  .footer-cta + .footer-link + .disclaimer
```

**Target: 8-12 visual elements across 3,000-4,000 words.**

## Template B: Educational / Framework

```
HEADER
  .brand "Sterling Signals"
  h1 "[Framework Title]"
  .preview [subtitle/hook]

  [VISUAL: stat-grid] ← 3-5 key statistics anchoring the framework

INTRO (300-400 words)

SECTION: The Data
  [VISUAL: data-table]

SECTION: The Framework
  [VISUAL: flow-diagram or comparison-visual]
  [VISUAL: pull-stat]

SECTION: Case Studies
  [VISUAL: case-study card] × 3-5 (alternating with 1-2 paragraphs each)

SECTION: How to Apply
  [VISUAL: pipeline-diagram or decision tree]

SECTION: Forward Look

FOOTER
```

**Target: 6-10 visual elements.**

## Template C: Weekly Briefing

```
HEADER
  .brand "Sterling Signals"
  h1 "Week [N]: [Theme]"

  [VISUAL: stat-grid] ← portfolio value, weekly return, vs SPY, positions

MARKET CONTEXT (200-300 words)
  [VISUAL: pull-stat or key-insight callout]

NEW ENTRIES
  [VISUAL: callout-box insight per entry]

EXITS
  [VISUAL: callout-box warning per exit]

POSITION UPDATES
  [VISUAL: data-table (portfolio)]

FORWARD LOOK

FOOTER
```

---

# PART 6: WORKFLOW

1. **Finish the research conversation** (deep dive, analysis, etc.)
2. **Paste the prompt from Part 1** at the end of the conversation
3. **Claude produces a single .html file** containing all text + visual elements
4. **Open the HTML file** in your browser
5. **Read through top-to-bottom.** For each section:
   - Copy the text paragraphs and paste into Substack's editor
   - When you reach a `[Screenshot: ...]` labelled block, take a screenshot of just that visual component
   - Paste the screenshot into Substack as an image at that position
6. **The dark background** of each visual matches Substack's dark mode, creating a seamless appearance

**Screenshotting tips:**
- Mac: Cmd+Shift+4 and drag to select the visual block
- Crop tightly to the visual component, excluding the grey label text above it
- On Retina displays, the 720px-wide visual becomes a 1440px screenshot (ideal for Substack)
- Dark background bleeds to the edges, blending with Substack's dark mode

---

# PART 7: QUALITY CHECKLIST

### Article Text
- [ ] First sentence contains a number or specific claim
- [ ] No em dashes (colons and periods instead)
- [ ] No banned terms (HMA, MACD, RSI, "let's dive in," etc.)
- [ ] No AI/LLM references
- [ ] $TICKER at $PRICE format for all positions
- [ ] Positions mapped to structural forces
- [ ] Ends with forward-looking statement
- [ ] Table of contents for articles >1,000 words

### Visual Elements
- [ ] Every visual wrapped in `<div class="visual" data-label="...">`
- [ ] All visuals render correctly at 720px width
- [ ] Dark background (#0a1628) on all components
- [ ] No text overlaps or clipping
- [ ] JetBrains Mono for all numbers
- [ ] Green = positive, Red = negative, Amber = caution, Blue = neutral
- [ ] Tables have dark headers with white text and alternating row shading
- [ ] Callout boxes use correct variant colouring

### Visual Density
- [ ] 8-12 visual elements for deep dives, 6-10 for educational
- [ ] No more than 600 words of continuous text without a visual break
- [ ] Hero stat grid is the first visual after title/reveal
- [ ] At least one pull stat for section transitions
- [ ] No two consecutive visuals without text between them

### Data Integrity
- [ ] All figures match the research conversation
- [ ] Currency consistent throughout
- [ ] Percentages sum correctly
- [ ] Price target weighted average calculated correctly

---

# PART 8: ADAPTATION GUIDE

### By Company Type

| Type | Pipeline → | Catalyst Map → | Peer Bars → | Waterfall → |
|------|-----------|---------------|-------------|-------------|
| **Biotech** | Drug pipeline by phase | FDA dates, data readouts | Market cap vs peers/acquisitions | Cash burn bridge |
| **SaaS** | Product roadmap | Earnings, product launches | ARR vs competitors | Revenue-to-profit waterfall |
| **Pre-revenue platform** | Technology milestones | Contract/partnership dates | TAM positioning | Projected bull case |
| **Mature / profitable** | Segment revenue breakdown | Earnings, dividend dates | Peer valuation multiples | Actual reported waterfall |
| **Commodity / cyclical** | Supply chain stages | Policy/cycle dates | Cost curve positioning | Margin sensitivity |

### Currency

Match the company's reporting currency. Use consistently across every visual element.

### Colour Assignment

When a company has multiple business segments:
- Primary revenue driver → Green (always)
- Growth/speculative → Blue
- Acquired/new → Amber or use inline `style` overrides
- If only 2 segments: Green + Blue

---

*Sterling Signals · sterlingsignals.substack.com*
*Long-Form Article Production System v2.0 · March 2026*

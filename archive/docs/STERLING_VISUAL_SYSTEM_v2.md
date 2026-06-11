# Sterling Signals — Visual Content Production System

> **Version:** 2.1 · March 2026
> **Purpose:** One document to produce publication-quality visual carousels, static diagrams, and accompanying Substack Notes for any company. Paste the prompt at the top of any research conversation, or use the full document as a reference system.

---

# PART 1: THE PROMPT

> Copy everything in this section. Paste it at the end of any stock deep dive conversation.

---

## PROMPT — COPY FROM HERE

Using all the research and analysis from this conversation, produce two deliverables:

### DELIVERABLE 1: Visual Carousel

A **6-slide branded image carousel** as a single React `.jsx` artifact. Each slide is **540×675px** (4:5 portrait ratio, optimised for Substack Notes thumbnail previews which crop square images at the sides). All 6 slides render inside a tab-switching gallery shell with a dark (#0e0e14) background, slide name tabs, and dot navigation.

**The 6 slides are:**

1. **COVER** — Company name, ticker, thesis subtitle, 5-box value chain pipeline, and 4 key metrics with deltas
2. **REVENUE ENGINE** — Flow diagram showing revenue segments → total revenue → cost structure → gross profit, with a key structural insight callout
3. **MARKET OPPORTUNITY** — Proportional treemap showing addressable market by segment and sub-market, sized by TAM ($M), with status indicators
4. **FLYWHEEL / MOAT** — Self-reinforcing competitive loop with 4–6 node cards around SVG rings, plus 3 sidebar moat insights. If the company has no clear flywheel, replace with a CATALYST TIMELINE (vertical timeline of upcoming binary events) or COMPETITIVE LANDSCAPE (comparison cards)
5. **WATERFALL** — Revenue-to-profit bridge with CSS bar chart. Revenue lines → COGS → Gross Profit → OpEx lines → Operating Income. Scale bar, percentage annotations, margin badges. For pre-revenue companies, use projected bull case figures or a Cash Burn Bridge
6. **SCENARIO TREE** — Probability-weighted bear/base/bull valuation with price targets, implied returns, driver assumptions, and risk/reward ratio

**Follow the Sterling Signals design system exactly** (full spec in Part 2 of this document):
- Fonts: Instrument Serif (headings), DM Sans (body), JetBrains Mono (numbers)
- Palette: Warm Editorial (green primary, blue secondary, purple tertiary, amber warning, red negative)
- CSS for ALL layout. SVG only for flywheel rings. Unicode arrows for flow direction.
- No interactivity — static, screenshot-ready output only
- Dot texture overlay, decorative corner, Sterling Signals footer on every slide
- Run the Quality Checklist before outputting

### DELIVERABLE 2: Substack Note

A ready-to-post Substack Note (plain text, ~150–250 words) designed to accompany the carousel when posted. The note should:

- **Open with a hook** — a surprising number, contrarian framing, or provocative question about the company. Never open with the company name or ticker.
- **Build the case in 3–4 sentences** — what the company does, why it matters now, and the key tension or catalyst
- **Reference the carousel** — "Swipe through for the full breakdown" or "The waterfall tells the story" — give readers a reason to engage with the images
- **Close with a question or forward-looking statement** — drive comments and engagement
- **Include 2–3 hashtags** at the end, relevant to the sector and investment theme
- **Tone:** First-person, data-forward, direct. No hedging language. No em dashes. Write like a confident analyst sharing with peers, not a marketer selling a product.
- **Banned terms:** Do not use: HMA, Banker, BoS, RSI, MACD, KDJ, "proprietary system", "our algorithm", or any reference to automated/AI tools. Use approved vocabulary only: "momentum", "structural setup", "institutional accumulation", "breakout confirmation".

Extract all data from this conversation. Do not hallucinate figures. Match the company's reporting currency throughout.

## END OF PROMPT

---

# PART 2: DESIGN SYSTEM REFERENCE

Everything below is the reference specification. Claude should follow this when executing the prompt above. You do not need to paste Part 2 into conversations — it serves as documentation and as a system prompt for Claude Code integration.

---

## 2.1 TYPOGRAPHY

```
Headings:     'Instrument Serif', Georgia, serif
Body/labels:  'DM Sans', -apple-system, sans-serif
Numbers/data: 'JetBrains Mono', monospace
```

Google Fonts import (include in every artifact):
```html
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

**Font size minimums:** Scale labels 7px, body text 7.5px+, data values 8px+, card labels 9px+, headings 10px+. Nothing below 7px.

---

## 2.2 COLOUR PALETTE

### Core

| Token | Value | Usage |
|-------|-------|-------|
| Background gradient | `linear-gradient(168deg, #fafaf5 0%, #f4f4ec 50%, #f0f0e6 100%)` | Every slide background |
| Card background | `#fff` | Card fills |
| Card border | `rgba(0,0,0,0.06)` | Default card stroke |
| Divider | `#d8d8cc` | Separator lines, footer borders |

### Text

| Token | Value | Usage |
|-------|-------|-------|
| Heading | `#1a3c2a` | Titles, primary labels, bold values |
| Subheading | `#2a5c3a` | Subtitles, secondary headings |
| Body | `#3a3a32` | Descriptive text, driver bullets |
| Muted | `#8a8a78` | Captions, supporting text |
| Faint | `#b8b8a8` | Scale labels, de-emphasised info |

### Semantic Colours

| Token | Solid | Background | Border | Usage |
|-------|-------|-----------|--------|-------|
| Green (primary) | `#1a5c3a` | `rgba(26,92,58,0.06)` | `rgba(26,92,58,0.18)` | Primary segment, positive, revenue, profit |
| Green medium | `#267a4a` | — | — | Subtotals, secondary positive |
| Green bright | `#2a8a50` | — | — | Tertiary positive, deltas |
| Blue | `#2a4a7a` | `rgba(42,74,122,0.06)` | `rgba(42,74,122,0.18)` | Secondary segment, base case, nuclear |
| Purple | `#5a3a7a` | `rgba(90,58,122,0.06)` | — | Tertiary segment, helium/alt |
| Amber | `#7a6020` | `rgba(122,96,32,0.07)` | — | Warnings, costs, caution, OpEx bars |
| Red | `#7a2a2a` | `rgba(122,42,42,0.06)` | — | Negative, COGS, losses, bear case |
| Red bar | `#9e4444` | — | — | COGS bars in waterfall |
| Amber bar | `#9a7040` | — | — | OpEx bars in waterfall |

### Colour Assignment Rules

- **Primary revenue segment** → Green (always)
- **Secondary segment** → Blue
- **Tertiary segment** → Purple
- **If only 2 segments:** Green + Blue
- **If 4+ segments:** Green, Blue, Purple, Amber (in that order)
- Revenue / profit / positive → Green
- COGS / cost of revenue → Red bar (#9e4444)
- Operating expenses → Amber bar (#9a7040)
- Bear case / losses → Red solid (#7a2a2a)
- Base case / neutral → Blue solid (#2a4a7a)
- Bull case / upside → Green solid (#1a5c3a)

---

## 2.3 SHARED VISUAL ELEMENTS

### Dot Texture Overlay (every slide)

```css
position: absolute; inset: 0; opacity: 0.012; pointer-events: none;
background-image: radial-gradient(circle at 1px 1px, #1a3c2a 0.5px, transparent 0);
background-size: 18px 18px;
```

### Decorative Corner Circle (every slide, top-right)

```css
position: absolute; top: -50px; right: -50px;
width: 140px; height: 140px; border-radius: 50%;
border: 1px solid rgba(26,92,58,0.18); opacity: 0.2;
```

### Tags

- Uppercase monospace, 7.5–8px, letter-spacing 2.5px, font-weight 500
- Coloured text on matching tinted background
- border-radius 2px, padding 3px 8px
- Maximum 2 tags per slide

### Footer (every slide)

Three-column flex layout separated by a 1px divider line above:
- Left: `STERLING SIGNALS` — monospace, 7px, letter-spacing 2, uppercase, faint colour
- Centre: `N / 6` — monospace, 8px, muted colour
- Right: `sterlingsignals.substack.com` — DM Sans, 8px, faint colour

---

## 2.4 ASPECT RATIO & SIZING

**Carousel slides: 540×675px (4:5 portrait)**

Substack Notes displays multi-image posts in a grid that crops images to approximately 4:5 portrait ratio in the thumbnail preview. Square (1:1) images lose content on both sides. The 4:5 ratio ensures all content — including tags, titles, and edge elements — remains visible in the Notes feed without cropping.

The extra vertical space (135px vs square) should be used for breathing room between content sections, not for cramming additional content. Keep the same information density as a tighter layout but with more comfortable spacing.

**Full-width article diagrams: 880×560px (landscape)**

For diagrams embedded within long-form Substack posts (not Notes), use a wider landscape format. These render inline at Substack's content width and are not subject to thumbnail cropping.

**Retina export:** When screenshotting or exporting via Playwright, use `deviceScaleFactor: 2` to produce a 1080×1350px PNG (2× resolution for crisp display on mobile).

---

## 2.5 ARCHITECTURE RULES

These prevent text overlap, clipping, and misalignment. Follow exactly.

1. **CSS for ALL layout.** Flexbox and grid for text, cards, rows, columns. Never use SVG `<text>` for data labels.
2. **SVG ONLY for:** concentric flywheel rings, directional arrow markers on rings, decorative circles, and connector dashes from ring to node cards. Nothing else.
3. **Unicode arrows** (→ ↓ ↘ ↙) for flow direction between HTML cards.
4. **Bars and charts** as positioned `<div>` elements using CSS percentage widths and `left` offsets. Grid lines as thin absolute-positioned divs, opacity 0.35.
5. **Each slide is a React component** wrapped in a shared `<Slide>` container providing: background gradient, dot texture, padding (32px sides, 32px top, 24px bottom), overflow hidden, and the content area as `flex: 1`.
6. **Tab-switching gallery shell** with dark (#0e0e14) background for viewing all slides.
7. **Flywheel node cards:** Absolutely-positioned HTML `<div>` elements with coordinates from angle math. Never SVG text.
8. **Minimum spacing:** 4px between all adjacent elements. Bar chart rows need 3px gap minimum.
9. **No interactivity.** No useState for hover/click. No animation. Every slide must look complete as initially rendered.
10. **Slide dimensions:** 540×675px (4:5 portrait). Padding: 32px sides, 32px top, 24px bottom. The extra 135px of vertical space vs square format should be distributed as additional breathing room between content sections, not crammed with more content. Keep the same information density as a 540×540 slide but with more comfortable vertical spacing.

---

# PART 3: SLIDE SPECIFICATIONS

Each slide specification defines what data to extract, how to lay it out, and what components to use.

---

## SLIDE 1 — COVER

### Data to Extract

| Field | Example |
|-------|---------|
| Company name | "ASP Isotopes" |
| Ticker + exchange | "NASDAQ: ASPI" |
| Thesis subtitle (1–2 lines) | "The Key Milestones That Will Determine Whether ASPI Becomes a $2B+ Critical Materials Platform" |
| Value chain pipeline (5 boxes) | Users → Conversions → Revenue → Costs → Profit |
| Key metric 1 + delta | "$4.1M Revenue · First commercial yr" |
| Key metric 2 + delta | "$660M Market Cap · Pre-revenue" |
| Key metric 3 + delta | "31.1% Gross Margin · +4.5pp" |
| Key metric 4 + delta | "$1.5B FCF · 1st positive yr" |

### Layout

```
[Tag 1] [Tag 2]                         ◯ decorative
                                            corner
Company Name     TICKER
Thesis subtitle (Instrument Serif italic)

┌─ Value Chain ──────────────────────────┐
│ [Box1] → [Box2] → [Box3] → [Box4] → [Box5] │
│ annotation line (italic, centred)      │
└────────────────────────────────────────┘

              <spacer flex:1>

 Metric1    Metric2    Metric3    Metric4
 Label      Label      Label      Label
 Delta      Delta      Delta      Delta

── STERLING SIGNALS ─── 1/6 ─── url ──
```

**Pipeline container:** Green background, green border, 8px border-radius. Inner label "Value Chain" in monospace 7.5px. Cards as flex row with → arrows between them. Below the cards, a centred italic annotation (e.g., "37% conversion · Royalties consume 69%").

**Stats grid:** 4-column CSS grid. Value in JetBrains Mono 16–17px bold. Label in DM Sans 9px. Delta in JetBrains Mono 7px, coloured appropriately (green for positive, amber for neutral context, red for negative).

---

## SLIDE 2 — REVENUE ENGINE

### Data to Extract

| Field | Example |
|-------|---------|
| Customer base / TAM | "640M Monthly Users" |
| Revenue segments (2–4) | Premium $11.6B (73%), Ad-Supported $1.8B (11%), Podcasts $0.8B (5%) |
| Total revenue + growth | "€15.7B (+19% YoY)" |
| Cost of revenue + % | "−€10.8B (69%)" with breakdown |
| Gross profit + margin | "€4.9B (31.1%)" with YoY delta |
| Key structural insight | "Label royalties are fixed % of revenue — margin only grows via mix shift" |
| OpEx + bottom line | "OpEx −€3.4B → FCF €1.5B" |

### Layout

```
[Tag]
Title (Instrument Serif)
Subtitle (DM Sans muted)

     ┌──── Customer/TAM Card ────┐
     └───────────────────────────┘
              ↓  ↓  ↓
  ┌─ Seg 1 ─┐ ┌─ Seg 2 ─┐ ┌─ Seg 3 ─┐
  │ HEADER   │ │ HEADER   │ │ HEADER   │
  │ $value   │ │ $value   │ │ $value   │
  │ detail   │ │ detail   │ │ detail   │
  └──────────┘ └──────────┘ └──────────┘
           ↘     ↓     ↙
     ┌─── Total Revenue Card ───┐
     │    $15.7B (+19%)         │
     └──────────────────────────┘
           ↙           ↘
  ┌─ Cost of Rev ─┐ ┌─ Gross Profit ─┐
  │ red-tinted     │ │ green-tinted    │
  │ −€10.8B (69%) │ │ €4.9B (31.1%)  │
  │ breakdown      │ │ +4.5pp YoY     │
  └────────────────┘ └────────────────┘

  ┌─ KEY INSIGHT ──┐ ┌ OpEx ┐ → ┌ FCF ┐
  │ amber border   │ │      │   │     │
  └────────────────┘ └──────┘   └─────┘

── STERLING SIGNALS ─── 2/6 ─── url ──
```

**Segment cards:** CSS grid row. Each has a coloured header bar (full-width, white text, monospace) and white body with value + detail. Green for primary, amber for secondary, blue for tertiary.

**Key Insight:** Amber left-border callout, 7.5px monospace label, 8px body text.

---

## SLIDE 3 — MARKET OPPORTUNITY (Treemap)

### Data to Extract

| Field | Example |
|-------|---------|
| Top-level segments (2–4) | Nuclear Fuels $8B, Helium $5B, Isotopes $2.2B |
| Sub-markets per segment (2–5) | HALEU $6B, LEU+ $1.5B, Li-7 $500M |
| Status per sub-market | "✅ Shipping", "⏳ Pre-commercial", "🔧 R&D" |

### Layout

CSS flexbox blocks sized proportionally by TAM. The largest segment gets the most visual real estate.

**If one segment is >50% of total:** Full left column (flex: 5), stack others vertically in right column (flex: 4).

**Block anatomy:** Coloured header bar (label + total $), optional sub-note, then flex row of sub-market cards inside.

**Sub-market cards:** flex: 1, padding 8px, large value (JetBrains Mono 13px bold), label (DM Sans 8.5px bold), status emoji + text (monospace 7px in segment colour).

---

## SLIDE 4 — FLYWHEEL / MOAT

### Data to Extract

| Field | Example |
|-------|---------|
| Nodes (4–6) | "Isotope Revenue: $50–70M pipeline — Funds operations, proves tech" |
| Sidebar insights (3) | "🔒 Switching Cost: Proprietary ASP + QE tech..." |
| Subtitle | "Why competitors can't replicate this" |

### Layout (Flywheel)

Two areas: SVG flywheel (left, ~65% width) + insight sidebar (right, ~35%).

**SVG elements (the ONLY SVG):**
- Outer glow ring: r+22, strokeOpacity 0.03, strokeWidth 18
- Main ring: r (108), strokeOpacity 0.09, strokeWidth 18
- Inner dashed ring: r-16, strokeOpacity 0.05, dasharray "4 3"
- 5 directional arrow markers on the main ring
- 5 connector dashes from ring to node positions

**Node cards:** HTML divs at `(cx + (r+70) × cos(angle), cy + (r+70) × sin(angle))`. Width 128px, white bg, 3px left colour border. Three lines: label (9.5px bold), metric (9px mono bold), detail (7.5px muted).

**Centre:** "FLYWHEEL" monospace 7px + "compounds" 7px muted.

### Alternative: Catalyst Timeline

For companies without a flywheel. Vertical timeline with:
- Date column (left, 58px, right-aligned)
- 2.5px vertical gradient line
- Coloured dots (10px normal, 14px for imminent/critical)
- Event cards with segment tags
- Status legend sidebar

### Alternative: Competitive Landscape

For differentiated positioning. Comparison cards or 2×2 quadrant grid.

---

## SLIDE 5 — WATERFALL

### Data to Extract

| Field | Example |
|-------|---------|
| Revenue lines (1–4) | Isotope Rev $45M, Helium Rev $80M, Nuclear Rev $15M |
| Total Revenue | $140M |
| COGS | $56M (40%) |
| Gross Profit | $84M (60%) |
| OpEx lines (2–4) | R&D $18M (13%), SGA $12M (9%), D&A $8M (6%) |
| Operating Income | $46M |
| Gross margin % | 60% |
| Operating margin % | 33% |
| Trend | "↑ First profitable year" |

### Layout

```
[Tag]
Title
Subtitle
                                          Scale bar
$0M      $40M      $80M      $120M     $160M

  Label    %  |████████████████████| $val  ← Revenue (green)
  Label    %     |████████| −$val          ← COGS (red)
  ─────────────────────────────────────────
  Label       |████████████| $val          ← Gross Profit (green)
  Label   %      |████| −$val             ← OpEx (amber)
  Label   %    |██| −$val                 ← OpEx (amber)
  ─────────────────────────────────────────
  Label       |██████| $val               ← Op Income (green)

  [60% Gross] [33% Operating] ↑ trend

── STERLING SIGNALS ─── 5/6 ─── url ──
```

**Row anatomy:** Label (100px, right-aligned) + % annotation (22px) + bar area (flex: 1, position: relative).

**Bar positioning:** `left` = cumLeft as % of max, `width` = value as % of max. Revenue and totals start at 0. Costs start at (previous total − cumulative costs).

**Value labels:** Inside bar (white, centered) if bar > ~15% of max. Outside bar (coloured, 6px right of bar end) if narrower.

**Grid lines:** 5 vertical lines at 0/25/50/75/100% of scale, opacity 0.35.

**Separators:** 1px divider before Gross Profit and Operating Income rows.

**Pre-revenue adaptation:** Replace with Cash Burn Bridge or projected bull case.

---

## SLIDE 6 — SCENARIO TREE

### Data to Extract

| Field | Example |
|-------|---------|
| Current price | $5.30 |
| Bear case: probability, target, return, EV, basis, 4 drivers | 30%, $2.00, −62%, $250M, "Cash floor", [...] |
| Base case: same fields | 45%, $8.00, +51%, $1.0B, "20× rev", [...] |
| Bull case: same fields | 25%, $14.00, +164%, $1.75B, "35× rev", [...] |

### Layout

```
[Tag]
Title
Subtitle

┌─ Current ─┬─ Weighted ─┬─ Implied ──┬─ Risk/Reward ─┐
│  $5.30     │  $7.10     │  +34%      │  2.6 : 1      │
└────────────┴────────────┴────────────┴───────────────┘

┌── BULL ──┐  ┌── BASE ──┐  ┌── BEAR ──┐
│ green hdr│  │ blue hdr │  │ red hdr  │
│ $14.00   │  │ $8.00    │  │ $2.00    │
│ +164%    │  │ +51%     │  │ −62%     │
│ ▓▓▓░░ 25%│  │ ▓▓▓▓░ 45%│  │ ▓▓▓░░ 30%│
│ • driver │  │ • driver │  │ • driver │
│ • driver │  │ • driver │  │ • driver │
│ • driver │  │ • driver │  │ • driver │
│ • driver │  │ • driver │  │ • driver │
└──────────┘  └──────────┘  └──────────┘

┌─ RISK/REWARD ── amber ──────────────────┐
│ Bull upside vs Bear downside = X:1 ratio │
└─────────────────────────────────────────┘

── STERLING SIGNALS ─── 6/6 ─── url ──
```

**Header bar:** 4-column flex. Large monospace values (22px), small uppercase labels. Current Price in heading colour, Weighted Target in blue, Implied Return in green, Risk/Reward in green.

**Scenario cards:** CSS grid 1fr 1fr 1fr. Coloured header with name + probability %. Body: large target (30px), return %, EV + basis, probability bar (5px height), then 4 driver bullets.

**Bottom callout:** Amber background, left amber border. Shows ratio calculation. "Asymmetric" badge if >2:1.

---

# PART 4: SUBSTACK NOTE WRITING GUIDE

The Substack Note accompanies the carousel when posted. It is the text that appears above/alongside the images in the Notes feed.

### Structure (150–250 words)

1. **Hook (1 sentence):** Surprising number, contrarian take, or question. Never open with company name.
2. **Context (2–3 sentences):** What the company does, why now, what's at stake.
3. **Carousel callout (1 sentence):** Reference the visual content. "Swipe through for the full breakdown."
4. **Close (1 sentence):** Question or forward-looking statement to drive engagement.
5. **Hashtags (2–3):** Sector and theme relevant.

### Voice Rules

- First person ("I", "we" when referring to the portfolio)
- Data-forward: every claim has a specific number attached
- Direct and confident, not hedged
- Deliberate sentence length variation (short punchy + longer analytical)
- No em dashes anywhere
- American English spellings (realize, analyze, etc.)
- ET timezone for all time references

### Banned Terms

Never use: HMA, Banker, BoS, RSI, MACD, KDJ, "proprietary system", "our algorithm", "deep learning", "AI-powered", any reference to automated tools or LLMs. Never mention the scanner or system internals.

### Approved Vocabulary

Use instead: "momentum", "structural setup", "institutional accumulation", "breakout confirmation", "sector rotation", "position sizing", "risk/reward", "asymmetric", "catalyst", "thesis".

### Example Note

```
A $660M market cap on $4 million of revenue.

That's ASP Isotopes (ASPI) today. Three operational enrichment
facilities in South Africa. Silicon-28 shipping to semiconductor
customers. A $750M debt facility backing their Renergen helium
acquisition. And a HALEU nuclear fuel play that positions them
as one of very few Western suppliers ahead of the 2028 Russian
uranium import ban.

The bull case writes itself. The question is execution across
three business lines simultaneously, each at a different stage
of commercialisation. Isotopes are generating cash now. Helium
targets positive cash flow by end-2026. Nuclear fuels remain
pre-commercial through at least 2027.

Swipe through for the full visual breakdown: capital flow,
market opportunity sizing, milestone timeline, and the
probability-weighted scenario analysis.

The FY 2025 earnings report drops March 30. That's the next
real data point. What are you watching for?

#NuclearEnergy #CriticalMaterials #ASPI
```

---

# PART 5: ADAPTATION GUIDE

### By Company Type

| Company Type | Slide 2 | Slide 3 | Slide 4 | Slide 5 |
|-------------|---------|---------|---------|---------|
| **Multi-segment (SPOT, ASPI)** | Revenue Engine | Treemap | Flywheel | Waterfall |
| **Pre-revenue / early stage** | Go-to-Market Architecture | Treemap (TAM) | Catalyst Timeline | Cash Burn Bridge |
| **Biotech / catalyst-driven** | Pipeline Diagram (Phase 1/2/3) | Treemap (TAM) | Catalyst Timeline | Funding Bridge |
| **SaaS / subscription** | Revenue Engine | Treemap (ARR by segment) | Growth Flywheel | Waterfall |
| **Mature / value** | Revenue Engine | Treemap (revenue mix) | Moat / Competitive Landscape | Waterfall (actual, not projected) |
| **Commodity / cyclical** | Revenue Engine | Market share / positioning | Catalyst Timeline | Waterfall + cycle positioning |

### Currency

Match reporting currency ($, €, £, A$). Consistent across all 6 slides.

### Scale (Waterfall)

- Sub-$100M revenue → max scale nearest $20M ($0–$120M)
- $100M–$1B → nearest $200M ($0–$1.2B)
- $1B+ → nearest $2B ($0–$16B)

### Segments

- 1–2 segments: Wider cards, merge flow into fewer nodes
- 3–4 segments: Default layout (recommended)
- 5+ segments: Top 3–4 + "Other" grouping

### Colour Assignment

When a company has different segments than the original examples, assign consistently:
- Primary revenue driver → Green (always)
- Growth / speculative → Blue
- Acquired / tertiary → Purple
- If only 2 segments: Green + Blue

---

# PART 6: QUALITY CHECKLIST

Run before delivering. Every item must pass.

### Layout
- [ ] No text overlaps at 540×675
- [ ] All elements have ≥4px spacing from neighbours
- [ ] All text ≥7px font size
- [ ] Slides fit within 540×675 with no clipping
- [ ] Footer on every slide with correct slide number (N/6)

### Typography
- [ ] Headings: Instrument Serif
- [ ] Body: DM Sans
- [ ] Numbers: JetBrains Mono
- [ ] Google Fonts link included

### Colour
- [ ] Green = positive, Red = negative, Amber = warning, Blue = secondary
- [ ] Segment colours consistent across all 6 slides
- [ ] Tags are monospace uppercase with correct letter-spacing

### Visual
- [ ] Dot texture overlay on every slide
- [ ] Decorative corner circle on every slide
- [ ] No SVG `<text>` elements for data (except flywheel centre label)

### Data
- [ ] All figures match the research conversation
- [ ] Currency consistent throughout
- [ ] Percentages sum correctly (segments = ~100%, probabilities = 100%)
- [ ] Waterfall cumulative bar positions are mathematically correct
- [ ] Weighted target = Σ(probability × price target)

### Note
- [ ] Opens with hook, not company name
- [ ] 150–250 words
- [ ] No banned terms
- [ ] References the carousel
- [ ] Includes 2–3 hashtags
- [ ] No em dashes

---

# PART 7: QUICK REFERENCE

### Prompt Templates

**Full set (6 slides + note):** Use the prompt in Part 1.

**Single slide only:**
```
Produce a static [SLIDE TYPE] slide for [COMPANY] at 540×675px (4:5 portrait) using
the Sterling Signals Warm Editorial design system. Extract data from
this conversation. Instrument Serif headings, DM Sans body, JetBrains
Mono numbers. CSS layout only, no interactivity, screenshot-ready.
```

**Diagrams at larger size (for articles, not Notes):**
```
Same as above but use 880×560px DiagramFrame instead of 540×675
Slide container. Adjust font sizes proportionally (+2px across
the board). These are for embedding in long-form Substack posts.
```

### File Naming Convention

```
{ticker}-carousel-{date}.jsx       → Full 6-slide carousel
{ticker}-note-{date}.md            → Accompanying Substack Note
{ticker}-diagram-{type}-{date}.jsx → Single diagram
```

---

*Sterling Signals · sterlingsignals.substack.com*
*Visual Content Production System v2.1 · March 2026*

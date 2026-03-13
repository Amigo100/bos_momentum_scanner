# Animated Business Model Flow Diagram — Design Specification

## Purpose
This document defines exact rules for building animated HTML business model diagrams designed for screen-recording as Substack video content. Attach this to any new Claude conversation where you need a business model diagram for a specific company.

---

## 1. Frame & Canvas

- **Fixed dimensions**: 1280 × 720px (16:9, standard HD)
- **Background**: `#111318` (dark charcoal, not pure black)
- **Body background**: `#000` (pure black — frame sits centered on this)
- **Frame must have `overflow: hidden`**
- **Dot grid overlay** via `::before` pseudo-element:
  ```css
  background-image: radial-gradient(circle, rgba(255,255,255,.025) 1px, transparent 1px);
  background-size: 28px 28px;
  ```
- **Everything must fit within the 1280×720 frame** — no scrolling, no overflow. The entire diagram is visible at all times. This is not a webpage; it is a fixed canvas for video capture.

---

## 2. Layout Planning — MANDATORY FIRST STEP

Before writing any HTML, plan the full pixel-exact layout as an ASCII grid comment. This prevents overlap, ensures routing channels exist, and catches spatial conflicts before they become visual bugs.

### Column + Channel Architecture
The layout uses **columns** (where boxes live) separated by **routing channels** (where connector lines run). Lines ONLY travel through channels, never through boxes.

```
┌────────────────────────────────────────────────────────────────────┐
│  Title bar (y=10..48)                                              │
│                                                                    │
│  COL1          CHAN_A    COL2          CHAN_B    COL3     CHAN_C COL4│
│  ┌─────┐      ║         ┌─────┐      ║         ┌─────┐       ┌──┐│
│  │Box A│──────╫────────→│Box D│──────╫────────→│Box G│──────→│H ││
│  └─────┘      ║         └─────┘      ║         └─────┘       └──┘│
│               ║         ┌─────┐      ║         ┌─────┐           │
│  ┌─────┐      ║    ┌───→│Box E│──────╫────┐    │Box I│           │
│  │Box B│──────╫────┘    └─────┘      ║    └───→│     │           │
│  └─────┘      ║         ┌─────┐      ║         └─────┘           │
│               ║    ┌───→│Box F│──────╫─────────────┘             │
│               ║    │    └─────┘      ║                            │
│               loop │                  ║                            │
│  ◄────────────gutter──────────────────────────────────────────────┤
│  Footer / loop-back line (y=618)                                   │
└────────────────────────────────────────────────────────────────────┘
```

### Spacing Rules
- **Title area**: y=10 to y=48 (reserved, no boxes here)
- **Box region starts**: y=56
- **Minimum gap between boxes vertically**: 20px
- **Minimum channel width**: 80px (gives room for 2-3 parallel vertical line runs)
- **Parallel lines in same channel**: space 30px apart (e.g., x=270 and x=305)
- **Loop-back gutter**: must clear BOTH frame edges AND all box regions
  - Bottom run: y ≤ 618 (102px above frame bottom)
  - Left run: x must be **less than** the leftmost box's x-position minus 20px.
    If the leftmost box starts at x=40, the left gutter must be x ≤ 20.
    The old rule (x ≥ 60) assumed no boxes in the left margin — this is WRONG
    when Column 1 starts at x=40.
  - **⛔ CRITICAL**: After computing the loop-back path, verify that every
    segment's x,y coordinates do NOT pass through any box's bounding rectangle
    (left, top, left+width, top+height). This is the single most common
    routing bug — the loop-back line clips through a bottom-left box.
- **Last box bottom edge**: must be at least 50px above the loop-back bottom line

### Box Sizing
- Every box gets an **explicit width AND height** in pixels
- Height must be tested against actual content — title + icons + KPI strip
- Typical heights: 140-210px depending on content density
- Use `padding: 10px 12px` inside each box

---

## 3. Box Design (Section Containers)

### Structure
```html
<div class="bx b-COLOR" style="left:Xpx; top:Ypx; width:Wpx; height:Hpx;">
  <div class="bt">Section Title</div>
  <div class="icons">
    <div class="ic"><div class="d d-COLOR">EMOJI</div><div class="t">Label</div></div>
    <!-- more items -->
  </div>
  <div class="kpi">KEY METRIC · <b>$VALUE</b></div>
</div>
```

### Styling
- **Border**: `2px dashed` with color-coded alpha (e.g., `rgba(52,211,153,0.4)`)
- **Border radius**: `12px`
- **Background**: transparent (inherits from frame)
- **z-index**: `3`
- **Icon tiles**: 42×42px, `border-radius: 9px`, tinted background at 14% opacity
- **Icon emoji**: 22px font-size
- **Labels**: 8.5px, weight 600, `rgba(255,255,255,0.55)`
- **KPI strip**: monospace, 9px, dark background `rgba(255,255,255,0.035)`, key values in white bold

### Color Palette (6 segment colors)
```css
/* Cyan — core technology / primary */
.b-cy  { border-color: rgba(56,189,248,.4); }
.b-cy .bt { color: #7dd3fc; }
.d-cy  { background: rgba(56,189,248,.14); }

/* Green — healthcare / medicine */
.b-gr  { border-color: rgba(52,211,153,.4); }
.d-gr  { background: rgba(52,211,153,.14); }

/* Purple — technology / semiconductors */
.b-pu  { border-color: rgba(167,139,250,.4); }
.d-pu  { background: rgba(167,139,250,.14); }

/* Orange — energy / industrial */
.b-or  { border-color: rgba(251,146,60,.4); }
.d-or  { background: rgba(251,146,60,.14); }

/* Yellow/Gold — revenue / financials / flywheel */
.b-yl  { border-color: rgba(250,204,21,.3); }
.d-yl  { background: rgba(250,204,21,.12); }

/* Pink — strategic / future / pending (always dashed) */
.b-pk  { border-color: rgba(244,114,182,.3); }
.d-pk  { background: rgba(244,114,182,.12); }
```

### Box Color Guide by Business Function

Assign colors based on what the box represents in the business model. This creates instant visual hierarchy — readers see revenue (green), technology (cyan), and future pipeline (pink) without reading labels.

| Business Function | CSS Class | When to Use | Example Boxes |
|---|---|---|---|
| **Core Technology / IP** | `b-cy` (cyan) | The company's competitive advantage, patents, platform | "Core Tech", "IP & Spectrum", "Platform" |
| **Revenue Segments** | `b-gr` (green) | Active revenue-generating business lines | "Direct-to-Device", "Enterprise", "Licensing" |
| **Growth / R&D Pipeline** | `b-pu` (purple) | Pre-revenue segments, R&D, upcoming launches | "Pipeline", "Phase 3 Trials", "Next-Gen Products" |
| **Industrial / Infrastructure** | `b-or` (orange) | Physical assets, manufacturing, operations | "Production Facility", "Supply Chain", "Deployments" |
| **Revenue / Financials / Flywheel** | `b-yl` (gold) | Aggregate revenue, financial summary, compounding loops | "Revenue Engine", "Flywheel", "Capital Allocation" |
| **Strategic / Future / Pending** | `b-pk` (pink) | Items that haven't materialised yet — dashed border signals uncertainty | "Strategic Pipeline", "Pending Contracts", "Regulatory Approvals" |

**Rules:**
- Every diagram should use at least 3 different colors to create visual variety
- Core Tech is almost always cyan (left column) — it's the anchor
- Revenue summaries are almost always gold (right column) — it's the destination
- Pink is always dashed border — it visually signals "not yet confirmed"
- Green boxes should contain revenue KPIs ($M or growth rates)
- Purple boxes should contain pipeline KPIs (dates, probabilities, counts)

### Optional: Glow Pulse on Primary Box
```css
.glow::after {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 12px;
  border: 1.5px solid #38bdf8;
  opacity: 0;
  animation: gp 3s ease-in-out infinite;
  pointer-events: none;
}
@keyframes gp { 0%,100%{opacity:0} 50%{opacity:0.25} }
```

---

## 4. SVG Connector Lines — CRITICAL RULES

The SVG layer renders ALL connector lines. This is where most bugs occur. Follow every rule precisely.

### Layer Setup
```css
.svg-layer {
  position: absolute;
  z-index: 10;          /* MUST be above boxes (z-index 3) */
  pointer-events: none;
  overflow: visible;
}
```
The SVG element:
```html
<svg class="svg-layer" style="left:0;top:0;width:1280px;height:720px;"
     viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">
```

### ⛔ CRITICAL: Path Definitions MUST Be Inside `<defs>`

**This is the single most important rule in this document.**

SVG `<path>` elements placed directly in the SVG body render with `fill: black` by default. For L-shaped or multi-segment paths, SVG connects the start and end points and fills the enclosed area as a solid black shape. This creates massive black triangles/rectangles that obscure the diagram.

```html
<!-- ✅ CORRECT — paths inside <defs> are never rendered directly -->
<defs>
  <path id="p1" d="M224,125 L350,125"/>
  <path id="p2" d="M224,165 L270,165 L270,295 L350,295"/>
</defs>
<use href="#p1" class="sline" stroke="#38bdf8"/>
<use href="#p1" class="fline f1" stroke="#38bdf8"/>

<!-- ❌ WRONG — path renders as black filled shape -->
<path id="p1" d="M224,165 L270,165 L270,295 L350,295"/>
<use href="#p1" class="sline" stroke="#38bdf8"/>
```

### ⛔ NEVER Use SVG `<filter>` Elements

SVG filters (`feGaussianBlur`, `feMerge`, etc.) cause black rectangular artifacts when applied to elements that animate between `opacity: 0` and `opacity: 1`. The filter's bounding box renders as opaque black during the zero-opacity phase.

**Use CSS `filter: drop-shadow()` instead** — it handles opacity transitions correctly:
```css
/* ✅ CORRECT */
.td { filter: drop-shadow(0 0 6px currentColor); }

/* ❌ WRONG — creates black artifacts */
.td { filter: url(#svgGlowFilter); }
```

### Line Routing Rules
1. **All lines are orthogonal** — horizontal and vertical segments only, using `M` and `L` commands. No curves (`C`, `Q`, `A`).
2. **Lines ONLY travel through routing channels** — never through any box region.
3. **Lines turn at right angles** — e.g., exit box right, go horizontal to channel x-position, turn down, go vertical to target y, turn right, enter target box.
4. **Parallel lines in same channel** use different x-positions (spaced 30px apart) to avoid overlap.
5. **Arrowhead triangles** are placed at the destination end of each line.

### Path Coordinate Rules
- **Exit coordinates**: Use the box's right edge x-value (left + width) for horizontal exits, bottom edge y-value (top + height) for vertical exits.
- **Entry coordinates**: Use the box's left edge x-value for right-pointing arrows, top edge y-value for down-pointing arrows.
- **Y-coordinates for exit**: Space them vertically within the source box (e.g., y=125, y=165, y=200 for three lines exiting a single box).

---

## 5. Animations — Three Layers Per Connector

Each connector line has exactly three visual layers:

### Layer 1: Static Dashed Base Line
```css
.sline {
  fill: none;
  stroke-width: 2;
  stroke-dasharray: 6 6;
  opacity: 0.22;
}
```

### Layer 2: Animated Flowing Dashes
Dashes that move in the direction of flow via `stroke-dashoffset` animation:
```css
.fline {
  fill: none;
  stroke-width: 2;
  stroke-dasharray: 8 18;
  stroke-linecap: round;
  opacity: 0.7;
}
@keyframes dsh { to { stroke-dashoffset: -52; } }

/* Each line gets unique timing + delay for organic feel */
.f1 { animation: dsh 2.2s linear infinite; }
.f2 { animation: dsh 2.4s linear infinite; animation-delay: 0.35s; }
/* ... etc */
```

### Layer 3: Traveling Glowing Dot
A circle that moves along the path using CSS `offset-path`:
```html
<circle class="td a s0" r="4" fill="#38bdf8"
  style="offset-path: path('M224,125 L350,125')"/>
```
```css
.td {
  opacity: 0;
  filter: drop-shadow(0 0 6px currentColor);  /* CSS glow, NOT SVG filter */
}
.td.a { animation: mv 2.8s ease-in-out infinite; }

@keyframes mv {
  0%   { offset-distance: 0%;   opacity: 0; }
  6%   { opacity: 0.95; }
  90%  { opacity: 0.95; }
  100% { offset-distance: 100%; opacity: 0; }
}
```

### Staggering
Give each dot a unique animation-delay class so they don't all pulse in sync:
```css
.s0 { animation-delay: 0s !important; }
.s1 { animation-delay: 0.4s !important; }
.s2 { animation-delay: 0.8s !important; }
/* ... assign one per connector line */
```

### Arrowheads
Small filled triangles at the destination end:
```html
<!-- Pointing left (entering box from right) -->
<polygon class="ah" points="350,119 338,125 350,131" fill="#38bdf8"/>

<!-- Pointing up (entering box from below) -->
<polygon class="ah" points="833,242 839,232 845,242" fill="#fbbf24"/>
```
```css
.ah { opacity: 0.65; }
```

---

## 6. Loop-Back (Flywheel → Source) Line

Most business model diagrams have a reinforcing loop. This line runs along the outer edges of the frame:

```
Source box bottom → down to bottom gutter → left to left gutter → up to target → into target box
```

### Rules
- Bottom gutter: y=618 maximum (keeps 102px clearance from 720px frame edge)
- Left gutter: x must be **less than the leftmost box's x-position minus 20px**.
  Example: if Column 1 boxes start at x=40, the left gutter runs at x=20.
  The line must NEVER share x-coordinates with any box region.
- The loop-back path must not pass through any box — verify by checking every
  segment against every box's bounding rectangle
- Use gold/yellow color for flywheel/reinforcement loops
- Add a text label along the bottom run:
  ```html
  <text x="440" y="612" font-family="'IBM Plex Mono',monospace" font-size="9"
    fill="#fbbf24" opacity=".45" letter-spacing="1.5" text-anchor="middle">
    REINVEST → COMPOUND → SCALE
  </text>
  ```

---

## 7. Typography & Visibility

All text must be clearly legible against the `#111318` background. The values below were tuned specifically for this dark theme — earlier iterations were too dim.

- **Font stack**: `'IBM Plex Sans'` for body, `'IBM Plex Mono'` for KPIs, tickers, labels
- **Load via Google Fonts**: `@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');`
- **Title**: 17px bold `#fff`
- **Title subtitle**: 10px, `rgba(255,255,255,0.5)`, weight 500
- **Ticker**: 10px monospace, `#38bdf8` (cyan), letter-spacing 2.5px
- **Box titles**: 14px bold, color-matched to segment accent
- **Box subtitles** (`<small>`): 9.5px, weight 500, opacity `0.55`
- **Icon labels**: 8.5px, weight 600, `rgba(255,255,255,0.8)`
- **KPI text**: 10px monospace, `rgba(255,255,255,0.75)`, key values in `#fff` bold. 10px is the minimum — 9px is too dim after MP4 encoding.
- **KPI background**: `rgba(255,255,255,0.05)`
- **Box borders (default)**: `rgba(255,255,255,0.25)` dashed
- **Box borders (colored)**: `0.4–0.5` alpha on the segment color
- **Static connector lines**: opacity `0.22`
- **Animated flowing dashes**: opacity `0.7`
- **Arrowheads**: opacity `0.65`
- **Loop-back label**: opacity `0.45`
- **Title bar z-index**: `15` (above all boxes to prevent overlap)

### ⛔ Common Visibility Mistake
Early iterations used 35-55% opacity for text and 15-18% for borders. These are nearly invisible on the dark background, especially after MP4 encoding which loses some contrast. Use the values above as minimums.

---

## 8. Content Structure for Business Models

### Typical Sections to Include
1. **Core Technology / Competitive Advantage** (left column) — what makes the company unique
2. **Business Segments** (center column, stacked vertically) — 2-4 revenue-generating segments
3. **Revenue / Financials** (right column, top) — TTM revenue, projections, cash, targets
4. **Growth Flywheel** (right column, below revenue) — the compounding loop
5. **Strategic Pipeline** (far right or bottom) — pending/future moves (dashed pink border)
6. **Geographic Footprint** (below core tech, optional) — operational locations with flag emojis

### Flow Direction
Left → Right: Technology → Segments → Revenue → Strategy
Bottom loop: Revenue/Flywheel → back to Core Technology (reinforcement)

### KPI Selection Priority

Each box should have 1-3 KPIs in its KPI strip. Choose from the company's researched data in this priority order:

| Priority | KPI Type | Format | Example |
|---|---|---|---|
| 1 | Revenue or contract value | `$XM` or `$XB` | `TTM Rev · $42M` |
| 2 | Growth rate | `+X% YoY` or `+X% QoQ` | `Growth · +340% YoY` |
| 3 | Market share or penetration | `X% of TAM` | `Penetration · 2.3% of $1.1T TAM` |
| 4 | Unit count | Number + label | `47 Patents · 5 Launches Pending` |
| 5 | Timeline | Date + milestone | `FDA Decision · Jun 2026` |
| 6 | Financial health | `$XM cash` or ratio | `Cash · $265M · Zero Debt` |

**AVOID vague KPIs:**
- ❌ `Revenue: Growing` → ✅ `TTM Rev · $42M (+340% YoY)`
- ❌ `Market: Large` → ✅ `TAM · $1.1T by 2030`
- ❌ `Strong Pipeline` → ✅ `Pipeline · 4 Contracts ($180M)`
- ❌ `Institutional Interest` → ✅ `13F Buyers · +16% QoQ`

Every KPI must be a specific number sourced from the Deep Dive research stage. If you don't have a number, search for it before building the diagram — never leave a box without at least one quantified KPI.

### Research-First Workflow

**Never build a diagram from memory or assumptions.** The quality of the diagram is directly proportional to the quality of the research that precedes it.

Before writing any HTML, you must have:
1. **Revenue segments** — how many, what each does, approximate revenue per segment
2. **Key metrics per segment** — at least one quantified KPI per box
3. **Strategic pipeline** — what's coming next, with dates if available
4. **Flywheel dynamics** — what compounds? Users → data → better product → more users?
5. **Financial snapshot** — TTM revenue, cash, debt, burn rate (if pre-profit)

The Sunday planner's prompt kit includes a diagram prompt that says "Web search for $TICKER business model." Execute that search thoroughly — the diagram will be exactly as good as the data you find.

---

## 9. Exporting to MP4 / GIF for Substack

### Why Not Screen Recording?
Screen recording introduces frame rate inconsistency, requires manual cropping to exactly 1280×720, and can't guarantee smooth animation timing. Use the automated capture script instead.

### The Capture Script (`capture.py`)

The script uses Playwright (headless Chromium) to take frame-perfect screenshots with controlled animation timing, then stitches them into MP4/GIF via ffmpeg.

#### Requirements
```bash
pip install playwright
playwright install chromium
# ffmpeg must be installed (brew install ffmpeg / apt install ffmpeg)
```

#### Usage
```bash
# Both MP4 and GIF (default, 8 seconds at 30fps)
python capture.py diagram.html

# MP4 only, 10 seconds
python capture.py diagram.html --duration 10 --format mp4

# Custom frame rate
python capture.py diagram.html --fps 24 --format mp4
```

#### Recommended Settings
- **Duration**: 8 seconds (covers 3 full animation cycles for most diagrams)
- **FPS**: 30 (smooth enough for the dashed-line animations, reasonable file size)
- **Format**: MP4 for Substack video upload, GIF if you need auto-play as an image

### ⛔ CRITICAL: Animation Clock Control

The script MUST control the browser's animation clock. Without this, animations play in real time while screenshots take 30-80ms each. The result is that a "30fps" capture actually records animation at 2-4× real speed.

**How it works:**
1. Page loads normally, fonts render, animations start
2. Script pauses ALL CSS animations via `document.getAnimations().forEach(a => a.pause())`
3. For each frame, script sets `animation.currentTime` to the exact millisecond for that frame
4. Screenshot is taken while animation is frozen at the correct moment
5. Playback at the target FPS produces animation at exactly the same speed as the browser

```javascript
// Core clock control logic (injected into the page)
const anims = document.getAnimations();
anims.forEach(a => a.pause());

window.__setTime = (ms) => {
  document.getAnimations().forEach(a => {
    const t = a.effect.getTiming();
    const dur = t.duration || 1000;
    const del = t.delay || 0;
    if (t.iterations === Infinity) {
      const local = ms - del;
      a.currentTime = local >= 0 ? del + (local % dur) : 0;
    } else {
      a.currentTime = Math.min(ms, (dur + del) * (t.iterations || 1));
    }
  });
};
```

**Without clock control**: animations run 2-4× too fast in the exported video.
**With clock control**: MP4 playback speed matches the HTML exactly.

### Output File Sizes (typical)
- **MP4** (30fps, 8s, 1280×720): 0.4–0.6 MB
- **GIF** (15fps, 8s, 1280×720): 0.6–1.0 MB

### Uploading to Substack
- **As native video**: Upload the MP4 via the video button in the post editor. It will loop on web but not in email (email shows a static thumbnail).
- **As GIF image**: Drag the GIF into the post as an image. Auto-plays and loops on both web and email. Larger file size but more engagement.
- **For Notes**: Attach the MP4 when composing a note. Video plays inline in the feed.

---

## 10. Checklist Before Finalizing

### Layout & Structure
- [ ] All boxes have explicit `width` AND `height` in pixels
- [ ] No box content overflows its container
- [ ] ASCII layout map is present as HTML comment
- [ ] Title bar z-index is 15 (above boxes) and positioned at y ≤ 4px so subtitle clears box tops
- [ ] At least 3 different box colors used for visual hierarchy
- [ ] Color assignments follow the Business Function guide (cyan=tech, green=revenue, etc.)

### Research & Content
- [ ] Every box has at least one quantified KPI (not "Growing" — a specific number)
- [ ] All KPIs sourced from actual research (SEC filings, earnings, press releases)
- [ ] Revenue segments match the company's actual business lines (not guessed)
- [ ] Pipeline items have dates or probability estimates where available

### SVG — The Danger Zone
- [ ] All `<path>` elements are inside `<defs>`, never in SVG body directly
- [ ] No SVG `<filter>` elements anywhere (use CSS `drop-shadow` instead)
- [ ] SVG layer z-index (10) is above box z-index (3)
- [ ] SVG has `overflow: visible` in CSS

### Line Routing
- [ ] All lines are orthogonal (only `M` and `L` path commands)
- [ ] No line passes through any box area
- [ ] Parallel lines in same channel use different x/y coordinates (30px apart)
- [ ] **Loop-back box clearance**: trace every segment of the loop-back path and verify its x,y coordinates do NOT intersect any box's bounding rectangle. Pay special attention to the left vertical segment — if Column 1 boxes start at x=40, the left gutter must be x ≤ 20.
- [ ] Loop-back bottom run is ≥102px from bottom edge (y ≤ 618)
- [ ] All traveling dots use `offset-path` with matching path string
- [ ] Each dot has a unique stagger delay class
- [ ] Every box connects to at least one other box — no orphaned sections

### Visibility
- [ ] Icon labels at ≥ 80% white opacity
- [ ] KPI text at ≥ 75% white opacity
- [ ] Box borders at ≥ 25% white (default) or ≥ 40% (colored)
- [ ] Static connector lines at ≥ 22% opacity
- [ ] Animated dashes at ≥ 70% opacity
- [ ] Arrowheads at ≥ 65% opacity
- [ ] No text is below 45% opacity (invisible after MP4 encoding)

### Frame
- [ ] Frame has `overflow: hidden`
- [ ] Tested at 1280×720 — nothing clipped, everything visible

### Export
- [ ] Capture script uses animation clock control (pause + setTime per frame)
- [ ] MP4 animation speed matches HTML playback speed
- [ ] File size is under 5MB for Substack upload

---

## 11. Template for New Diagrams

When requesting a new business model diagram in claude.ai chat, attach these files:
1. **This spec** (`animated-diagram-spec.md`) — the rules
2. **The reference diagram** (`aspi-v7.html`) — a production-quality example
3. **banned_terms.py** — to avoid internal terminology in KPI labels

Then provide the research data (or ask the model to web search for it):

```
Company: [TICKER] [Company Name]
Core Technology/Advantage: [What makes them unique]
Segments (2-4):
  1. [Name] — [Products/Services] — [Key metric: $X revenue or X users]
  2. [Name] — [Products/Services] — [Key metric]
  3. [Name] — [Products/Services] — [Key metric]
Revenue: TTM $[X]M → [Projection] $[Y]M | Cash: $[Z]M | Debt: $[W]M
Flywheel: [Step 1] → [Step 2] → [Step 3] → [Step 4] → (loops back)
Strategic/Pending: [Item 1 + date] | [Item 2 + date] | [Item 3 + probability]
```

**If you don't have this data:** Start the claude.ai chat with Research mode ON and ask:
"Web search for [TICKER] business model, revenue segments, key financials, strategic pipeline, and flywheel dynamics. Present as structured data for a business model diagram."
Then switch to Standard mode and ask for the diagram HTML.

---

## Reference Implementation

Three files form the complete working reference:

1. **aspi-v7.html** — the canonical diagram. All rules in this document were derived from debugging this implementation through 7+ iterations.
2. **capture.py** — the clock-controlled export script. Produces frame-perfect MP4/GIF from any diagram HTML built to this spec.
3. **animated-diagram-spec.md** — this document. Attach to new conversations alongside the HTML reference when requesting new diagrams.

All three files should be kept together and attached when starting a new diagram conversation.

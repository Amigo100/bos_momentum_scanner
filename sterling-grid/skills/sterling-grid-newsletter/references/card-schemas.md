# Sterling Grid — Input & Source Map (Newsletter, V9)

> The newsletter consumes the week's pipeline output + `portfolio.csv` + a supplied calendar/chart prose
> and emits one HTML briefing — not a card. Content generation only; prices from `portfolio.csv` alone.

---

## INPUT — the week's outputs + the supplied data
```
PIPELINE (this week)
· Tier-0 theme map        the structural forces (Theme lineage lines), status, key data points
· Tier 1/2/2.5 funnel     counts at each stage + the DROP log (for the funnel + rejection stories)
· Tier-3 memos            each new entry's fundamental thesis (the 3c memo + 3d article)
· Tier-4 buy list         the GREEN signals (BUYs) + the DO-NOT-BUY log (near-misses)
· decisions.json          technical SELLs fired this week + the DROP reasons (tagged by stage)

SUPPLIED (operator / data layer — the newsletter does not fetch)
· portfolio.csv           positions + entry + current price + P&L% + days held  (SOLE price source)
· market calendar         the week-ahead events (dates/times ET, consensus)     (Section 5)
· chart-analysis prose    per new entry — the screener's technical setup in investor language (Section 3)
```
No new web, no new model. A missing number is omitted or flagged, never filled from memory.

## SECTION → SOURCE MAP
| Section                 | Renders (from)                                                             |
|-------------------------|----------------------------------------------------------------------------|
| Preview / Headline      | the week's single most important data point (portfolio P&L / a new signal / a force) |
| 2. The forces at work   | Tier-0 themes (structural forces) + exposed positions' P&L + catalyst updates |
| 3. The portfolio        | `portfolio.csv` P&L table + winners/under-pressure + new entries (3c memo + chart prose) + exits |
| 4. The screening        | the funnel counts + the DROP log (rejection stories tagged by V9 stage) + DO-NOT-BUY near-misses |
| 5. The week ahead       | the supplied market calendar (held-position earnings flagged)              |
| 6. The bottom line      | synthesis of the above + Tuesday/Thursday content preview                  |

## Legacy → V9 mapping (for the rejection-story tags)
- "Pipeline B value-capture cut" → a **Tier 1/1.5 or Tier 2** exposure/proxy drop (weak value-capture grade).
- "Stage 2.5 disagreement" → a **Tier 2.5** reconciliation drop (only if a 2nd pipeline ran).
- "Stage 3 multibagger gate" → a **Tier 2** deep-dive-gate drop (thin path / marginal asymmetry).
- "DD V3 fail" → a **Tier 3** deep-dive drop (§9 disqualifier / no path / ruin / bear survived).
- "structural force" → a **Tier-0 theme**; "thesis (DD-5/DD-6)" → the **3c memo / 3d article**;
  "CP-2A prices" → **portfolio.csv**; "CP-1 technical overview" → the supplied **chart prose**.

## OUTPUT
The complete self-contained **HTML briefing** (house design system; 3,000–3,500 words; the
`[WINNERS_TABLE]` and `[SCAN_FUNNEL]` placeholders) → `articles/weekly-screening-<YYYY-MM-DD>.html`,
labelled `[NEWSLETTER HTML — {YYYY-MM-DD}]`.

## Handoff
The newsletter is the source the **Substack notes** spin out of.

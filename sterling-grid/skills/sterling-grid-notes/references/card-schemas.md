# Sterling Grid — Input & Source Map (Notes, V9)

> The notes engine consumes the weekly newsletter (+ portfolio.csv + the Tier-3d articles / chart prose)
> and emits TWO files — note text + cards. Content generation only; prices from portfolio.csv / the
> newsletter alone. Terminal step (nothing downstream).

## INPUT
```
· portfolio.csv            SOLE price source (do not web-search prices)
· weekly newsletter HTML    primary structured source (portfolio table, forces, rejection stories,
                            week-ahead, new entries with thesis + technical overview)
· Tier-3d article HTML(s)   for D2 signal companions (the deep dive)
· chart-analysis prose      per new signal, for the technical context in D2 (screener-supplied)
· newsletter identity       name · URL · cap focus · tagline · palette (Sterling/Ground Floor/Inflection)
```

## NOTE → NEWSLETTER-SOURCE MAP
| Category | Notes | Source in the newsletter |
|----------|-------|--------------------------|
| A Portfolio | A1–A3 | §3 (portfolio table + winners/under-pressure/exits) + portfolio.csv |
| B Market    | B1–B3 | §1 + §6 (headline / bottom line) + macro |
| C Forces    | C1–C4 | §2 (the forces at work = Tier-0 themes) |
| D Signals   | D1–D3 | §3 NEW ENTRIES + the Tier-3d articles + chart prose |
| E Rejections| E1–E2 | §4 (rejection stories + the funnel; tag to the V9 stage) |
| F Education | F1–F4 | whatever concept/metric/parallel surfaced this week |
| G Week ahead| G1–G2 | §5 (the calendar) |

## V9 mapping (for tags)
structural force = Tier-0 theme · signal thesis = 3c memo / 3d article · comparable-winner = 3a read ·
rejection stage = Tier 1/1.5 (exposure) / Tier 2 (gate) / Tier 2.5 (reconciliation) / Tier 3 (deep
dive) · funnel = the V9 stages · no sizing (D3 checkpoints are informational, never scale/sell).

## OUTPUT — two files
- **FILE 1** `[NOTES MARKDOWN — {YYYY-MM-DD}]` → `articles/notes-<YYYY-MM-DD>.md` (21 + ≤3 bonus, `---`
  separated, ID + title + day/time, `[LINK]` placeholders, BONUS marked).
- **FILE 2** `[CARDS HTML — {YYYY-MM-DD}]` → `articles/note-cards-<YYYY-MM-DD>.html` (all cards stacked,
  labelled by note ID, one `<style>` block, Google Fonts).

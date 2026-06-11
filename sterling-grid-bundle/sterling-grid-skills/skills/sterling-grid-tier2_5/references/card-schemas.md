# Sterling Grid — Card Schemas (Tier 2.5, V9)

> Tier 2.5 reconciles two pipelines' finished verdicts into one ranked Tier-3 DD queue. It runs only
> when a second pipeline ran. Its output card is a **valid Tier-3a input** (matches
> `sterling-grid-tier3`'s input) + a source tag + a reconciliation line. No sizing.

---

## INPUT A — this pipeline's Tier-2 output
- The **ADVANCE cards** (the Tier-3 DD queue this pipeline wants) — each the Tier-2 ADVANCE card
  (working layer + inherited lineage; see `sterling-grid-tier2`).
- The **DROP log** — ticker + the DROP *reason* (essential to debate a name the other side progressed).

## INPUT B — the other pipeline's reconciliation handoff (the companion spec)
*The other pipeline emits this at the end of its selection run — a thin reformat of its re-ranked
shortlist, theme-qualification result, and drop reasons. Two paste-friendly blocks.*

**Block A — DD-progressed** (one row per name it sends to DD):
```
| ticker | decision | track | archetype | theme | theme status | rank/cap |
  ≥4x mechanism (1 line) | strongest bear | evidence grade + 1–2 facts | ADV ($) | why-progressed |
```
- **decision** = its progression tag (e.g. PRIORITISE) · **track** = thematic / shape ·
  **theme status** = qualified / forming / unqualified · **rank/cap** = its rank + whether it cleared
  or was a marginal include under any shortlist cap · **ADV** = confirms the shared liquidity floor.

**Block B — considered-but-dropped** (one row per name it did *not* progress):
```
| ticker | drop stage | drop reason |
```
- **drop reason** mapped to a label this tier reads: `cap` · `theme-forming` · `liquidity` ·
  `no-path` · `disqualifier:<which>` · `ruin` · `footing` (peripheral / extended / theme-dead).
  Block B is what lets the debate attribute every THIS-ONLY divergence.

Keep both blocks to the names that cleared the other pipeline's earlier stages — not its full funnel.

## INPUT C — your DD budget
How many names Tier 3 can realistically take this cycle.

---

## OUTPUT — the reconciled DD queue (→ Tier 3a)

### Per-name queue card (a valid Tier-3a input + reconciliation)
```
WORKING LAYER
TICKER — ADVANCE · provisional type [multibagger / great-trade] · [V/G/N] · source [BOTH / THIS / OTHER]
Theme / benchmark: [theme] · proxy quality [strong/adequate/weak]
Path (rough): [mechanism + ~Nx]   Asymmetry: [rough U/D]   Survival: [permanent-impairment ~%]
Strongest bear: [1–2 lines]
Reconciliation: [divergence cause | "consensus"] → [ruling], one line
Tier 3a must resolve first: [the contested point]
Open questions (merged, both pipelines): [...]

LINEAGE LAYER
· Macro / Theme / Mapping   (inherited; from the other pipeline too where it adds)
· Triage / Gate             (inherited)
· Consensus   source BOTH / THIS / OTHER + the reconciliation ruling      ← appended here
```

### DD order
The ranked queue in order (consensus first → conviction/asymmetry → shape-rescues last; **type does
not change rank**), deep-dived to capacity this cycle. Beyond capacity → re-enter via the next scan
(no backlog).

### DROP log → `decisions.json`
```
DROP: ticker · stage=tier2_5 · reason_code (spec §0) + one line.
  Debate-vocab → code legend:
    firewall catch → the cited §9 hit's code (ruin if the ruin test fired, else disqualifier)
    footing        → the failing leg: peripheral → weak-proxy · too-extended → move-exhausted ·
                     theme-dead → theme-posture   (name the leg in `reason`)
    theme-only     → theme-posture · no-path → no-path
  (firewall drops still cite the §9 hit in `reason`)
```

### Divergence log (append-ready → `decisions.json`)
```json
{ "date":"YYYY-MM-DD", "week_id":"", "ticker":"", "stage":"tier2_5",
  "this_band":"ADVANCE|DROP", "other_tag":"", "cause":"", "ruling":"ADVANCE|DROP",
  "reason_code":"", "rationale":"" }
```
`reason_code` (spec §0) is required when `ruling` = DROP; `cause` stays the divergence taxonomy
(quota / great-trade / theme-forming / shape-bypass …) — it is not a reason_code.

## Handoff
The reconciled queue → **Tier 3a**, one name per session, in rank order.

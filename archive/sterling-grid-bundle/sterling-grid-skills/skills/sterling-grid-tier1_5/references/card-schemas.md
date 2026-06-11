# Sterling Grid — Card Schemas (Tier 1.5, V9)

> Tier 1.5 clears the Tier-1 ADVANCE pile a **batch** at a time (≤8 — handoff-card-spec §0); parallel
> batches **merge by concatenation**. Input = Tier 1's ADVANCE payload; ADVANCE payload feeds
> **Tier 2**. V9: **ADVANCE / DROP only — no WATCH, no sizing.**

---

## INPUT — the Tier-1 ADVANCE payload (batch of ≤8)
```
Per name:
  TICKER · Verify-first note (the ONE thing to confirm) · provisional Arch / Theme
  lineage: the §2 array [Macro, Theme, Mapping, Triage] — carried whole; you edit Triage IN PLACE
```
**Optional:** the **Tier-0 theme map** (theme health, early/late read) · **holdings** (skip held names).

---

## OUTPUT — what Tier 1.5 emits (per batch)

### Verification table
| Ticker | Result  | Exposure real?             | Still early? | Disq | One-line basis                  |
|--------|---------|----------------------------|--------------|------|---------------------------------|
| XYZ    | ADVANCE | yes — 60% rev in sub-theme | yes          | clear| confirmed core play, theme early|
| QRS    | DROP    | no — peripheral supplier   | —            | —    | tenuous label, not a real play  |

- **ADVANCE payload** → Tier 2: ticker + **the one thing Tier 2 must pin down** + the carried lineage,
  with the Triage line updated `→ T1.5 ADVANCE · verify-question answered: [result]`.
- **DROP log** (+ confirmed reason) → `decisions.json`.
- **Counts:** ADVANCE _n_ / DROP _n_.

*(No WATCH bucket — V9 keeps no watchlist. A not-ready name re-enters only via a later scan.)*

## Merge rule (parallel batches)
Concatenate the verification tables and the ADVANCE/DROP payloads. Mechanical — don't re-reason over
all batches in one context.

## Bucket discipline
**DROP only on confirmed evidence — never "couldn't tell."** Unresolved → ADVANCE. Early-but-real is
not a drop. (A false DROP is a permanently missed multibagger.)

# Sterling Grid — Output Schema (Tier 3a Research, V9)

> A single-name evidence-gathering pass run as a workflow. Output = a cross-checked evidence pack that
> the Tier-3 skill's 3a interprets into the dossier (appending the Evidence lineage line). No verdict,
> no valuation, no scenarios here — that is 3b/3c.

## INPUT
The Tier-2 ADVANCE card (ticker via `$ARGUMENTS`) + its open questions.

## OUTPUT — the evidence pack
```
ticker: $ARGUMENTS
re_validation:        clean | broke (+ what)
discriminator_scorecard:
  backlog_converting:   present|partial|absent  (source)
  milestone_on_date:    present|partial|absent  (source)
  firm_cash_contract:   present|partial|absent  (source)
  margin_cf_inflection: present|partial|absent  (source)
disqualifiers_§9:     [ each: clear | triggered (+ which) ]
ge_4x_drivers:        [ firm evidence behind the path, with sources ]
survival:             runway | burn | dilution path | accounting reads | ruin_flag: yes/no
positioning:          short_interest | float | borrow_fee | days_to_cover   (amplifier only)
comparable_winner:    analog (peak multiple, time-to) + failure case + differentiator
bear_landscape:       types_swept: [...] · lead_bear: ... · bull_claims_bear_could_not_break: [...]
archetype:            V | G | N | ?
unverified:           [ items tagged [UNVERIFIED] ]
sources:              [ URLs — filings / transcripts / IR / regulators preferred ]
```

## HANDOFF
→ Tier-3 skill **3a**: interprets this pack into the **evidence dossier** and appends the **Evidence**
lineage line (scorecard · survival + accounting · comparable anchor). Then **3b** (geometry/valuation)
and **3c** (verdict + memo + decision record) proceed. No sizing anywhere.

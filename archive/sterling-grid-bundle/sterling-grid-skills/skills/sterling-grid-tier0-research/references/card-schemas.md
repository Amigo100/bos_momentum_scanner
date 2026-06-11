# Sterling Grid — Output Schema (Tier 0 Research, V9)

> A research/gathering pass run as a workflow. Output = a cross-checked research pack that the Tier-0
> skill's 0c (scoring) and 0d (mapping) consume. No scoring, ranking, or priority tiers here.

## OUTPUT — the research pack
```
HEADER
· run_mode: delta-refresh | cold (explicit)     (cold ONLY when the operator asked; never a fallback)
· carry_digest_present: yes/no                  (no + delta-refresh = STOP upstream, spec §W)

MACRO READ (→ Macro lineage seed)
· regime: ...            (liquidity / rates / credit / risk)
· posture: ...           (informs, never gates)
· easing_inflection: yes/no/near + basis
· binding_axes: [ 1–3 reads that would change the posture if crossed — theme-intelligence §8 ]
· key_data_points: [ ... with sources ]

CANDIDATE THEMES (cross-checked; unscored)
- name / sub-theme:
  surfaced_via:          cluster | top-down | VC-funding | policy-capex | bottleneck-migration
  demand_mechanism:      ... (+ $ size / flow)
  precursors:            [ P1|P2|P3|P4 — each with dated evidence + source (theme-intelligence §2) ]
  stage_scurve:          S0 | S1 | S2 | S3 | S4   (the §1 staging guess; 0c finalises)
  stage:                 early | mid | late        (legacy derivation: S0/S1→early, S2→mid, S3/S4→late)
  recognition_state:     open | closing | priced
  fuel_mix:              fundamental | mixed | sentiment
  constraint_chain_evidence:  [ for migration-surfaced candidates: the chain step + scarcity signature ]
  cluster_corroborators: [ for cluster-surfaced candidates: §6 corroborators found ]
  candidate_vehicles:    [ tickers / benchmarks ]
  sources:               [ URLs — primary preferred ]
  adversarial_verdict:   survived | survived-with-caveats | filtered (+ why)
  unverified:            [ ... ]
```

## HANDOFF
→ Tier-0 skill: **0c** gates + scores these (→ the **Theme** lineage line, priority tier P1/P2/P3,
HUNT/HOLD/STAND-DOWN/AVOID); **0d** maps value-chain + benchmarks (→ the **Mapping** lineage line) and
writes the hunting brief carrying the three theme-level lineage lines per HUNT theme.

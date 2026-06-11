---
name: sterling-grid-tier2_5
description: >-
  Sterling Grid Tier 2.5 (V9) — cross-pipeline reconciliation, run ONCE after Tier 2 and before Tier
  3a, and ONLY when a second selection pipeline is also producing DD candidates over the same weekly
  universe. Takes the other pipeline's DD-progressed list + its considered-but-dropped log, debates
  each divergent ticker against this pipeline's Tier-2 ADVANCE/DROP verdicts on the two sides' EXISTING
  reasons (not fresh analysis), and resolves everything into one ranked Tier-3 DD queue — so you run
  selection twice but the deep dive once. It allocates the scarce DD slots; it does not re-run
  selection or re-judge a thesis (the deep dive is the adjudicator of substance). Same spine, no new
  gates — only the §9 firewall and the scarce DD slots override. No sizing. Skip entirely if only one
  pipeline runs (the Tier-2 queue goes straight to Tier 3).
  INVOCATION: invoked deliberately — one session, only when a second pipeline ran — by the pipeline
  orchestrator. NOT a keyword-triggered skill. On EVERY invocation, re-read this file and its reference
  files from disk; never run it from memory.
disable-model-invocation: true
effort: high
allowed-tools: WebSearch WebFetch Read Write Bash
---

# Sterling Grid — Tier 2.5 (V9): Cross-Pipeline Reconciliation

## How this skill is invoked

Explicitly-invoked, looked-up-each-time. **One session, run only when a second selection pipeline also
produced DD candidates over the same universe** — otherwise skip it entirely and pass the Tier-2 queue
straight to Tier 3. On every run, re-read this file and `references/` fresh from disk. Don't run it
from topic keywords.

**When does a second pipeline run at all (the trigger policy — decided at Checkpoint A, recorded in
the run context): default NO.** Run one — and therefore this tier — when ANY of:
- **(a) gate pressure** — the Tier-2 queue is ≥~8 names, so the scarce DD slots warrant a second
  opinion on the allocation;
- **(b) selection-change probation** — the pipeline's skill text materially changed in the last ~4
  weeks; A/B the selection before trusting it;
- **(c) the quarterly calibration probe** — K.1 wants divergence data on the gates.
Otherwise skip: a second pipeline on an ordinary week buys reconciliation overhead, not signal.

## Read first — load the DNA and the lineage spec

Load **`references/shared-context-dna.md`** (V9 — §3 recall→precision, §4 the spine, §5 binary no
sizing, §7 discriminators, §9 firewall, §10 the lineage) and **`references/lineage-block.md`** (you
append the **Consensus** line). Card shapes — and the **companion handoff contract** the other pipeline
must emit — are in **`references/card-schemas.md`**.

## Operating rules

1. **Adjudicate finished verdicts; don't re-run selection.** Debate the two pipelines' *existing*
   verdicts and stated reasons — never pull new data or re-judge a thesis. The deep dive settles
   substance; this tier only allocates the scarce DD slots.
2. **Same spine, no new gates (§3, §4).** Only two things override: the **firewall (§9)** and the
   **scarce DD slots.**
3. **Don't import the other pipeline's extra gates as cuts.** Runway, dilution, current
   unprofitability, and theme-maturity **never disqualify a name that has a credible path** (§3, §7).
   This pipeline is the newer, lower-gate expression of the same spine.
4. **No sizing, no caps, great trades are full BUYs (§5).** This pipeline carries great trades equal to
   multibaggers — so a drop the other side made *only* on a cap/quota or a "we only hunt ≥4x" rule is
   **not** a real disagreement about merit.
5. **No watchlist, no backlog.** Names beyond DD capacity this cycle re-enter via the next weekly scan;
   nothing sits on a maintained list.
6. **Carry the lineage; append the Consensus line.**

> **Same-universe precondition.** Both pipelines must be fed from the *same* weekly signal list (§2)
> and sit behind the *same* liquidity floor. If they aren't, **stop** — the divergences aren't
> comparable, and the universe gap is the first thing to fix. Liquidity is settled upstream and is
> **not** re-litigated here.

**Inputs:** this pipeline's **Tier-2 ADVANCE cards + DROP log** (the DROP *reasons* are essential to
debate a name the other side progressed) · the other pipeline's **reconciliation handoff** (its
DD-progressed list + its considered-but-dropped log — the companion-spec blocks in `card-schemas.md`) ·
your **DD budget** (how many names Tier 3 can take this cycle).

---

## Step 1 — Align the two lists
Match by ticker into four sets:
- **CONSENSUS** — both pipelines progressed it. Highest-prior DD candidates (two independent passes
  agreed) → DD first; no debate beyond carrying both cards forward.
- **THIS-ONLY** — Tier 2 ADVANCED it; the other pipeline dropped it.
- **OTHER-ONLY** — the other pipeline progressed it; Tier 2 DROPPED it.
- **NEITHER** — both dropped it. Ignore.

## Step 2 — Debate each divergent name
For every THIS-ONLY and OTHER-ONLY name, a short disciplined debate on the two pipelines' *existing*
verdicts and reasons:
- **Case for DD** — the progressing pipeline's strongest reason: the named ≥4x (or protected 3–4x)
  mechanism, which discriminators (§7) it shows, the archetype, the provisional type, the conviction.
- **Case against** — the dropping pipeline's stated reason: the gate failed, or the spine judgment missed.
- **Divergence cause** — name it: **Cap quota** (fell below a fixed shortlist cap — an artifact of
  their quota, not merit) · **Theme forming** (dropped because the theme isn't "qualified" yet — a
  theme stage gates a theme, never a name, §8) · **Great-trade framing** (a protected 3–4x the other
  side won't carry; this pipeline carries great trades as full BUYs, §5) · **Shape bypass** (a
  non-thematic turnaround / special situation this pipeline's V/G/N read under-weighted) · **Footing
  call** (disagree on peripheral / too-extended / theme-dead) · **Firewall catch** (one side found a §9
  hit the other's lighter pass missed) · **No-path** (this pipeline dropped for no credible ≥4x *or*
  protected 3–4x).
- **Ruling — apply in this order:**
  1. **Firewall first — overrides everything.** A *cited* §9 hit from *either* pipeline → **DROP**,
     however enthusiastic the other side. Never spend a DD slot on a fired §9 disqualifier or ruin.
  2. **Quota / great-trade / name-specific-theme → ADVANCE.** A cap-quota drop, a great trade the other
     side won't hold, or a theme-forming drop where the path rests on a *name-specific* discriminator
     (§7) rather than the theme — none is a real merit disagreement → carry into DD at this pipeline's
     provisional type. (Great trades take the lighter Tier-3 DD: confirm the catalyst, the floor, the
     target.)
  3. **Theme forming, thesis = the theme → DROP** — if the only path rests on the unqualified theme
     rather than a name-specific signal. Re-enters via the scan when the theme qualifies or a
     name-specific signal appears (no watchlist).
  4. **Shape bypass → DD only if budget remains** after the higher-ranked queue. The one case the
     *other* pipeline legitimately overrides this one.
  5. **Otherwise default to this pipeline.** A this-pipeline DROP on no-path or footing stands —
     *unless* the other pipeline cites a specific fact that refutes the DROP reason. Then it is a
     **genuine standoff**, and a genuine standoff **resolves toward DD if budget allows** (the deep
     dive is where substance gets settled, not here).

## Step 3 — Assemble the reconciled DD queue
Rank for DD on merit: **consensus first**; then by **conviction and asymmetry**; **shape-rescues last.**
**Type does not change the ranking** — a great trade and a multibagger compete on merit, not type (§5).
Deep-dive in rank order to **DD capacity this cycle**; names not reached re-enter via the next weekly
scan (no maintained backlog). Carry each survivor forward as a **valid Tier-3a input card (§10)**,
merging both pipelines' content + the **union of both pipelines' open questions**, with the contested
point named as the first thing 3a must resolve.

---

## Output (schemas in `card-schemas.md`)

### Reconciled Tier-3 DD queue (ranked → Tier 3a)
Per name, a Tier-2-equivalent card + a reconciliation line:
- **TICKER — ADVANCE · provisional type [multibagger / great-trade] · [V/G/N] · source [BOTH / THIS / OTHER]**
- Theme / benchmark / proxy quality · Path (mechanism + ~Nx) · Asymmetry · Survival · Strongest bear —
  carried from the Tier-2 card (and the other pipeline's, where it adds).
- **Reconciliation:** divergence cause (or "consensus") → ruling, one line.
- **Tier 3a must resolve first:** [the contested point]; **open questions (merged):** […].

### DD order
The ranked queue, in order — deep-dive to capacity this cycle; the rest re-enter via the next scan.

### DROP log
- **DROP:** name · stage=tier2_5 · **reason_code (spec §0)** + one line; the debate-vocab legend in
  `card-schemas.md` maps the causes (firewall catch → the cited §9 hit's code; footing → the failing
  leg's code; theme-only → theme-posture); firewall drops still note the cited §9 hit in `reason`.

### Divergence log (append-ready → `decisions.json`)
One row per disagreement: `date, week_id, ticker, stage, this_band, other_tag, cause, ruling,
reason_code (required when ruling = DROP), rationale`. The
calibration record — over time it answers whether the other pipeline's *unique* picks (OTHER-ONLY
promotions and shape-rescues) ever become winners, i.e. whether the second pipeline still earns its keep.

### Lineage — append
```
· Consensus   source BOTH / THIS / OTHER + the reconciliation ruling                     ← Tier 2.5
```

### Handoff
The reconciled queue feeds **Tier 3a** in rank order, one name per session.

## Self-check
- Adjudicated on the two pipelines' *existing* verdicts and reasons — no new data, no re-run thesis
  (that's 3a)? · A cited §9 hit from *either* side killed the name regardless of the other's enthusiasm?
  · Every divergence attributed to a named cause before ruling? · Avoided importing the other pipeline's
  *extra* gates (runway / dilution / unprofitability / theme-maturity never disqualify a name with a
  credible path)? · Ranked on merit (consensus, then conviction/asymmetry) without letting type decide,
  and let names beyond capacity re-enter via the scan (no backlog)? · Every queued card a valid Tier-3a
  input (§10) with merged open questions + the contested point? · Logged every disagreement and appended
  the Consensus line?

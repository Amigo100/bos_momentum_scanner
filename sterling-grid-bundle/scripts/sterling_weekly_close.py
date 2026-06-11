#!/usr/bin/env python3
"""Sterling Grid — Weekly Close (calibration Part C, deterministic engine).

Parses one week's pipeline outputs under sterling-run/runs/<date>/ and:
  1. appends per-theme rows to log/theme_research_history.csv,
  2. appends per-ticker funnel-journey rows to log/ticker_journey_history.csv,
  3. drops the same rows as a that-week slice into runs/<date>/report/,
  4. writes portfolio.csv rows for any new Tier-4 BUY (targets from the 3c geometry),
  5. emits runs/<date>/report/report_data.json (the bundle the narrative report renders from).

Append-only by design: existing CSV rows are never rewritten; a new week only adds rows.
Never fabricates a price or date — pulls it from the run outputs or leaves it blank.

Usage:
  python -m scripts.sterling_weekly_close <YYYY-MM-DD> [--theme-map PATH] [--run-root sterling-run]
"""
import argparse, csv, json, os, sys
from collections import OrderedDict

THEME_COLS = ["week_id","anchor_date","theme","sub_theme","surfaced_via","stage","recognition",
    "fuel_mix","floor_level","regime_fit","eligibility_gate","escape_applied","hunting_priority",
    "priority_tier","score_demand","score_growth","score_inflection","score_durability",
    "score_catalyst","score_capital","score_vehicle","demand_mechanism","delta_vs_last_week",
    "proxy_quality","best_vehicles","flagged_this_week"]

TICKER_COLS = ["week_id","anchor_date","ticker","sector","signal_strength","theme","archetype",
    "furthest_stage","outcome","decided_at_stage","reason","type","conviction","signal_price",
    "target_bear","target_base","target_bull","target_overshoot","target_prob_adj",
    "catalyst_window","opportunity_vs_RKLB","decision_date",
    "px_3mo","px_6mo","px_12mo","px_18mo","px_24mo","notes"]

PORTFOLIO_COLS = ["Ticker","Entry","Current","P&L%","Structural Force","Days Held","Type",
    "Conviction","Bear","Base","Bull","ProbAdjTarget","Catalyst Window"]

def load(path, default=None):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return default

def jsonl(path):
    out=[]
    try:
        for line in open(path):
            line=line.strip()
            if line: out.append(json.loads(line))
    except Exception: pass
    return out

def week_id(anchor):
    # anchor 'YYYY-MM-DD'; reuse the regime/theme-map iso_week if available, else derive
    import datetime
    y,m,d=[int(x) for x in anchor.split("-")]
    iso=datetime.date(y,m,d).isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"

# ---------- THEME ROWS ----------
def extract_themes(theme_map, wid, anchor):
    rows=[]
    themes=(theme_map or {}).get("themes",{})
    for name,t in themes.items():
        s=t.get("scores",{})
        rows.append(OrderedDict(zip(THEME_COLS,[
            wid, anchor, name, t.get("sub_theme",""), t.get("surfaced_via",""), t.get("stage",""),
            t.get("recognition",""), t.get("fuel_mix",""), t.get("floor_level",""), t.get("regime_fit",""),
            t.get("eligibility_gate",""), t.get("escape_applied",""), t.get("hunting_priority",""),
            t.get("priority_tier",""), s.get("demand_floor_strength",""), s.get("growth_magnitude",""),
            s.get("inflection_evidence",""), s.get("durability_tech_curve",""), s.get("catalyst_density",""),
            s.get("capital_momentum",""), s.get("vehicle_quality",""),
            (t.get("demand_mechanism","") or "")[:400], (t.get("delta_vs_last_week","") or "")[:300],
            t.get("proxy_quality_overall",""),
            "; ".join((v or {}).get("ticker","") for v in (t.get("best_vehicles") or []))[:160],
            "; ".join(t.get("flagged_this_week") or [])])))
    return rows

# ---------- TICKER JOURNEY (current/v607 format) ----------
STAGE_ORDER=["first triage","verification","deep-dive gate","deep dive","capital decision"]
def prob_adj(scn):
    try: return round(sum(v["price"]*v["prob"] for v in scn.values()),2)
    except Exception: return ""

def extract_tickers(run_dir, wid, anchor, decisions):
    rd=run_dir
    # canonical names first (handoff-card-spec §4); pre-V9.1 aliases kept as read-fallbacks for old runs
    canon=load(f"{rd}/tier1_5/tier1_5_result_{anchor}.json")
    triage=(canon or load(f"{rd}/tier1_5/triage_final_{anchor}.json")
            or load(f"{rd}/tier1_5/triage_result_{anchor}.json") or {})
    tres=next((d for d in (canon, load(f"{rd}/tier1_5/triage_result_{anchor}.json"))
               if isinstance(d, dict) and d.get("tier1")), {})
    t2=load(f"{rd}/tier2/tier2_result_{anchor}.json") or {}
    t4=load(f"{rd}/tier4/decision_rows_{anchor}.json") or load(f"{rd}/tier4/tier4_result_{anchor}.json") or {}
    # base map from all triaged tickers
    J=OrderedDict()
    for bt in tres.get("tier1",[]):
        for row in bt.get("triage",[]):
            tk=row["ticker"]
            J[tk]={"ticker":tk,"theme":row.get("theme",""),"archetype":row.get("arch",""),
                   "furthest_stage":"first triage","outcome":"","decided_at_stage":"","reason":"",
                   "type":"","conviction":"","signal_price":"","target_bear":"","target_base":"",
                   "target_bull":"","target_overshoot":"","target_prob_adj":"","catalyst_window":"",
                   "opportunity_vs_RKLB":"","decision_date":"","sector":"","signal_strength":"","notes":""}
    def ensure(tk):
        if tk not in J:
            J[tk]={k:"" for k in ["ticker","theme","archetype","furthest_stage","outcome","decided_at_stage",
                "reason","type","conviction","signal_price","target_bear","target_base","target_bull",
                "target_overshoot","target_prob_adj","catalyst_window","opportunity_vs_RKLB","decision_date",
                "sector","signal_strength","notes"]}; J[tk]["ticker"]=tk; J[tk]["furthest_stage"]="first triage"
        return J[tk]
    def advance(tk,stage):
        r=ensure(tk)
        if STAGE_ORDER.index(stage)>STAGE_ORDER.index(r["furthest_stage"] or "first triage"):
            r["furthest_stage"]=stage
    # drop log (T1 + T1.5)
    for d in triage.get("drop_log",[]):
        r=ensure(d["ticker"]); stg="first triage" if d.get("stage")=="T1" else "verification"
        advance(tk:=d["ticker"], stg)
        r["outcome"]="DROP"; r["decided_at_stage"]=stg; r["reason"]=(d.get("reason","") or "")[:300]
        if d.get("theme"): r["theme"]=r["theme"] or d["theme"]
    # tier-2 queue reached the gate
    for a in (triage.get("tier2_queue",[]) or []):
        advance(a["ticker"],"deep-dive gate")
    # tier 2 results — canonical {results:[…]} or the advance/drop split shape (2026-06-08)
    t2_rows=t2.get("results")
    if t2_rows is None:
        t2_rows=([dict(x, decision=x.get("decision","ADVANCE")) for x in (t2.get("advance") or [])]
                 + [dict(x, decision=x.get("decision","DROP")) for x in (t2.get("drop") or [])])
    for x in t2_rows:
        if not x.get("ticker"): continue
        tk=x["ticker"]; r=ensure(tk); advance(tk,"deep-dive gate")
        r["archetype"]=r["archetype"] or x.get("archetype",""); r["theme"]=x.get("theme",r["theme"])
        if x.get("decision")=="DROP":
            r["outcome"]="DROP"; r["decided_at_stage"]="deep-dive gate"; r["reason"]=(x.get("drop_reason","") or "")[:300]
        elif x.get("decision")=="ADVANCE":
            r["type"]=x.get("provisional_type",""); advance(tk,"deep dive")
    # tier 3 deep dives (per ticker dir)
    t3root=f"{rd}/tier3"
    if os.path.isdir(t3root):
        for tk in os.listdir(t3root):
            gp=load(f"{t3root}/{tk}/geometry.json"); vd=load(f"{t3root}/{tk}/verdict.json")
            if not (gp or vd): continue
            r=ensure(tk); advance(tk,"deep dive")
            scn=(gp or {}).get("four_scenarios",{})
            r["target_bear"]=scn.get("bear",{}).get("price",""); r["target_base"]=scn.get("base",{}).get("price","")
            r["target_bull"]=scn.get("rerate",{}).get("price",""); r["target_overshoot"]=scn.get("overshoot",{}).get("price","")
            r["target_prob_adj"]=prob_adj(scn) if scn else ""
            if vd:
                r["type"]=vd.get("type",r["type"]); r["conviction"]=vd.get("conviction","")
                r["catalyst_window"]=(vd.get("catalyst_window","") or "")[:200]
    # tier 4 capital decision — canonical decision_rows (a list of (d) rows, or {"rows":[…]}) first;
    # the legacy single-name reconcile wrapper as the old-run fallback
    t4_rows=None
    if isinstance(t4, list): t4_rows=t4
    elif isinstance(t4, dict) and isinstance(t4.get("rows"), list): t4_rows=t4["rows"]
    if t4_rows is not None:
        for dr in t4_rows:
            tk=dr.get("ticker")
            if not tk: continue
            r=ensure(tk); advance(tk,"capital decision")
            r["outcome"]="BUY" if dr.get("decision")=="BUY" else "DO_NOT_BUY"
            r["decided_at_stage"]="capital decision"
            r["opportunity_vs_RKLB"]=dr.get("opportunity_vs_RKLB","") or ""
            r["reason"]=(dr.get("reason","") or r["reason"])[:300]; r["decision_date"]=anchor
            r["catalyst_window"]=r["catalyst_window"] or (dr.get("catalyst_window","") or "")[:200]
            r["type"]=r["type"] or (dr.get("type","") or "").replace("_"," ")
            r["conviction"]=r["conviction"] or (dr.get("conviction","") or "")
    elif isinstance(t4, dict) and t4.get("reconcile"):
        rec=t4.get("reconcile",{})
        # single-name legacy format; map by decision_row ticker
        dr=rec.get("decision_row",{}); tk=dr.get("ticker")
        if tk:
            r=ensure(tk); advance(tk,"capital decision")
            r["outcome"]="BUY" if rec.get("final_decision")=="BUY" else "DO_NOT_BUY"
            r["decided_at_stage"]="capital decision"; r["opportunity_vs_RKLB"]=rec.get("opportunity_vs_RKLB","")
            r["reason"]=(dr.get("reason","") or r["reason"])[:300]; r["decision_date"]=anchor
            r["catalyst_window"]=r["catalyst_window"] or (dr.get("catalyst_window","") or "")[:200]
    # decisions ledger: enrich ONLY names THIS run actually carried to a verdict/capital decision.
    # The cross-week ledger may hold same-dated records from another run (e.g. a prior weekend run of
    # the same ISO week) — never let those flip a name this run DROPped. The run-dir tier4 (above) is
    # the authoritative outcome source for the week; the ledger only fills gaps for already-decided names.
    for rec0 in decisions:
        if rec0.get("date")!=anchor: continue
        tk=rec0.get("ticker"); r=J.get(tk)
        if not r: continue
        # structured `stage` (V9.1 ledger) governs; legacy `tier` spellings kept for back-compat
        if r.get("decided_at_stage")=="capital decision" and (
                rec0.get("stage")=="tier4" or rec0.get("tier") in ("4","4-binding")):
            r["opportunity_vs_RKLB"]=r["opportunity_vs_RKLB"] or rec0.get("opportunity_vs_RKLB","")
        if r.get("outcome") in ("BUY","DO_NOT_BUY"):
            r["type"]=r["type"] or (rec0.get("type","") or "").replace("_"," ")
            r["conviction"]=r["conviction"] or rec0.get("conviction","")
    # forward prices: px_* columns are DERIVED from the decisions.json forward snapshots (the sole
    # home of forward prices — see calibration card-schemas Part C); pull-or-blank, never fabricated.
    fwd={}
    for rec0 in decisions:
        tk0=rec0.get("ticker"); f=rec0.get("forward")
        if not tk0 or not isinstance(f, dict): continue
        if tk0 not in fwd or rec0.get("date")==anchor:   # prefer this run's record over older ones
            fwd[tk0]={k:("" if v is None else v) for k,v in f.items()}
    # finalize rows
    rows=[]
    for tk,r in J.items():
        f=fwd.get(tk,{})
        rows.append(OrderedDict(zip(TICKER_COLS,[
            wid,anchor,tk,r.get("sector",""),r.get("signal_strength",""),r.get("theme",""),r.get("archetype",""),
            r["furthest_stage"],r.get("outcome",""),r.get("decided_at_stage",""),r.get("reason",""),
            r.get("type",""),r.get("conviction",""),r.get("signal_price",""),
            r.get("target_bear",""),r.get("target_base",""),r.get("target_bull",""),r.get("target_overshoot",""),
            r.get("target_prob_adj",""),r.get("catalyst_window",""),r.get("opportunity_vs_RKLB",""),
            r.get("decision_date",""),
            f.get("p3",""),f.get("p6",""),f.get("p12",""),f.get("p18",""),f.get("p24",""),
            r.get("notes","")])))
    return rows

def update_portfolio_for_buys(root, run_dir, anchor):
    """Append a portfolio.csv row for any Tier-4 BUY, with targets from the 3c geometry.
    No-op when there are no buys. Never overwrites an existing holding."""
    pf=f"{root}/portfolio.csv"
    if not os.path.exists(pf): return []
    # collect this week's BUY tickers — canonical decision_rows first, legacy reconcile shape after
    t4=load(f"{run_dir}/tier4/decision_rows_{anchor}.json") or load(f"{run_dir}/tier4/tier4_result_{anchor}.json") or {}
    buys=[]
    rows4=t4 if isinstance(t4, list) else (t4.get("rows") if isinstance(t4, dict) and isinstance(t4.get("rows"), list) else None)
    if rows4 is not None:
        buys=[r.get("ticker") for r in rows4 if r.get("decision")=="BUY" and r.get("ticker")]
    elif isinstance(t4, dict):
        rec=t4.get("reconcile",{})
        if rec.get("final_decision")=="BUY":
            tk=rec.get("decision_row",{}).get("ticker")
            if tk: buys.append(tk)
        for b in (t4.get("buy_list",[]) or []):  # multi-buy shape, if present
            if b.get("ticker"): buys.append(b["ticker"])
    if not buys: return []
    # existing holdings (skip dupes)
    held=set()
    body=[]
    for line in open(pf):
        body.append(line)
        if not line.startswith("#") and not line.startswith("Ticker"):
            held.add(line.split(",")[0])
    # force lookup per ticker from the tier-3 queue (carries each name's theme)
    force_of={q.get("ticker"):q.get("theme","") for q in
              (load(f"{run_dir}/tier2/tier3_queue.json") or {}).get("queue",[])}
    added=[]
    for tk in buys:
        if tk in held: continue
        g=load(f"{run_dir}/tier3/{tk}/geometry.json") or {}
        v=load(f"{run_dir}/tier3/{tk}/verdict.json") or {}
        scn=g.get("four_scenarios",{})
        entry=v.get("decision_record",{}).get("entry_price","") or ""
        # theme attribution: tier3_queue first, then the name's own verdict/decision record
        theme=(force_of.get(tk) or v.get("theme","")
               or v.get("decision_record",{}).get("theme","") or "")
        if not theme:
            print(f"  WARN: no theme attribution found for BUY {tk} (tier3_queue + verdict both empty)")
        row=[tk, entry, entry, "+0.0%", theme[:60], 0,
             v.get("type",""), v.get("conviction",""),
             scn.get("bear",{}).get("price",""), scn.get("base",{}).get("price",""),
             scn.get("rerate",{}).get("price",""), prob_adj(scn) if scn else "",
             (v.get("catalyst_window","") or "")[:120]]
        with open(pf,"a",newline="") as f:
            csv.writer(f).writerow(row)
        added.append(tk)
    return added

def append_csv(path, cols, rows):
    new = not os.path.exists(path)
    with open(path,"a",newline="") as f:
        w=csv.DictWriter(f, fieldnames=cols)
        if new: w.writeheader()
        for r in rows: w.writerow(r)
    return len(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("date"); ap.add_argument("--theme-map",default=None)
    ap.add_argument("--run-root",default="sterling-run")
    a=ap.parse_args()
    root=a.run_root; anchor=a.date; wid=week_id(anchor)
    rd=f"{root}/runs/{anchor}"; rep=f"{rd}/report"; os.makedirs(rep,exist_ok=True)
    tmpath=a.theme_map or f"{root}/log/theme_map.json"
    # decisions.json is the sole ledger (calibration Part A); the legacy jsonl side-log remains a
    # fallback for one transition run only.
    decisions=load(f"{root}/decisions.json") or jsonl(f"{root}/log/decisions_v9.jsonl")

    theme_map=load(tmpath,{})
    themes=extract_themes(theme_map, wid, anchor)
    tickers=extract_tickers(rd, wid, anchor, decisions)
    # persist a dated theme-map snapshot so the per-week scored map is recoverable from runs/<date>/
    if theme_map:
        json.dump(theme_map, open(f"{rd}/tier0/theme_map_{anchor}.json","w"), indent=1)
    # write portfolio rows for any new BUY (targets from the 3c geometry); no-op when 0 buys
    bought=update_portfolio_for_buys(root, rd, anchor)
    if bought: print(f"  portfolio += {bought}")

    n1=append_csv(f"{root}/log/theme_research_history.csv", THEME_COLS, themes)
    n2=append_csv(f"{root}/log/ticker_journey_history.csv", TICKER_COLS, tickers)
    # that-week slices in report/
    append_csv(f"{rep}/themes_{anchor}.csv", THEME_COLS, themes)
    append_csv(f"{rep}/ticker_journey_{anchor}.csv", TICKER_COLS, tickers)
    json.dump({"week_id":wid,"anchor":anchor,"theme_rows":len(themes),"ticker_rows":len(tickers),
               "themes":themes,"tickers":tickers},
              open(f"{rep}/report_data.json","w"), indent=1)
    print(f"[close {anchor} / {wid}] themes+={n1} tickers+={n2} -> log/ + {rep}/")
    # outcomes summary
    from collections import Counter
    print("  outcomes:", dict(Counter(t['outcome'] or 'in-funnel' for t in tickers)))

if __name__=="__main__":
    sys.exit(main())

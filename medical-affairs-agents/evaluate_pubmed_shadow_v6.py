"""Prospective V6 source-only challenge: new NCT families and CI-level guard.

Original answers were frozen before any V6 predictor run. The predictor
takes ONLY PubMed PMIDs, NEVER this manifest. This evaluation is an
assistant-curated source spotcheck, NOT a clinical expert gold dataset or
representative accuracy statistic.
"""
import argparse
import json
from pathlib import Path
from evaluate_pubmed_shadow_v5 import exact_pair,render as _unused


def run_check(predictions,frozen):
    if frozen.get("status")!="PUBLIC_SOURCE_SPOTCHECK_NOT_QUALIFIED_GOLD" or frozen.get("no_medical_gold") is not True:
        raise ValueError("V6 is a source spotcheck; do not claim expert gold")
    studies=frozen["sources"]
    ids=[s["pmid"] for s in studies]
    trials=[s["trial_id"] for s in studies]
    if len(set(ids))!=len(ids) or len(set(trials))!=len(trials):
        raise ValueError("Duplicate source or trial family in V6")
    docs=predictions.get("articles",[])
    byid={x["pmid"]:x for x in docs}
    if len(byid)!=len(docs) or set(byid)!=set(ids):
        raise ValueError("Unexpected or missing original publication")
    checks=[]
    source_ok=0; sections=0
    matched=0;eligible=0;unlabelled_guard_passed=0;guard_total=0
    for s in studies:
        doc=byid[s["pmid"]]
        identity=doc.get("doi","").lower()==s["doi"].lower() and doc.get("source_status")!="BLOCKED_ORIGINAL_PUBMED_MISSING"
        source_ok+=int(identity)
        sections+=int(doc.get("source_status") in ("ORIGINAL_PUBMED_XML_RESULTS_TAGGED","ABSTRACT_RESULTS_ONLY"))
        predictions_for_paper=doc.get("candidates",[])
        used=set()
        for e in s["expected"]:
            eligible+=1
            indexes=[i for i,p in enumerate(predictions_for_paper)
                     if i not in used and exact_pair(e,p)]
            supported=bool(indexes) and identity
            if supported:
                matched+=1;used.add(indexes[0])
            checks.append({
                "trial":s["name"],"pmid":s["pmid"],
                "type":"PREDECLARED_EXACT_HR_CI_TUPLE",
                "endpoint":e["endpoint"],"measure":e["measure"],
                "expected":e["estimate"],"ci_level":e["ci_level"],
                "source":s["source"],
                "result":"MATCHED" if supported else "MISSED_OR_ABSTAINED",
                "fully_medically_validated":False,
            })
        for e in s.get("no_assumed_CI_controls",[]):
            guard_total+=1
            invalid=[p for p in predictions_for_paper
                     if p.get("measure")==e["measure"] and
                     abs(float(p.get("estimate",float("inf")))-e["estimate"])<1e-7]
            passed=len(invalid)==0
            unlabelled_guard_passed+=int(passed)
            checks.append({
                "trial":s["name"],"pmid":s["pmid"],"type":"DONT_INVENT_UNLABELED_CI_LEVEL",
                "effect_estimate":e["estimate"],
                "result":"PASS" if passed else "UNSUPPORTED_CI_CANDIDATE",
                "reason":e["reason"],"fully_medically_validated":False,
            })
    return {
      "source_only_engineering_test":True,
      "expert_medical_gold_claims":0,
      "trial_families":len(studies),
      "pubmed_doi_sources_matched":source_ok,
      "structured_result_sections":sections,
      "predeclared_numeric_tuples":eligible,
      "tuples_matched":matched,
      "tuples_not_matched":eligible-matched,
      "no_fabricated_ci_controls":guard_total,
      "no_fabricated_ci_controls_passed":unlabelled_guard_passed,
      "prediction_candidates":sum(len(x.get("candidates",[])) for x in docs),
      "abstentions":sum(len(x.get("abstentions",[])) for x in docs),
      "evaluation_dataset_exhaustive":False,
      "publication_selection_random_or_representative":False,
      "clinical_accuracy_measured":False,
      "v6_unseen_state":"CONSUMED_AFTER_FIRST_EVALUATION",
      "interpretation":"Tuple retrieval and abstentions only. Different disease types, dose arms, ILD severity, errata and actual statistical significance require independent source review.",
      "checks":checks,
    }


def to_markdown(r):
    lines=["# First V6 Public Abstract Engineering Shadow Evaluation","",
       "**Not expert gold, not clinical precision/recall, and not a treatment recommendation.**",
       "This V6 manifest was frozen before extracting these three original PMID sources.",
       f"- Original paper DOI matches: **{r['pubmed_doi_sources_matched']}/{r['trial_families']}**",
       f"- Tagged Results sections recognized: **{r['structured_result_sections']}/{r['trial_families']}**",
       f"- Exact prespecified HR + level + CI pairs: **{r['tuples_matched']}/{r['predeclared_numeric_tuples']}**",
       f"- No invented CI controls passed: **{r['no_fabricated_ci_controls_passed']}/{r['no_fabricated_ci_controls']}**",
       f"- All source numeric candidates: {r['prediction_candidates']}; abstentions: {r['abstentions']}",
       "- Qualified independently medically adjudicated claims: **0**",
       "","| Publication | Label type | Intended outcome | Actual check result |",
       "|---|---|---|---|"]
    for c in r["checks"]:
        lines.append(f"| {c['trial']} | {c['type']} | {c.get('endpoint',c.get('effect_estimate'))} | {c['result']} |")
    lines.extend(["","## Mandatory qualification","",
      "- A match is a source-abstract HR/CI candidate, NOT verified arm, population, analysis cutoff, or medical conclusion.",
      "- Two controls require withholding a CI when the HR's original abstract does not explicitly provide its confidence level; matching a CI for a different number is not valid.",
      "- DESTINY-Breast02 includes important drug-related ILD and reported grade-5 events; medical specialists must independently validate harms and source corrections.",
      "- SERENA-2 has a subsequent erratum. All affected items require clinical adjudication.",
      "- Clinical accuracy will remain unmeasured until two independent qualified reviewers create a complete, adjudicated, frozen outcome-level reference across truly unseen families.",
      "- V6 is no longer unseen after this first run. All later uses are regressions.",
      "","No paid API, private employer files, or redistributed copyrighted publisher full text."])
    return "\n".join(lines)+"\n"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--frozen",required=True)
    p.add_argument("--predictions",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    gold=json.loads(Path(args.frozen).read_text(encoding="utf-8"))
    predictions=json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    evaluated=run_check(predictions,gold)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    (out/"v6_source_spotcheck_score.json").write_text(json.dumps(evaluated,indent=2)+"\n",encoding="utf-8")
    (out/"v6_source_spotcheck_report.md").write_text(to_markdown(evaluated),encoding="utf-8")
    print("V6_ORIGINAL_SOURCE_MATCH",evaluated["pubmed_doi_sources_matched"],"/",evaluated["trial_families"])
    print("V6_NUMERIC_PAIR_MATCH",evaluated["tuples_matched"],"/",evaluated["predeclared_numeric_tuples"])
    print("V6_NO_INVENTED_CI",evaluated["no_fabricated_ci_controls_passed"],"/",evaluated["no_fabricated_ci_controls"])
    print("V6_ABSTENTIONS",evaluated["abstentions"])
    print("V6_REAL_QUALIFIED_GOLD",0)
    if evaluated["pubmed_doi_sources_matched"]!=evaluated["trial_families"]:
        raise RuntimeError("Source DOI identity mismatch; no positive trial inference allowed")

if __name__=="__main__":
    main()

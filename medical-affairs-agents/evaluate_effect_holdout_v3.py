"""Strict once-only V3 evaluation: do not use scores to tune V3 on these articles."""
import argparse
import json
import time
from pathlib import Path
from clinical_effects_v3 import run as extract

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/"benchmarks"/"EFFECT_HOLDOUT_V3_FROZEN.json"


def equal_num(a,b):
    return isinstance(a,(float,int)) and abs(float(a)-float(b))<1e-7


def score(records,manifest):
    families=[s["family"] for s in manifest["sources"]]
    if len(set(families))!=len(families) or set(families).intersection(
            manifest["trained_and_examined_families"]):
        raise ValueError("V3 evaluation contamination or duplicate study family")
    by_id={r["pmcid"]:r for r in records}
    checks=[]
    for source in manifest["sources"]:
        rec=by_id.get(source["pmcid"],{})
        identity_ok=(rec.get("pmcid")==source["pmcid"]
                     and rec.get("doi","").lower()==source["doi"].lower())
        for c in source["checks"]:
            kind=c["type"]
            if kind=="exact_association":
                candidates=[
                    e for e in rec.get("candidates",[])
                    if e.get("status")=="NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED"
                    and e.get("endpoint")==c["endpoint"]
                    and e.get("measure")==c["measure"]
                    and equal_num(e.get("estimate"),c["value"])
                    and e.get("ci_level")==c["ci_level"]
                    and equal_num(e.get("ci_lower"),c["lower"])
                    and equal_num(e.get("ci_upper"),c["upper"])
                    and e.get("causal_interpretation")=="OBSERVATIONAL_ASSOCIATION_ONLY"
                ]
                passed=identity_ok and bool(candidates)
                detail={"found_candidates":len(candidates),
                        "source_tiers":[e["source_level"] for e in candidates]}
            elif kind=="no_observed_outcome_claim":
                passed=(identity_ok and rec.get("status")==
                        "BLOCKED_NO_OBSERVED_FULLTEXT_RESULTS" and
                        not rec.get("candidates"))
                detail={"article_status":rec.get("status")}
            elif kind=="secondary_synthesis_not_independent_trial":
                passed=(identity_ok and rec.get("status")==
                        "BLOCKED_SECONDARY_SYNTHESIS_AS_PRIMARY_STUDY" and
                        not rec.get("candidates"))
                detail={"article_status":rec.get("status")}
            elif kind=="license_requires_separate_approval":
                passed=(identity_ok and rec.get("status")==
                        "BLOCKED_LICENSE_REVIEW_REQUIRED" and
                        not rec.get("candidates"))
                detail={"license":rec.get("license",{}).get("status")}
            else:
                raise ValueError("Unrecognized V3 gold check")
            checks.append({"pmcid":source["pmcid"],"kind":kind,
                           "passed":bool(passed),"identity_ok":identity_ok,
                           **detail})
    return {"correct":sum(x["passed"] for x in checks),"count":len(checks),
            "checks":checks,"is_real_world_clinical_accuracy":False,
            "independent_dataset":False,
            "prospective_predeclared_article_families":True,
            "data_quality_note":"Five predeclared checks; not a representative sample, no formal gold labels from a blinded reviewer."}


def evaluate(target):
    begin=time.perf_counter()
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    out=Path(target)
    records=extract([x["pmcid"] for x in manifest["sources"]],out)
    scored=score(records,manifest)
    elapsed=round(time.perf_counter()-begin,3)
    payload={"frozen_version":3,"benchmark":scored,
             "runtime_seconds":elapsed,"not_scientifically_validated":True}
    (out/"v3_effect_holdout_scorecard.json").write_text(
        json.dumps(payload,indent=2),encoding="utf-8")
    lines=["# Frozen V3 — Prospective, study-family-disjoint research test", "",
           f"**Predeclared checks passed: {scored['correct']}/{scored['count']}.**",
           "**Do not call this a medical accuracy percentage or statistical precision/recall.**",
           "Version 3 was frozen before running it on these article families.",
           "",
           "| Article | Check | Result |",
           "|---|---|---|"]
    for c in scored["checks"]:
        lines.append(f"| [{c['pmcid']}](https://pmc.ncbi.nlm.nih.gov/articles/{c['pmcid']}/) | "
                     f"{c['kind']} | {'PASS' if c['passed'] else 'NOT PASSED'} |")
    lines+=["","## Interpretation","",
            "- Each check verifies a narrow candidate extraction or an abstention, not a medical conclusion.",
            "- Abstract-only matches and full Results matches are differentiated in the JSON output.",
            "- No confidence in comparative treatment effectiveness is computed.",
            "- Numeric pair matching does not verify treatment-arm mapping, endpoint primacy, analyses, or missing outcomes.",
            "- A secondary network meta-analysis is not counted as a new randomized clinical trial.",
            "- Non-commercial or no-derivatives licensed content is not mined in this public demo.",
            "- Clinical review is required for all source-linked outputs.",
            "- Do not modify V3 labels after reviewing the scores. Use a new trial-family-disjoint V4 for further external evaluation.",
            f"","**Elapsed:** {elapsed} s network and machine processing; excludes reviewer time."]
    (out/"v3_effect_holdout_scorecard.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("V3_FROZEN_CHECKS",scored["correct"],"/",scored["count"])
    for x in scored["checks"]:
        print("V3_CHECK",x["pmcid"],x["kind"],"PASS" if x["passed"] else "NOT_PASSED")
    print("V3_BENCHMARK_SECONDS",elapsed)
    return payload


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="medical-affairs-agents/output/v3_effect_holdout")
    args=p.parse_args()
    evaluate(args.out)

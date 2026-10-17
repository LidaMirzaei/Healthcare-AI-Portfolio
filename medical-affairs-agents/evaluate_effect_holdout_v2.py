"""Once-only prospective outcome-effect benchmark on frozen, independent studies.

Never feed gold values into the extractor. The benchmark only compares JSON
records produced by clinical_effects.py with independently frozen labels.
Results are an engineering sanity audit, NOT a medical accuracy estimate.
"""
import argparse
import json
import time
from pathlib import Path

from clinical_effects import run as extract

ROOT=Path(__file__).resolve().parent
FROZEN=ROOT/"benchmarks"/"EFFECT_HOLDOUT_V2_FROZEN.json"


def exact_value(x,y):
    return type(x) in (float,int) and abs(x-float(y)) < 0.000001


def score(records, frozen):
    train=set(frozen["development_family_ids"])
    source_ids=[x["study_family"] for x in frozen["references"]]
    if len(set(source_ids)) != len(source_ids) or train.intersection(source_ids):
        raise ValueError("Study-family leakage between development and evaluation")
    by_id={r["pmcid"]:r for r in records}
    checks=[]
    for item in frozen["references"]:
        r=by_id.get(item["pmcid"],{})
        expected=item["expected"]
        kind=expected["kind"]
        if kind=="numeric":
            matches=[
                c for c in r.get("candidates",[])
                if c.get("status")=="SOURCE_EFFECT_CANDIDATE_REVIEW_REQUIRED"
                and c.get("endpoint")==expected["endpoint"]
                and c.get("measure")==expected["measure"]
                and c.get("ci_level")==expected["ci_level"]
                and all(exact_value(c.get(k), expected[gold])
                        for k,gold in (("point","estimate"),
                                       ("ci_lower","ci_lower"),("ci_upper","ci_upper")))
                and c.get("source_url","").startswith(r.get("url","UNSET"))
            ]
            correct=bool(matches) and r.get("status")=="EFFECT_CANDIDATES_REVIEW_REQUIRED"
            if expected["measure"]=="OR":
                correct=correct and any(
                    c.get("causal_status")=="ASSOCIATION_NOT_RANDOMIZED_TREATMENT_EFFECT"
                    for c in matches)
            checks.append({
                "pmcid":item["pmcid"],"kind":"numeric_exact_source_candidate",
                "passed":correct,"matched_candidate_count":len(matches),
                "issue":None if correct else "Expected reviewable numeric effect/interval not extracted or incorrectly categorized",
            })
        elif kind=="do_not_conflate":
            # This test checks if multi-HR expressions were detected as ambiguous.
            # It DOES NOT check complete subgroup extraction or all source contexts.
            abstentions=[c for c in r.get("candidates",[])
                         if c.get("status")=="ABSTAIN_MULTIPLE_OR_MISSING_ESTIMATE_OR_CI"
                         and c.get("detected_estimates",0)>1]
            checks.append({
                "pmcid":item["pmcid"],"kind":"subgroup_estimate_ambiguity",
                "passed":bool(abstentions),
                "ambiguous_source_segments":len(abstentions),
                "issue":None if abstentions else "Expected multi-estimate ambiguity not detected",
            })
        elif kind=="license_block":
            accepted=(r.get("status")=="BLOCKED_LICENSE_REVIEW_REQUIRED"
                      and r.get("license",{}).get("status")!="CC_BY_OR_CC0_CONFIRMED"
                      and not r.get("candidates"))
            checks.append({
                "pmcid":item["pmcid"],"kind":"commercial_rights_gate",
                "passed":accepted,
                "issue":None if accepted else "Restricted text was processed or right unknown",
            })
        else:
            raise ValueError("Unknown frozen evaluation label")
    return {
        "correct_checks":sum(1 for x in checks if x["passed"]),
        "total_checks":len(checks),
        "checks":checks,
        "clinical_precision_recall_not_measured":True,
        "holdout_selection":"Predeclared four independent study families, not a representative sample",
        "reporting_rule":"No tuning on this V2 after first evaluation; future improvements evaluated on new V3.",
    }


def render(scores, records, seconds):
    lines=["# Frozen V2: independent-study clinical-effect benchmark", "",
        "**This is an engineering evaluation, NOT a clinically validated accuracy percentage.**",
        "The evaluation manifest was frozen before the general extractor was run on these articles.",
        f"**Correct predetermined checks: {scores['correct_checks']}/{scores['total_checks']}**.",
        f"**Elapsed network + extraction + scoring: {seconds:.3f}s** (excludes expert review).",
        "",
        "| Source | Check type | Result | What it means |",
        "|---|---|---|---|"]
    for ch in scores["checks"]:
        link=f"https://pmc.ncbi.nlm.nih.gov/articles/{ch['pmcid']}/"
        lines.append(f"| [{ch['pmcid']}]({link}) | {ch['kind']} | "
                     f"{'PASS' if ch['passed'] else 'NOT PASSED'} | "
                     f"{ch.get('issue') or 'Rule checked, no medical conclusion'} |")
    lines += ["", "## Caveats", "",
        "- **Outcomes:** 2 expected numerical pairs; 1 ambiguity-detection check; 1 restricted-license check.",
        "- **Do not convert this score into precision, recall or a clinical accuracy rate.**",
        "- Source matching in Results is not adjudication of treatment arms, clinical significance or risk of bias.",
        "- The benchmark does not measure how many relevant results were missed in each full text.",
        "- A license blocked article contributes to a rights-safety check, not numeric effect extraction.",
        "- Study families do not overlap with the previous TROPION-Breast01 development case.",
        "- The frozen V2 cannot be called unseen again after this inspection.",
        "",
        "## Next work needed", "",
        "1. Curate a larger outcome-level gold dataset with an independent clinical reviewer.",
        "2. Evaluate *all* annotated outcomes, counting false positives, false negatives and abstentions separately.",
        "3. Build a separate V3 once-only holdout after development; never edit V2 to inflate its results.",
        "4. Independently check forest plots, denominators, data cutoffs, safety tables and adverse-event classifications.",
        "5. Compare total human time (reading, corrections, signoff) against manual literature review.",
    ]
    return "\n".join(lines)+"\n"


def evaluate(target):
    start=time.perf_counter()
    gold=json.loads(FROZEN.read_text(encoding="utf-8"))
    ids=[x["pmcid"] for x in gold["references"]]
    output=Path(target)
    records=extract(ids, output)
    scored=score(records,gold)
    total=time.perf_counter()-start
    result={"benchmark_version":2,"frozen_manifest":FROZEN.name,
            "runtime_seconds":round(total,3),"evaluation":scored,
            "fulltext_extraction_allowed":sum(
                r.get("license",{}).get("status")=="CC_BY_OR_CC0_CONFIRMED" for r in records),
            "record_count":len(records)}
    (output/"v2_frozen_effect_scorecard.json").write_text(
        json.dumps(result,indent=2),encoding="utf-8")
    (output/"v2_frozen_effect_scorecard.md").write_text(
        render(scored,records,total),encoding="utf-8")
    print("V2_FROZEN_CHECKS",scored["correct_checks"],"/",scored["total_checks"])
    for x in scored["checks"]:
        print("V2_CHECK",x["pmcid"],x["kind"],"PASS" if x["passed"] else "NOT_PASSED")
    print("V2_EVALUATION_SECONDS",round(total,3))
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="medical-affairs-agents/output/v2_effect_holdout")
    args=p.parse_args()
    evaluate(args.out)

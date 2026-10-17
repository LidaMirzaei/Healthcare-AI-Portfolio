"""Two-reviewer, study-family-disjoint evaluation for clinical effect extraction.

No gold labels are bundled. This computes *research metrics only* when
adjudicated expert reference labels are actually provided. It never marks a
claim fit for medical use; exact clinical matching requires population, arms,
cutoff and citation validation beyond numeric source-candidate extraction.

Input schema intentionally contains IDs/fields only — no licensed source text.
"""
import argparse
import json
import math
from pathlib import Path

REQUIRED_GOLD = (
    "claim_id", "pmcid", "study_family_id", "endpoint", "measure",
    "estimate", "ci_level", "ci_lower", "ci_upper",
    "intervention", "comparator", "population", "analysis_cutoff",
    "source_url", "reviewer_1", "reviewer_2", "adjudicated", "source_checked"
)
METRICS_SCHEMA = "two-reviewer-clinical-outcome-exact-v1"


def _number(x):
    if isinstance(x, bool) or not isinstance(x, (int,float)) or not math.isfinite(x):
        raise ValueError("Nonfinite or nonnumeric effect estimate/CI")
    return float(x)


def _normalized(x):
    return " ".join(str(x or "").casefold().split())


def validate_gold(gold):
    if not isinstance(gold,list) or not gold:
        raise ValueError("No independent adjudicated gold outcomes supplied; accuracy unavailable")
    ids=set()
    for rec in gold:
        absent=[k for k in REQUIRED_GOLD if k not in rec]
        if absent:
            raise ValueError("Gold annotation incomplete: "+",".join(absent))
        if not rec["claim_id"] or rec["claim_id"] in ids:
            raise ValueError("Duplicate or empty gold claim_id")
        ids.add(rec["claim_id"])
        for field in ("pmcid","study_family_id","endpoint","measure",
                      "intervention","comparator","population","analysis_cutoff","source_url"):
            if not str(rec[field]).strip():
                raise ValueError("Gold missing clinical context: "+field)
        if rec["reviewer_1"] == rec["reviewer_2"] or not all(
                str(rec[k]).strip() for k in ("reviewer_1","reviewer_2")):
            raise ValueError("Two distinct reviewers are required")
        if rec["adjudicated"] is not True or rec["source_checked"] is not True:
            raise ValueError("Unadjudicated or unverified gold standard")
        point=_number(rec["estimate"])
        low=_number(rec["ci_lower"]); high=_number(rec["ci_upper"])
        if not (0<low<=point<=high<100):
            raise ValueError("Invalid gold CI")
        if rec["ci_level"] not in (90,95,99):
            raise ValueError("Unsupported CI level in gold label")


def same_numeric_tuple(gold, candidate):
    try:
        if candidate.get("status")!="NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED":
            return False
        return (_normalized(gold["pmcid"]) == _normalized(candidate["pmcid"])
                and _normalized(gold["endpoint"]) == _normalized(candidate["endpoint"])
                and _normalized(gold["measure"]) == _normalized(candidate["measure"])
                and gold["ci_level"] == candidate["ci_level"]
                and all(abs(_number(gold[g])-_number(candidate[p]))<=1e-6
                        for g,p in (("estimate","estimate"),("ci_lower","ci_lower"),
                                    ("ci_upper","ci_upper"))))
    except (KeyError,ValueError,TypeError):
        return False


def same_complete_claim(gold,candidate):
    """No unreviewed candidate can satisfy the clinical-context release gate."""
    if not same_numeric_tuple(gold,candidate):
        return False
    if candidate.get("source_context_verified") is not True:
        return False
    for field in ("intervention","comparator","population","analysis_cutoff"):
        if not _normalized(candidate.get(field)) or (
                _normalized(candidate[field])!=_normalized(gold[field])):
            return False
    return (_normalized(candidate.get("source_url")) ==
            _normalized(gold["source_url"]))


def _greedy_one_to_one(gold,predictions,match):
    matched_gold=set()
    true_positive=0
    for prediction in predictions:
        for j,reference in enumerate(gold):
            if j not in matched_gold and match(reference,prediction):
                matched_gold.add(j)
                true_positive+=1
                break
    return true_positive


def evaluate(gold, records, train_families=()):
    """Compute separate tuple-candidate and full-context metrics.

    Refrain from clinical precision/recall claims when the reference is
    incomplete; this function requires two-reviewer adjudication.
    """
    validate_gold(gold)
    if set(_normalized(x) for x in train_families).intersection(
            _normalized(g["study_family_id"]) for g in gold):
        raise ValueError("Study-family train/test leakage")
    if not isinstance(records,list):
        raise ValueError("Prediction records must be a list")
    seen=set()
    attempted=0
    abstained=0
    candidates=[]
    blocked=0
    for record in records:
        pmcid=record.get("pmcid")
        if not pmcid or pmcid in seen:
            raise ValueError("Duplicate/missing predicted PMCID")
        seen.add(pmcid)
        if record.get("status","").startswith("BLOCKED"):
            blocked+=1
            if record.get("candidates"):
                raise ValueError("Blocked paper must not have clinical candidates")
        for c in record.get("candidates",[]):
            attempted+=1
            if c.get("status")=="NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED":
                pred=dict(c,pmcid=pmcid)
                if not pred.get("source_url"):
                    raise ValueError("Candidate lacking source locator")
                candidates.append(pred)
            else:
                abstained+=1
    numeric_tp=_greedy_one_to_one(gold,candidates,same_numeric_tuple)
    complete_tp=_greedy_one_to_one(gold,candidates,same_complete_claim)
    def rates(tp):
        n_pred=len(candidates);n_gold=len(gold)
        precision=round(tp/n_pred,4) if n_pred else None
        recall=round(tp/n_gold,4)
        f1=(round(2*precision*recall/(precision+recall),4)
            if precision is not None and (precision+recall)>0 else None)
        return {"tp":tp,"fp":n_pred-tp,"fn":n_gold-tp,
                "precision":precision,"recall":recall,"f1":f1}
    n_families=len({g["study_family_id"] for g in gold})
    return {
        "schema":METRICS_SCHEMA,"gold_n":len(gold),
        "gold_distinct_study_families":n_families,
        "predictions_n":len(candidates),"attempted_n":attempted,
        "abstentions_n":abstained,"blocked_papers_n":blocked,
        "numeric_tuple_only":rates(numeric_tp),
        "full_clinical_context_and_citation":rates(complete_tp),
        "qualified_reviewer_approval_not_inferred":True,
        "evaluation_is_real_world_representative":False,
        "clinically_validated_product":False,
        "benchmark_minimum_for_accuracy_reporting_reached":len(gold)>=30 and n_families>=10,
        "warning":"Even completed adjudicated gold labels require representative sampling and source-context verification. Do not equate tuple precision with clinical safety.",
    }


def cli(gold_path,predictions_path,out_path,train_families=()):
    gold=json.loads(Path(gold_path).read_text(encoding="utf-8"))
    data=json.loads(Path(predictions_path).read_text(encoding="utf-8"))
    records=data.get("articles",data.get("records",[]))
    scores=evaluate(gold,records,train_families)
    target=Path(out_path)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(scores,indent=2),encoding="utf-8")
    print("GOLD_REVIEWED_OUTCOMES",scores["gold_n"])
    print("TUPLE_MATCHED",scores["numeric_tuple_only"]["tp"])
    print("FULL_CONTEXT_MATCHED",scores["full_clinical_context_and_citation"]["tp"])
    print("SUFFICIENT_FOR_ACCURACY_CLAIM",scores["benchmark_minimum_for_accuracy_reporting_reached"])
    return scores


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gold",required=True,help="Independently curated and adjudicated reference JSON")
    p.add_argument("--predictions",required=True,help="Extractor output JSON")
    p.add_argument("--out",required=True,help="Output metrics JSON")
    p.add_argument("--train-families",nargs="*",default=[])
    args=p.parse_args()
    cli(args.gold,args.predictions,args.out,args.train_families)

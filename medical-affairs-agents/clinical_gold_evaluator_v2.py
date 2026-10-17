"""Outcome-level medical evidence scorer v2: independent, strictly source-aware.

Only call with EXTERNALLY adjudicated scientific reference records. This tool
checks the STRUCTURE and arithmetic; it cannot authenticate medical credentials,
clinical correctness, or the original source contents. Without gold labels,
it refuses to provide any accuracy estimate.

Supports original PubMed-only NEJM articles (no PMCID), non-comparative
single-arm percentages, unusual CI levels (e.g. 95.01%), source locator and
denominator checks. Neither public GitHub CI nor a medical recommendation.
"""
import json
import math
from pathlib import Path

ALLOWED={"HR","OR","RR","percent"}
GOLD_CONTEXT=("claim_id","study_family_id","endpoint","measure",
              "estimate","ci_level","ci_lower","ci_upper",
              "intervention","population","analysis_cutoff",
              "analysis_denominator","source_url","source_locator",
              "endpoint_hierarchy")
CLINICAL_CONTEXT=("intervention","comparator","population",
                  "analysis_cutoff","analysis_denominator",
                  "endpoint_hierarchy","source_url","source_locator")


def norm(value):
    return " ".join(str(value).strip().casefold().split()) if value is not None else ""


def num(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError("Expected finite numeric field")
    return float(value)


def shared_source_ids(a,b):
    """Require matching at least one original article identifier, no contradictions."""
    shared=0
    for key in ("pmid","pmcid","doi"):
        av=norm(a.get(key));bv=norm(b.get(key))
        if av and bv:
            shared+=1
            if av!=bv:
                return False
    return shared>0


def verify_gold(gold, training_families=(), eligible_test_families=None):
    if not isinstance(gold,list) or not gold:
        raise ValueError("No independent, expert-adjudicated reference results available")
    ids=set()
    train={norm(x) for x in training_families}
    test=({norm(x) for x in eligible_test_families}
          if eligible_test_families is not None else None)
    for r in gold:
        missing=[field for field in GOLD_CONTEXT if field not in r]
        if missing:
            raise ValueError("Incomplete clinical gold context: "+",".join(missing))
        if not any(norm(r.get(k)) for k in ("pmid","pmcid","doi")):
            raise ValueError("Gold must cite original PMID/PMCID/DOI")
        for field in GOLD_CONTEXT:
            if field in ("estimate","ci_level","ci_lower","ci_upper"):
                continue
            if not norm(r[field]):
                raise ValueError("Missing clinical gold context: "+field)
        claim_id=r["claim_id"]
        if claim_id in ids:
            raise ValueError("Duplicate clinical reference claim")
        ids.add(claim_id)
        family=norm(r["study_family_id"])
        if family in train or (test is not None and family not in test):
            raise ValueError("Training leakage or unreserved test family")
        if r["measure"] not in ALLOWED:
            raise ValueError("Unsupported gold effect type")
        point=num(r["estimate"]);lower=num(r["ci_lower"]);upper=num(r["ci_upper"])
        ci=num(r["ci_level"])
        if not (0<ci<100 and 0<=lower<=point<=upper):
            raise ValueError("Invalid confidence interval")
        if r["measure"] in ("HR","OR","RR") and lower<=0:
            raise ValueError("Ratio confidence interval must be positive")
        if r["measure"]=="percent" and upper>100:
            raise ValueError("Response percentage CI over 100")
        if r.get("comparator") is None:
            if r["measure"]!="percent" or r.get("study_design")!="single_arm":
                raise ValueError("Missing comparator only allowed for explicit single-arm response")
        elif not norm(r["comparator"]):
            raise ValueError("Empty comparator must not masquerade as single-arm")
        if r.get("source_checked") is not True or r.get("adjudicated") is not True:
            raise ValueError("Gold must already be explicitly source checked and adjudicated")
        reviewer_ids=r.get("reviewer_ids")
        if not isinstance(reviewer_ids,list) or len(set(reviewer_ids))<2:
            raise ValueError("Two distinct reviewing identities are required")
        if not norm(r.get("external_review_reference")):
            raise ValueError("Independent organization's signoff reference is required")
    return {"gold_count":len(gold),"trial_families":len({norm(g["study_family_id"]) for g in gold}),
            "authenticity_not_verifiable_by_software":True}


def numeric_match(reference, prediction):
    if prediction.get("status")!="NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED":
        return False
    if not shared_source_ids(reference,prediction):
        return False
    if norm(reference["endpoint"])!=norm(prediction.get("endpoint")):
        return False
    if reference["measure"]!=prediction.get("measure"):
        return False
    try:
        return all(abs(num(reference[k])-num(prediction.get(k))) <= 1e-6
                   for k in ("estimate","ci_level","ci_lower","ci_upper"))
    except (ValueError,TypeError):
        return False


def full_context_match(reference,prediction):
    if not numeric_match(reference,prediction):
        return False
    if prediction.get("source_context_verified") is not True:
        return False
    return all(norm(reference.get(field))==norm(prediction.get(field))
               and (norm(reference.get(field)) or field=="comparator")
               for field in CLINICAL_CONTEXT)


def one_to_one(references,candidates,matcher):
    used=set()
    matches=0
    for candidate in candidates:
        for idx,ref in enumerate(references):
            if idx not in used and matcher(ref,candidate):
                used.add(idx)
                matches+=1
                break
    return matches


def metrics(gold,articles,training_families=(),eligible_test_families=None):
    provenance=verify_gold(gold,training_families,eligible_test_families)
    candidates=[];abstentions=0;blocked=0
    observed=set()
    for a in articles:
        source=a.get("pmcid") or a.get("pmid") or a.get("doi")
        if not source or source in observed:
            raise ValueError("Duplicate/unknown original article in predictions")
        observed.add(source)
        if str(a.get("status","")).startswith("BLOCKED"):
            blocked+=1
            if a.get("candidates"):
                raise ValueError("Blocked source cannot issue clinical estimates")
        for c in a.get("candidates",[]):
            if c.get("status")=="NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED":
                pred=dict(c)
                for k in ("pmcid","pmid","doi"):
                    if k in a:
                        if k in pred and norm(pred[k])!=norm(a[k]):
                            raise ValueError("Prediction source ID contradicts parent article")
                        pred[k]=a[k]
                if not norm(pred.get("source_url")):
                    raise ValueError("Missing per-claim source URL")
                candidates.append(pred)
            else:
                abstentions+=1
    def scores(tp):
        precision=tp/len(candidates) if candidates else None
        recall=tp/len(gold)
        f1=(2*precision*recall/(precision+recall)
            if precision is not None and precision+recall else None)
        return {"tp":tp,"fp":len(candidates)-tp,"fn":len(gold)-tp,
                "precision":round(precision,4) if precision is not None else None,
                "recall":round(recall,4),"f1":round(f1,4) if f1 is not None else None}
    basic=one_to_one(gold,candidates,numeric_match)
    strict=one_to_one(gold,candidates,full_context_match)
    return {
        **provenance,
        "numeric_tuple":scores(basic),
        "strict_clinical_context":scores(strict),
        "candidate_count":len(candidates),
        "abstention_count":abstentions,
        "blocked_source_count":blocked,
        "qualified_independence_and_real_gold_not_cryptographically_authenticated":True,
        "scores_are_not_a_medical_approval":True,
        "warning":"Compute on a locked independent, expert-adjudicated source corpus only. Two pseudonyms and a reference string alone do not prove real independent medical review.",
    }


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--gold",required=True)
    p.add_argument("--predictions",required=True)
    p.add_argument("--train-families",nargs="*",default=[])
    p.add_argument("--reserved",required=True,
                   help="Frozen reserved trial family manifest with NO outcome labels")
    p.add_argument("--development-seed",required=True,
                   help="Pinned original development source registry")
    p.add_argument("--out",required=True)
    args=p.parse_args()
    gold=json.loads(Path(args.gold).read_text(encoding="utf-8"))
    data=json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    pool=json.loads(Path(args.reserved).read_text(encoding="utf-8"))
    seed=json.loads(Path(args.development_seed).read_text(encoding="utf-8"))
    from validate_reserved_holdout import validate_holdout
    validate_holdout(pool,seed)
    reserved={s["trial_family_id"] for s in pool["studies"]}
    trained=set(args.train_families)|{s["nct"] for s in seed["studies"]}
    scored=metrics(gold,data.get("articles",data.get("records",[])),
                   training_families=trained,eligible_test_families=reserved)
    dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(scored,indent=2),encoding="utf-8")
    print("NUMERIC_TRUE_POSITIVES",scored["numeric_tuple"]["tp"])
    print("CLINICAL_CONTEXT_TRUE_POSITIVES",scored["strict_clinical_context"]["tp"])


if __name__=="__main__":
    main()

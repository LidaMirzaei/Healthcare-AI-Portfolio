"""Two-independent-reviewer oncology reference workflow — no fake gold labels.

1) prepare: research candidate claims + mandatory harms/method tasks, WITHOUT
   implying they are truth or medical conclusions.
2) compare_reviews: compare separately supplied qualified-reviewer submissions;
   detect conflicts, invalid provenance and missing fields. It NEVER releases gold.

Human identity, clinical qualifications, licensing and real independence cannot
be established by an unauthenticated Python script. External scientific
adjudication/approval is required before exporting a definitive gold corpus.
No paid API, tokens, or copied article full text.
"""
import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from adc_reference_dataset import check_reference_schema

ALLOWED_VERDICTS={"supported","unsupported","unverifiable"}
REVIEWABLE_FIELDS=(
    "study_family_id", "pmid", "doi", "endpoint", "measure", "estimate",
    "ci_level", "ci_lower", "ci_upper", "population", "intervention",
    "comparator", "analysis_cutoff", "analysis_denominator",
    "endpoint_hierarchy", "source_url", "source_locator",
    "methods_limitations", "safety_review_completed",
    "corrections_checked", "source_checked"
)
REQUIRED_SUPPORTED_TEXT=(
    "study_family_id", "pmid", "doi", "endpoint", "measure", "population",
    "intervention", "analysis_cutoff", "analysis_denominator",
    "endpoint_hierarchy", "source_url", "source_locator",
    "methods_limitations"
)
MANDATORY_TASKS=("harms_and_grade", "study_design_and_risk_of_bias",
                 "missing_and_negative_outcomes")


def stable_json_sha256(data):
    blob=json.dumps(data,sort_keys=True,separators=(",",":"),
                    ensure_ascii=False,allow_nan=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def make_review_queue(seed, source_audit, reserved_families=()):
    check_reference_schema(seed)
    reserved=set(x.upper() for x in reserved_families)
    existing=set(x["nct"].upper() for x in seed["studies"])
    if existing & reserved:
        raise ValueError("Trial-family leakage: development studies overlap future holdout")
    lookup={x.get("pmid"):x for x in source_audit.get("studies",[])}
    if len(lookup)!=len(source_audit.get("studies",[])):
        raise ValueError("Duplicate audited source IDs")
    if len(lookup)!=len(seed["studies"]):
        raise ValueError("Incomplete source audit; no reference queue release")

    claims=[]
    for study in seed["studies"]:
        record=lookup.get(study["pmid"])
        if record is None:
            raise ValueError("Missing audited source: "+study["pmid"])
        checks=record.get("checks",{})
        if not (checks.get("pubmed_identity") and checks.get("source_doi_identity")):
            raise ValueError("PMID/DOI source identity must match original publication")
        if record.get("source_doi","").lower()!=study["expected_doi"].lower():
            raise ValueError("Audited DOI differs from pinned source DOI")
        claim_id=study["key"]+"|"+study["endpoint"]+"|"+study["outcome_role"]
        claims.append({
            "claim_id":claim_id,
            "parent_trial_id":study["nct"],
            "source_pmid":study["pmid"],
            "source_doi":study["expected_doi"],
            "original_publication":f"https://pubmed.ncbi.nlm.nih.gov/{study['pmid']}/",
            "candidate_only":{
                "endpoint":study["endpoint"],
                "endpoint_role":study["outcome_role"],
                "estimate_type":study["measure"],
                "estimate":study["estimate"],
                "ci_level":study["ci_level"],
                "ci_lower":study["ci_lower"],
                "ci_upper":study["ci_upper"],
                "population_hint":study["subtype"],
                "setting_hint":study["setting"],
                "prior_treatment_hint":study["line"],
                "intervention_hint":study["intervention"],
                "comparator_hint":study["comparator"],
                "not_clinically_validated":True,
            },
            "source_audit_only":{
                "pmid_doi":True,
                "local_statistic_candidate":bool(checks.get("local_statistic_endpoint_candidate")),
                "registry_in_original_pubmed":bool(
                    checks.get("nct_found_in_abstract") or
                    checks.get("nct_found_in_pubmed_databank")),
                "source_status":record.get("verification_status"),
            },
            "review_tasks":[
                {"task":topic, "status":"PENDING_INDEPENDENT_EXPERT_REVIEW"}
                for topic in MANDATORY_TASKS
            ],
            "mandatory_fields_per_outcome":list(REVIEWABLE_FIELDS),
            "source_locator_verified":False,
            "two_human_reviews_complete":False,
            "adjudicated_gold":False,
            "safety_and_methods_fully_annotated":False,
        })

    queue={
        "schema":"breast-adc-review-candidates-v1",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "state":"UNREVIEWED_NOT_GOLD",
        "reference_count":len(claims),
        "target_minimum_review_tasks":len(claims)*len(MANDATORY_TASKS),
        "human_review_submissions":0,
        "gold_claims":0,
        "claims":claims,
    }
    queue["candidate_set_sha256"]=stable_json_sha256([
        {"claim_id":x["claim_id"],"source_doi":x["source_doi"],
         "candidate_only":x["candidate_only"]} for x in claims])
    return queue


def review_template(queue, reviewer_id):
    """Blank per-person sheet. No synthetic 'validated' fields or fake signoffs."""
    if not reviewer_id or not isinstance(reviewer_id,str):
        raise ValueError("Reviewer pseudonym required")
    return {
        "schema":"independent-scientific-review-v1",
        "candidate_set_sha256":queue["candidate_set_sha256"],
        "reviewer_id":reviewer_id,
        "professional_qualification_externally_checked":False,
        "independent_review_performed":False,
        "records":[{
            "claim_id":item["claim_id"],
            "verdict":"unverifiable",
            "verified_fields":{},
            "rationale":"PENDING_REVIEW",
            "additional_outcomes_not_in_seed":[],
            "methods_review_status":"PENDING",
            "harms_review_status":"PENDING",
            "negative_results_review_status":"PENDING"
        } for item in queue["claims"]
        ]
    }


def validate_review(queue, submission):
    """Validate format. Does NOT authenticate reviewer identity/competence."""
    if submission.get("schema")!="independent-scientific-review-v1":
        raise ValueError("Review schema unsupported")
    if submission.get("candidate_set_sha256")!=queue["candidate_set_sha256"]:
        raise ValueError("Review conducted against a different candidate-set revision")
    if not isinstance(submission.get("reviewer_id"),str) or not submission["reviewer_id"].strip():
        raise ValueError("Missing reviewer ID")
    if submission.get("professional_qualification_externally_checked") is not True:
        raise ValueError("Qualified reviewer identity must be externally checked")
    if submission.get("independent_review_performed") is not True:
        raise ValueError("Independent-review attestation missing")
    refs={x["claim_id"]:x for x in queue["claims"]}
    observed=set()
    for row in submission.get("records",[]):
        cid=row.get("claim_id")
        if cid not in refs or cid in observed:
            raise ValueError("Unknown/duplicate claim in submission")
        observed.add(cid)
        verdict=row.get("verdict")
        if verdict not in ALLOWED_VERDICTS:
            raise ValueError("Invalid clinical verdict")
        if not isinstance(row.get("rationale"),str) or len(row["rationale"].strip())<12:
            raise ValueError("Reviewer rationale is missing")
        if verdict=="supported":
            f=row.get("verified_fields",{})
            for key in REQUIRED_SUPPORTED_TEXT:
                val=f.get(key)
                if not isinstance(val,str) or not val.strip():
                    raise ValueError(f"Supported result missing {key}")
            if not all(f.get(k) is True for k in
                       ("source_checked","corrections_checked","safety_review_completed")):
                raise ValueError("Supported result lacks source, correction or harms review")
            if f["study_family_id"].upper()!=refs[cid]["parent_trial_id"].upper():
                raise ValueError("Reviewer trial family differs from original parent study")
            if f["pmid"]!=refs[cid]["source_pmid"] or f["doi"].lower()!=refs[cid]["source_doi"].lower():
                raise ValueError("Reviewer identity inconsistent with original PMID/DOI")
            if not f["source_url"].startswith(("https://pubmed.ncbi.nlm.nih.gov/",
                                                "https://pmc.ncbi.nlm.nih.gov/",
                                                "https://doi.org/","https://www.")):
                raise ValueError("Original evidence URL required")
            for k in ("estimate","ci_level","ci_lower","ci_upper"):
                v=f.get(k)
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
                    raise ValueError("Supported effect lacks numeric estimate/CI: "+k)
            if not 0 < f["ci_level"] < 100 or not 0 < f["ci_lower"] <= f["estimate"] <= f["ci_upper"] <= 100:
                raise ValueError("Confidence interval or effect invalid")
            if f["measure"] in ("HR","OR") and f["ci_upper"]>50:
                raise ValueError("Likely misattributed comparative effect")
            if f["comparator"] is None:
                if f["measure"] != "percent":
                    raise ValueError("Null comparator only for non-comparative estimate")
            elif not isinstance(f["comparator"],str) or not f["comparator"].strip():
                raise ValueError("Comparator absent or malformed")
        else:
            if row.get("verified_fields"):
                raise ValueError("Unverified/unsupported verdict must not carry approved fields")
        if row.get("methods_review_status")!="COMPLETE" or row.get("harms_review_status")!="COMPLETE" or row.get("negative_results_review_status")!="COMPLETE":
            raise ValueError("Methods/harms/negative-outcome completeness check pending")
        if not isinstance(row.get("additional_outcomes_not_in_seed"),list):
            raise ValueError("Must explicitly record missing outcomes separately")
    if observed!=set(refs):
        raise ValueError("Incomplete independent review submission")
    return {"claim_count":len(observed),"reviewer_id":submission["reviewer_id"],
            "format_valid":True,"human_credentials_authenticated_by_program":False}


def compare_reviews(queue, first, second):
    """Report agreements/disagreements; NEVER synthesize or approve final gold."""
    a=validate_review(queue,first)
    b=validate_review(queue,second)
    if a["reviewer_id"].casefold()==b["reviewer_id"].casefold():
        raise ValueError("The two reviewer IDs must differ")
    first_map={x["claim_id"]:x for x in first["records"]}
    second_map={x["claim_id"]:x for x in second["records"]}
    report=[]
    for candidate in queue["claims"]:
        cid=candidate["claim_id"]
        x,y=first_map[cid],second_map[cid]
        # Never silently choose one version if two verified values differ.
        same=(x["verdict"]==y["verdict"] and
              x.get("verified_fields",{})==y.get("verified_fields",{}))
        report.append({
            "claim_id":cid,
            "agreement_type":("MATCHING_INDEPENDENT_DECLARATIONS" if same else
                              "CONFLICT_REQUIRES_SEPARATE_ADJUDICATION"),
            "both_marked_supported":x["verdict"]==y["verdict"]=="supported",
            "requires_human_adjudication":not same,
            "eligible_for_external_identity_and_evidence_audit":(
                same and x["verdict"]=="supported"),
        })
    return {
        "status":"REVIEW_COMPARISON_ONLY_NOT_GOLD",
        "declared_reviewers":[a["reviewer_id"],b["reviewer_id"]],
        "declarations_externally_authenticated_by_this_tool":False,
        "agreement_count":sum(not x["requires_human_adjudication"] for x in report),
        "disagreement_count":sum(x["requires_human_adjudication"] for x in report),
        "human_adjudicated_gold_count":0,
        "scientific_accuracy_measured":False,
        "items":report,
    }


def main():
    p=argparse.ArgumentParser()
    modes=p.add_subparsers(dest="action",required=True)
    prep=modes.add_parser("prepare")
    prep.add_argument("--seed",required=True)
    prep.add_argument("--audit",required=True)
    prep.add_argument("--reserved",required=True)
    prep.add_argument("--out",required=True)
    template=modes.add_parser("template")
    template.add_argument("--queue",required=True)
    template.add_argument("--reviewer-id",required=True)
    template.add_argument("--out",required=True)
    check=modes.add_parser("compare")
    check.add_argument("--queue",required=True)
    check.add_argument("--first",required=True)
    check.add_argument("--second",required=True)
    check.add_argument("--out",required=True)
    args=p.parse_args()
    if args.action=="prepare":
        seed=json.loads(Path(args.seed).read_text())
        audit=json.loads(Path(args.audit).read_text())
        reserved=json.loads(Path(args.reserved).read_text())
        q=make_review_queue(seed,audit,
            [x["trial_family_id"] for x in reserved["studies"]])
        out=q
        print("PRELIMINARY_CLAIMS",q["reference_count"])
        print("MANDATORY_REVIEW_TASKS",q["target_minimum_review_tasks"])
        print("ADJUDICATED_GOLD",q["gold_claims"])
    else:
        q=json.loads(Path(args.queue).read_text())
        if args.action=="template":
            out=review_template(q,args.reviewer_id)
            print("REVIEW_TEMPLATE_UNFILLED",len(out["records"]))
        else:
            a=json.loads(Path(args.first).read_text())
            b=json.loads(Path(args.second).read_text())
            out=compare_reviews(q,a,b)
            print("REVIEW_DISAGREEMENTS",out["disagreement_count"])
            print("GOLD_RELEASED",out["human_adjudicated_gold_count"])
    dest=Path(args.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()

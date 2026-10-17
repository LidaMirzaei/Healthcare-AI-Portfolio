"""Holdout family isolation + no-outcome-labels release checks.

Only original article identifiers, intended category and trial-family IDs are
stored; no held-out clinical values are ever passed to development extractors.
"""
import argparse
import json
import re
from pathlib import Path
from clinical_reference_review import stable_json_sha256

TRIAL=re.compile(r"^NCT\d{8}$",re.I)
PMID=re.compile(r"^\d{7,9}$")
DOI=re.compile(r"^10\.\d{4,9}/\S+",re.I)


def validate_holdout(pool, development):
    if pool.get("status")!="RESERVED_NOT_EVALUATED_NOT_GOLD":
        raise ValueError("Holdout can only be reserved, never automatically scored")
    studies=pool.get("studies")
    if not isinstance(studies,list) or len(studies)<5:
        raise ValueError("Insufficient reserved trial families")
    if pool.get("contains_outcome_values") is not False:
        raise ValueError("An independent reserved manifest must not contain outcomes")
    dev={s["nct"].upper() for s in development.get("studies",[])}
    excluded={
        "NCT05104866","NCT03725059","NCT05375461","NCT06311383",
        "NCT04191499_NONEXISTENT_STUB"
    }
    # Exclude previously inspected holdout manuscript families when known;
    # exclusion of INAVO120 here would conflict with its new allocation;
    # prior V2/V3 were different families and are recorded in provenance.
    selected=set()
    pmids=set()
    for study in studies:
        trial=study.get("trial_family_id","")
        pmid=study.get("pmid","")
        if not TRIAL.fullmatch(trial) or not PMID.fullmatch(pmid):
            raise ValueError("Missing exact trial identifier or original PMID")
        if not DOI.fullmatch(study.get("doi","")):
            raise ValueError("Missing original DOI")
        if trial.upper() in dev or trial.upper() in excluded:
            raise ValueError("Study-family overlap with development or prior holdout")
        if trial in selected or pmid in pmids:
            raise ValueError("Duplicate trial family or PMID")
        selected.add(trial)
        pmids.add(pmid)
        allowed={"trial_family_id","label","pmid","doi","study_type",
                 "category","source"}
        if set(study)-allowed:
            raise ValueError("Unexpected possibly outcome-bearing field in holdout manifest")
    return {
        "reserved_families":len(selected),
        "unseen_outcome_labels":True,
        "clinical_gold_labels":0,
        "scoring_blocked_pending_expert_review":True,
        "manifest_sha256":stable_json_sha256(studies),
        "note":"Source abstracts partly inspected during planning; reserve is not a fully blinded external benchmark."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",required=True)
    p.add_argument("--reserved",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    dev=json.loads(Path(args.seed).read_text(encoding="utf-8"))
    pool=json.loads(Path(args.reserved).read_text(encoding="utf-8"))
    audit=validate_holdout(pool,dev)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    print("HOLDOUT_RESERVED_FAMILIES",audit["reserved_families"])
    print("HOLDOUT_CLINICAL_GOLD_LABELS",audit["clinical_gold_labels"])
    print("HOLDOUT_SCORING_BLOCKED",audit["scoring_blocked_pending_expert_review"])


if __name__=="__main__":
    main()

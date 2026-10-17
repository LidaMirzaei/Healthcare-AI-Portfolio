"""Once-only, small, original-source abstract shadow challenge (NOT gold).

Expected labels and study-family rules are read ONLY after predictions have
been generated and persisted by pubmed_shadow_extractor.py. Do NOT use these
labels to optimize extraction or rebrand any rerun as a new independent test.
"""
import argparse
import json
from pathlib import Path

STATS_FIELDS=("endpoint","measure","estimate","ci_level","ci_lower","ci_upper")


def approx(x,y):
    try:
        if isinstance(x,bool) or isinstance(y,bool):
            return False
        return abs(float(x)-float(y))<=1e-7
    except (ValueError,TypeError):
        return False


def exact_pair(label,prediction):
    return (prediction.get("status")=="SOURCE_NUMERIC_TUPLE_CANDIDATE_REVIEW_REQUIRED"
            and label["endpoint"]==prediction.get("endpoint")
            and label["measure"]==prediction.get("measure")
            and all(approx(label[k],prediction.get(k))
                    for k in ("estimate","ci_level","ci_lower","ci_upper")))


def score(predictions, frozen):
    if frozen.get("status")!="PUBLIC_ORIGINAL_ABSTRACT_ASSISTANT_SPOTCHECK_NOT_MEDICAL_GOLD":
        raise ValueError("Not a frozen preliminary source spotcheck")
    src=frozen["studies"]
    fams=[s["nct"] for s in src]
    pmids=[s["pmid"] for s in src]
    if len(set(fams))!=len(fams) or len(set(pmids))!=len(pmids):
        raise ValueError("Duplicate study families or original PMIDs in reference")
    banned=set(frozen.get("training_families",[]))|set(frozen.get("reserved_v4_families_excluded",[]))
    if any(v in banned for v in fams):
        raise ValueError("External challenge overlaps prior trained or reserved families")
    docs={x["pmid"]:x for x in predictions["articles"]}
    if len(docs)!=len(predictions["articles"]) or set(docs)!=set(pmids):
        raise ValueError("Unexpected or duplicated prediction source IDs")
    checked=[];total_candidates=0;total_abstained=0;source_identity_pass=0
    for source in src:
        record=docs[source["pmid"]]
        identity=(record.get("doi","").lower()==source["doi"].lower()
                  and record.get("source_status") in (
                      "ABSTRACT_RESULTS_ONLY","ORIGINAL_PUBMED_XML_RESULTS_TAGGED"))
        source_identity_pass+=int(identity)
        candidates=record.get("candidates",[])
        total_candidates+=len(candidates)
        total_abstained+=len(record.get("abstentions",[]))
        used=set()
        statuses=[]
        for j,ref in enumerate(source["expected"]):
            matches=[(i,c) for i,c in enumerate(candidates)
                     if i not in used and exact_pair(ref,c)]
            if identity and matches:
                i,_=matches[0];used.add(i)
                passed=True
            else:
                passed=False
            statuses.append({
                "trial":source["trial"],"nct":source["nct"],"pmid":source["pmid"],
                "source_url":source["source"],
                "endpoint":ref["endpoint"],"measure":ref["measure"],
                "expected_effect":ref["estimate"],"ci_level":ref["ci_level"],
                "ci_lower":ref["ci_lower"],"ci_upper":ref["ci_upper"],
                "outcome_context_ANNOTATED_BUT_NOT_MACHINE_CHECKED":ref["scope"],
                "candidate_numeric_tuple_match":passed,
                "requires_full_scientific_review":True,
            })
        checked.extend(statuses)
        if source.get("critical_interpretation"):
            checked.append({
                "trial":source["trial"],"pmid":source["pmid"],
                "check_type":"SOURCE_INTERPRETATION_UNADJUDICATED",
                "critical_context_note":source["critical_interpretation"],
                "source_text_warning_flags":record.get("risk_language_review_flags",[]),
                "not_a_numeric_gold_label":True,
            })
    numeric=[x for x in checked if "candidate_numeric_tuple_match" in x]
    passed=sum(x["candidate_numeric_tuple_match"] for x in numeric)
    return {
        "evaluation":"PROSPECTIVE_SOURCE_ABSTRACT_SHADOW_CHALLENGE",
        "not_an_expert_gold_standard":True,
        "medically_adjudicated_claims":0,
        "statistical_clinical_precision_unmeasured":True,
        "first_run_only_external_status":"CONSUMED_AFTER_FIRST_RUN",
        "source_records_verified":source_identity_pass,
        "source_records_expected":len(src),
        "predeclared_numeric_pairs":len(numeric),
        "exact_numeric_tuple_pairs_matched":passed,
        "unmatched_predeclared_pairs":len(numeric)-passed,
        "source_candidate_count_all":total_candidates,
        "abstentions_count":total_abstained,
        "numeric_tuple_match_rate_on_selected_original_abstract_pairs":(
            round(passed/len(numeric),4) if numeric else None),
        "caveat":"Not medical accuracy: source abstract candidate matching cannot establish comparator, endpoint hierarchy, subgroup, multiplicity, cutoff, harms, corrections or clinical significance; baseline and labels are unblinded after run.",
        "itemized_evidence":checked,
    }


def render(out):
    lines=["# One-time V5: external abstract numeric source challenge","",
           "**This is NOT clinical accuracy, specialist gold, or full-text evidence validation.**",
           "Predictions were created without labels. This run consumes V5's initial independence.",
           f"- Original PubMed PMID+DOI sources: {out['source_records_verified']}/{out['source_records_expected']}",
           f"- Predeclared numeric tuples matched: {out['exact_numeric_tuple_pairs_matched']}/{out['predeclared_numeric_pairs']}",
           f"- Numeric tuples missed: {out['unmatched_predeclared_pairs']}",
           f"- All extracted reviewable candidates (may include unlabelled): {out['source_candidate_count_all']}",
           f"- Abstentions: {out['abstentions_count']}",
           "- True independent specialist-reviewed gold labels: **0**",
           "",
           "| Parent study | Endpoint | Candidate tuple | Context caution |",
           "|---|---|---|---|"]
    for x in out["itemized_evidence"]:
        if "candidate_numeric_tuple_match" in x:
            lines.append(
                f"| [{x['trial']}]({x['source_url']}) | {x['endpoint']} "
                f"| {'MATCHED' if x['candidate_numeric_tuple_match'] else 'MISSING'} "
                f"| {x['outcome_context_ANNOTATED_BUT_NOT_MACHINE_CHECKED']} |")
    lines+=["","## Critical original-source cautions",""]
    for x in out["itemized_evidence"]:
        if x.get("check_type")=="SOURCE_INTERPRETATION_UNADJUDICATED":
            lines.append(f"- **{x['trial']}**: {x['critical_context_note']}")
    lines+=["","## Why this cannot certify the AI agent","",
            "- The challenge tests selected abstract HR/CI tuples only, not unobserved paper outcomes or full-text tables.",
            "- Study type and original paper identity are verified; endpoint/cohort assignment is STILL PROVISIONAL.",
            "- An apparent PFS advantage cannot be substituted for meeting a prespecified OS threshold.",
            "- Negative/non-significant results and serious harms require independent full-text clinical verification.",
            "- Repeating V5 after inspecting its results is a REGRESSION, not independent validation.",
            "- Two qualified independent reviewers, adjudication and a separately blinded trial-family set are required for real precision/recall and time-saving claims.",
            "",
            "No paid API, proprietary full-text redistribution, or corporate clinical data involved."]
    return "\n".join(lines)+"\n"


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen",required=True)
    parser.add_argument("--predictions",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    frozen=json.loads(Path(args.frozen).read_text(encoding="utf-8"))
    predictions=json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    evaluated=score(predictions,frozen)
    path=Path(args.out);path.mkdir(parents=True,exist_ok=True)
    (path/"shadow_v5_scorecard.json").write_text(
        json.dumps(evaluated,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (path/"shadow_v5_scorecard.md").write_text(render(evaluated),encoding="utf-8")
    print("V5_SOURCE_IDENTITIES",evaluated["source_records_verified"],
          "/",evaluated["source_records_expected"])
    print("V5_EXACT_TUPLE_MATCHES",evaluated["exact_numeric_tuple_pairs_matched"],
          "/",evaluated["predeclared_numeric_pairs"])
    print("V5_UNMATCHED_TUPLES",evaluated["unmatched_predeclared_pairs"])
    print("V5_REVIEWABLE_CANDIDATES",evaluated["source_candidate_count_all"])
    print("V5_ABSTENTIONS",evaluated["abstentions_count"])
    print("V5_REAL_EXPERT_GOLD",0)
    if evaluated["source_records_verified"]!=evaluated["source_records_expected"]:
        raise RuntimeError("Original DOI/PMID source identity mismatch")

if __name__=="__main__":
    main()

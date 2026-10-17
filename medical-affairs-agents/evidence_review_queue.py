"""Generate a review-ready queue, NOT an automatically approved clinical brief.

Uses rights-filtered V3 extraction records. Groups shared registry identifiers
as PROVISIONAL trial families (never asserts independent evidence from papers
sharing an NCT). Protects against publication-level double-counting, unsupported
OS/PFS equivalence, and claims without clinician sign-off.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

NCT = re.compile(r"^NCT\d{8}$", re.I)
NUMERIC_STATUS = "NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED"


def family_for(record):
    """Conservative source-level grouping; registration itself remains unverified."""
    trial = record.get("registration_candidate") or ""
    if NCT.fullmatch(trial):
        return "POTENTIAL_SHARED_TRIAL:" + trial.upper(), True
    return "UNVERIFIED_FAMILY:" + record["pmcid"], False


def triage(records):
    """Accept input study records without reading benchmarks or gold labels."""
    if len({r["pmcid"] for r in records}) != len(records):
        raise ValueError("Duplicate PMCID input — would distort evidence coverage")
    families=defaultdict(list)
    rows=[]
    for r in records:
        id_ = r["pmcid"]
        family, corroborated = family_for(r)
        families[family].append(id_)
        license_ok=r.get("license",{}).get("status")=="CC_BY_OR_CC0_CONFIRMED"
        studies=[]
        for i, c in enumerate(r.get("candidates",[])):
            if "source_url" not in c or "source_level" not in c or "status" not in c:
                raise ValueError("Candidate lacking citation/provenance cannot enter reviewer queue")
            positive=c["status"]==NUMERIC_STATUS
            details={
                "candidate_id":f"{id_}:{i+1}",
                "source_url":c["source_url"],
                "source_id":c.get("source_id"),
                "source_id_kind":c.get("source_id_kind"),
                "source_level":c["source_level"],
                "endpoint":c.get("endpoint", "NOT_RESOLVED"),
                "status":c["status"],
                "finding_available":positive,
                "review_priority":"FULLTEXT_CANDIDATE" if (
                    positive and c["source_level"]=="FULLTEXT_RESULTS") else (
                    "ABSTRACT_ONLY_REQUIRES_ORIGINAL_RESULTS" if positive else "ABSTENTION_CHECK"),
                "scientifically_validated":False,
                "clinical_release_authorized":False,
            }
            if positive:
                must_have=["measure","estimate","ci_level","ci_lower","ci_upper"]
                if not all(k in c for k in must_have):
                    raise ValueError("Malformed positive effect record — missing CI/estimate")
                if not (0<c["ci_lower"]<=c["estimate"]<=c["ci_upper"]<100):
                    raise ValueError("Invalid CI estimate range")
                details.update({k:c[k] for k in must_have})
                details["comparator_verified"]=bool(c.get("arm_assignment_verified"))
                details["cutoff_verified"]=bool(c.get("data_cutoff_verified"))
                details["population_verified"]=bool(c.get("population_verified"))
                details["review_needed"]=[
                    "verify_reported_treatment_arms_and_comparator",
                    "verify_outcome_population_and_subgroup",
                    "verify_analysis_cutoff_and_model",
                    "verify_statistical_interpretation_and_source_tables",
                ]
            studies.append(details)
        if not license_ok and studies:
            raise ValueError("Restricted/unknown-license article yielded mined content")
        if r.get("status","").startswith("BLOCKED") and studies:
            raise ValueError("Blocked article yielded clinical effect candidates")
        rows.append({
            "pmcid":id_,
            "title":r.get("title",""),
            "article_kind":r.get("article_kind") or r.get("title_type_hint") or "UNKNOWN",
            "license_status":r.get("license",{}).get("status","UNREPORTED"),
            "source_status":r.get("status","UNREPORTED"),
            "family_key":family,
            "registration_hint_not_verified":corroborated,
            "findings":studies,
            "source_candidate_count":sum(x["finding_available"] for x in studies),
            "abstained_count":sum(not x["finding_available"] for x in studies),
        })
    overlapping={k:ids for k,ids in families.items()
                 if k.startswith("POTENTIAL_SHARED_TRIAL:") and len(ids)>1}
    results={
        "article_count":len(rows),
        "provisional_study_family_count":len(families),
        "repeated_registry_groups_needing_confirmation":overlapping,
        "unverified_registration_count":sum(not r["registration_hint_not_verified"] for r in rows),
        "source_candidate_count":sum(r["source_candidate_count"] for r in rows),
        "abstention_count":sum(r["abstained_count"] for r in rows),
        "abstract_only_candidate_count":sum(
            x["finding_available"] and x["source_level"].startswith("ABSTRACT")
            for r in rows for x in r["findings"]),
        "clinical_claims_released":0,
        "requires_qualified_reviewer":True,
        "metric_is_clinical_accuracy":False,
        "records":rows,
    }
    return results


def render(q):
    lines=["# Clinical Evidence Review Queue — NOT approved conclusions", "",
        "**No claims in this queue have passed clinical sign-off.**",
        "This is source-linked extraction for Medical Affairs review, not efficacy, safety or treatment recommendations.",
        "**Trial registrations are metadata hints, not validated study identity.**",
        "",
        f"- Papers processed: **{q['article_count']}**",
        f"- Provisional study families: **{q['provisional_study_family_count']}**",
        f"- Effect candidates for expert review: **{q['source_candidate_count']}**",
        f"- Abstentions: **{q['abstention_count']}**",
        f"- Abstract-only candidates: **{q['abstract_only_candidate_count']}**",
        f"- Medically approved claims: **{q['clinical_claims_released']}**",
        "",
        "| Article | License/source status | Trial-family grouping (unverified) | Candidate / abstained |",
        "|---|---|---|---|",
    ]
    for r in q["records"]:
        lines.append(
            f"| [{r['pmcid']}](https://pmc.ncbi.nlm.nih.gov/articles/{r['pmcid']}/) "
            f"| {r['license_status']} / {r['source_status']} "
            f"| {r['family_key']} "
            f"| {r['source_candidate_count']} / {r['abstained_count']} |")
    if q["repeated_registry_groups_needing_confirmation"]:
        lines.extend(["","## Potential publication overlap — DO NOT double-count"])
        for family, ids in q["repeated_registry_groups_needing_confirmation"].items():
            lines.append(f"- **{family}:** {', '.join(ids)}. Verify the actual registration against trial report before grouping.")
    for r in q["records"]:
        lines += ["", f"## {r['title'] or r['pmcid']}", "",
                  "**Source:** https://pmc.ncbi.nlm.nih.gov/articles/"+r["pmcid"]+"/",
                  "**Article type (provisional):** "+r["article_kind"], ""]
        if not r["findings"]:
            lines += ["No mined results. This can mean a license gate, missing source, or no reliably extractable estimate; **not** a claim that the study lacked outcomes.",""]
        for a in r["findings"]:
            label=(f"{a['measure']} {a['estimate']} ({a['ci_level']}% CI "
                   f"{a['ci_lower']}–{a['ci_upper']})" if a["finding_available"] else a["status"])
            lines += [f"- **{a['candidate_id']} — {a['endpoint']}: {label}**",
                      f"  - Priority: {a['review_priority']}",
                      f"  - {a['source_level']} / {a['source_id_kind']}: {a['source_id']}",
                      f"  - Original source: {a['source_url']}",
                      "  - **Not validated:** population, intervention/comparator, cutoff, model and statistical interpretation.", ""]
    lines += ["## Strict release gate", "",
              "- [ ] Confirm article license/rights and study-family identity.",
              "- [ ] Confirm primary vs secondary/exploratory endpoint and original study population.",
              "- [ ] Check numeric effect, CI level, intervention/comparator, denominators and full source tables.",
              "- [ ] Confirm whether an apparent negative outcome is non-significant or inconclusive; do not treat PFS as OS.",
              "- [ ] Apply outcome-specific risk-of-bias criteria and discuss missingness.",
              "- [ ] Review all relevant harms, not only favorable efficacy outcomes.",
              "- [ ] Qualified scientific reviewer signs off each claim before executive release.",
              "",
              "**This tool deliberately cannot release a medical executive conclusion.**"]
    return "\n".join(lines)+"\n"


def run(input_file, out_dir):
    data=json.loads(Path(input_file).read_text(encoding="utf-8"))
    queue=triage(data["articles"])
    out=Path(out_dir)
    out.mkdir(parents=True,exist_ok=True)
    (out/"evidence_review_queue.json").write_text(json.dumps(queue,indent=2),encoding="utf-8")
    (out/"evidence_review_queue.md").write_text(render(queue),encoding="utf-8")
    print("REVIEW_QUEUE_ARTICLES",queue["article_count"])
    print("REVIEW_QUEUE_CANDIDATES",queue["source_candidate_count"])
    print("REVIEW_QUEUE_ABSTENTIONS",queue["abstention_count"])
    print("REVIEW_QUEUE_APPROVED_CLINICAL_CLAIMS",queue["clinical_claims_released"])


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--out",default="medical-affairs-agents/output/review_queue")
    args=p.parse_args()
    run(args.input,args.out)

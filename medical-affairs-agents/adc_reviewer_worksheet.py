"""Prepare an UNFILLED two-reviewer checklist for each selected ADC study.

This does not analyze restricted full text or produce validated medical labels.
It documents what two independent scientific reviewers must verify before a
provisional source reference becomes an adjudicated gold-standard outcome.
"""
import argparse
import json
from pathlib import Path
from adc_reference_dataset import DEFAULT_SEED, check_reference_schema


def create_worksheet(seed, audit):
    check_reference_schema(seed)
    if audit.get("source_checks_completed",0)!=len(seed["studies"]):
        raise ValueError("Cannot prepare a complete review packet from missing original source records")
    by_pmid={x["pmid"]:x for x in audit["studies"]}
    lines=[
      "# Breast Cancer ADC — Independent Scientific Review Worksheet",
      "",
      "**NOT VERIFIED, NOT APPROVED, NOT A GOLD STANDARD.**",
      "Every outcome requires two qualified reviewers examining original article",
      "Methods, Results, tables, corrections and supplementary material.",
      "This worksheet deliberately contains no approved study-quality grades.",
      "",
      "## Review questions across all parent trials",
      "- Is the question about a population that matches the source eligibility and biomarker subgroup?",
      "- Is this early adjuvant disease, first-line metastatic disease, or a pretreated metastatic cohort?",
      "- Is there an actual randomized comparator, or is the result a single-arm response rate?",
      "- Do PFS, OS, invasive DFS, ORR and PRO address different questions?",
      "- Was the endpoint co-primary, primary, secondary or exploratory and what were the multiplicity rules?",
      "- Are confidence interval levels and bounds faithfully reproduced (including unusual 99% or 95.01%)?",
      "- Are analysis data cutoffs, censoring, follow-up, dose, comparator, and subsequent therapies documented?",
      "- Are adverse events including interstitial lung disease/pneumonitis, deaths, and treatment discontinuation covered?",
      "- Are there publication corrections, overlapping reports, missing denominators, biases or sponsorship disclosures?",
      "",
    ]
    for item in seed["studies"]:
        record=by_pmid.get(item["pmid"],{})
        lines += [
            "## "+item["key"]+" — "+item["nct"],
            "",
            "- Primary PubMed: https://pubmed.ncbi.nlm.nih.gov/"+item["pmid"]+"/",
            "- Trial registry: https://clinicaltrials.gov/study/"+item["nct"],
            "- Expected original DOI: "+item["expected_doi"],
            "- Source-check status: "+record.get("verification_status","NOT_RETRIEVED"),
            "- Biomarker subtype: "+item["subtype"],
            "- Population and setting: "+item["setting"],
            "- Prior treatment: "+item["line"],
            "- Intervention: "+item["intervention"],
            "- Comparator: "+(item["comparator"] or "NONE — SINGLE ARM"),
            "- Proposed outcome: "+item["endpoint"]+" ("+item["outcome_role"]+")",
            "- Proposed effect/response: "+item["measure"]+" "+str(item["estimate"]),
            "- Confidence interval level: "+(str(item["ci_level"])+"%" if item["ci_level"] is not None else "NOT REPORTED IN SOURCE ABSTRACT"),
            "- Special review note: "+item["note"],
        ]
        if item.get("additional_regulatory_cross_reference"):
            lines += [
                "- Regulatory cross-reference (separate from original PMID registration metadata): "+
                  item["additional_regulatory_cross_reference"],
                "- Trial registration linkage in original PubMed audit: PENDING independent confirmation",
            ]
        lines += [
          "",
          "- [ ] Reviewer 1 verifies PMID, DOI, NCT, version and any erratum.",
          "- [ ] Reviewer 2 independently verifies PMID, DOI, NCT, version and any erratum.",
          "- [ ] Verify eligibility, biomarker assay, study phase, randomization/control and line of therapy.",
          "- [ ] Verify source Results/Table/Figure for estimate, CI level, CI bounds, arm assignment and endpoint.",
          "- [ ] Verify endpoint hierarchy, missingness, multiplicity, data cutoff and population denominator.",
          "- [ ] Extract specific severe adverse events and harms, including ILD/pneumonitis and deaths.",
          "- [ ] Evaluate biases and whether results generalize beyond this trial's population.",
          "- [ ] Compare corrections and supplements and document licensing for intended use.",
          "- [ ] Reviewer 1 conclusion and source: PENDING",
          "- [ ] Reviewer 2 conclusion and source: PENDING",
          "- [ ] Disagreements resolved by third-party adjudication: PENDING",
          "- [ ] Medically approved for any external use: NO",
          "",
        ]
    lines += [
      "## Release gate",
      "All of the above are pending. Passing source-text token checks does not mean",
      "an outcome is medically validated or approved for a Medical Affairs brief.",
      "Never merge publications that share the same trial registration as independent experiments.",
      "Only independently adjudicated clinical outcome labels may enter a future gold standard.",
    ]
    return "\n".join(lines)+"\n"


def run(seed_path=DEFAULT_SEED, audit_path="medical-affairs-agents/output/adc_reference_packet/adc_source_audit.json", out_path="medical-affairs-agents/output/adc_reference_packet/adc_independent_review_worksheet.md"):
    seed=json.loads(Path(seed_path).read_text(encoding="utf-8"))
    audit=json.loads(Path(audit_path).read_text(encoding="utf-8"))
    report=create_worksheet(seed,audit)
    path=Path(out_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(report,encoding="utf-8")
    print("INDEPENDENT_REVIEW_WORKSHEETS",len(seed["studies"]))
    print("ADJUDICATED_SCIENTIFIC_LABELS",0)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",type=Path,default=DEFAULT_SEED)
    parser.add_argument("--audit",default="medical-affairs-agents/output/adc_reference_packet/adc_source_audit.json")
    parser.add_argument("--out",default="medical-affairs-agents/output/adc_reference_packet/adc_independent_review_worksheet.md")
    args=parser.parse_args()
    run(args.seed,args.audit,args.out)

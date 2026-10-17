"""Fail-closed audit of selected numerical claims against OA full-text XML.

Retrieval matches are NOT independent scientific validation: reviewer must check
arms, endpoint, data cutoff, denominator and source table/figure.
"""
import argparse
import json
import re
from pathlib import Path

from fulltext_evidence import BASE, fetch, parse_xml

CLAIMS = [
    {"id":"global_pfs_medians", "pmcid":"PMC11771365",
     "statement":"Reported median PFS: Dato-DXd 6.9 months versus ICC 4.9 months.",
     "numbers":["6.9","4.9"],"concepts":["PFS","progression-free survival"]},
    {"id":"global_pfs_hr", "pmcid":"PMC11771365",
     "statement":"Reported PFS hazard ratio 0.63 (interpretation requires clinical review).",
     "numbers":["0.63"],"concepts":["hazard ratio","HR"]},
    {"id":"china_pfs_medians", "pmcid":"PMC13583573",
     "statement":"China exploratory subgroup: median PFS 8.1 versus 4.2 months.",
     "numbers":["8.1","4.2"],"concepts":["PFS","progression-free survival"]},
    {"id":"final_os_context", "pmcid":None,
     "statement":"Final OS 18.6 versus 18.3 months, HR 1.01. Separate 2026 OS article NOT ingested in this pipeline.",
     "numbers":["18.6","18.3","1.01"],"concepts":["overall survival"],
     "reference":"https://pubmed.ncbi.nlm.nih.gov/41448362/"},
]


def number_present(text, numeric):
    # Avoid treating e.g. 16.9 as 6.9 or 0.6300 as the exact 0.63.
    return bool(re.search(r"(?<![\d.])" + re.escape(numeric) + r"(?![\d.])",text))


def check_claim(claim, document):
    if claim["pmcid"] is None:
        return {"id":claim["id"],"status":"NOT_INGESTED_EXTERNAL_SOURCE",
                "statement":claim["statement"],"reference":claim.get("reference"),
                "candidates":[]}
    if document is None or document["pmcid"] != claim["pmcid"]:
        return {"id":claim["id"],"status":"SOURCE_MISSING",
                "statement":claim["statement"],"candidates":[]}
    candidates=[]
    for paragraphs in document["sections"].values():
        for p in paragraphs:
            text=p["text"]
            if all(number_present(text,n) for n in claim["numbers"]) and any(
                re.search(r"\b"+re.escape(term)+r"\b",text,re.I) for term in claim["concepts"]):
                candidates.append({"pmcid":document["pmcid"],"paragraph_id":p["id"],
                                   "source_section":p["heading"],
                                   "source_url":document["url"],
                                   "exact_numbers":claim["numbers"],
                                   "verbatim_paragraph":text})
    return {"id":claim["id"],"statement":claim["statement"],
            "status":"SOURCE_TEXT_CANDIDATE_REVIEW_REQUIRED" if candidates else "NOT_LOCATED_REVIEW_REQUIRED",
            "candidates":candidates[:3], "omitted_candidate_count":max(0,len(candidates)-3)}


def audit(documents, claims=CLAIMS):
    return [check_claim(claim,documents.get(claim["pmcid"])) for claim in claims]


def render(items):
    lines=["# Numerical Claim Audit — TROPION-Breast01","",
           "**A matched sentence is not a fact-checked clinical conclusion.**",
           "Numbers must be checked in context against original tables, arms, cutoffs, study endpoints and statistical plans.",
           "One trial, multiple overlapping publications. Final OS evidence is NOT in the three XML sources.",
           "","| Proposed claim | Source-text status | Candidate paragraphs |",
           "|---|---|---:|"]
    for a in items:
        lines.append("| "+a["id"]+" | "+a["status"]+" | "+str(len(a["candidates"]))+" |")
    for a in items:
        lines += ["","## "+a["id"],"",a["statement"],"",
                  "**Status:** "+a["status"],""]
        if a.get("reference"):
            lines += ["**External source:** "+a["reference"],""]
        for c in a["candidates"]:
            lines += [f"**{c['paragraph_id']} — {c['source_section']}**",
                      "Source: "+c["source_url"],"",
                      "> "+c["verbatim_paragraph"],""]
        if not a["candidates"]:
            lines += ["No evidence paragraph has been verified by this pipeline. Inspect source manually.",""]
    lines += ["## Reviewer release gate","",
              "- [ ] All numbers, units, denominators, arm assignments and time cutoffs verified",
              "- [ ] Table and supplemental analyses independently checked",
              "- [ ] PFS benefit not misreported as final OS benefit",
              "- [ ] Single parent trial counted once",
              "- [ ] External final OS source ingested and independently reviewed",
              "- [ ] Qualified scientific review completed",
              "",
              "Do **not** mark this report medically validated based on keyword/number co-occurrence."]
    return "\n".join(lines)+"\n"


def run(out):
    from pinned_trial_review import PAPERS
    docs = {}
    for p in PAPERS:
        pmcid = p["pmcid"]
        docs[pmcid] = parse_xml(fetch(BASE+"/"+pmcid+"/fullTextXML"),pmcid)
    items=audit(docs)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    (out/"numeric_claim_audit.json").write_text(json.dumps(items,indent=2),encoding="utf-8")
    (out/"numeric_claim_audit.md").write_text(render(items),encoding="utf-8")
    for item in items:
        print("CLAIM",item["id"],item["status"],len(item["candidates"]))
    print("NUMERIC_CLAIM_AUDIT_COMPLETED")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="medical-affairs-agents/output/pinned_trial")
    args=parser.parse_args()
    run(args.out)

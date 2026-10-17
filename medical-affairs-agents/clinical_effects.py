"""Study-family-aware, conservative outcome effect candidate extraction.

This is NOT an autonomous clinical analyst. It only identifies sentence-level,
source-attributed HR/OR estimates with *explicit* confidence intervals in JATS
Results paragraphs. Anything ambiguous abstains. Gold labels are NEVER loaded
in this module; benchmark scoring lives separately.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from fulltext_evidence import BASE, fetch
from independent_holdout import license_classification, extract_source_identity, text_of

ENDPOINTS = {
    "PFS": re.compile(r"\b(?:progression[\s-]?free survival|PFS)\b", re.I),
    "OS": re.compile(r"\b(?:overall survival|OS)\b", re.I),
    "EFS": re.compile(r"\b(?:event[\s-]?free survival|EFS)\b", re.I),
    "DFS": re.compile(r"\b(?:disease[\s-]?free survival|DFS)\b", re.I),
    "pCR": re.compile(r"\b(?:patholog(?:ic|ical)\s+complete response|pCR)\b", re.I),
    "ORR": re.compile(r"\b(?:objective response rate|ORR)\b", re.I),
}

EFFECT = re.compile(
    r"\b(?P<measure>hazard\s+ratio|odds\s+ratio|(?<!\w)HR(?!\w)|(?<!\w)OR(?!\w))"
    r"\s*(?:[:=,]|\bof\b|\bis\b|\s)*\s*(?P<point>\d{1,2}(?:\.\d{1,5})?)",
    re.I,
)
INTERVAL = re.compile(
    r"(?P<level>90|95|99)\s*%\s*"
    r"(?:CI|confidence\s+interval(?:\s*\(CI\))?)\s*[,;:=\(]?\s*"
    r"(?P<lower>\d+(?:\.\d+)?)\s*(?:to|[-–—,])\s*"
    r"(?P<upper>\d+(?:\.\d+)?)",
    re.I,
)
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def compact(text):
    return " ".join(text.replace("\u2212", "-").split())


def design_from_title(title):
    title = title.lower()
    if re.search(r"\b(cohort|observational|non.interventional|retrospective|real.world)\b", title):
        return "OBSERVATIONAL_OR_ASSOCIATION"
    if re.search(r"\b(randomi[sz]ed|phase\s*(?:2|3|ii|iii)\s+trial)\b", title):
        return "RANDOMIZED_TRIAL"
    return "DESIGN_UNCLEAR_REVIEW_REQUIRED"


def classify_heading(heading, inherited):
    name = heading.lower()
    if re.search(r"\b(results?|findings?|efficacy outcomes?)\b", name):
        return "results"
    if re.search(r"\b(safety|adverse events?|discussion|conclusions?|limitations?|introduction|"
                 r"background|methods?|patients? and methods|references?)\b", name):
        return "other"
    return inherited


def results_paragraphs(root, pmcid):
    body = root.find(".//body")
    if body is None:
        raise ValueError("No JATS body")
    index = 0

    def traverse(sec, inherited="other", parent_path=""):
        nonlocal index
        heading = text_of(sec.find("title"))
        category = classify_heading(heading, inherited)
        path = " / ".join(filter(None, (parent_path, heading)))
        for paragraph in sec.findall("p"):
            value = compact(text_of(paragraph))
            if not value or len(value) < 20:
                continue
            index += 1
            if category == "results":
                original_id = paragraph.get("id")
                href = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
                if original_id and re.fullmatch(r"[A-Za-z0-9_.:-]+", original_id):
                    href += "#" + original_id
                yield {
                    "source_id": original_id or f"{pmcid}-internal-p{index}",
                    "source_id_kind": "JATS_ID" if original_id else "INTERNAL_ONLY",
                    "section": path, "url": href,
                    "text": value,
                }
        for child in sec.findall("sec"):
            yield from traverse(child, category, path)

    for sec in body.findall("sec"):
        yield from traverse(sec)


def detect_endpoint(sentence, heading):
    present = [k for k, pattern in ENDPOINTS.items() if pattern.search(sentence)]
    if len(present) > 1:
        return "AMBIGUOUS_MULTIPLE_ENDPOINTS"
    if present:
        return present[0]
    inherited = [k for k, pattern in ENDPOINTS.items() if pattern.search(heading)]
    if len(inherited) == 1:
        return inherited[0]
    return "ENDPOINT_UNSPECIFIED"


def analyze_sentence(text, heading, source, design):
    """Return reviewable evidence candidate or abstention; never a conclusion."""
    estimates = list(EFFECT.finditer(text))
    intervals = list(INTERVAL.finditer(text))
    if not estimates:
        return None
    endpoint = detect_endpoint(text, heading)
    record = {
        "pmcid": source["pmcid"], "source_id": source["source_id"],
        "source_id_kind": source["source_id_kind"],
        "section": heading, "source_url": source["url"],
        "endpoint": endpoint, "design_context": design,
        "excerpt":text[:180] + ("…" if len(text)>180 else ""),
        "review_status": "HUMAN_SCIENTIFIC_REVIEW_REQUIRED",
        "automated_treatment_recommendation": False,
    }
    if len(estimates) != 1 or len(intervals) != 1:
        record["status"] = "ABSTAIN_MULTIPLE_OR_MISSING_ESTIMATE_OR_CI"
        record["detected_estimates"] = len(estimates)
        record["detected_intervals"] = len(intervals)
        return record
    if endpoint.startswith(("AMBIGUOUS", "ENDPOINT_")):
        record["status"] = "ABSTAIN_ENDPOINT_NOT_UNAMBIGUOUS"
        return record

    m,ci=estimates[0],intervals[0]
    point=float(m.group("point"))
    lower=float(ci.group("lower"))
    upper=float(ci.group("upper"))
    if not (0 < lower <= point <= upper and upper < 100):
        record["status"]="ABSTAIN_INVALID_CI_OR_POINT"
        return record
    # A single effect estimate and CI in one sentence must not be matched
    # across a second independent result in the same sentence.
    measure=m.group("measure").lower()
    key="HR" if "hazard" in measure or measure=="hr" else "OR"
    record.update({
        "measure":key,"point":point,"ci_level":int(ci.group("level")),
        "ci_lower":lower,"ci_upper":upper,
        "status":"SOURCE_EFFECT_CANDIDATE_REVIEW_REQUIRED",
        "causal_status":("ASSOCIATION_NOT_RANDOMIZED_TREATMENT_EFFECT"
                         if design=="OBSERVATIONAL_OR_ASSOCIATION"
                         else "TREATMENT_ATTRIBUTION_NOT_VALIDATED"),
        "arm_assignment_verified":False,
        "primary_endpoint_verified":False,
        "statistical_analysis_cutoff_verified":False,
    })
    return record


def extract_article(xml_bytes, pmcid):
    """Fail closed before reading Results when article rights are unsuitable."""
    root=ET.fromstring(xml_bytes)
    ids=extract_source_identity(root)
    actual_pmc=ids.get("pmc", "").replace("PMC","")
    if actual_pmc and actual_pmc != pmcid.replace("PMC",""):
        raise ValueError("PMCID identity mismatch")
    doi=ids.get("doi","").lower().strip()
    title=text_of(root.find(".//front/article-meta/title-group/article-title"))
    record={"pmcid":pmcid,"doi":doi, "title":title,
            "url":f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
            "license":license_classification(root),
            "status":"BLOCKED","candidates":[],"review_gaps":[]}
    if not doi or not title:
        record["status"]="BLOCKED_MISSING_SOURCE_IDENTITY"
        return record
    if record["license"]["status"]!="CC_BY_OR_CC0_CONFIRMED":
        record["status"]="BLOCKED_LICENSE_REVIEW_REQUIRED"
        record["review_gaps"].append("Article licensed terms not approved for public commercial-intent text mining")
        return record
    design=design_from_title(title)
    record["design"]=design
    paragraphs=list(results_paragraphs(root,pmcid))
    record["results_paragraph_count"]=len(paragraphs)
    if not paragraphs:
        record["status"]="BLOCKED_NO_RESULTS_PARAGRAPHS"
        return record
    for paragraph in paragraphs:
        source=dict(paragraph,pmcid=pmcid)
        # Individual sentences prevent pairing an HR from one endpoint with
        # a confidence interval from another sentence or study subgroup.
        for sent in SENTENCE.split(paragraph["text"]):
            finding=analyze_sentence(sent,paragraph["section"],source,design)
            if finding:
                record["candidates"].append(finding)
    record["accepted_candidate_count"]=sum(
        x["status"]=="SOURCE_EFFECT_CANDIDATE_REVIEW_REQUIRED" for x in record["candidates"])
    record["abstained_candidate_count"]=len(record["candidates"])-record["accepted_candidate_count"]
    record["status"]="EFFECT_CANDIDATES_REVIEW_REQUIRED"
    record["review_gaps"]=[
        "No treatment-arm attribution, denominator or data-cutoff verification",
        "Tables, charts, supplementary files and clinical implications not validated",
        "A candidate is NOT evidence that the endpoint was primary or conclusive",
        "Multiple published analyses of one trial must be grouped by trial identifier",
    ]
    return record


def render(records, seconds):
    out=[
        "# Clinical Outcome Effect Candidates — Independent Articles",
        "",
        "**Research prototype, NOT clinical evidence validation or a treatment recommendation.**",
        "Only results-section HR/OR estimates with an explicit 90%, 95%, or 99% CI are considered.",
        "All candidates require a specialist to confirm outcome, comparison, analysis date and denominators.",
        "The tool never calculates a treatment benefit or converts HR into increased survival.",
        "",
        "| Article | Access | Candidate HR/OR with CI | Abstained |",
        "|---|---|---:|---:|",
    ]
    for r in records:
        out.append(
            f"| [{r['pmcid']}]({r['url']}) | {r['status']} | "
            f"{r.get('accepted_candidate_count',0)} | {r.get('abstained_candidate_count',0)} |")
    for r in records:
        out += ["",f"## {r['title'] or r['pmcid']}","",
                f"**Source:** {r['url']}",f"**DOI:** {r['doi']}",
                f"**License:** {r['license']['status']}",
                f"**Design triage:** {r.get('design','NOT ASSESSED')}",""]
        if r["status"].startswith("BLOCKED"):
            out += ["**No full-text numeric extraction performed because access/identity gate failed.**",""]
        for c in r["candidates"]:
            s=f"{c['status']} — {c['endpoint']}"
            if "point" in c:
                s+=f" — {c['measure']} {c['point']:g}; {c['ci_level']}% CI {c['ci_lower']:g}–{c['ci_upper']:g}"
            out += [f"- **{s}**",
                    f"  - Location: {c['section']} / {c['source_id_kind']}: {c['source_id']}",
                    f"  - Link: {c['source_url']}",
                    f"  - Context (short, not validated): {c['excerpt']}",""]
        out += ["**Unresolved:** " + "; ".join(r["review_gaps"]),""]
    out += ["## Mandatory release conditions","",
            "- [ ] Check original full-text Results and every relevant table/figure.",
            "- [ ] Verify treatment arms, endpoint, comparator, CI level, cutoff and population.",
            "- [ ] Distinguish adjusted observational associations from randomized treatment effects.",
            "- [ ] Group reports sharing a trial registry ID and prevent double-counting.",
            "- [ ] Independently assess RoB 2 for specific randomized outcomes.",
            "- [ ] Confirm quality, citations, missing results and licensing with reviewer.",
            f"","**Automated processing time:** {seconds:.3f} s (excludes human review)."]
    return "\n".join(out)+"\n"


def run(pmcids, target):
    start=time.perf_counter()
    records=[]
    for pmcid in pmcids:
        if not re.fullmatch(r"PMC\d{5,10}",pmcid):
            raise ValueError("Invalid PMCID identifier")
        try:
            rec=extract_article(fetch(f"{BASE}/{pmcid}/fullTextXML"),pmcid)
        except (OSError,ET.ParseError,ValueError,TimeoutError) as exc:
            rec={"pmcid":pmcid,"doi":"","title":"","url":f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
                 "license":{"status":"UNKNOWN"},"status":"BLOCKED_FETCH_PARSE_OR_IDENTITY",
                 "candidates":[],"review_gaps":[type(exc).__name__]}
        records.append(rec)
        print("EFFECT_STUDY",pmcid,rec["status"],
              "ACCEPTED",rec.get("accepted_candidate_count",0),
              "ABSTAINED",rec.get("abstained_candidate_count",0))
    elapsed=time.perf_counter()-start
    dest=Path(target);dest.mkdir(parents=True,exist_ok=True)
    payload={"generated_from":"Europe PMC OA JATS","automated_seconds":round(elapsed,3),
             "science_validated":False,"records":records}
    (dest/"clinical_effect_candidates.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    (dest/"clinical_effect_candidates.md").write_text(render(records,elapsed),encoding="utf-8")
    print("CLINICAL_EFFECT_SECONDS",round(elapsed,3))
    return records


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pmcids",nargs="+",required=True)
    p.add_argument("--out",default="medical-affairs-agents/output/clinical_effects")
    args=p.parse_args()
    run(args.pmcids,args.out)

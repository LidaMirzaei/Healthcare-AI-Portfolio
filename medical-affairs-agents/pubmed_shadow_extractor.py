"""Gold-blind original PubMed ABSTRACT clinical effect candidate extractor.

This is independent of all manually curated seed/holdout labels: only PubMed
IDs are inputs. No label file is imported or accessed. Returned public
bibliographic abstracts are parsed in memory, NEVER copied into generated
artifacts. Claim provenance is publication/section plus internal offsets,
NOT verified original fulltext/tables, treatment arms or clinical inference.
"""
import argparse
import json
import re
import time
from pathlib import Path

from adc_reference_dataset import fetch_pmids_batch, fetch_pmid, norm
from pubmed_xml_results import fetch_results_batch

# Values are NEVER drawn from evaluation/gold files.
RATIO=re.compile(
    r"\b(?P<measure>(?:(?:stratified|adjusted|estimated)\s+)?"
    r"(?:hazard|odds)\s+ratio|HR|OR)\b"
    r"(?:\s*[\(\[]\s*(?:HR|OR)\s*[\)\]])?"
    r"(?:\s+for\s+[A-Za-z][A-Za-z\s\-/]{0,72}?)?"
    r"\s*[,;:=]?\s*"
    r"(?P<point>\d+(?:\.\d{1,5})?)\b",re.I
)
INTERVAL=re.compile(
    r"\b(?P<level>90(?:\.\d{1,2})?|95(?:\.\d{1,2})?|99(?:\.\d{1,2})?)"
    r"\s*%\s*(?:(?:confidence\s+interval)(?:\s*[\(\[]\s*CI\s*[\)\]])?|\bCI\b)"
    r"\s*[\(\[\s,:;]*"
    r"(?P<low>\d+(?:\.\d+)?)\s*(?:to|[-,])\s*"
    r"(?P<high>\d+(?:\.\d+)?)",
    re.I,
)
ENDPOINTS={
    "PFS":re.compile(r"\b(?:PFS|progression[\s-]?free\s+survival)\b",re.I),
    "OS":re.compile(r"\b(?:OS|overall\s+survival)\b",re.I),
    "EFS":re.compile(r"\b(?:EFS|event[\s-]?free\s+survival)\b",re.I),
    "iDFS":re.compile(r"\b(?:iDFS|invasive[\s-]?disease[\s-]?free\s+survival)\b",re.I),
    "ORR":re.compile(r"\b(?:ORR|objective\s+response\s+rate)\b",re.I),
}
OBSERVED_RESULTS=re.compile(r"(?<![A-Za-z])(?:RESULTS?|FINDINGS)\s*:",re.I)
RESULTS_END=re.compile(r"(?<![A-Za-z])(?:CONCLUSIONS?|DISCUSSION|INTERPRETATION)\s*:",re.I)


def get_results_only(raw):
    """Only extract statistical effects from explicit Results/FINDINGS section.

    A paper without recognizable structured abstract headings abstains.
    Prefix citations from Background can never contaminate the extraction.
    """
    text=norm(raw)
    # Europe PMC may return HTML <h4>Results:</h4> or <h4>Results</h4>;
    # norm() removes tags but retains heading text.
    start=OBSERVED_RESULTS.search(text)
    if not start:
        # Allow standalone "RESULTS" heading with no colon when followed
        # by a capitalized sentence; still an explicitly identified section.
        alternate=re.search(r"\bRESULTS\b\s+(?=[A-Z][a-z]{2,})",text)
        if not alternate:
            return "", "ABSTAIN_NO_EXPLICIT_RESULTS_SECTION"
        start=alternate
    body=text[start.end():]
    end=RESULTS_END.search(body)
    if end:
        body=body[:end.start()]
    return body.strip(),"ABSTRACT_RESULTS_ONLY"


def contextual_endpoint(results, ratio_start):
    """Closest explicit endpoint before ratio; do not infer from a drug name."""
    prefix=results[max(0,ratio_start-480):ratio_start]
    matches=[]
    for label,rx in ENDPOINTS.items():
        matches.extend((m.end(),label,m.start()) for m in rx.finditer(prefix))
    if not matches:
        return "ENDPOINT_NOT_ESTABLISHED"
    matches.sort()
    best=matches[-1]
    # If two different endpoints are adjacent (PFS and OS in same phrase)
    # do not arbitrarily assign an effect to the last one.
    if len(matches)>1 and matches[-2][1]!=best[1] and (best[2]-matches[-2][0])<20:
        # "PFS and OS" is genuinely ambiguous. But "PFS HR 0.70 and
        # OS HR 0.50" carries two separate effect statistics and the
        # second endpoint is explicit; do not abstain on this case.
        between=prefix[matches[-2][0]:best[2]]
        if not re.search(r"\b(?:HR|OR|hazard\s+ratio|odds\s+ratio)\b",between,re.I):
            return "AMBIGUOUS_MULTIPLE_ENDPOINTS"
    return best[1]


def ratio_effects(results):
    """Parse independent HR/OR expressions and locally attached CIs."""
    ratios=list(RATIO.finditer(results))
    cis=list(INTERVAL.finditer(results))
    accepted, abstained=[],[]
    for i,ratio in enumerate(ratios):
        end=ratios[i+1].start() if i+1<len(ratios) else len(results)
        intervals=[ci for ci in cis if ratio.end()<=ci.start()<=ratio.end()+130
                   and ci.end()<=end]
        label=contextual_endpoint(results,ratio.start())
        base={
            "endpoint":label,
            "measure":"OR" if "odds" in ratio.group("measure").lower()
                      or ratio.group("measure").strip().upper()=="OR" else "HR",
            "source_tier":"ORIGINAL_PUBMED_ABSTRACT_RESULTS",
            "source_offset":ratio.start(),
            "source_offset_is_url_anchor":False,
            "review_status":"UNVERIFIED_SOURCE_CANDIDATE",
            "treatment_arms_verified":False,
            "population_subgroup_verified":False,
            "analysis_cutoff_verified":False,
            "statistical_significance_verified":False,
            "clinical_claim_approved":False,
        }
        if len(intervals)!=1:
            following=[ci.start()-ratio.end() for ci in cis if ci.start()>=ratio.end()]
            abstained.append(dict(
                base,status="ABSTAIN_NO_UNIQUE_ATTACHED_CI",
                observed_effect_number=float(ratio.group("point")),
                parsed_CI_count_in_results=len(cis),
                local_CI_count=len(intervals),
                next_parsed_CI_distance=min(following) if following else None))
            continue
        if label.startswith(("ENDPOINT_","AMBIGUOUS")):
            abstained.append(dict(base,status="ABSTAIN_ENDPOINT_UNCERTAIN"))
            continue
        ci=intervals[0]
        value=float(ratio.group("point"))
        lo,hi=float(ci.group("low")),float(ci.group("high"))
        if not (0<lo<=value<=hi and hi<100):
            abstained.append(dict(base,status="ABSTAIN_INVALID_CI"))
            continue
        accepted.append(dict(
            base, status="SOURCE_NUMERIC_TUPLE_CANDIDATE_REVIEW_REQUIRED",
            estimate=value,ci_level=float(ci.group("level")),
            ci_lower=lo,ci_upper=hi))
    return accepted,abstained


def risk_language(results, abstract):
    """Report textual risk warning ONLY; no statistical hypothesis inference."""
    joined=results+" "+norm(abstract)[-650:]
    warnings=[]
    if re.search(r"(?:did not meet|not reach|failed to meet).{0,100}?(?:OS|overall survival|significance)",
                 joined,re.I):
        warnings.append("SOURCE_TEXT_INDICATES_UNMET_OS_OR_SIGNIFICANCE_THRESHOLD_REVIEW")
    if re.search(r"(?:but\s+not\s+in\s+the\s+overall\s+population|"
                 r"did\s+not\s+(?:significantly\s+)?improve.{0,60}?(?:PFS|progression))",
                 joined,re.I):
        warnings.append("SOURCE_TEXT_FLAGS_NONPOSITIVE_OVERALL_PFS_REVIEW")
    return warnings


def interpret_original_record(pmid, record, structured=None):
    if str(record.get("id",""))!=str(pmid) or record.get("source")!="MED":
        raise ValueError("Original PubMed record identity mismatch")
    doi=str(record.get("doi") or "").lower().strip()
    if not doi or not re.match(r"^10\.\d{4,9}/",doi):
        raise ValueError("Missing original article DOI")
    if structured and structured.get("status")=="ORIGINAL_PUBMED_XML_RESULTS_TAGGED" and structured.get("verified_original_pmid") is True:
        results=structured["results"]
        status="ORIGINAL_PUBMED_XML_RESULTS_TAGGED"
    else:
        results,status=get_results_only(record.get("abstractText",""))
    allowed=[]
    abstained=[]
    if results:
        allowed,abstained=ratio_effects(results)
    base={
        "pmid":str(pmid),"doi":doi,"title":str(record.get("title") or "")[:220],
        "original_source_url":f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "source_type":"original_pubmed_abstract_metadata",
        "source_status":status,
        "abstract_extracted_full_text":False,
        "raw_abstract_saved":False,
        "clinical_approval_count":0,
        "candidates":allowed,
        "abstentions":abstained,
        "safety_fully_extracted":False,
    }
    base["risk_language_review_flags"]=risk_language(results,record.get("abstractText","")) if results else []
    return base


def collect(pmids):
    if len(pmids)!=len(set(pmids)):
        raise ValueError("Duplicate PMID would inflate source counts")
    begin=time.perf_counter()
    try:
        by_id=fetch_pmids_batch(pmids)
    except (OSError,ValueError,TimeoutError):
        by_id={}
    # Retrieve original NCBI-tagged Results separately, with no label/benchmark
    # access and no full-text article request. Unstructured abstracts abstain.
    try:
        structured=fetch_results_batch(pmids)
    except (OSError,ValueError,TimeoutError):
        structured={}
    fetched=0
    docs=[]
    for pmid in pmids:
        try:
            rec=by_id.get(pmid)
            if rec is None:
                rec=fetch_pmid(pmid)
            fetched+=1
            docs.append(interpret_original_record(pmid,rec,structured.get(pmid)))
        except (OSError,ValueError,TimeoutError) as exc:
            docs.append({
                "pmid":pmid,"source_status":"BLOCKED_ORIGINAL_PUBMED_MISSING",
                "error_type":type(exc).__name__,
                "candidates":[],"abstentions":[],
                "clinical_approval_count":0})
    return {
        "schema":"pubmed-unseen-shadow-predictions-v1",
        "run_role":"SINGLE_USE_SHADOW_GENERALIZATION",
        "clinical_gold_evaluated":False,
        "verified_medical_claim_count":0,
        "pmids":pmids,
        "requested":len(pmids),"resolved":fetched,
        "source_sections_resolved_by_original_xml":sum(x.get("source_status")=="ORIGINAL_PUBMED_XML_RESULTS_TAGGED" for x in docs),
        "seconds":round(time.perf_counter()-begin,3),
        "articles":docs,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pmids",nargs="+",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    if any(not re.fullmatch(r"\d{7,9}",v) for v in args.pmids):
        raise ValueError("Invalid requested PMID")
    results=collect(args.pmids)
    dest=Path(args.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SHADOW_SOURCE_RESOLVED",results["resolved"],"/",results["requested"])
    print("SHADOW_NUMERIC_CANDIDATES",sum(len(a["candidates"]) for a in results["articles"]))
    print("SHADOW_ABSTENTIONS",sum(len(a["abstentions"]) for a in results["articles"]))
    for article in results["articles"]:
        for a in article.get("abstentions",[]):
            if a.get("status")=="ABSTAIN_NO_UNIQUE_ATTACHED_CI":
                print("SHADOW_ABSTAIN_DIAGNOSTIC",article["pmid"],
                      a.get("observed_effect_number"),
                      "RESULTS_CI_COUNT",a.get("parsed_CI_count_in_results"),
                      "NEAREST_CI_DISTANCE",a.get("next_parsed_CI_distance"))

    print("SHADOW_SOURCE_SECONDS",results["seconds"])
    if results["resolved"]!=results["requested"]:
        raise RuntimeError("At least one original PubMed source is missing; shadow outcome assessment is incomplete")

if __name__=="__main__":
    main()

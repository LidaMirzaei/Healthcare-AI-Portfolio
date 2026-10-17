"""PubMed-only source audit and structured *provisional* ADC research reference packet.

This tool does NOT download restricted article full text, does NOT call an LLM,
and does NOT claim medical or expert-validated gold-standard labels. It checks
whether hand-curated facts can be *located* in original PubMed abstracts.
Numeric co-occurrence cannot prove correct arm/endpoint attribution.
"""
import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from abstract_statistic_verifier import verify_local_result
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DEFAULT_SEED=ROOT/"benchmarks"/"ADC_REFERENCE_CANDIDATES_V1.json"
BASE="https://www.ebi.ac.uk/europepmc/webservices/rest/search"
NCT=re.compile(r"^NCT\d{8}$")
PMID=re.compile(r"^\d{7,9}$")
SAFE_KEYS={"PFS","OS","DFS","iDFS","ORR","EFS","pCR","BCSS"}
BIOMARKER_GROUPS={
    "HR_positive_HER2_negative","triple_negative","HER2_positive",
    "HER2_low","HR_positive_HER2_low_or_ultralow","HR_negative_HER2_low",
}

def norm(text):
    """Normalize clinical numeric typography without altering its values."""
    t=html.unescape(re.sub(r"<[^>]*>", " ", str(text or "")))
    t=t.replace("\u00b7",".").replace("\u2219",".").replace("\u2022",".")
    t=t.replace("\u2212","-").replace("\u2013","-").replace("\u2014","-")
    return " ".join(t.split())

def has_exact_number(text, value):
    target=format(float(value),".10g")
    return bool(re.search(r"(?<![\d.])"+re.escape(target)+r"(?![\d.])",norm(text)))

def check_reference_schema(root):
    studies=root.get("studies")
    if root.get("status")!="PRELIMINARY_NOT_INDEPENDENTLY_ADJUDICATED":
        raise ValueError("This public development registry cannot claim a gold-standard label")
    if not isinstance(studies,list) or len(studies)<10:
        raise ValueError("Expected ten or more individual original study families")
    if root.get("holdout_status")!="DEVELOPMENT_ONLY_NOT_FROZEN_HELDOUT":
        raise ValueError("Reference development items must not be mislabeled unseen holdout")
    seen_pmids=set()
    seen_trials=set()
    for rec in studies:
        if not PMID.fullmatch(rec.get("pmid","")) or not NCT.fullmatch(rec.get("nct","")):
            raise ValueError("Invalid primary PMID or NCT: "+str(rec.get("key")))
        if rec["pmid"] in seen_pmids or rec["nct"] in seen_trials:
            raise ValueError("Source PMID or trial-family duplicated: "+rec["nct"])
        seen_pmids.add(rec["pmid"])
        seen_trials.add(rec["nct"])
        for field in ("key","year","drug","design","subtype","setting","line",
                      "intervention","endpoint","measure","outcome_role","note","expected_doi"):
            if not rec.get(field):
                raise ValueError(f"Missing field {field} in {rec.get('key')}")
        if rec["subtype"] not in BIOMARKER_GROUPS or rec["endpoint"] not in SAFE_KEYS:
            raise ValueError("Unexpected subtype/endpoint value")
        if rec["measure"] not in ("HR","OR","percent"):
            raise ValueError("Invalid measure type")
        if rec["measure"]=="percent" and rec["comparator"] is not None:
            raise ValueError("Single-arm response percent must not be used as a comparative trial estimate")
        if rec["design"]=="single_arm_phase_1b_2" and rec["comparator"] is not None:
            raise ValueError("Single-arm data cannot have a randomized comparator")
        if rec["design"].startswith("randomized") and not rec["comparator"]:
            raise ValueError("Randomized comparison missing intervention/control")
        estimate=rec["estimate"]
        if isinstance(estimate,bool) or not isinstance(estimate,(float,int)) or estimate<=0:
            raise ValueError("Invalid outcome estimate")
        confidence=rec["ci_level"]
        if confidence is not None:
            if not (0<rec["ci_lower"]<=estimate<=rec["ci_upper"]<=100):
                raise ValueError("Confidence interval and point estimate inconsistent")
            if not isinstance(confidence,(float,int)) or not 0<confidence<100:
                raise ValueError("Invalid CI confidence level")
        elif rec["ci_lower"] is not None or rec["ci_upper"] is not None:
            raise ValueError("Missing CI confidence level must not be silently filled in")
    return len(studies)

def fetch_pmid(pmid):
    query=urllib.parse.urlencode({
        "query":f"EXT_ID:{pmid} AND SRC:MED", "format":"json",
        "resultType":"core","pageSize":"3"})
    req=urllib.request.Request(BASE+"?"+query,
        headers={"User-Agent":"PublicOncologyReferenceSourceAudit/1.0"})
    with urllib.request.urlopen(req,timeout=30) as response:
        matches=json.load(response).get("resultList",{}).get("result",[])
    original=[r for r in matches if str(r.get("id"))==pmid]
    if len(original)!=1:
        raise LookupError("Original PubMed record not uniquely resolved")
    return original[0]

def select_batched_originals(payload, required_pmids):
    """Return ONLY unique exact PubMed-origin records from a batch response."""
    required=set(required_pmids)
    if len(required)!=len(required_pmids):
        raise ValueError("Duplicate PMID requested")
    grouped={}
    for item in payload.get("resultList",{}).get("result",[]):
        pmid=str(item.get("id",""))
        if pmid not in required or item.get("source")!="MED":
            continue
        if pmid in grouped:
            raise ValueError("Ambiguous duplicate PubMed source: "+pmid)
        grouped[pmid]=item
    return grouped


def fetch_pmids_batch(pmids):
    """One bounded Europe PMC metadata request for up to 20 original PMIDs.

    Falls back only for missing records, not for ambiguous matches.
    """
    if not pmids or len(pmids)>20 or any(not PMID.fullmatch(p) for p in pmids):
        raise ValueError("Invalid PubMed metadata batch input")
    terms=" OR ".join("EXT_ID:"+p for p in pmids)
    params=urllib.parse.urlencode({
        "query":"("+terms+") AND SRC:MED","format":"json",
        "resultType":"core","pageSize":str(len(pmids)+2)})
    req=urllib.request.Request(BASE+"?"+params,
        headers={"User-Agent":"PublicOncologyReferenceSourceAudit/1.0"})
    with urllib.request.urlopen(req,timeout=30) as response:
        return select_batched_originals(json.load(response),pmids)


def parse_ncbi_trial_registrations(xml_bytes):
    """Extract only trial IDs from structured original PubMed databank entries."""
    root=ET.fromstring(xml_bytes)
    result=set()
    for bank in root.findall(".//DataBankList/DataBank"):
        name=norm(bank.findtext("DataBankName")).lower()
        if name not in ("clinicaltrials.gov","clinical trials.gov"):
            continue
        for node in bank.findall(".//AccessionNumber"):
            candidate=norm(node.text).upper()
            if NCT.fullmatch(candidate):
                result.add(candidate)
    # Some PubMed records encode trial IDs as specialized identifiers.
    for node in root.findall(".//ArticleIdList/ArticleId"):
        if "clinicaltrials" in (node.get("IdType","")).lower():
            candidate=norm(node.text).upper()
            if NCT.fullmatch(candidate):
                result.add(candidate)
    return sorted(result)


def fetch_ncbi_trial_registrations(pmid):
    """Free NCBI PubMed XML databank metadata, not publisher article full text."""
    params=urllib.parse.urlencode({"db":"pubmed","id":pmid,"retmode":"xml"})
    endpoint="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"+params
    req=urllib.request.Request(endpoint,
        headers={"User-Agent":"PublicOncologyResearchTrialIdentityAudit/1.0"})
    with urllib.request.urlopen(req,timeout=30) as response:
        return parse_ncbi_trial_registrations(response.read())


def evaluate_source(seed, record):
    """Source identity + number-token audit, NOT adjudicated result extraction."""
    abstract=norm(record.get("abstractText"))
    title=norm(record.get("title"))
    observed_pmid=str(record.get("id",""))
    pmid_ok=observed_pmid==seed["pmid"] and record.get("source","MED")=="MED"
    doi_ok=norm(record.get("doi")).lower().strip()==seed["expected_doi"].lower().strip()
    nct_ok=bool(re.search(r"(?<!\w)"+re.escape(seed["nct"])+r"(?!\w)",abstract,re.I))
    local=verify_local_result(abstract,measure=seed["measure"],
         estimate=seed["estimate"],ci_level=seed["ci_level"],
         ci_lower=seed["ci_lower"],ci_upper=seed["ci_upper"],
         endpoint=seed["endpoint"])
    # Regulatory and statistical outputs need manual verification even if all
    # their numbers occur nearby, because association to comparator isn't proven.
    found=has_exact_number(abstract,seed["estimate"])
    ci_parts={
        "ci_level":seed["ci_level"] is None or
                    bool(re.search(r"(?<!\d)"+re.escape(format(float(seed["ci_level"]),".10g"))+
                                   r"\s*%",abstract)),
        "ci_lower":seed["ci_lower"] is None or has_exact_number(abstract,seed["ci_lower"]),
        "ci_upper":seed["ci_upper"] is None or has_exact_number(abstract,seed["ci_upper"]),
    }
    ci_ok=all(ci_parts.values())
    # Some abstracts omit trial IDs or particular CI bounds; mark incomplete.
    # Never convert incomplete metadata to a fabricated positive finding.
    # A local effect/CI match and nearby endpoint are necessary to advance.
    # Scattered abstract number tokens never produce a positive verification.
    local_candidate=local["endpoint_bound_candidate_count"]>0
    status=("ABSTRACT_LOCAL_STATISTIC_CANDIDATE_REVIEW_REQUIRED"
            if pmid_ok and doi_ok and nct_ok and local_candidate
            else "ABSTRACT_SOURCE_CHECK_INCOMPLETE_REVIEW_REQUIRED")
    # Records deliberately exclude copied abstracts/source full text.
    return {
        "key":seed["key"],"pmid":seed["pmid"],"nct_candidate":seed["nct"],
        "trial_group_unique_in_seed":True,
        "source_url":f"https://pubmed.ncbi.nlm.nih.gov/{seed['pmid']}/",
        "source_title":title,"source_doi":record.get("doi"),
        "source_published":record.get("firstPublicationDate") or record.get("firstIndexDate"),
        "verification_status":status,
        "checks":{"pubmed_identity":pmid_ok,"source_doi_identity":doi_ok,
                  "nct_found_in_abstract":nct_ok,
                  "local_statistic_endpoint_candidate":local_candidate,
                  "estimate_number_token_found":found,**ci_parts},
        "statistic_context_check":local,
        "endpoint_label_provisional":seed["endpoint"],
        "effect_measure_provisional":seed["measure"],
        "effect_estimate_provisional":seed["estimate"],
        "ci_level_provisional":seed["ci_level"],
        "ci_lower_provisional":seed["ci_lower"],
        "ci_upper_provisional":seed["ci_upper"],
        "study_design_provisional":seed["design"],
        "patient_population_provisional":seed["subtype"],
        "line_of_therapy_provisional":seed["line"],
        "comparator_provisional":seed["comparator"],
        "cohort_context":seed["setting"],
        "source_contains_original_full_text":False,
        "human_adjudicated":False,
        "not_for_treatment_comparison":True,
    }

def build_report(seed, findings, seconds):
    rows={x["pmid"]:x for x in findings}
    out=[
      "# Breast Cancer ADC — Provisional Reference Packet",
      "",
      "**NOT a gold standard, formal systematic review, medical recommendation, or verified head-to-head comparison.**",
      "This is a structured research-development dataset from original PubMed article metadata and abstracts.",
      "Its purpose is to establish what must be extracted, review the source, and organize patient populations.",
      "A numeric token in an abstract is *not* proof that the estimate belongs to the proposed endpoint/arm.",
      "",
      "## Two research questions",
      "1. What efficacy, safety, and endpoint-specific numerical findings are reported for ADCs in distinct breast-cancer populations?",
      "2. Which methods, populations, eligibility, control arms, follow-up and statistical limitations prevent invalid comparisons?",
      "",
      "## 10 independent parent study families (one selected source per family)",
      "",
      "| Trial family | Subtype and setting | Intervention vs comparator | Proposed endpoint | Reported candidate | Source verification |",
      "|---|---|---|---|---|---|",
    ]
    for study in seed["studies"]:
        v=rows.get(study["pmid"],{})
        ci=study["ci_level"]
        ci_phrase=f"{ci:g}% CI {study['ci_lower']:g}–{study['ci_upper']:g}" if ci is not None else "CI not in selected abstract label"
        estimate=f"{study['measure']} {study['estimate']:g}; {ci_phrase}"
        intervention=(study["intervention"]+" vs "+study["comparator"]) if study["comparator"] else (
            study["intervention"]+" — single-arm, NO control")
        out.append(
            f"| [{study['key']}](https://pubmed.ncbi.nlm.nih.gov/{study['pmid']}/) "
            f"| {study['subtype']}, {study['setting']} "
            f"| {intervention} "
            f"| {study['endpoint']} ({study['outcome_role']}) "
            f"| {estimate} "
            f"| {v.get('verification_status','UNVERIFIED')} |")
    out += ["", "## Interpretability and comparability warnings",
       "- **Different populations:** HR+/HER2-, HER2-low/ultralow, HER2-positive and TNBC must not be treated as equivalent.",
       "- **Different lines:** first-line metastatic, heavily pretreated metastatic and post-neoadjuvant early disease are not exchangeable.",
       "- **Different endpoints:** PFS, OS, invasive DFS and ORR have different meanings and are not comparable effect sizes.",
       "- **Distinct control arms:** investigator-choice chemotherapy, T-DM1, THP, and no comparator are fundamentally different experimental designs.",
       "- **Endpoint hierarchy:** a secondary OS result must not be counted as a second independent randomized trial.",
       "- **BEGONIA arm 6 is single-arm:** its ORR does not establish benefit versus another treatment; its prespecified response objective was not met.",
       "- **DESTINY-Breast04:** the selected HR refers to the HR-positive HER2-low subgroup, not the entire population; the chosen abstract lacks CI bounds.",
       "- **DESTINY-Breast05:** the source lists an erratum requiring review and studies early disease rather than metastatic survival.",
       "- **TROPION-Breast02:** the PFS CI level is reported as 99%, not 95%; OS uses a different, unusual level (95.01%). FDA separately identifies NCT05374512, while this PubMed registry metadata check remains unresolved.",
       "- **TROPION-Breast01:** final OS must be checked in the later paper from the same NCT, not inferred from the earlier PFS result.",
       "",
       "## Requirements to move from candidates to a legitimate gold standard",
       "1. Two independent qualified reviewers read the original Results, Methods, harms, tables and any correction/appendix.",
       "2. Each endpoint/arm/population/analysis-cutoff/CI and source section receives an adjudicated label.",
       "3. Record the outcome-specific bias analysis (RoB 2 where applicable), not a generic article-wide quality score.",
       "4. Every missing, non-comparable or uncertain result must remain flagged instead of being invented.",
       "5. Keep these 10 development families out of all future **unseen independent holdout** evaluations.",
       "",
       f"**PubMed source-metadata audit runtime:** {seconds:.3f} seconds (excluding manual source review and annotation).",
       "**Licensing:** no original article full text or copied abstracts are exported in this packet.",
       "**No paid API or enterprise data used.**",
    ]
    return "\n".join(out)+"\n"

def run(seed_path=DEFAULT_SEED, dest="medical-affairs-agents/output/adc_reference_packet"):
    seed=json.loads(Path(seed_path).read_text(encoding="utf-8"))
    check_reference_schema(seed)
    start=time.perf_counter()
    results=[]
    pmids=[study["pmid"] for study in seed["studies"]]
    try:
        originals=fetch_pmids_batch(pmids)
        print("REFERENCE_BULK_RECORDS",len(originals),"/",len(pmids))
    except (LookupError,OSError,ValueError,TimeoutError) as exc:
        originals={}
        print("REFERENCE_BULK_UNAVAILABLE",type(exc).__name__)
    fallback_count=0
    for study in seed["studies"]:
        try:
            record=originals.get(study["pmid"])
            if record is None:
                fallback_count+=1
                record=fetch_pmid(study["pmid"])
            result=evaluate_source(study,record)
            if not result["checks"]["nct_found_in_abstract"]:
                # Original PubMed's ClinicalTrials.gov databank registration
                # is a separate evidence tier from an abstract citation.
                try:
                    registrations=fetch_ncbi_trial_registrations(study["pmid"])
                    verified=study["nct"] in registrations
                    result["checks"]["nct_found_in_pubmed_databank"]=verified
                    result["registration_verification_source"]=(
                        "NCBI_PUBMED_CLINICALTRIALS_DATABANK" if verified else
                        "PENDING_SOURCE_REVIEW")
                    if verified and all(result["checks"][k] for k in (
                        "pubmed_identity","source_doi_identity",
                        "local_statistic_endpoint_candidate")):
                        result["verification_status"]=(
                            "ABSTRACT_LOCAL_STATISTIC_AND_NCBI_REGISTRY_REVIEW_REQUIRED")
                except (OSError,ET.ParseError,ValueError,TimeoutError):
                    result["checks"]["nct_found_in_pubmed_databank"]=False
                    result["registration_verification_source"]="NCBI_METADATA_FETCH_FAILED"
        except (LookupError,OSError,ValueError,TimeoutError) as exc:
            result={"key":study["key"],"pmid":study["pmid"],
                    "verification_status":"SOURCE_FETCH_OR_RESOLUTION_FAILED",
                    "error_type":type(exc).__name__,
                    "source_url":f"https://pubmed.ncbi.nlm.nih.gov/{study['pmid']}/",
                    "human_adjudicated":False}
        results.append(result)
        print("REFERENCE_SOURCE",study["key"],result["verification_status"])
    elapsed=time.perf_counter()-start
    payload={
      "generated_utc":datetime.now(timezone.utc).isoformat(),
      "reference_status":"PROVISIONAL_NOT_EXPERT_ADJUDICATED",
      "study_families":len(seed["studies"]),
      "source_checks_completed":sum("checks" in r for r in results),
      "bulk_original_records_returned":len(originals),
      "individual_fallback_requests":fallback_count,
      "strict_local_effect_checks_passed":sum(
          r["verification_status"]=="ABSTRACT_LOCAL_STATISTIC_CANDIDATE_REVIEW_REQUIRED"
          for r in results),
      "strict_local_effect_plus_pubmed_registry_checks_passed":sum(
          r["verification_status"]=="ABSTRACT_LOCAL_STATISTIC_AND_NCBI_REGISTRY_REVIEW_REQUIRED"
          for r in results),
      "statistically_validated_outcome_count":0,
      "expert_adjudicated_outcome_count":0,
      "scientific_accuracy_unmeasured":True,
      "source_audit_elapsed_seconds":round(elapsed,3),
      "studies":results,
    }
    destination=Path(dest)
    destination.mkdir(parents=True,exist_ok=True)
    (destination/"adc_source_audit.json").write_text(
        json.dumps(payload,indent=2),encoding="utf-8")
    (destination/"adc_reference_packet.md").write_text(
        build_report(seed,results,elapsed),encoding="utf-8")
    print("REFERENCE_UNIQUE_FAMILIES",len(seed["studies"]))
    print("REFERENCE_PUBMED_CHECKS",payload["source_checks_completed"])
    print("REFERENCE_LOCAL_EFFECT_CANDIDATES",payload["strict_local_effect_checks_passed"])
    print("REFERENCE_LOCAL_EFFECT_PLUS_NCBI_REGISTRY",payload["strict_local_effect_plus_pubmed_registry_checks_passed"])
    print("REFERENCE_METADATA_FALLBACK_REQUESTS",fallback_count)
    print("REFERENCE_RUNTIME_SECONDS",round(elapsed,3))
    return payload

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",type=Path,default=DEFAULT_SEED)
    parser.add_argument("--out",default="medical-affairs-agents/output/adc_reference_packet")
    args=parser.parse_args()
    run(args.seed,args.out)

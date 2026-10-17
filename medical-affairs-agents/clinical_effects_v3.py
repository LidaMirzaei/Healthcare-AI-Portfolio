"""Version 3: clause-local HR/OR + CI extraction with source quality tiers.

Designed from generic CONSORT 2025 reporting principles and synthetic examples,
not trained on any frozen holdout labels. The separate V3 frozen benchmark must
not be edited after evaluation. NOT automated clinical interpretation.
"""
import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from clinical_effects import (results_paragraphs, compact, EFFECT, INTERVAL,
                              ENDPOINTS, SENTENCE)
from independent_holdout import (extract_source_identity, license_classification,
                                 text_of, abstract_and_design_text,
                                 infer_study_registration)
from fulltext_evidence import BASE, fetch

ENDPOINTS_V3={
    **ENDPOINTS,
    "BCSS": re.compile(r"\b(?:breast[\s-]?cancer[\s-]?specific survival|BCSS)\b",re.I)
}

def article_kind(title, abstract):
    t=title.lower()
    if re.search(r"systematic review|network meta.analysis|meta.analysis|scoping review",t):
        return "SECONDARY_REVIEW_NOT_NEW_TRIAL"
    if re.search(r"study protocol|protocol for|trial protocol",t):
        return "PROTOCOL_NOT_OBSERVED_RESULTS"
    if re.search(r"cohort|observational|screening participation|population.based screening",t):
        return "OBSERVATIONAL_ASSOCIATION"
    if re.search(r"randomi[sz]ed|randomi[sz]ation",t):
        return "POSSIBLY_RANDOMIZED_TRIAL_NEEDS_METHODS_REVIEW"
    if re.search(r"\bcohort\b",abstract.lower()[:1200]):
        return "OBSERVATIONAL_ASSOCIATION"
    return "DESIGN_NOT_INFERRED"


def abstract_results(root, pmcid):
    """Abstract can contribute candidate signals, but never masquerade as full text."""
    items=[]
    for abstract in root.findall(".//front/article-meta/abstract"):
        sections=abstract.findall(".//sec")
        if sections:
            paragraphs=[]
            for section in sections:
                heading=text_of(section.find("title"))
                if not re.search(r"^results?|^findings?",heading.lower()):
                    continue
                paragraphs.extend(section.findall(".//p"))
        else:
            paragraphs=abstract.findall(".//p")
            if not paragraphs and text_of(abstract):
                paragraphs=[abstract]
        for p in paragraphs:
            content=compact(text_of(p))
            if len(content)>=35:
                items.append({
                    "source_id":"ABSTRACT_NO_DIRECT_PARAGRAPH_ANCHOR",
                    "source_id_kind":"ABSTRACT_SECTION_ONLY",
                    "section":"Abstract / Results" if sections else "Abstract / Unstructured",
                    "url":f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
                    "text":content,
                })
    return items


def section_endpoint(sentence, heading, effect_start):
    # Consider only what precedes the estimate (rather than interpreting a
    # follow-up effect as belonging to a previous endpoint). Keep ambiguity.
    relevant=sentence[max(0,effect_start-240):effect_start]
    matches=[]
    for key,pattern in ENDPOINTS_V3.items():
        for m in pattern.finditer(relevant):
            matches.append((m.start(),m.end(),key))
    if matches:
        matches.sort(key=lambda x:x[0])
        latest=matches[-1]
        if len({m[2] for m in matches[-2:]})>1 and latest[0]-matches[-2][1]<25:
            return "AMBIGUOUS_ENDPOINT_NEAR_ESTIMATE"
        return latest[2]
    heading_hits=[k for k,p in ENDPOINTS_V3.items() if p.search(heading)]
    return heading_hits[0] if len(heading_hits)==1 else "ENDPOINT_NOT_CONFIRMED"


def mine_sentence(sentence, source, source_level, article_design):
    """Bind every estimate to its OWN following CI, without crossing next effect."""
    sentence=compact(sentence)
    effects=list(EFFECT.finditer(sentence))
    intervals=list(INTERVAL.finditer(sentence))
    output=[]
    for i,effect in enumerate(effects):
        end=effects[i+1].start() if i+1<len(effects) else len(sentence)
        # Require CI to follow estimate locally, before the next HR/OR.
        candidates=[ci for ci in intervals if ci.start()>=effect.end()
                    and ci.start()-effect.end()<=90 and ci.end()<=end]
        endpoint=section_endpoint(sentence,source["section"],effect.start())
        rec={"pmcid":source["pmcid"],
             "source_level":source_level,
             "section":source["section"],
             "source_url":source["url"],
             "source_id":source["source_id"],
             "source_id_kind":source["source_id_kind"],
             "endpoint":endpoint,
             "study_design_flag":article_design,
             "review_status":"SPECIALIST_REVIEW_REQUIRED",
             "arm_assignment_verified":False,
             "adjustment_covariate_verified":False,
             "population_verified":False,
             "data_cutoff_verified":False,
             "multiple_effects_in_sentence":len(effects)>1,
             "snippet":sentence[max(0,effect.start()-90):min(len(sentence),effect.end()+65)][:175]}
        if len(candidates)!=1:
            rec["status"]="ABSTAIN_CI_UNAVAILABLE_OR_MULTIPLE"
            output.append(rec)
            continue
        ci=candidates[0]
        value=float(effect.group("point"));lower=float(ci.group("lower"));upper=float(ci.group("upper"))
        if not (0<lower<=value<=upper<=100):
            rec["status"]="ABSTAIN_INVALID_CI"
            output.append(rec)
            continue
        if endpoint.startswith(("AMBIGUOUS","ENDPOINT_")):
            rec["status"]="ABSTAIN_ENDPOINT_NOT_SUPPORTED"
            output.append(rec)
            continue
        name=effect.group("measure").lower()
        measure="HR" if name=="hr" or "hazard" in name else "OR"
        rec.update({"status":"NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED",
                    "measure":measure,"estimate":value,"ci_level":int(ci.group("level")),
                    "ci_lower":lower,"ci_upper":upper,
                    "causal_interpretation":("OBSERVATIONAL_ASSOCIATION_ONLY"
                                             if article_design=="OBSERVATIONAL_ASSOCIATION"
                                             else "NO_CAUSAL_CLAIM_AUTOMATICALLY_GENERATED")})
        output.append(rec)
    return output


def extract_v3(xml_bytes, pmcid):
    root=ET.fromstring(xml_bytes)
    ids=extract_source_identity(root)
    title=text_of(root.find(".//front/article-meta/title-group/article-title"))
    doi=ids.get("doi","").lower().strip()
    pmc_id=ids.get("pmc","").replace("PMC","")
    result={"pmcid":pmcid,"doi":doi,"title":title,
            "url":f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
            "license":license_classification(root),
            "status":"BLOCKED","candidates":[]}
    if not doi or not title or (pmc_id and pmc_id!=pmcid.replace("PMC","")):
        result["status"]="BLOCKED_IDENTITY"
        return result
    # Metadata-only title assessment is safe even if full-text analysis is
    # subsequently blocked by document rights. It does NOT certify study type.
    result["title_type_hint"]=article_kind(title,"")
    if result["license"]["status"]!="CC_BY_OR_CC0_CONFIRMED":
        result["status"]="BLOCKED_LICENSE_REVIEW_REQUIRED"
        return result
    abstracts=abstract_results(root,pmcid)
    abstext=" ".join(a["text"] for a in abstracts)
    kind=article_kind(title,abstext)
    result["article_kind"]=kind
    # Registration is an unverified grouping candidate, NOT proof that a
    # registration mentioned in the abstract belongs to this publication.
    _, abstract_for_registration, method_for_registration = abstract_and_design_text(root)
    registration, registration_location = infer_study_registration(
        abstract_for_registration, method_for_registration)
    result["registration_candidate"]=registration
    result["registration_candidate_source"]=registration_location
    if kind=="PROTOCOL_NOT_OBSERVED_RESULTS":
        result["status"]="BLOCKED_PROTOCOL_NOT_OBSERVED_RESULTS"
        return result
    if kind=="SECONDARY_REVIEW_NOT_NEW_TRIAL":
        result["status"]="BLOCKED_SECONDARY_SYNTHESIS_AS_PRIMARY_STUDY"
        return result
    fulltext=list(results_paragraphs(root,pmcid))
    result["results_paragraph_count"]=len(fulltext)
    if not fulltext:
        result["status"]="BLOCKED_NO_OBSERVED_FULLTEXT_RESULTS"
        return result
    # Full Results take priority over abstract; abstract matches are labeled
    # explicitly and never called a full-text verification.
    all_candidates=[]
    for level,parts in (("FULLTEXT_RESULTS",fulltext),("ABSTRACT_RESULTS_ONLY",abstracts)):
        for p in parts:
            source=dict(p,pmcid=pmcid)
            for sentence in SENTENCE.split(p["text"]):
                all_candidates.extend(mine_sentence(sentence,source,level,kind))
    # When exact same numeric tuple appears in body and abstract, retain
    # full-text as the primary pointer; separate distinct estimates.
    unique={}
    for c in all_candidates:
        if c["status"]=="NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED":
            key=(c["endpoint"],c["measure"],c["estimate"],c["ci_level"],
                 c["ci_lower"],c["ci_upper"])
        else:
            key=("ABSTAIN",c["source_id"],c.get("snippet",""))
        if key not in unique:
            unique[key]=c
    result["candidates"]=list(unique.values())
    result["unresolved_critical_fields"]=[
        "population_and_line_of_therapy", "treatment_and_control_arms",
        "subgroup_or_analysis_population", "primary_or_secondary_endpoint",
        "data_cutoff_and_follow_up", "source_table_or_figure_reconciliation",
        "effect_direction_and_clinical_significance", "outcome_specific_risk_of_bias",
    ]
    result["scientific_claim_approved"]=False
    result["matched_effect_count"]=sum(
        1 for c in result["candidates"]
        if c["status"]=="NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED")
    result["abstained_effect_count"]=len(result["candidates"])-result["matched_effect_count"]
    result["status"]="EFFECT_CANDIDATES_UNVERIFIED"
    return result


def run(pmcids,target):
    start=time.perf_counter()
    items=[]
    for pmcid in pmcids:
        if not re.fullmatch(r"PMC\d{5,10}",pmcid):
            raise ValueError("Invalid PMCID")
        try:
            r=extract_v3(fetch(BASE+"/"+pmcid+"/fullTextXML"),pmcid)
        except (OSError,ET.ParseError,ValueError,TimeoutError) as e:
            r={"pmcid":pmcid,"status":"BLOCKED_SOURCE_FAILURE",
               "doi":"","title":"","candidates":[],"error_type":type(e).__name__}
        items.append(r)
        print("V3_STUDY",pmcid,r["status"],
              "CANDIDATES",r.get("matched_effect_count",0),
              "ABSTAINED",r.get("abstained_effect_count",0))
    elapsed=round(time.perf_counter()-start,3)
    dest=Path(target);dest.mkdir(parents=True,exist_ok=True)
    data={"articles":items,"elapsed_seconds":elapsed,
          "scientific_validation":False,
          "fulltext_includes_tables_figures_supplements":False}
    (dest/"v3_effect_candidates.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    md=["# Clinical Effect Source Candidates v3","",
        "**Not a medical recommendation or validated efficacy comparison.**",
        "Each number must be checked against source, denominator, treatment allocation, endpoint and analysis cutoff.",
        "| Source | Status | Numeric candidates | Abstentions |",
        "|---|---|---:|---:|"]
    for r in items:
        md.append(f"| [{r['pmcid']}](https://pmc.ncbi.nlm.nih.gov/articles/{r['pmcid']}/) "
                  f"| {r['status']} | {r.get('matched_effect_count',0)} | {r.get('abstained_effect_count',0)} |")
    for r in items:
        md.extend(["",f"## {r.get('title') or r['pmcid']}","",
                   "**Article type:** "+r.get("article_kind","Not processed"),""])
        for c in r.get("candidates",[]):
            s=c["status"]+" — "+c["endpoint"]
            if "estimate" in c:
                s+=f" — {c['measure']} {c['estimate']} ({c['ci_level']}% CI {c['ci_lower']}–{c['ci_upper']})"
            md.extend(["- **"+s+"**",
                       f"  - Source level: {c['source_level']}; {c['section']}",
                       f"  - [Article and source location]({c['source_url']})",
                       f"  - Context: {c['snippet']}",""])
    md.extend(["","## Not yet verified","",
         "- No result is automatically categorized as primary, adjusted, or causal.",
         "- Full-text vs abstract matches are reported as separate evidence grades.",
         "- Combinations of trial subgroups, missing denominators and supplementary tables remain unresolved.",
         "- Releasing clinical recommendations requires specialist source-level review.",
         f"- Source processing time: {elapsed}s (human review excluded)."])
    (dest/"v3_effect_candidates.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("V3_EFFECT_RUNTIME_SECONDS",elapsed)
    return items


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--pmcids",nargs="+",required=True)
    parser.add_argument("--out",default="medical-affairs-agents/output/v3_effects")
    args=parser.parse_args()
    run(args.pmcids,args.out)

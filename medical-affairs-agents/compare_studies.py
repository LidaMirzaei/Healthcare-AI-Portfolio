"""Evidence matrix based on source-attributed candidate sentences.

This is deterministic information retrieval, NOT independent scientific reasoning.
"""
import argparse
import re
from pathlib import Path
from fulltext_evidence import fetch, search, parse_xml, authorized_xml_for_public_demo

FIELDS = {
    "study_design": re.compile(r"\b(?:randomized|randomised|prospective|retrospective|phase [I,V]+|cohort|case.control)\b", re.I),
    "sample_size": re.compile(r"\b(?:[0-9][0-9,]* patients|[0-9][0-9,]* participants|enrolled [0-9][0-9,]*)\b",re.I),
    "endpoint": re.compile(r"\b(?:primary endpoint|primary outcome|overall survival|progression.free survival|disease.free survival)\b",re.I),
    "effect_estimate": re.compile(r"\b(?:hazard ratio|odds ratio|risk ratio|95% CI|95% confidence interval)\b",re.I),
    "safety": re.compile(r"\b(?:adverse events?|toxicit(?:y|ies)|interstitial lung disease|serious adverse)\b",re.I),
    "limitations": re.compile(r"\b(?:limitations?|confounding|bias|generalizab|small sample)\b",re.I),
}

def candidate_matrix(document, max_candidates=2):
    output={"pmcid":document["pmcid"],"title":document["title"],"url":document["url"],"candidates":{}}
    for field, pattern in FIELDS.items():
        candidates=[]
        for section,paragraphs in document["sections"].items():
            for paragraph in paragraphs:
                # Splits may mishandle abbreviations. Excerpts must be verified at source.
                sentences=re.split(r"(?<=[.!?])\s+(?=[A-Z])",paragraph["text"])
                for sentence in sentences:
                    if pattern.search(sentence):
                        candidates.append({"paragraph_id":paragraph["id"],"section":paragraph["heading"],
                                           "quote":sentence[:280],"field":field})
                    if len(candidates)>=max_candidates: break
                if len(candidates)>=max_candidates: break
            if len(candidates)>=max_candidates: break
        output["candidates"][field]=candidates
    return output

def render_matrix(entries):
    keys=list(FIELDS)
    lines=["# Cross-Study Candidate Evidence Matrix","",
       "**Warning:** This is automated keyword retrieval from full-text articles, not validated study interpretation.",
       "A blank cell means **not detected**, NOT absent. Extracted sentences may be truncated.",
       "Each item includes a source and paragraph ID for independent checking.","",
       "| Study | "+" | ".join(k.replace("_"," ").title() for k in keys)+" |",
       "|---|"+"|".join(["---"]*len(keys))+"|"]
    for e in entries:
        cells=[]
        for key in keys:
            hits=e["candidates"][key]
            cells.append(f"{len(hits)} candidate(s)" if hits else "Not detected")
        lines.append("| ["+e["pmcid"]+"]("+e["url"]+") | "+" | ".join(cells)+" |")
    for e in entries:
        lines+=["","## "+e["title"],"","**Source:** "+e["url"],""]
        for key in keys:
            lines+=["### "+key.replace("_"," ").title(),""]
            if not e["candidates"][key]:
                lines+=["Not detected; manual review required.",""]
            else:
                for hit in e["candidates"][key]:
                    lines+=["- **"+hit["paragraph_id"]+" / "+hit["section"]+"**: "+hit["quote"],""]
    lines+=["","## Executive review questions (NOT automated judgments)","",
        "1. Do populations, comparators, endpoints and follow-up periods match?",
        "2. Which findings are supported by denominators and uncertainty intervals?",
        "3. What harms, missing data, biases or limits were reported?",
        "4. Is any study directly relevant to the intended clinical question?",
        "5. Did the article include corrections, supplementary material or a data-access restriction?",
        "",
        "No comparative efficacy, recommendation, or strength-of-evidence ranking is generated automatically."]
    return "\n".join(lines)+"\n"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--query",default='"breast cancer" AND HER2')
    p.add_argument("--limit",type=int,default=3)
    p.add_argument("--out",default="medical-affairs-agents/output/cross_study_candidates.md")
    args=p.parse_args()
    documents=[]
    for item in search(args.query,args.limit):
        pmcid=item.get("pmcid")
        if not pmcid: continue
        try:
            article_xml=fetch("https://www.ebi.ac.uk/europepmc/webservices/rest/"+pmcid+"/fullTextXML")
            if not authorized_xml_for_public_demo(article_xml):
                print("Skipped restricted/unknown-license full text",pmcid)
                continue
            documents.append(candidate_matrix(parse_xml(article_xml,pmcid)))
        except Exception as exc:
            print("Skipped",pmcid,type(exc).__name__,str(exc))
    if not documents:
        raise RuntimeError("No full-text studies retrieved")
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(render_matrix(documents),encoding="utf-8")
    print("Created candidate evidence matrix for",len(documents),"studies")

if __name__=="__main__":
    main()

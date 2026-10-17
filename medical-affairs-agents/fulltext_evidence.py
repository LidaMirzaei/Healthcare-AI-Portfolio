"""Open access full text: section-level evidence extraction, no LLM or clinical conclusions."""
import argparse, json, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
CATEGORIES = {
    "methods": ("method","material","patient","study design","procedure","statistical"),
    "results": ("result","outcome","finding","efficacy"),
    "safety": ("safety","adverse","toxicity","tolerability"),
    "limitations": ("limitation",),
    "discussion": ("discussion","conclusion","interpretation")
}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"OncologyFullTextEvidence/0.1"})
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read()

def search(query, limit=3):
    if not 1 <= limit <= 10:
        raise ValueError("limit must be 1..10")
    q = f'({query}) AND OPEN_ACCESS:y AND FIRST_PDATE:[2024-01-01 TO 2026-12-31]'
    params = urllib.parse.urlencode({"query":q,"format":"json","pageSize":str(limit),"sort":"FIRST_PDATE_D desc"})
    return json.loads(fetch(BASE+"/search?"+params)).get("resultList",{}).get("result",[])

def plain(node):
    return " ".join(" ".join(node.itertext()).split()) if node is not None else ""

def section_type(title, inherited="other"):
    low=title.lower()
    for category, terms in CATEGORIES.items():
        if any(s in low for s in terms):
            return category
    return inherited

def parse_xml(xml, pmcid):
    root=ET.fromstring(xml)
    title=plain(root.find(".//front/article-meta/title-group/article-title")) or pmcid
    license_text=plain(root.find(".//license")) or "Not identified"
    output={"pmcid":pmcid,"title":title,"url":"https://europepmc.org/articles/"+pmcid,
            "license":license_text[:400], "sections":{k:[] for k in [*CATEGORIES,"other"]}}
    counter=0
    def walk(section, category, heading):
        nonlocal counter
        for node in section.findall("p"):
            value=plain(node)
            if len(value)>=35:
                counter+=1
                output["sections"][category].append({"id":f"{pmcid}-p{counter}","heading":heading,"text":value})
        for sub in section.findall("sec"):
            heading2=plain(sub.find("title")) or "Untitled"
            walk(sub,section_type(heading2,category),heading+" > "+heading2)
    body=root.find(".//body")
    if body is not None:
        walk(body,"other","Body")
    return output

def evidence(doc, max_per_section=3):
    return {"pmcid":doc["pmcid"],"title":doc["title"],"url":doc["url"],
            "license":doc["license"],
            "excerpts":{category:items[:max_per_section] for category,items in doc["sections"].items()}}

def markdown(docs):
    lines=["# Full-Text Oncology Evidence Packet","",
           "**Automated extracts, not AI interpretations or medical advice.**",
           "Source: Europe PMC open-access fullTextXML; source paragraph IDs refer to the extracted document.",
           "","## Cross-study evidence map","",
           "| Article | Methods | Results | Safety | Limitations |",
           "|---|---:|---:|---:|---:|"]
    for d in docs:
        lines.append("| ["+d["pmcid"]+"]("+d["url"]+") | "+" | ".join(
            str(len(d["excerpts"].get(c,[]))) for c in ["methods","results","safety","limitations"])+" |")
    for d in docs:
        lines+=["", "## "+d["title"],"", "Source: "+d["url"],"","License notice: "+d["license"],""]
        for name in ("methods","results","safety","limitations","discussion"):
            lines+=["### "+name.title(),""]
            paras=d["excerpts"].get(name,[])
            if not paras:
                lines+=["No matching heading found; this does not establish absence of evidence.",""]
            for p in paras:
                lines+=["- **"+p["id"]+" — "+p["heading"]+"**: "+p["text"][:650],""]
    lines+=["## Scientific review required","",
            "- Verify all extracts against their full-text source.",
            "- Compare population, study design, endpoints, follow-up and statistical methods.",
            "- Check adverse events, limitations, conflicts and supplementary materials.",
            "- Do not interpret this extraction as a demonstration of efficacy or study quality.",
            "- Check license terms before sharing or commercial use.","",
            "Figures, supplementary files, and tables are not comprehensively analyzed."]
    return "\n".join(lines)+"\n"

def run(query, limit, target):
    results=[]
    for item in search(query,limit):
        pmcid=item.get("pmcid")
        if not pmcid: continue
        try:
            results.append(evidence(parse_xml(fetch(BASE+"/"+pmcid+"/fullTextXML"),pmcid)))
        except (OSError,ET.ParseError,ValueError) as exc:
            print("Skipped",pmcid,str(exc))
    if not results:
        raise RuntimeError("No open-access full text available; refusing empty success")
    path=Path(target)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(markdown(results),encoding="utf-8")
    print("Extracted full text from",len(results),"articles to",path)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--query",default='"breast cancer" AND HER2')
    parser.add_argument("--limit",type=int,default=3)
    parser.add_argument("--out",default="medical-affairs-agents/output/fulltext_evidence.md")
    args=parser.parse_args()
    run(args.query,args.limit,args.out)

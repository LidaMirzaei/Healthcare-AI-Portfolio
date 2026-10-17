"""Metadata-only rights preflight for public GitHub Actions, fail closed.

Europe PMC public bibliographic metadata is checked BEFORE any workflow step
mines full-text JATS. A journal article being free to READ is not a blanket
commercial text-mining or redistributed-derivatives grant.
No source XML/body is downloaded by this preflight.
"""
import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from pinned_trial_review import PAPERS

ROOT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
DOIS = {
    "PMC11771365":"10.1200/JCO.24.00920",
    "PMC13449377":"10.1016/j.esmoop.2026.108330",
    "PMC13583573":"10.1016/j.esmoop.2026.108538",
}
# Deliberately narrow approval: any novel, missing, NC/ND, or custom licence
# needs specialist/legal approval before automated commercial-intent mining.
APPROVED = {"cc by", "cc by 4.0", "cc by 3.0", "cc-by", "cc-by-4.0", "cc-by-3.0",
            "cc0", "cc0 1.0", "cc0-1.0"}


def authorize_license(value):
    if not isinstance(value, str) or not value.strip():
        return False
    s=" ".join(value.lower().replace("_","-").split())
    if re.search(r"(?:non.?commercial|no.?derivatives|\bnc\b|\bnd\b)", s):
        return False
    return s in APPROVED


def fetch_metadata(pmcid):
    query=urllib.parse.urlencode({
        "query":f"PMCID:{pmcid}",
        "format":"json","resultType":"core","pageSize":"2"})
    req=urllib.request.Request(ROOT+"?"+query,
        headers={"User-Agent":"OncologyRightsPreflight/1.0"})
    with urllib.request.urlopen(req,timeout=30) as res:
        payload=json.load(res)
    matches=payload.get("resultList",{}).get("result",[])
    # PubMed-indexed records are often SRC:MED with a separate PMCID, not
    # SRC:PMC. Resolve by the PMCID field and verify DOI independently.
    matching=[x for x in matches if x.get("pmcid")==pmcid]
    if len(matching)!=1:
        return {"pmcid":pmcid,"rights_status":"BLOCKED_UNVERIFIED_METADATA",
                "license":None,"metadata_match_count":len(matching)}
    item=matching[0]
    observed_doi=(item.get("doi") or "").lower().strip()
    expected_doi=DOIS[pmcid].lower()
    license_value=item.get("license")
    id_matches=observed_doi==expected_doi
    approved=id_matches and authorize_license(license_value)
    return {"pmcid":pmcid,
            "title":item.get("title","")[:180],
            "doi":observed_doi,"doi_identity_ok":id_matches,
            "license":license_value or "UNKNOWN",
            "rights_status":("APPROVED_FOR_PUBLIC_DEMO" if approved else
                             "BLOCKED_REQUIRES_RIGHTS_REVIEW"),
            "article_url":f"https://europepmc.org/articles/{pmcid}"}


def write_status(path, valid):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write("authorized="+("true" if valid else "false")+"\n")


def run(target, github_output=None):
    articles=[]
    for source in PAPERS:
        pmcid=source["pmcid"]
        try:
            item=fetch_metadata(pmcid)
        except (OSError,ValueError,KeyError,TimeoutError):
            item={"pmcid":pmcid,"license":"UNKNOWN",
                  "rights_status":"BLOCKED_METADATA_FETCH_FAILED"}
        articles.append(item)
        print("RIGHTS",pmcid,item["rights_status"],"LICENSE",item.get("license"))
    all_approved=bool(articles) and all(
        a["rights_status"]=="APPROVED_FOR_PUBLIC_DEMO" for a in articles)
    if github_output:
        write_status(github_output,all_approved)
    destination=Path(target)
    destination.mkdir(parents=True,exist_ok=True)
    payload={
        "time_utc":datetime.now(timezone.utc).isoformat(),
        "commercial_intent_public_workflow_fulltext_authorized":all_approved,
        "policy":"Only explicit CC BY or CC0 approved in public demonstration.",
        "not_legal_advice":True,"article_metadata":articles,
    }
    (destination/"PUBLIC_RIGHTS_PRECHECK.json").write_text(
        json.dumps(payload,indent=2),encoding="utf-8")
    lines=["# Rights preflight — Public oncology research workflow","",
        "**This step only used public bibliographic metadata, not article full text.**",
        "**Full-text processing allowed for this public commercial-intent prototype:** "+
        ("YES" if all_approved else "NO — SKIP"),"",
        "| PMCID | DOI identity | License metadata | Processing |",
        "|---|---|---|---|"]
    for a in articles:
        lines.append(f"| [{a['pmcid']}](https://europepmc.org/articles/{a['pmcid']}) "
                    f"| {'Yes' if a.get('doi_identity_ok') else 'Unverified'} "
                    f"| {a.get('license') or 'UNKNOWN'} | {a['rights_status']} |")
    lines+=["",
        "This is an intentionally restrictive automated rights gate, not a determination of legality.",
        "For a company's licensed journal subscription, rights and text-mining permissions must be established",
        "by its authorized library/publisher/contract, followed by processing in approved PRIVATE systems.",
        "Article access status is **NOT** evidence quality; negative licensing results do not imply weak science.",
        "No existing private or paid service was used."]
    (destination/"PUBLIC_RIGHTS_PRECHECK.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("RIGHTS_PREFLIGHT_FULLTEXT_ALLOWED",all_approved)
    return payload


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="medical-affairs-agents/output/pinned_trial")
    p.add_argument("--github-output",default=os.getenv("GITHUB_OUTPUT"))
    args=p.parse_args()
    run(args.out,args.github_output)

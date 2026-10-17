"""Cross-check final OS against the ORIGINAL 2026 paper's PubMed/Europe PMC abstract.

Abstract verification is NOT the same as parsing its entire original full text.
No guesses: unavailable metadata or unmatching values are explicitly blocked.
"""
import argparse
import html
import json
import re
import urllib.parse
from pathlib import Path

from fulltext_evidence import BASE, fetch

PMID="41448362"
EXPECTED_DOI="10.1016/j.annonc.2025.12.017"
PUBMED_URL=f"https://pubmed.ncbi.nlm.nih.gov/{PMID}/"


def cleaned(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def validate_record(record):
    d=(record.get("doi") or "").lower()
    title=cleaned(record.get("title",""))
    abstract=cleaned(record.get("abstractText",""))
    valid_identity=(str(record.get("id",""))==PMID
                    and d==EXPECTED_DOI
                    and "datopotamab deruxtecan" in title.lower()
                    and "overall survival" in title.lower())
    checks={
      "article_identity":valid_identity,
      "OS":bool(re.search(r"\boverall survival\b|\bOS\b", abstract, re.I)),
      "final_os_hr_1_01":bool(re.search(r"\b(?:hazard ratio|HR)\s*[:=,]?\s*1\.01(?!\d)",abstract,re.I)),
      "p_0_9445":bool(re.search(r"\b0\.9445\b",abstract)),
      "no_significant_os":bool(re.search(
           r"(?:no statistically significant|did not reach statistical significance|"
           r"not statistically significant|did not differ significantly|"
           r"no significant difference)",abstract,re.I)),
      "median_os_18_6":bool(re.search(r"(?<!\d)18\.6(?!\d)",abstract)),
      "median_os_18_3":bool(re.search(r"(?<!\d)18\.3(?!\d)",abstract)),
    }
    required=["article_identity","OS","final_os_hr_1_01"]
    status=("ORIGINAL_ARTICLE_ABSTRACT_SUPPORT_REVIEW_REQUIRED"
            if all(checks[k] for k in required)
            else "BLOCKED_ORIGINAL_ABSTRACT_NOT_SUFFICIENT")
    # The medians in a publisher full-text result cannot be certified just
    # because its DOI is valid or its abstract reports HR=1.01.
    return {"status":status,"pmid":PMID,"doi":d,"title":title,
            "source":PUBMED_URL,"original_publisher":
             "https://www.annalsofoncology.org/article/S0923-7534%2825%2906337-9/fulltext",
            "verification_scope":"Published abstract only, not entire article",
            "checks":checks,"abstract_length":len(abstract),
            "cannot_claim_fulltext_verified":True}


def fetch_original_os():
    params=urllib.parse.urlencode({
        "query":f"EXT_ID:{PMID} AND SRC:MED",
        "format":"json","resultType":"core","pageSize":"2"})
    data=json.loads(fetch(BASE+"/search?"+params))
    hits=data.get("resultList",{}).get("result",[])
    match=[x for x in hits if str(x.get("id"))==PMID]
    if len(match)!=1:
        return {"status":"BLOCKED_ORIGINAL_RECORD_NOT_UNIQUELY_FOUND",
                "source":PUBMED_URL,"count":len(match)}
    return validate_record(match[0])


def run(dest):
    out=Path(dest);out.mkdir(parents=True,exist_ok=True)
    try:
        result=fetch_original_os()
    except (OSError,ValueError,KeyError,TimeoutError) as err:
        result={"status":"BLOCKED_ORIGINAL_ABSTRACT_FETCH_FAILED",
                "source":PUBMED_URL,"error_type":type(err).__name__}
    (out/"final_os_primary_abstract_audit.json").write_text(
        json.dumps(result,indent=2),encoding="utf-8")
    print("ORIGINAL_OS_SOURCE",result["status"])
    print("OS_ABSTRACT_CHECKS",result.get("checks",{}))
    # Provenance checks must not convert lack of text into a positive claim.
    if result["status"] != "ORIGINAL_ARTICLE_ABSTRACT_SUPPORT_REVIEW_REQUIRED":
        print("WARNING: Final OS abstract is not independently source-matched; consult original publisher full text.")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="medical-affairs-agents/output/pinned_trial")
    args=parser.parse_args()
    run(args.out)

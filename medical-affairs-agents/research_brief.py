"""Public-literature oncology briefing prototype. No patient or company data."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DEFAULT_QUERY = '("breast neoplasms"[MeSH Terms] OR "breast cancer"[Title/Abstract]) AND (clinical trial[Publication Type] OR randomized[Title/Abstract] OR systematic review[Publication Type])'


def get_bytes(endpoint: str, params: dict[str, str]) -> bytes:
    params = {**params, "tool": "public_oncology_brief_demo"}
    url = BASE + endpoint + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "PublicOncologyBriefDemo/0.1"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def fetch_pubmed(query: str, max_results: int = 10, since: str = "2024/01/01", until: str | None = None):
    until = until or dt.date.today().strftime("%Y/%m/%d")
    ids = json.loads(get_bytes("esearch.fcgi", {
        "db": "pubmed", "term": query, "mindate": since, "maxdate": until,
        "datetype": "pdat", "retmax": str(max_results), "retmode": "json",
        "sort": "pub date",
    }))["esearchresult"]["idlist"]
    if not ids:
        return []
    return parse_pubmed_xml(get_bytes("efetch.fcgi", {
        "db": "pubmed", "id": ",".join(ids), "retmode": "xml",
    }))


def node_text(node):
    return "".join(node.itertext()).strip() if node is not None else ""


def parse_pubmed_xml(payload: bytes):
    root = ET.fromstring(payload)
    results = []
    for article in root.findall(".//PubmedArticle"):
        pmid = node_text(article.find(".//MedlineCitation/PMID"))
        title = node_text(article.find(".//Article/ArticleTitle"))
        journal = node_text(article.find(".//Article/Journal/Title"))
        abstract_parts = []
        for node in article.findall(".//Article/Abstract/AbstractText"):
            part = node_text(node)
            label = node.attrib.get("Label")
            if part:
                abstract_parts.append((label + ": " if label else "") + part)
        doi = ""
        for aid in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if aid.attrib.get("IdType") == "doi":
                doi = node_text(aid)
                break
        date = (node_text(article.find(".//Article/Journal/JournalIssue/PubDate/Year"))
                or node_text(article.find(".//Article/Journal/JournalIssue/PubDate/MedlineDate"))[:4]
                or "Not provided")
        if pmid and title:
            results.append({"pmid": pmid, "title": title, "journal": journal,
                            "year": date, "doi": doi,
                            "abstract": " ".join(abstract_parts),
                            "url": "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/"})
    return results


def render_markdown(articles, query: str, generated_on: str):
    lines = [
        "# Oncology Public Literature Brief — DEMO",
        "", f"Generated (UTC date): {generated_on}", "",
        "Source: PubMed public metadata. Retrieval does not establish clinical relevance.",
        "", f"Search query: {query}", "",
        "## Retrieved papers", "",
    ]
    if not articles:
        lines.append("No matching articles retrieved.")
    for index, item in enumerate(articles, 1):
        lines.extend([
            f"### {index}. {item['title']}", "",
            f"- **Journal/year:** {item['journal']} ({item['year']})",
            f"- **PMID:** [{item['pmid']}]({item['url']})",
            f"- **DOI:** {item['doi'] or 'Not available'}",
            "- **Evidence extracted:** Abstract only; human scientific review required.",
            f"- **Abstract:** {item['abstract'] or 'No abstract available.'}", "",
        ])
    lines.extend([
        "## Human review checklist", "",
        "- [ ] Confirm relevance to the actual medical question.",
        "- [ ] Verify all findings against the original publication.",
        "- [ ] Check study population, endpoints, limitations, and retractions.",
        "- [ ] Remove duplicates and assess whether any article is promotional.",
        "- [ ] Do not use as medical advice, pharmacovigilance processing, or approved company material.",
        "", "**No LLM is used in this baseline; summaries have not been generated or verified.**",
    ])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Compile public PubMed metadata into a review brief")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--since", default="2024/01/01")
    parser.add_argument("--out", default="medical-affairs-agents/output/public_breast_cancer_brief.md")
    args = parser.parse_args()
    if not 1 <= args.max_results <= 50:
        parser.error("--max-results must be 1..50")
    papers = fetch_pubmed(args.query, args.max_results, args.since)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(papers, args.query, dt.datetime.now(dt.timezone.utc).date().isoformat()), encoding="utf-8")
    print(f"Wrote {len(papers)} public articles to {output}")


if __name__ == "__main__":
    main()

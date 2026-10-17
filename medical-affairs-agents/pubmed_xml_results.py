"""Original NCBI PubMed EFetch structured RESULTS retrieval (metadata only).

Use tagged AbstractText NlmCategory=RESULTS or Label=Results/FINDINGS.
Never guess the Results portion from an unstructured abstract and never
copy the copyrighted abstract into the public JSON/artifacts.
"""
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

URL="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMID_RX=re.compile(r"\d{7,9}$")


def section_text(element):
    return " ".join(" ".join(element.itertext()).split())


def parse_results_xml(xml_bytes,requested_pmids):
    root=ET.fromstring(xml_bytes)
    accepted=set(requested_pmids)
    results={}
    for article in root.findall(".//PubmedArticle"):
        idnode=article.find("./MedlineCitation/PMID")
        pmid=(idnode.text or "").strip() if idnode is not None else ""
        if pmid not in accepted:
            continue
        if pmid in results:
            raise ValueError("Duplicate NCBI PubMed article ID")
        abstracts=article.findall("./MedlineCitation/Article/Abstract/AbstractText")
        selected=[]
        for node in abstracts:
            label=(node.attrib.get("Label") or node.attrib.get("NlmCategory") or "").strip().lower()
            if label in ("results","result","findings","outcomes"):
                value=section_text(node)
                if value:
                    selected.append(value)
        results[pmid]={
            "status":("ORIGINAL_PUBMED_XML_RESULTS_TAGGED" if selected
                      else "ORIGINAL_PUBMED_ABSTRACT_UNSTRUCTURED_ABSTAIN"),
            "results": " ".join(selected),
            "tagged_results_sections":len(selected),
            "verified_original_pmid":True,
        }
    return results


def fetch_results_batch(pmids):
    if not pmids or len(pmids)>20 or len(set(pmids))!=len(pmids) or any(
            not PMID_RX.fullmatch(v) for v in pmids):
        raise ValueError("Invalid PubMed results request")
    params=urllib.parse.urlencode({
        "db":"pubmed","id":",".join(pmids),"retmode":"xml"})
    request=urllib.request.Request(
        URL+"?"+params,
        headers={"User-Agent":"ResearchOncologyPubMedSourceAudit/2.0"})
    with urllib.request.urlopen(request,timeout=30) as response:
        return parse_results_xml(response.read(),pmids)

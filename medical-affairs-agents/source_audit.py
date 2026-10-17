"""Conservative source-audit layer for reproducible oncology research.

No AI inference; this module measures extraction coverage and produces linked,
verbatim evidence candidates. 'Located' means text found, not clinically validated.
"""
import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from fulltext_evidence import BASE, fetch, parse_xml
from pinned_trial_review import PAPERS

FIELDS = {
    "population": r"\b(?:patients|participants|eligib(?:le|ility)|inclusion|exclusion)\b",
    "trial_design": r"\b(?:randomi[sz]ed|open.label|phase\s*(?:I{1,3}|IV|3)|investigator.s choice)\b",
    "pfs": r"\b(?:progression.free survival|PFS)\b",
    "os": r"\b(?:overall survival|OS)\b",
    "effect_size": r"\b(?:hazard ratio|HR\s*[=:]|\b95%\s*CI)\b",
    "safety": r"\b(?:adverse event|stomatitis|mucositis|interstitial lung disease|toxicit)\b",
    "limitations": r"\b(?:limitation|exploratory|post.hoc|small sample|missing data|confounding)\b",
    "patient_reported": r"\b(?:patient.reported|quality of life|time to deterioration)\b",
}
PATTERNS = {key: re.compile(value, re.I) for key, value in FIELDS.items()}
# A quote is a retrieval candidate, NOT evidence of efficacy, risk or low bias.
MAX_CANDIDATES_PER_FIELD = 5
MAX_QUOTE_CHARS = 950


def normalize(s):
    return " ".join(s.split())


def extract_structure(xml_bytes):
    root = ET.fromstring(xml_bytes)
    body = root.find(".//body")
    if body is None:
        raise ValueError("Full-text XML contains no body")
    article_ids = {}
    for node in root.findall(".//front/article-meta/article-id"):
        kind = node.get("pub-id-type", "other")
        article_ids[kind] = normalize("".join(node.itertext()))
    raw_tables = body.findall(".//table-wrap")
    # Table narratives may be important and are NOT treated as verified numeric evidence.
    tables = []
    for i, table in enumerate(raw_tables, 1):
        caption = table.find("caption")
        tables.append({
            "table_index": i,
            "label": normalize("".join(table.find("label").itertext())) if table.find("label") is not None else "",
            "caption": normalize("".join(caption.itertext()))[:250] if caption is not None else "",
            "has_table_xml": table.find(".//table") is not None,
        })
    refs = root.findall(".//ref-list/ref")
    supplements = root.findall(".//supplementary-material")
    return {
        "article_ids": article_ids,
        "table_count": len(tables),
        "tables": tables,
        "supplement_count": len(supplements),
        "reference_count": len(refs),
        "body_section_count": len(body.findall(".//sec")),
    }


def build_audit(xml_bytes, pmcid):
    doc = parse_xml(xml_bytes, pmcid)
    structure = extract_structure(xml_bytes)
    paragraphs = [p for category in doc["sections"].values() for p in category]
    if not paragraphs:
        raise ValueError("No usable full-text paragraphs: " + pmcid)
    # Store all complete paragraphs for audit; no first-three-per-section truncation.
    hits = {}
    for field, pattern in PATTERNS.items():
        found = []
        for p in paragraphs:
            m = pattern.search(p["text"])
            if m:
                found.append({
                    "paragraph_id": p["id"],
                    "section": p["heading"],
                    "keyword": m.group(0),
                    "quote": p["text"][:MAX_QUOTE_CHARS],
                    "quote_truncated": len(p["text"]) > MAX_QUOTE_CHARS,
                    "source": doc["url"],
                    "review_status": "UNVALIDATED_SOURCE_CANDIDATE",
                })
        hits[field] = {
            "matching_paragraph_count": len(found),
            "examples": found[:MAX_CANDIDATES_PER_FIELD],
            "examples_omitted": max(0, len(found)-MAX_CANDIDATES_PER_FIELD),
        }
    return {
        "pmcid": pmcid, "title": doc["title"], "source": doc["url"],
        "trial_id_expected": "NCT05104866",
        "trial_id_in_fulltext": any("NCT05104866" in p["text"] for p in paragraphs),
        "paragraph_count": len(paragraphs),
        "structure": structure, "fields": hits,
        "flags": [
            "PUBLICATIONS_SHARE_TRIAL__NOT_INDEPENDENT",
            "TABLE_VALUES_NOT_AUTOMATICALLY_VERIFIED" if structure["table_count"] else "NO_XML_TABLES_FOUND_CHECK_PDF",
            "SUPPLEMENTS_NOT_PARSED" if structure["supplement_count"] else "SUPPLEMENT_AVAILABILITY_NOT_VERIFIED",
            "QUALITY_OF_EVIDENCE_NOT_AUTOMATICALLY_GRADED",
        ],
    }


def render(audits, seconds):
    lines = [
        "# Oncology Full-Text Source Audit — TROPION-Breast01",
        "",
        "**Status: source candidates; scientific interpretation NOT automatically verified.**",
        "",
        "Three publications from **one underlying randomized trial** (NCT05104866).",
        "The 2025-issue primary report first appeared online in **2024**.",
        "A separate final-overall-survival paper is essential context and is **not ingested here**.",
        "Do not infer an OS advantage from a PFS result or count three independent trials.",
        "",
        f"Full-text XML retrieval and audit: **{seconds:.3f} seconds** (excludes human review).",
        "",
        "## Coverage & limitations",
        "",
        "| Article | Body paragraphs | XML tables detected | Supplements detected | Trial ID present |",
        "|---|---:|---:|---:|---|",
    ]
    for a in audits:
        s = a["structure"]
        lines.append(
            f"| [{a['pmcid']}]({a['source']}) | {a['paragraph_count']} | {s['table_count']} | "
            f"{s['supplement_count']} | {'Yes' if a['trial_id_in_fulltext'] else 'NOT FOUND — review'} |")
    lines += [
        "",
        "**Limits:** Text matching can miss synonyms, data embedded in figures/tables, appendices and statistical nuance.",
        "No extracted phrase is a verified result. Missing fields mean *not detected*, not evidence absent.",
        "For a commercial or clinical briefing, inspect full licensed source, tables, supplement, corrections and protocol.",
        "",
        "## Cross-publication evidence index (number of matching paragraphs, NOT independent findings)",
        "",
        "| Publication | " + " | ".join(FIELDS) + " |",
        "|---|" + "|".join(["---:"]*len(FIELDS)) + "|",
    ]
    for a in audits:
        lines.append(
            f"| [{a['pmcid']}]({a['source']}) | " +
            " | ".join(str(a["fields"][f]["matching_paragraph_count"]) for f in FIELDS) + " |")
    for a in audits:
        lines += ["", f"## {a['title']}", "", f"**Full text:** {a['source']}",
                  "", f"**Audit flags:** {', '.join(a['flags'])}", ""]
        if a["structure"]["tables"]:
            lines += ["### Tables requiring manual reading"]
            for t in a["structure"]["tables"]:
                lines.append(f"- Table {t['table_index']}: {t['label']} — {t['caption']}")
            lines += [""]
        for field in FIELDS:
            info=a["fields"][field]
            lines += [f"### {field.replace('_', ' ').title()}",
                      f"**{info['matching_paragraph_count']} matching paragraphs; "
                      f"{info['examples_omitted']} example(s) omitted**", ""]
            if not info["examples"]:
                lines += ["Not detected; inspect complete article manually.", ""]
            for hit in info["examples"]:
                lines += [
                    f"- **{hit['paragraph_id']} / {hit['section']} — UNVALIDATED**",
                    f"  Source: {hit['source']}",
                    f"  > {hit['quote']}" + (" … [TRUNCATED]" if hit["quote_truncated"] else ""),
                    "",
                ]
    lines += [
        "## Quality-review gate (not passed automatically)",
        "",
        "- [ ] For every clinical claim: locate exact sentence/table/figure and check full context.",
        "- [ ] Check populations, lines of therapy, cutoffs, comparators and denominators.",
        "- [ ] Compare PFS and final OS without conflating endpoints or analysis dates.",
        "- [ ] Inspect tables and supplements; verify all HRs, confidence intervals and adverse events.",
        "- [ ] Evaluate randomization, allocation concealment, open-label biases, outcome assessor blinding, missing PRO data.",
        "- [ ] Validate adverse-event definitions, grade and attribution; assess ILD signal.",
        "- [ ] Verify subgroup is nested, adequately powered and not an independent replication.",
        "- [ ] Have the result approved by a qualified scientific reviewer before external use.",
        "",
        "This file is an **audit index**, not a finished medical-affairs executive synthesis.",
        "",
    ]
    return "\n".join(lines)


def run(out):
    begin = time.perf_counter()
    audits = []
    for paper in PAPERS:
        pmcid = paper["pmcid"]
        xml_bytes = fetch(f"{BASE}/{pmcid}/fullTextXML")
        audit = build_audit(xml_bytes, pmcid)
        audits.append(audit)
        print("AUDIT", pmcid, "paragraphs", audit["paragraph_count"],
              "tables", audit["structure"]["table_count"])
    elapsed = time.perf_counter()-begin
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out/"full_source_audit.json").write_text(
        json.dumps({"trial_id":"NCT05104866", "independent_trials":1,
                    "articles":audits,"elapsed_seconds":round(elapsed,3),
                    "scientific_accuracy_not_established":True},indent=2), encoding="utf-8")
    (out/"full_source_audit.md").write_text(render(audits,elapsed), encoding="utf-8")
    print("SOURCE_AUDIT_SECONDS:", round(elapsed,3))
    print("AUDIT_COMPLETED:",len(audits))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",default="medical-affairs-agents/output/pinned_trial")
    args = parser.parse_args()
    run(args.out)

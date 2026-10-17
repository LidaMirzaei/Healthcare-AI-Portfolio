"""Cautious structured evidence report from original open-access JATS full text.

Every released quantitative claim must pass an exact text-context gate.
This is a reproducible, deterministic report; NOT autonomous clinical reasoning,
formal RoB 2 grading, or an independently medically validated conclusion.
"""
import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from fulltext_evidence import BASE, fetch, parse_xml
from pinned_trial_review import PAPERS

EXPECTED_DOI = {
    "PMC11771365": "10.1200/JCO.24.00920",
    "PMC13449377": "10.1016/j.esmoop.2026.108330",
    "PMC13583573": "10.1016/j.esmoop.2026.108538",
}
# These are hand-curated candidate claims. The automated gate either locates
# *precise contextual support* in the chosen RESULTS section or suppresses them.
# Each value's comparator and outcome were independently checked against the
# original papers when authoring this registry; future papers need new rules.
CLAIMS = [
    dict(id="pfs_global", pmcid="PMC11771365", endpoint="PFS (BICR)", category="Efficacy",
         value="Median PFS 6.9 months (Dato-DXd) vs 4.9 months (ICC)",
         pattern=r"median\s+PFS.{0,180}?6\.9\s+months.{0,200}?versus\s+4\.9\s+months",
         context=("Dato-DXd","ICC","BICR"), priority=True,
         implication="The trial reported a longer median period without progression or death; this is NOT evidence of longer overall survival."),
    dict(id="pfs_hr", pmcid="PMC11771365", endpoint="PFS (BICR)",category="Efficacy",
         value="PFS HR 0.63 (95% CI 0.52–0.76)",
         pattern=r"HR.{0,8}?0\.63.{0,80}?0\.52\s+to\s+0\.76",
         context=("PFS","ICC"), priority=True,
         implication="The hazard ratio describes relative event rates over follow-up, not an absolute 37% longer lifespan."),
    dict(id="safety_grade3",pmcid="PMC13449377",endpoint="TRAEs (final data cutoff)",category="Safety",
         value="Grade ≥3 treatment-related AEs: 22.2% (Dato-DXd) vs 45.6% (ICC)",
         pattern=r"22\.2%\s+versus\s+45\.6%",
         context=("grade","TRAEs","ICC"),priority=True,
         implication="Fewer high-grade treatment-related events in this comparison do not eliminate oral, ocular or pulmonary risks."),
    dict(id="china_pfs",pmcid="PMC13583573",endpoint="PFS in mainland China (exploratory)",category="Subgroup",
         value="China subgroup median PFS: 8.1 vs 4.2 months",
         pattern=r"median\s+PFS.{0,130}?8\.1\s+months.{0,180}?versus\s+4\.2\s+months",
         context=("Dato-DXd","ICC"),priority=True,
         implication="The China group is a small subset of the SAME trial, not independent confirmation of effect or proof of a geographic interaction."),
    dict(id="china_pfs_hr",pmcid="PMC13583573",endpoint="PFS in mainland China (exploratory)",category="Subgroup",
         value="China subgroup PFS HR 0.54 (95% CI 0.30–0.96; nominal P=0.0329)",
         pattern=r"HR\s+0\.54.{0,45}?0\.30.{0,12}?0\.96",
         context=("PFS","nominal"),priority=False,
         implication="Subgroup P values are nominal and cannot establish treatment-by-region interaction."),
]

OS_SOURCE = {
    "doi":"10.1016/j.annonc.2025.12.017",
    "url":"https://www.annalsofoncology.org/article/S0923-7534%2825%2906337-9/fulltext",
    "pubmed":"https://pubmed.ncbi.nlm.nih.gov/41448362/",
    "value":"Final OS: median 18.6 vs 18.3 months; HR 1.01 (95% CI 0.83–1.22), P=0.9445",
    "status":"EXTERNAL_PRIMARY_PUBLICATION_VERIFIED_MANUALLY_NOT_MACHINE_INGESTED",
    "interpretation":"No statistically significant overall-survival difference was shown at the final analysis.",
}

def normal(s):
    return " ".join(s.split())

def tables_from_xml(xml_data, pmcid):
    """Inspect *all* in-body table rows. Store only limited previews/metadata."""
    root=ET.fromstring(xml_data)
    body=root.find(".//body")
    if body is None:
        raise ValueError("No body in full-text XML")
    tables=[]
    for i,wrap in enumerate(body.findall(".//table-wrap"),1):
        label=normal(" ".join(wrap.find("label").itertext())) if wrap.find("label") is not None else f"Table {i}"
        caption=normal(" ".join(wrap.find("caption").itertext())) if wrap.find("caption") is not None else ""
        table_nodes=wrap.findall(".//table")
        rows=[]; irregular=0
        for table in table_nodes:
            for tr in table.findall(".//tr")+table.findall(".//row"):
                cells=[c for c in tr if c.tag.rsplit("}",1)[-1] in ("th","td","entry")]
                if not cells:
                    continue
                if any(
                    int(cell.attrib.get("rowspan", "1")) > 1
                    or int(cell.attrib.get("colspan", "1")) > 1
                    or (cell.attrib.get("namest") and cell.attrib.get("nameend")
                        and cell.attrib["namest"] != cell.attrib["nameend"])
                    for cell in cells
                ):
                    irregular += 1
                rows.append([normal(" ".join(c.itertext())) for c in cells])
        table_id=wrap.get("id")
        # Do not imply a table is correctly parsed merely because rows exist.
        tables.append({"pmcid":pmcid,"label":label,"caption":caption[:250],
            "table_id":table_id,
            "url":f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" + (f"#{table_id}" if table_id else ""),
            "row_count":len(rows),"irregular_rows":irregular,
            "head_preview":rows[:2], "row_data":rows})
    figures=body.findall(".//fig")
    supplementary=root.findall(".//supplementary-material")
    return {"tables":tables,"figures_count":len(figures),
            "supplement_markers":len(supplementary)}

def verify_article_id(xml_data, pmcid):
    root=ET.fromstring(xml_data)
    ids={}
    for node in root.findall(".//front/article-meta/article-id"):
        ids[node.get("pub-id-type","other").lower()]=normal(" ".join(node.itertext()))
    expected=EXPECTED_DOI[pmcid].lower()
    actual=ids.get("doi","").lower()
    if not actual or actual != expected:
        raise ValueError(f"DOI missing/mismatched for {pmcid}; got {actual!r}, expected {expected!r}")
    pmc=ids.get("pmc","").replace("PMC","")
    if pmc and pmc != pmcid.replace("PMC",""):
        raise ValueError(f"PMCID identity mismatch: {pmc} vs {pmcid}")
    return {"doi":actual, "pmcid":pmcid}

def verify_claim(spec, documents):
    doc=documents.get(spec["pmcid"])
    if doc is None:
        return {"id":spec["id"],"status":"BLOCKED_SOURCE_MISSING","candidates":[]}
    pattern=re.compile(spec["pattern"],re.I|re.S)
    found=[]
    for section, paragraphs in doc["sections"].items():
        # NEVER accept an abstract, introduction, conclusion or discussion
        # repeating a value as proof of the original endpoint result.
        permitted = ("results", "safety") if spec["category"] == "Safety" else ("results",)
        if section not in permitted:
            continue
        for p in paragraphs:
            content=normal(p["text"])
            if pattern.search(content) and all(term.lower() in content.lower() for term in spec["context"]):
                match=pattern.search(content)
                start=max(0,match.start()-90); end=min(len(content),match.end()+90)
                found.append({"section":p["heading"],"paragraph_id":p["id"],
                              "link":doc["url"],
                              "excerpt":content[start:end][:360],
                              "excerpt_is_partial":start>0 or end<len(content)})
    return {"id":spec["id"],
            "status":"SOURCE_CONTEXT_MATCH_REVIEW_REQUIRED" if found else "BLOCKED_CONTEXT_NOT_FOUND",
            "candidates":found[:3],"candidate_total":len(found),
            "source_pmcid":spec["pmcid"],
            "proposed_value":spec["value"],
            "review_status":"PENDING_CLINICAL_REVIEW"}


def reviewer_questions():
    """RoB 2-aligned QUESTIONS, not algorithmic study-wide RoB 2 scores."""
    return [
      ("Randomization process","Check actual sequence generation, concealment, baseline imbalance and protocol; 'randomized' alone is insufficient."),
      ("Deviations from intended interventions","Open-label trial: check changes in care and analysis appropriate to treatment assignment."),
      ("Missing outcome data","Assess censoring and incomplete patient-reported questionnaire data separately for each outcome."),
      ("Measurement of outcome","PFS BICR can mitigate assessment bias; patient-reported symptoms in an open-label trial require independent appraisal."),
      ("Selection of reported result","Compare protocol, prespecified dual primary endpoints, analysis plan, subgroup decisions and final OS report."),
    ]


def brief_markdown(released, blocked, structures, elapsed, os_abstract_audit=None):
    lines=[
      "# TROPION-Breast01 — Source-Gated Evidence Brief (research prototype)",
      "",
      "**NOT an approved medical-affairs document, clinical recommendation, or completed systematic review.**",
      "Automated text-context matches are *candidates requiring scientific review*, not verified medical claims. Paragraph numbers such as PMC11771365-p15 are **internal parser identifiers**, not direct publisher URL anchors; use the linked article, section title and quoted context in the JSON audit to verify.",
      "",
      "## Research questions",
      "1. Among previously treated inoperable/metastatic HR+/HER2-negative breast cancer patients, how does Dato-DXd compare with investigator-choice chemotherapy for efficacy?",
      "2. What do safety, patient experience and the exploratory geographic subgroup add, and what limits the evidence?",
      "",
      "## Scope and comparability",
      "The three ingested papers describe **ONE phase III randomized, open-label clinical trial** (NCT05104866): a global primary analysis, an updated safety/PRO analysis, and a nested China subgroup.",
      "**Do not pool them as three independent samples or conduct a meta-analysis on these publications.**",
      "The study population had progression on endocrine therapy, with further endocrine therapy unsuitable, and **1–2 prior chemotherapy lines** in the advanced setting.",
      "The 2025-issue primary paper was **first published online in 2024**.",
      "",
      "## Executive answer — efficacy and safety",
    ]
    accepted={x["id"]:x for x in released}
    if "pfs_global" in accepted and "pfs_hr" in accepted:
        lines += [
          "**PFS:** Original global data report median progression-free survival of **6.9 vs 4.9 months** (Dato-DXd vs ICC), with **HR 0.63 (95% CI 0.52–0.76)**.",
          "That means a delay in disease progression or death as measured in this study, **not proof of increased overall survival**.",
          "Sources: [global primary analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC11771365/); exact evidence pointers below.",
        ]
    else:
        lines += ["**PFS conclusion BLOCKED:** mandatory source-context checks were not all satisfied."]
    lines += [
      "",
      "**Final overall survival — ESSENTIAL NEGATIVE RESULT:**",
      f"{OS_SOURCE['value']}. {OS_SOURCE['interpretation']}",
      f"**Provenance warning:** {OS_SOURCE['status']}. The original [final OS publication]({OS_SOURCE['url']}) was checked separately, but its publisher full text has NOT been automatically ingested by this run.",
      "Do not treat the primary PFS report's earlier, immature OS analysis as the final outcome.",
      "**Original final-OS abstract cross-check:** " +
        (os_abstract_audit or {}).get("status", "NOT_RUN") +
        ". This verifies at most public abstract metadata; the complete final OS article remains outside XML ingestion.",
      "",
    ]
    if "safety_grade3" in accepted:
        lines += [
          "**Final safety cutoff:** Reported grade ≥3 treatment-related AEs were **22.2% vs 45.6%** (Dato-DXd vs ICC).",
          "This is a *final-cutoff* comparison: the earlier primary report uses different percentages. Never mix those data cutoffs in one row without labels.",
          "Relevant oral mucositis/stomatitis, ocular events and rare potentially serious ILD/pneumonitis require separate clinical review. The aggregate grade ≥3 rate is not a universal ranking of safety.",
        ]
    else:
        lines += ["**Safety summary BLOCKED** until exact final-cutoff paragraph match is located."]
    lines += ["",
      "## Cross-publication evidence matrix",
      "| Publication | Cohort and analysis | Extractable result | Interpretation guard |",
      "|---|---|---|---|",
      "| [Primary global](https://pmc.ncbi.nlm.nih.gov/articles/PMC11771365/) | ITT global randomized (365 vs 367) | PFS by BICR | Earlier OS immature; first online 2024 |",
      "| [Safety and PRO](https://pmc.ncbi.nlm.nih.gov/articles/PMC13449377/) | Treated patients (360 vs 351), same trial | Adverse events and PRO | Final safety cutoff; symptom-specific risks and PRO missingness |",
      "| [China subgroup](https://pmc.ncbi.nlm.nih.gov/articles/PMC13583573/) | Subset (44 vs 39), same trial | Exploratory PFS and toxicity | Nominal P; small group; do not infer interaction |",
      f"| [Final global OS]({OS_SOURCE['url']}) | Original trial, later cutoff | Final OS not significant | Publisher full text not yet machine-ingested |",
      "",
      "## Automatically traced candidate findings (not clinically approved)",
      "| Endpoint | Proposed value | Status | Evidence pointer |",
      "|---|---|---|---|",
    ]
    spec_by_id={s["id"]:s for s in CLAIMS}
    for s in CLAIMS:
        a=next((x for x in released+blocked if x["id"]==s["id"]),
               {"id":s["id"],"status":"BLOCKED_NOT_EVALUATED","candidates":[]})
        link="; ".join(f"[{c['paragraph_id']} — {c['section']}]({c['link']})" for c in a.get("candidates",[])) or "NONE"
        lines.append(f"| {s['endpoint']} | {s['value']} | {a['status']} | {link} |")
    lines += ["","## Benefits, harms and limits — grounded interpretation rules",
       "**Strengths for PFS evidence:** a global phase III randomized comparison and blinded independent central review of PFS lessen some common biases, but do not guarantee an overall low risk of bias.",
       "**Limitations:** open-label design; investigator-selected chemotherapy comparators; staggered analysis cutoffs; incomplete PRO responses over time; region subgroup size and nominal inference.",
       "**Critical distinction:** available final OS did **not** demonstrate a statistically significant survival difference. Subsequent therapy imbalance has been proposed as a possible factor; it is not proof of a hidden OS benefit.",
       "**Generalizability:** conclusions apply to the trial's specified HR+/HER2-negative, previously treated advanced-disease cohort—not HER2-positive early breast cancer.",
       "",
       "## Outcome-specific risk-of-bias review (Cochrane RoB 2-aligned; UNSCORED)",
       "Cochrane RoB 2 evaluates bias for an individual result, not by awarding an automatic credibility score to an entire paper.",
       "The following are reviewer prompts, **not** formal RoB 2 signalling-question judgments.",
    ]
    for name,question in reviewer_questions():
        lines.append(f"- **{name}:** {question}")
    lines += ["","Reference: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-08",
              "",
              "## Article coverage audit: tables and supplementary material",
              "| Article | XML tables seen | Rows parsed | Rows with multi-cell spans | Figures found | Supplement markers |",
              "|---|---:|---:|---:|---:|---:|"]
    for pmcid,x in structures.items():
        lines.append(f"| [{pmcid}](https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/) | "
          f"{len(x['tables'])} | {sum(t['row_count'] for t in x['tables'])} | "
          f"{sum(t['irregular_rows'] for t in x['tables'])} | {x['figures_count']} | {x['supplement_markers']} |")
    lines += [
      "", "**Detected is not interpreted:** table row parsing is structural, and does not resolve multilevel headers, statistical annotations, dose denominators or supplementary files.",
      "",
      "## Blocked evidence and unresolved checks",
    ]
    for a in blocked:
        lines.append(f"- **{a['id']}**: {a['status']}; evidence suppressed pending review.")
    lines += [
      "- Final OS publisher **full-text ingestion and line-by-line claim audit still pending**.",
      "- Table numeric attribution, all figures, appendices, protocol and corrections need independent verification.",
      "- Any outcome-specific RoB 2 grade requires a qualified reviewer and completed signalling questions.",
      "- External distribution requires a human medical/scientific and current-label check; no confidential data were used.",
      "",
      "## Traceability and timing",
      "The source candidate registry records PMCID, paragraph ID, matched context, exact match rule and status in **evidence_release_audit.json**.",
      "Table metadata and a limited row preview are in **table_structure_audit.json** (not a validated dataset).",
      f"Automated retrieval, matching, structural parsing and report creation: **{elapsed:.3f} seconds**.",
      "This elapsed time excludes publication discovery, expert analysis, claim authoring, manual checking and report approval. No time-saving percentage is asserted.",
      "",
      "## Next-stage release gate",
      "- [ ] Compare all clinical numbers against original full text, tables and supplementary data.",
      "- [ ] Verify source DOI and publication version, and separate analysis data cutoffs.",
      "- [ ] Check statistical multiplicity and endpoint-specific risk of bias.",
      "- [ ] Confirm final OS direct-text extraction and causal caveats.",
      "- [ ] Benchmark on a clinician-reviewed gold dataset, reporting per-field precision, recall and citation support.",
      "- [ ] Obtain qualified medical reviewer approval before use in professional contexts.",
      "",
      "Built using public original literature and standard-library Python. No paid API.",
      "",
    ]
    return "\n".join(lines)


def run(output_dir):
    start=time.perf_counter()
    documents={}; structures={}; articles=[]
    for source in PAPERS:
        pmcid=source["pmcid"]
        raw=fetch(f"{BASE}/{pmcid}/fullTextXML")
        ids=verify_article_id(raw,pmcid)
        doc=parse_xml(raw,pmcid)
        if not any(doc["sections"].values()):
            raise ValueError("No usable body paragraphs for "+pmcid)
        documents[pmcid]=doc
        structures[pmcid]=tables_from_xml(raw,pmcid)
        articles.append({**ids,"title":doc["title"],
                         "url":doc["url"],"trial_id":"NCT05104866"})
        print("PAPER_VERIFIED",pmcid,"DOI",ids["doi"],
              "TABLES",len(structures[pmcid]["tables"]))
    audited=[verify_claim(spec,documents) for spec in CLAIMS]
    released=[a for a in audited if a["status"]=="SOURCE_CONTEXT_MATCH_REVIEW_REQUIRED"]
    blocked=[a for a in audited if a["status"]!="SOURCE_CONTEXT_MATCH_REVIEW_REQUIRED"]
    elapsed=time.perf_counter()-start
    dest=Path(output_dir)
    dest.mkdir(parents=True,exist_ok=True)
    manifest={"generated_utc":datetime.now(timezone.utc).isoformat(),
         "source_trial":"NCT05104866","independent_trials":1,"article_count":3,
         "source_articles":articles,
         "claims":audited,"external_final_os":OS_SOURCE,
         "automated_source_context_matched":len(released),
         "automated_claims_not_matched":len(blocked),
         "human_validated_claims":0,"formal_rob2_assessed":False,
         "elapsed_seconds":round(elapsed,3)}
    (dest/"evidence_release_audit.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    # Store table structure with minimal cell previews, not full copyrighted tables.
    safe_tables={}
    for key,s in structures.items():
        safe_tables[key]={k:v for k,v in s.items() if k!="tables"}
        safe_tables[key]["tables"]=[{k:v for k,v in t.items() if k!="row_data"} for t in s["tables"]]
    (dest/"table_structure_audit.json").write_text(json.dumps(safe_tables,indent=2),encoding="utf-8")
    os_audit_path = dest / "final_os_primary_abstract_audit.json"
    os_audit = json.loads(os_audit_path.read_text(encoding="utf-8")) if os_audit_path.exists() else None
    (dest/"source_gated_executive_brief.md").write_text(
        brief_markdown(released,blocked,structures,elapsed,os_audit),encoding="utf-8")
    print("SOURCE_CONTEXT_MATCHED",len(released),"BLOCKED",len(blocked))
    for a in audited: print("CLAIM_CHECK",a["id"],a["status"])
    print("BRIEF_AUTOMATED_SECONDS",round(elapsed,3))
    # Mandatory primary and safety results must not silently disappear.
    mandatory={x["id"] for x in CLAIMS if x["priority"]}
    failed=mandatory-{x["id"] for x in released}
    if failed:
        raise ValueError("Release gate failed: required claims unsupported: "+",".join(sorted(failed)))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="medical-affairs-agents/output/pinned_trial")
    args=parser.parse_args()
    run(args.out)

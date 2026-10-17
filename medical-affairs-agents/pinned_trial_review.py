"""Reproducible pinned-paper pipeline, with explicit run timing and audit metadata.
Uses only public, OA XML; output is extraction, NOT automated scientific appraisal.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from fulltext_evidence import BASE, fetch, parse_xml, evidence, markdown
from compare_studies import candidate_matrix, render_matrix

# Global phase III trial NCT05104866; papers analyze OVERLAPPING participants.
PAPERS = [
    {"pmcid": "PMC11771365", "label": "2025 journal issue, first online 2024 — primary PFS report"},
    {"pmcid": "PMC13449377", "label": "2026 — safety and patient-reported outcomes"},
    {"pmcid": "PMC13583573", "label": "2026 — China prespecified subgroup"},
]


def run(destination: Path) -> None:
    started = time.perf_counter()
    destination.mkdir(parents=True, exist_ok=True)
    docs = []
    timings = []
    for paper in PAPERS:
        start = time.perf_counter()
        url = BASE + "/" + paper["pmcid"] + "/fullTextXML"
        payload = fetch(url)
        document = parse_xml(payload, paper["pmcid"])
        if not sum(len(p) for p in document["sections"].values()):
            raise RuntimeError("Missing parsed full-text body: " + paper["pmcid"])
        docs.append(document)
        timings.append({
            "pmcid": paper["pmcid"],
            "description": paper["label"],
            "paragraphs_parsed": sum(len(p) for p in document["sections"].values()),
            "seconds": round(time.perf_counter() - start, 3),
            "source": document["url"],
        })
        print("FULL TEXT OK:", paper["pmcid"], "paragraphs=", timings[-1]["paragraphs_parsed"])
    extracted = [evidence(doc) for doc in docs]
    candidates = [candidate_matrix(doc) for doc in docs]
    (destination / "pinned_fulltext_evidence.md").write_text(markdown(extracted), encoding="utf-8")
    (destination / "pinned_cross_study_candidates.md").write_text(render_matrix(candidates), encoding="utf-8")
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_trial": "NCT05104866",
        "independent_trial_count": 1,
        "article_count": len(docs),
        "total_elapsed_seconds": round(time.perf_counter() - started, 3),
        "papers": timings,
        "not_completed_by_code": [
            "validated conclusions", "independent study-quality grading",
            "complete table and supplement verification",
            "full-article scientific reasoning",
            "clinical approval or regulatory assessment",
        ],
    }
    (destination / "timing_and_provenance.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print("TOTAL_ELAPSED_SECONDS:", result["total_elapsed_seconds"])
    print("OUTPUT:", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path("medical-affairs-agents/output/pinned_trial"))
    args = parser.parse_args()
    run(args.out)

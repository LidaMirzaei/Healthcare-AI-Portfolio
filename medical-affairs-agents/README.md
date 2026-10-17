# Medical Affairs Agents — Public-Data Prototype

**Independent educational experiment, not affiliated with Daiichi Sankyo.**

## Objective
Test whether a reproducible literature brief can reduce the manual work of finding *public* oncology publications. No corporate account, private material, or patient records are needed.

## Prototype 1 — Oncology Research Brief

- **Inputs:** public PubMed records from 2024 onward by default.
- **Pipeline:** PubMed ESearch -> EFetch -> XML parsing -> evidence-linked Markdown review packet.
- **Outputs:** titles, dates, journal, PMID, DOI, and unmodified abstract text (not an AI-authored summary).
- **Current status:** implementation and offline tests provided, **live PubMed output not yet validated**.
- **Not included:** treatment recommendations, semantic article scoring, LLM factual synthesis, integration into employer systems, or autonomous sending.
- **Privacy:** do not supply sensitive or employer-proprietary queries; never input unpublished abstracts or personal health information.

### Run locally

Python 3.10+; standard library only:

```bash
python -m unittest discover -s medical-affairs-agents -p "test_*.py" -v
python medical-affairs-agents/research_brief.py --max-results 10 --out medical-affairs-agents/output/public_breast_cancer_brief.md
```

The second command needs internet access to NCBI. If requests fail, investigate NCBI limits, access and errors; do not replace missing live results with invented article records.

### Why no LLM yet?
A reliable retrieval + citation + human-review baseline must come first. Once we measure relevance and review time, an optional LLM summarizer can be added and evaluated for factual errors and omissions. The source documents remain the authority.

### Measurement protocol
1. Collect 10 public relevant articles and define relevance criteria.
2. Have a user conduct the same weekly task manually.
3. Compare human time spent, relevance precision, omissions, and citation correctness.
4. Keep a human approval step for every scientific claim.

### Possible next prototypes
- Meeting follow-up tracker on **synthetic** notes.
- ClinicalTrials.gov public trial-change monitor.

Reference: [NCBI E-Utilities](https://www.ncbi.nlm.nih.gov/books/NBK25499/).

**Note:** This repo is public. Do not commit corporate data or secrets.

## Zero-cost operating rule

See [COST_AND_PRIVACY_POLICY.md](COST_AND_PRIVACY_POLICY.md). No paid model API or billing account is required to run this prototype. The public-repository workflow uses GitHub's standard runner and retrieves at most ten public PubMed records per scheduled execution. Any step needing paid credits must stop for explicit owner approval.

The [weekly workflow](../.github/workflows/weekly-oncology-brief.yml) runs each Monday, but the live retrieval step has **not yet been verified as successful**. A successful offline CI run is not proof of successful live PubMed retrieval.

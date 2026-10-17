# Full-text evidence extraction (experimental)

This extends the **abstract-only** PubMed pipeline with retrieval of legally accessible **open-access full-text XML** from Europe PMC. It groups paragraphs from sections such as Methods, Results, Safety, Limitations and Discussion, labels each excerpt with a traceable paragraph ID, and creates a cross-study evidence availability table.

It **does not** yet reason about methodological validity, read every table/figure or write a genuine scientific synthesis. Do not claim that it does. Manual review remains mandatory.

## Run (free, no API key)
```bash
python -m unittest discover -s medical-affairs-agents -p 'test_*.py' -v
python medical-affairs-agents/fulltext_evidence.py --limit 3
```

Outputs: `medical-affairs-agents/output/fulltext_evidence.md`.

## Scientific quality gates before any demo
1. Verify OA license restrictions per article, especially commercial reuse.
2. Validate headings against original full text and check extraction omissions.
3. Add tables, supplementary material and corrections handling.
4. Add a source-cited argument/evidence representation and an evaluation dataset checked by subject-matter experts.
5. Compare studies only when designs and outcomes support comparisons.
6. Never issue treatment recommendations or upload private organizational documents.

Data source: [Europe PMC REST API](https://europepmc.org/RestfulWebService) and [open access terms](https://europepmc.org/downloads/openaccess).

# Independent Clinical Evidence QA: Baseline and Release Criteria
**Date:** 2026-10-17  
**Status:** Engineering research prototype; **not** a medically validated AI scientific analyst.

## Frozen results (unaltered; never call them new unseen tests again)

| Version | Held-out study families | Checks passed | What actually measured | Failing checks |
|---|---:|---:|---|---|
| V1 | 3 | 12/12 | DOI, registry, study design, disease setting only | None in this small metadata check |
| V2 | 4 | **2/4** | 2 numerical endpoint tuple retrievals, one multi-subgroup ambiguity gate, one licensing gate | Two numeric tuples missed: original full Results wording differs from abstract and multi-OR sentence was abstained |
| V3 | 4 | **3/5** | 2 predeclared survival HR+CI tuples, one protocol classification, one review classification, one licensing block | Two items were restricted by uncertain/restrictive XML licence metadata before protocol/review classification |

**Important:** These are *tiny targeted engineering checks*, not clinical-accuracy percentages. V2 was not modified to improve the frozen score after its first evaluation. V3 labels are also frozen. A restrictive gate can cause a false negative, and it must not be quietly counted as a scientific classification success.

**V3 details:** In source [PMC12494613](https://pmc.ncbi.nlm.nih.gov/articles/PMC12494613/) the new generic extractor found both original-Results candidates: unadjusted BCSS HR 0.28 (95% CI 0.17–0.48), and unadjusted OS HR 0.54 (95% CI 0.36–0.79). This is **observational** screening participation evidence, **not** randomized evidence that screening causally produces those hazard ratios. Any comparison is conditional on populations, model adjustment, and potential selection/lead-time biases.

**Licensing:** Source PMC12238040 was conservatively blocked as `BLOCKED_AMBIGUOUS_OR_MULTIPLE_LICENSES` even though the public article landing page describes CC BY; this is a **metadata parsing/authorization gap**, not proof that mining is unlawful. Sources PMC12514518 and PMC12736403 were blocked due their reported restrictive licences. Do not override uncertain XML terms by guessing. Evaluate actual rights through the provider/organization in the future.

## Baseline limitations

- Original `source_gated_brief.py` contains **hand-selected TROPION-Breast01 numbers**, so passing its targeted numerical tests does not demonstrate generalizable clinical outcome extraction.
- `clinical_effects.py` and `clinical_effects_v3.py` are distinct proof-of-concept extractors. V3 improves numeric-pair recall on one new family but is still **deterministic source-candidate extraction**, not evidence synthesis.
- The original final-OS publication is not yet fully parsed; direct PubMed abstract checks cannot stand in for analysis of its full methods, tables, and supplemental data.
- Capturing HR, OR, CI or paragraph citations does not establish correct treatment-arm attribution, endpoint importance, statistical validity, comparability, causal interpretation or risk of bias.
- Full-text availability and licence status are separate from scientific study quality. Commercial or enterprise TDM requires its own content-rights pathway.

## Gold-standard annotation for future clinical accuracy

Use the accompanying `CLINICAL_ANNOTATION_TEMPLATE.csv` as a **blank annotation schema**, not a pre-populated ground truth. For every distinct outcome/result, two medically qualified reviewers should independently record:
- Study-family identifier (e.g. NCT), DOI/PMID/PMCID, version and publication date.
- Source locator at heading/paragraph/table/figure/supplement level.
- Treatment arms, population/subgroup, setting, line of therapy and analysis cutoff.
- Endpoint and whether primary/prespecified/exploratory/post-hoc.
- Measure type (HR/OR/RR/rate difference), point estimate, confidence interval **level and bounds**, denominator and effect direction.
- Statistical interpretation, maturity/censoring and missing data.
- Distinct harms including grade, numerator/denominator, attribution and timing.
- Source license and permitted data-processing environment.
- Reviewer 1, Reviewer 2, disagreement and adjudicated final label.

### Measurement definitions

**Only after independent expert adjudication**, compute per field:
- **Precision** = truly supported extracted claims / all extracted claims.
- **Recall** = truly supported extracted claims / all relevant gold-standard claims.
- **F1** = harmonic mean of precision and recall.
- **Unsupported-claim rate** = claims lacking correct source, endpoint, arms, or statistical context / all output claims.
- **Abstention rate** = candidates withheld due uncertain context / all attempted candidates; abstained gold outcomes count as missed for end-to-end recall.
- **Time benefit** = baseline time for human search + reading + drafting **minus** agent runtime + human verification + corrections + approval. Do not equate script runtime with hours saved.

A partially correct tuple is a **miss** for exact-outcome precision/recall when population, comparator, CI level, or analysis time point is wrong. Report outcome-specific error types separately. Do not pool correlated papers from one NCT across training/evaluation or into meta-analysis as independent trials. Include observational cohorts, negative trial results, secondary analyses, mixed endpoint passages, publication corrections, protocols, and restricted-access scenarios.

### Release gates

1. Frozen train/dev/test split **by study family**, ideally also newer time periods and independent publishers.
2. Document article sample inclusion and permission status before viewing gold answers.
3. Two independent annotators and adjudicated disagreements.
4. Never allow uncited benefits, imaginary OS improvement, wrong comparator, or fabricated safety interpretation.
5. Show source excerpts only where the relevant licence permits; no proprietary text in public GitHub.
6. Specialist approves any medical-affairs-facing conclusions; RoB 2 for randomized studies is **outcome/result-specific**, not one automatic paper grade.
7. Record actual human review time, corrections and unsolved ambiguities.
8. Prefer a new **V4** holdout once future changes are frozen; do not report V2/V3 repeated reruns as new external validation.

## Standards
- [CONSORT 2025 statement](https://www.bmj.com/content/389/bmj-2024-081123) — trial reporting, outcome results, confidence intervals, harms and missingness.
- [CINEX 2026 clinical information extraction reporting guideline](https://pubmed.ncbi.nlm.nih.gov/42570314/) — annotation, provenance, evaluation and external validation.
- [Cochrane RoB 2](https://www.riskofbias.info/welcome/rob-2-0-tool) — risk of bias must be evaluated for a specified randomized trial result.

## Zero-spend, non-corporate-development rule
These are public code/data experiments only. No enterprise system was accessed, no Claude API/payment was activated, no confidential information should be submitted, and no public GitHub workflow may process proprietary licensed company content.

# Clinical Gold Evaluation — Two-Reviewer Protocol

**Research-stage quality evaluation, not clinical approval.**

The production goal is not to predict one impressive aggregate percentage.
Each biomedical statement must be associated with its exact article, outcome,
treatment/comparator, population, analysis cutoff, confidence interval and
source location. A correct HR in the wrong population is **incorrect**.

## Required source files

1. An adjudicated reference JSON array with at least two independent reviewer
   identifiers per entry. Ideally an independently selected dataset with
   30+ annotated clinical outcomes across 10+ different study families,
   including negative OS findings, mixed safety data and observational cohorts.
   These numbers are a minimal engineering threshold, **not a statistical
   sample-size calculation or a guarantee of representativeness**.
2. Output JSON from `clinical_effects_v3.py` or a future extractor, with an
   `articles` array. This is only a set of **unvalidated source candidates**.

**Never copy actual trial full text, confidential company content, patient
information, or a proprietary clinician annotation into the public repo.**
Real annotations/metrics derived from confidential work belong in approved
private storage; here only the blank schema and fabricated examples remain.

## Fully synthetic gold example (NOT real study evidence)

```json
[
  {
    "claim_id": "fictional-1",
    "pmcid": "PMC99990001",
    "study_family_id": "NCT12345678",
    "endpoint": "PFS",
    "measure": "HR",
    "estimate": 0.82,
    "ci_level": 90,
    "ci_lower": 0.68,
    "ci_upper": 0.97,
    "intervention": "fictional drug A",
    "comparator": "fictional drug B",
    "population": "simulated adult group",
    "analysis_cutoff": "2030-01-01",
    "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC99990001/#r1",
    "reviewer_1": "reviewer-A",
    "reviewer_2": "reviewer-B",
    "adjudicated": true,
    "source_checked": true
  }
]
```

**These are fabricated values and URLs for a unit-test example, not a real article.**

## Evaluation command

```bash
python medical-affairs-agents/clinical_gold_evaluator.py \
  --gold path/to/privately_adjudicated_gold.json \
  --predictions path/to/extractor_output.json \
  --train-families NCT05104866 \
  --out path/to/quality_score.json
```

**Do not run a real private gold set in public GitHub Actions**. The
evaluator is intentionally offline (standard library), without API spending.

## Metrics and release policy

- Numeric tuple precision, recall and F1 check **PMCID, endpoint, effect type,
  point estimate and the exact CI level/bounds**.
- A **separate stricter clinical-context metric** additionally requires the
  correct intervention, comparator, population, analysis cutoff and a
  source location that has explicitly been independently reviewed.
- Repeated predictions count as extra false positives; missing outcomes count
  as false negatives; abstained relevant outcomes reduce recall.
- The evaluator stops if the gold set has missing adjudication, only one
  reviewer, duplicate identifiers, invalid confidence intervals or
  study-family overlap with training.
- Passing engineering tests does **not** certify AI clinical accuracy.
- A credible formal assessment needs an expert-adjudicated, blinded,
  representative dataset and outcome-specific review. Publication-level
  leakage across reports of the same NCT is prohibited.
- Only an authorized Medical Affairs/clinical reviewer can approve a
  result for external use.

**Current state:** no private, two-reviewer adjudicated gold set is connected.
Accordingly, precision and recall for the real Agent remain **unmeasured**.
The offline tests use fabricated examples solely to validate scoring behavior.

## Reading

- [CONSORT 2025 statement](https://www.bmj.com/content/389/bmj-2024-081123)
  distinguishes outcome effects, confidence intervals, harms, analysis
  populations and missing data.
- [Cochrane RoB 2](https://www.riskofbias.info/welcome/rob-2-0-tool) evaluates
  a specific trial result; it is not an automatic paper-wide quality score.

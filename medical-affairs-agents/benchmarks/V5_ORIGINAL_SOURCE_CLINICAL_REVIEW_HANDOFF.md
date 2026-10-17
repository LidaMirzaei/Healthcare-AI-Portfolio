# Breast Oncology — Original-Source Independent Review Handoff
**Date:** 17 October 2026
**Status:** assistant-led original-abstract cross-check, **NOT** expert-adjudicated gold, NOT full-text systematic review, NOT company-approved medical assessment.

## Review question

Across four **distinct underlying randomized breast-cancer trial families**, can a source-aware tool identify endpoint-specific effect estimates and CI limits while preserving the population, treatment line, comparator, subgroup and absence of an OS benefit where applicable? Can it abstain without a trustworthy Results section instead of inventing an outcome?

**Design constraint:** three of these sources report advanced TNBC (different treatment lines), while EMBER-3 reports HR+/HER2− disease after endocrine therapy. They **cannot be pooled** as a single treatment-effect experiment, and their drugs are not all ADCs. OptiTROP-Breast01 and ASCENT-03 involve ADCs; CAPItello-290 and EMBER-3 are **non-ADC stress controls** testing endpoint/confounding interpretation.

## Original publication abstract cross-check (provisional)

| Trial / population | Intervention vs comparator | Original abstract outcome | Source / scientific caveat |
|---|---|---|---|
| **OptiTROP-Breast01**, NCT05347134; pretreated metastatic TNBC (n=130 vs 133) | Sacituzumab tirumotecan vs physician choice chemotherapy | **Final BICR PFS:** 6.7 vs 2.5 months; HR **0.32** (95% CI **0.24–0.44**). **Interim OS:** HR **0.53** (95% CI **0.36–0.78**), median OS not reached vs 9.4 months | [Original PMID 40217078](https://pubmed.ncbi.nlm.nih.gov/40217078/). Final PFS and interim OS are **different cutoffs** and not independent trials. Nature Medicine's unstructured abstract does not expose a reliable tagged Results section in the automated source feed; extraction intentionally abstains on both. |
| **CAPItello-290**, NCT03997123; previously untreated metastatic TNBC (n=812 randomized) | Capivasertib + paclitaxel vs placebo + paclitaxel | **Primary OS overall:** HR **0.92** (95% CI 0.78–1.08; P=0.3239). **Primary OS biomarker altered:** HR **1.05** (95% CI 0.77–1.43; P=0.7602). **Key secondary PFS:** overall HR **0.72** (95% CI 0.61–0.84); altered subgroup HR **0.70** (95% CI 0.52–0.95) | [Original PMID 41422862](https://pubmed.ncbi.nlm.nih.gov/41422862/). **Neither primary OS endpoint met the prespecified threshold.** Secondary PFS trends must not be falsely described as a primary OS survival win. OS and PFS have **different analysis cutoffs** (18 March 2024 vs 25 May 2022). |
| **EMBER-3 primary**, NCT04975308; ER+/HER2− advanced disease after endocrine therapy; 874 randomized to three arms | Imlunestrant vs standard endocrine therapy; imlunestrant + abemaciclib vs imlunestrant | **All-patient PFS, imlunestrant vs SOC:** HR **0.87** (95% CI 0.72–1.04; P=0.12). **Combination vs imlunestrant:** PFS HR **0.57** (95% CI 0.44–0.73; P<0.001) | [Original PMID 39660834](https://pubmed.ncbi.nlm.nih.gov/39660834/). **All-patient imlunestrant vs SOC was not statistically significant.** In ESR1-mutant patients the original abstract supports a restricted-mean-survival-time comparison; do not substitute the **0.57 combination HR** for the ESR1-mutant monotherapy comparison. Three randomization arms and different analysis populations must be preserved. |
| **ASCENT-03**, NCT05382299; first-line advanced TNBC, checkpoint-inhibitor-ineligible (n=558) | Sacituzumab govitecan vs investigator chemotherapy | **BICR PFS:** 9.7 vs 6.9 months, stratified HR **0.62** (95% CI **0.50–0.77**; P<0.001). | [Original PMID 41124233](https://pubmed.ncbi.nlm.nih.gov/41124233/). Primary PFS only; do not invent a confirmed OS result. PFS and safety were reported in immunotherapy-ineligible first-line TNBC, not the heavily pretreated OptiTROP cohort. |

These numerical details were transcribed from the **original public abstracts**, not from the Agent's output or confidential/publisher full text. They are candidate reference facts that still require independent reviewer confirmation of versions, original protocol, subgroup, cutoffs, source tables and corrections.

## Safety and unfavorable results — do NOT omit

- **OptiTROP:** original abstract identifies hematological toxicities as the most common treatment-related events; a complete harms analysis requires original safety tables, severity, discontinuation and attribution.
- **CAPItello-290:** grade ≥3 diarrhea reported **12.7% versus 0.7%** (overall population). The abstract also reports adverse-event-related deaths across patients; **do not interpret this as a treatment-related death rate without adjudicating causality and denominators**. Primary OS endpoints did not meet their statistical threshold, despite numerically favorable PFS.
- **EMBER-3:** grade ≥3 adverse events reported **17.1%** imlunestrant, **20.7%** standard endocrine therapy and **48.6%** imlunestrant + abemaciclib. These numbers belong to **different randomized arms**. The all-patient imlunestrant versus SOC PFS was not significant.
- **ASCENT-03:** grade ≥3 adverse events were reported for **66% versus 62%**; common complications include neutropenia and diarrhea. Different treatment eligibility and safety reporting conventions prohibit simplistic safety ranking across these four trials.

## Actual automated validation and independent status

| Measure | First frozen V5 attempt | Post-diagnosis V5 regression |
|---|---:|---:|
| Original PubMed record identities retrieved | 4/4 | 4/4 |
| Original PMID and DOI identities matched | 4/4 | 4/4 |
| Original Results sections machine-identifiable | 0/4 | 3/4 |
| Predeclared original-abstract HR+CI tuples matched | **0/9** | **7/9** |
| Tuples still not extracted | 9 | **2** (both unstructured OptiTROP abstract) |
| Qualified independently adjudicated medical labels | **0** | **0** |

**Critical:** Once the initial V5 source labels have been inspected, V5 is **consumed**. The 7/9 rerun is an honest **regression result**, **not** a new independent/unseen accuracy claim. It does **not** measure clinical precision/recall, trial-specific inference, literature-retrieval coverage or quality of a manager-facing report.

The software deliberately does not extract an unstructured abstract when there is no reliable original Results heading; it may be possible to retrieve permitted full text via an approved institutional workflow, but it must never silently infer the Results boundary from Background/cited trials.

## Independent reviewers: mandatory adjudication questions

1. Check parent NCT, publication DOI/PMID, trial population, dates, protocol/amendments, crossover and linked reports. Two publications of one trial must not be double counted.
2. Verify full source: **specific Results paragraph or table**, comparator/arms, risk set, sample denominator, outcome-specific population/subgroup, prespecification, endpoint hierarchy, CI confidence level, model and cutoff.
3. Reconcile **primary/secondary PFS and OS** with formal multiplicity/statistical boundaries (especially CAPItello-290), maturity and subsequent treatments. HR estimates should not be translated to absolute survival benefit without the right context.
4. Review all adverse events of special interest, grade ≥3 events, ILD/pneumonitis where relevant, deaths, discontinuations, missingness and patient-reported outcomes. Record not reported/unclear instead of making up counts.
5. Two appropriately qualified independent reviewers record a verdict and each evidence locator. A senior adjudicator resolves disagreement from the source. This public tool cannot authenticate reviewers or sign off gold labels.
6. Freeze the **entire** relevant outcome-level expert reference with a hash, including negative and serious safety endpoints. Only then measure strict clinical precision, recall, citation errors and required expert review time.

## Next evaluation protocol

- V4's six reserved study families **remain unscored and unlabelled** for later *actual* expert validation; some identities were already visible, so the pool should not be advertised as fully blinded.
- If engineering regression continues, use **another newly selected, study-family-disjoint, label-frozen challenge** for engineering metrics; never recycle V5 as unseen.
- Measure both candidate tuple recall and **complete context accuracy** (arm, disease subtype, analysis population, cutoff, endpoint hierarchy, actual source locator). False confident interpretation of negative OS is high-risk, even if its raw HR number is correct.
- Keep per-claim reasoning and source links concise and auditable. Do not copy entire proprietary articles into a public GitHub artifact.
- Confirm enterprise text-mining permissions separately from article scientific quality, with no paid API or employer data used for this public prototype.

**Document classification: reviewer handoff / preliminary source spot-check only.**

# Step 2 — Independent Clinical Evidence Evaluation Progress
**As of 2026-10-17** · **source-verified engineering study, not a completed medically adjudicated Gold Standard**

## What's genuinely completed

- [Original-abstract handoff for four new breast trial families](V5_ORIGINAL_SOURCE_CLINICAL_REVIEW_HANDOFF.md), with trial population, comparator, negative OS results, distinct PFS/OS analyses, original PubMed citations and unresolved clinical-review items.
- Public metadata checks and **original NCBI PubMed XML Results section extraction** were implemented. Both PubMed source identities and tagged section availability are now separate audit dimensions.
- Outcome extractor takes **only PubMed IDs**, not answer labels. It emits source-linked candidate HR/CI tuples with explicit flags that arm assignment, population/subgroup, endpoint hierarchy, cutoff, and clinical approval are all pending.
- Fixed concrete parser errors found in live studies: flattened Europe PMC abstracts without Results boundaries, over-wide CI matching across unrelated outcomes, misclassification of **75 mg** or **150 mg** drug dose as hazard ratio, and Lancet's middle-dot decimal format (**0·59**, not zero).
- Strict refusal to invent a confidence level from an unlabeled HR interval. Tests explicitly cover 90%, 95%, 95.01% and 99% when published.
- Reproducible CI and synthetic regression suite, no paid API.

## Predeclared prospective numerical-source challenges

| Dataset | New parent studies | First, originally unseen source test | Later source regression | Safety/CI guard tests | Human medical gold |
|---|---:|---:|---:|---:|---:|
| V5 | Four: OptiTROP-Breast01; CAPItello-290; EMBER-3 primary; ASCENT-03 | **0/9 source tuples** (all Results headings lost in flattened feed) | **7/9 source tuples** after PubMed XML/CI fixes | Prespecified negative OS and subgroup clinical-review caveats, not specialist-scored | **0** |
| V6 | Three: VERITAC-2; SERENA-2; DESTINY-Breast02 | **2/3 explicit source tuples** | **3/3 source tuples** after dose/decimal fixes | **2/2** no-invented-CI controls on both first and repeated runs | **0** |

**Do not combine these two datasets into a fake single 'clinical accuracy' percentage.** This only samples manually preselected *original abstract numerical pairs*. The first result is the only valid first unseen attempt for each set; all subsequent tests on the same families are **regression**, and their labels are now exposed. The outcomes are not an exhaustive inventory of all important article content.

- [First V5 attempt](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions/runs/39015786354)
- [V5 final regression (7/9)](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions/runs/39016293274)
- [V6 first unseen trial-family test (2/3)](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions/runs/39016588170)
- [V6 final regression (3/3, two no-invented-CI guards)](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions/runs/39016851566)
- Final regression: **227/227 software tests**, source metadata 3/3, 2 incomplete-CI examples correctly **withheld**.

## Clinical negative and harms source-review items (do NOT omit)

1. [CAPItello-290 original PMID 41422862](https://pubmed.ncbi.nlm.nih.gov/41422862/): final overall OS **HR 0.92 (95% CI 0.78–1.08)** and altered-subgroup OS **HR 1.05 (95% CI 0.77–1.43)**; **neither primary OS endpoint met its prespecified statistical boundary**. Later/earlier PFS effects have separate analysis cutoffs and must not be equated to an OS benefit. Grade ≥3 diarrhea 12.7% versus 0.7% deserves safety review.
2. [EMBER-3 primary PMID 39660834](https://pubmed.ncbi.nlm.nih.gov/39660834/): in the entire population, imlunestrant versus standard endocrine therapy PFS **HR 0.87 (95% CI 0.72–1.04; P=0.12)** was not significant. The imlunestrant+abemaciclib vs imlunestrant **HR 0.57 (95% CI 0.44–0.73)** belongs to another treatment comparison; missing this arm distinction is a dangerous extraction mistake.
3. [VERITAC-2 PMID 40454645](https://pubmed.ncbi.nlm.nih.gov/40454645/): ESR1-mutant PFS HR **0.58 (95% CI 0.43–0.78)** differs from all-participant PFS HR **0.83 (95% CI 0.69–1.01)**, with no significant PFS benefit for the full cohort; the subgroup must not be generalized to every patient.
4. [SERENA-2 PMID 39481395](https://pubmed.ncbi.nlm.nih.gov/39481395/): original phase II paper uses **90% CI** for the 75-mg dose comparison; a dose of **75 mg is not an HR of 75**. Other HR bounds without an explicitly attached confidence level remain unresolved. The paper has a **2025 correction/erratum** (PMID 40049203), which a specialist must review.
5. [DESTINY-Breast02 PMID 37086745](https://pubmed.ncbi.nlm.nih.gov/37086745/): HER2-positive metastatic setting after T-DM1; the original abstract shows PFS HR 0.36 with adjacent unlabeled bounds. Do not invent a CI level in the extraction output. Drug-related ILD included **two fatal grade-5 events**; independent review must verify population, denominators, grade, causality, cutoff and any corrections.
6. [ASCENT-03 PMID 41124233](https://pubmed.ncbi.nlm.nih.gov/41124233/): first-line checkpoint-inhibitor-ineligible advanced TNBC PFS HR **0.62 (95% CI 0.50–0.77)**. This cannot be pooled as a direct comparison with the later-line, different ADC trial OptiTROP.

## What is NOT completed

- No two independently qualified oncology/Medical Affairs specialists have submitted or adjudicated reviews. Merely creating two named templates or having ChatGPT read twice is **not** two independent expert reviews.
- No original-publisher complete full-text, corrections, protocols, individual study tables, safety denominators and supplementary harm profiles have all been independently reconciled.
- No exhaustive outcome/harms-level blinded, adjudicated gold for new independent families.
- **Clinical precision, recall, hallucination rate and real workplace hours saved: UNMEASURED.**
- V4's six reserved parent-study families have **not been consumed** by V5 or V6 and remain unscored for potential future expert evaluation; review whether their identities were exposed during planning before claiming they are genuinely blinded.

## Concrete next gate

1. Assign two real qualified, independent reviewers; confirm expertise/rights privately. Give them the original source links and the existing [Gold review protocol](GOLD_REVIEW_PROTOCOL.md), plus blank reviewer JSON forms.
2. Independently annotate **all relevant efficacy and severe-safety outcomes**, their endpoints, subgroup/arms, denominators, cutoffs, CI levels, original table/figure anchors and missing results. Flag disagreements; adjudicate with a third domain-qualified reviewer.
3. Freeze the adjudicated reference file and source-version hashes privately; do not add copyrighted licensed full-text to public GitHub.
4. Freeze the next extractor commit **before viewing any new heldout labels**; evaluate once by underlying NCT, separating tuple precision/recall from *complete clinical context and citation* correctness.
5. Do a parallel timed Medical Affairs analyst review, counting the agent execution **plus** human corrections and approval.

**Cost:** $0 in paid APIs so far. No company/patient confidential material used, and no clinician signoff claimed.

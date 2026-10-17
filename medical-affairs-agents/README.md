# Medical Affairs Oncology Research Agent — Public Research Prototype

**Independent educational/research prototype. Not affiliated with, sponsored by, or approved by Daiichi Sankyo. Not a clinical decision support product.**

## What it actually does (verified in GitHub Actions)
1. **Public literature collection:** PubMed ESearch / EFetch (weekly bounded search, real network-tested), including title, DOI, PMID and supplied abstract.
2. **Open-access full-text processing:** Europe PMC JATS XML for selected accessible documents. Produces paragraph-backed source extracts, source identification and DOI checks.
3. **Cross-publication source audit:** table structure, a provisional comparison matrix, safety/efficacy claim evidence candidates, and explicit missing-data flags.
4. **Source-gated executive brief:** selected **hand-curated** claims are checked against Results/Safety paragraphs and source context before appearing as accepted *text matches*. It is not general autonomous medical reasoning or expert-validated evidence synthesis.
5. **Final OS verification:** verifies identity and relevant conclusions from the primary final-OS publication's public abstract. Full-text publisher ingestion and complete table/figure validation remain pending.
6. **Out-of-trial robustness evaluation:** a frozen 2025–2026 evaluation manifest covers three *distinct* breast-cancer studies, including randomized early disease, randomized advanced disease, and observational advanced disease.

### Important results — 17 October 2026

- PubMed online run generated 10 records (not auto-authored summaries).
- Three full-text TROPION-Breast01 publications were ingested. **All three describe one underlying clinical trial**, NCT05104866, not three independent studies.
- Source-gated report: 5/5 **selected** numerical source-text checks matched; 5/5 deliberately corrupted-number/reversed-arm negatives were blocked. Those examples were hand-chosen, so **do not interpret as 100% accuracy or clinical validation**.
- Independent-trial small holdout: 12/12 metadata/triage labels matched across three preselected article families; **this does not score effects, safety, RoB 2 or clinical reasoning**.
- Current offline tests: 58 passing. Results and timestamps in [GitHub Actions](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions).
- Measured seconds concern script processing only, **not** end-to-end reviewer time saved.

### Independent trial holdout

Frozen evaluation specification: [benchmarks/INDEPENDENT_HOLDOUT_V1.json](benchmarks/INDEPENDENT_HOLDOUT_V1.json).

The three outside-trial articles use DOI, NCT identifier, randomized-versus-observational classification, and early-versus-advanced disease setting as 12 evaluation labels. No effect-size precision/recall is measured yet. This is a *small, deliberately curated and non-blinded engineering holdout*: further tuning against these same results would invalidate its independence. For credible accuracy measurement, collect a separate reviewer-labeled **new-trial-family** corpus, freeze it, and evaluate only once.

### Two content access modes

We must **not** confuse article access restrictions with the scientific analysis algorithm.

- **Public demo:** open-access articles with suitable per-article rights; no corporate credentials or patient/employer data.
- **Future enterprise:** publisher-approved or internally licensed article connectors, subject to contract and text/data mining rights. A corporate subscription alone does not establish unrestricted commercial automated processing rights. Enterprise processing must happen in approved **private** infrastructure, not public GitHub Actions.

See [ENTERPRISE_CONTENT_ACCESS.md](ENTERPRISE_CONTENT_ACCESS.md) and the fail-closed code [content_access.py](content_access.py). The enterprise entitlement policy is only a configuration/authorization stub: **no enterprise system, licensed subscription, paid publisher API or employer records have been accessed**.

### Source-gated research demo

To reproduce the selected study workflow with public full-text connectivity:

```bash
python -m unittest discover -s medical-affairs-agents -p "test_*.py" -v
python medical-affairs-agents/pinned_trial_review.py
python medical-affairs-agents/source_audit.py
python medical-affairs-agents/numeric_claim_audit.py
python medical-affairs-agents/final_os_source_check.py
python medical-affairs-agents/source_gated_brief.py
python medical-affairs-agents/independent_holdout.py
```

These scripts require network access for full-text retrieval. The [reproducible Actions workflow](../.github/workflows/pinned-breast-trial-review.yml) runs and archives generated reports and measurement scorecards. The original [weekly PubMed brief workflow](../.github/workflows/weekly-oncology-brief.yml) remains active.

### Research quality and release gates

- **Do not count multiple analyses of the same NCT as independent trials.**
- **Do not interpret better PFS as demonstrated overall survival benefit.** Final OS must be checked separately; missing full text must be visibly marked.
- A located numeric pattern in a paragraph is a **source candidate**, not clinically validated extraction. Arm assignment, endpoint definition, denominators, analysis cutoff, CI and statistical context require review.
- Tables are structurally inspected; fully interpreting figures, multilevel tables, supplements, protocol amendments, corrections, and competing interests is not yet automated.
- RoB 2 risk of bias is **result-specific** and must not be fabricated as an automatic grade for an entire article.
- Clinical effect accuracy and reader usefulness still require an independently curated gold standard and a domain-qualified reviewer.
- Never upload restricted text or private records to a public repository, public CI artifacts, or an unapproved AI service.

## Zero-cost rule

See [COST_AND_PRIVACY_POLICY.md](COST_AND_PRIVACY_POLICY.md). **No paid models, publisher subscription, billing activation or external paid API may be enabled without the owner's explicit permission.**

## Resources

- [Europe PMC REST API](https://europepmc.org/RestfulWebService)
- [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25499/)
- [Cochrane Handbook — risk of bias](https://training.cochrane.org/handbook/current/chapter-08)
- [Elsevier TDM policy: corporate subscriptions](https://www.elsevier.com/about/policies-and-standards/text-and-data-mining)


### Clinical effect extraction: new robustness results

**Frozen V2 (first unseen test): 2/4 predeclared checks**; 2 numerical results missed, one subgroup ambiguity guard passed, one restricted-rights gate passed. [V2 scorecard](benchmarks/EFFECT_HOLDOUT_V2_FROZEN.json). This run has already been inspected and **must not be reused as an unseen evaluation**.

**Frozen V3 (new article families): 3/5 predeclared checks**. On the original Results of an independent 2025 **observational** screening cohort, the generic V3 extractor located BCSS HR 0.28 (95% CI 0.17–0.48) and OS HR 0.54 (95% CI 0.36–0.79), each as an **unverified association**, not a causal treatment claim. A separate restricted-license control was blocked. Two other article-type checks were **not passed because the licensing gate blocked their source before scientific classification** (one ambiguous metadata record, one explicitly restrictive licence). [V3 frozen manifest](benchmarks/EFFECT_HOLDOUT_V3_FROZEN.json).

Current software suite: **84 offline tests** passed in the V3 run. That number measures software tests, **not clinical accuracy**. The V2 and V3 scores are tiny targeted *engineering* audits, not statistical precision or recall. The clinical domain reviewer gold set is **not yet populated or approved**.

For precise failure notes, evaluation definitions, and a reviewer annotation template, see [Validation baseline](benchmarks/VALIDATION_BASELINE_AND_RELEASE_GATES.md) and [blank gold annotation schema](benchmarks/CLINICAL_ANNOTATION_TEMPLATE.csv). Do not edit previously observed holdout values to inflate results.

**New experimental scripts:** [clinical_effects.py](clinical_effects.py), [clinical_effects_v3.py](clinical_effects_v3.py), [evaluate_effect_holdout_v2.py](evaluate_effect_holdout_v2.py), and [evaluate_effect_holdout_v3.py](evaluate_effect_holdout_v3.py). None is an independently validated AI medical reasoning engine. V3 supports numeric source candidates across separate original papers, distinguishes abstract/full-text sources, captures CI levels, and clearly abstains when evidence is uncertain.


### Latest safeguards — 17 October 2026

- **Clinical evidence reviewer queue:** [evidence_review_queue.py](evidence_review_queue.py) groups provisional shared registry IDs (preventing naïve multi-publication double counting), differentiates full-text from abstract-only candidates, records abstentions, and marks **zero automatically approved clinical conclusions**. [Cloud smoke run](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions/runs/39010216403) passed.
- **Two-reviewer gold evaluator:** [clinical_gold_evaluator.py](clinical_gold_evaluator.py) tests exact numerical effect+CI tuples **separately** from the stricter end-to-end clinical context (population, treatment arms, comparator, analysis cutoff, verified source). It refuses to produce metrics without independently adjudicated gold and detects trial-family leakage, citation errors and duplicate predictions. See [the evaluation guide](benchmarks/TWO_REVIEWER_GOLD_EVALUATION_GUIDE.md). **No real two-reviewer dataset exists yet**, so scientific precision/recall remain UNMEASURED.
- **Protocol safeguard:** [clinical_effects_v3.py](clinical_effects_v3.py) now prevents protocol-only publications from being interpreted as observed trial efficacy even if they contain projected numbers under a `Results` heading.
- **Rights parity across old/new workflows:** all pinned-trial public full-text steps now require [rights_preflight.py](rights_preflight.py) approval. A genuine metadata check found the three pinned TROPION-Breast01 papers were **CC BY-NC-ND**, not approved by our conservative commercial-intent public text-mining policy. The pinned workflow therefore now **SKIPS full-text processing** and produces a rights-status report, rather than ignoring its own rights policy. [Rights preflight run](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions/runs/39010657789). This says NOTHING about trial quality and does not bar future authorized enterprise use.
- **Safe public full-text smoke:** [fulltext-smoke.yml](../.github/workflows/fulltext-smoke.yml) now processes a separately reviewed CC BY document and outputs only unapproved source candidates. [New passing cloud smoke](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions/runs/39010828243): 113/113 tests; 5 source candidates, 6 abstentions, 0 medically approved clinical claims. Old unrestricted legacy CLI search/matrix tools now filter out unknown or restrictive article licenses.
- **Do not conflate green CI with scientific validation.** A 113/113 software result means safety properties of synthetic tests were met, not 100% clinical accuracy. No licensed corporate content or paid API is used.

The next scientific work needs a clinician-reviewed and trial-family-disjoint outcome/harms gold standard, then end-to-end precision, recall, unsupported citation rate, and human review-time benchmarking. Corporate entitlements can later be pluggable via an approved private connector without weakening the scientific review gate.


### ADC provisional development references — October 2026

Step 1 of the clinical evidence accuracy project now has **10 independent original breast-cancer ADC parent-study families** across Dato-DXd, T-DXd, and sacituzumab govitecan. See [the structured development reference registry](benchmarks/ADC_REFERENCE_CANDIDATES_V1.json), [the public source-audit script](adc_reference_dataset.py), and [the two-reviewer worksheet generator](adc_reviewer_worksheet.py).

- **Latest live run:** [Public Breast ADC Reference Dataset Audit](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions/runs/39012663227) — **133/133** offline tests passed, **10/10** PubMed source records retrieved and checked for original PMID/DOI and numeric tokens; **9/10** candidate parent-study registrations located using source abstract or independent NCBI PubMed ClinicalTrials.gov databank metadata.
- **Still flagged:** TROPION-Breast02 has its original PubMed numeric data present but automated NCT linkage incomplete. The [FDA approval summary](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-datopotamab-deruxtecan-dlnk-unresectable-or-metastatic-triple-negative-breast-cancer) independently identifies it as NCT05374512; that is a **separate cross-reference**, not a manufactured PubMed metadata match.
- **Three artifact files:** the human-readable candidate reference brief, source metadata/number-token audit JSON, and an **unfilled** worksheet for two independent expert reviewers across all 10 study families. The artifact name is **provisional-adc-reference-packet-not-gold**.
- **Development data, not unseen evaluation:** these 10 studied families may be used for exploratory engineering and reviewer annotation. They must **not** be counted as a new independent holdout after inspection. The previous V2/V3 holdouts remain unchanged.
- **Scientific validity:** 0 independently adjudicated labels, 0 medically approved treatment claims, **no real clinical precision/recall estimate**. Abstract number-token presence is a provenance aid, not proof of treatment-effect attribution or valid methodology.
- **Statistical guardrails:** TROPION-Breast02 PFS reports a **99%** CI, DESTINY-Breast04's selected 0.51 HR is for the HR-positive HER2-low subgroup without CI limits in the selected abstract, DESTINY-Breast05 studies early post-neoadjuvant iDFS and has a later erratum, and BEGONIA arm 6 is single-arm with a response objective not met.
- **Rights:** this collection fetches public PubMed bibliographic metadata and abstracts for automated checks but **does not export copied abstracts or publisher full texts**. Restricted enterprise/publisher content is never routed through public GitHub. No paid models/APIs.

**To repeat the authorized public development-source check:**

    python -m unittest discover -s medical-affairs-agents -p "test_*.py" -v
    python medical-affairs-agents/adc_reference_dataset.py
    python medical-affairs-agents/adc_reviewer_worksheet.py

**Next rigorous step:** two qualified reviewers independently annotate endpoints, intervention/control arms, confidence interval level, population, harms, methods and limitations from original permitted full text; adjudicate disagreements; then evaluate on **fresh study-family-disjoint unseen sources**. See [gold evaluation guide](benchmarks/TWO_REVIEWER_GOLD_EVALUATION_GUIDE.md).



### Quality audit and speed improvement — October 17, 2026

The ten original ADC paper-development references have been re-audited for scientific source identity, numerical provenance and misleading endpoint attribution. Read [the full mistakes-and-fixes log](benchmarks/AUDIT_2026_10_17.md) and [source-linked safety priorities](benchmarks/SAFETY_REVIEW_PRIORITIES.md).

- **Bug corrected:** Numbers that merely occurred somewhere in the same abstract (e.g., HR from one endpoint, CI from another) no longer suffice. [abstract_statistic_verifier.py](abstract_statistic_verifier.py) requires locally attached point estimate and CI, checks CI confidence level **including 99% and 95.01%**, and reports whether the *nearest explicitly named endpoint* matches. These are candidate source checks, never accepted clinical conclusions.
- **Corrected scientific metadata:** TROPION-Breast02 has **dual primary** PFS and OS endpoints, not an uncertain hierarchy; other trials' endpoint and population ambiguities remain flagged.
- **Safety prioritized:** Pulmonary toxicities, fatal ILD cases, severe adverse events and BEGONIA's missed prespecified efficacy objective have individual original-source research-review links. They are not a cross-trial comparative safety ranking.
- **Speed:** ten serial Europe PMC metadata requests were consolidated to **one bounded, identity-checked batch call** with fallback for missing PMIDs. Observed original serial 10.955 s vs recent 2.819/2.918/3.186 s; network timing is variable and excludes all human scientific review.
- **Latest source audit:** [GitHub Actions run 39013783455](https://github.com/LidaMirzaei/Healthcare-AI-Portfolio/actions/runs/39013783455), **152/152** Python tests, 10/10 original PMID and DOI identities matched, **7/10** local estimate/CI/endpoint candidate matches, **9/10** PubMed-linked trial registries. The two missing endpoint linkages (DESTINY-Breast03/05), one missing CI (DESTINY-Breast04), and TROPION-Breast02's unresolved original PMID-to-trial registry linkage are visibly flagged. They must **not** be auto-filled.
- **Hard-fail gate:** one wrong or unavailable original PMID+DOI now fails the online audit, even when the remaining studies look fine. Earlier V2/V3 scores are preserved, and these 10 papers remain a **development set**, not a future unseen evaluation set.

**Scientific precision and recall are still unmeasured.** Green software tests, endpoint candidates and PubMed metadata checks are not independently adjudicated full-text scientific outcomes. Two medically qualified independent reviewers and a new study-family-disjoint holdout will be required before claiming clinical performance.


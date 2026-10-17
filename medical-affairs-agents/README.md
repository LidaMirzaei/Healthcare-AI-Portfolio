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

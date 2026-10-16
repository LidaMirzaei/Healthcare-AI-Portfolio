# Project 1 — Reproducible Cancer Drug Combination Prediction

**Status:** planning; no model training has yet been performed.
**Literature rule:** use only 2024–2026 research papers as the recommended project literature. See [curated reading list](READING_LIST_2024_2026.md).

## Anchor research
- **2025**: *AI-driven discovery of synergistic drug combinations against pancreatic cancer* — https://doi.org/10.1038/s41467-025-56818-6
- Open research code/data — https://github.com/ncats/PANC1
- Breast cancer comparison **2025**: *Interpretable prediction of drug synergy for breast cancer by random forest with features from Boolean modeling of signaling pathways* — https://www.nature.com/articles/s41598-025-02444-7 and https://github.com/Ktaoma/LogicForests

## Objective
Reproduce a documented baseline on published in-vitro drug-pair screening data. Then test whether a different evaluation split or model improves **held-out predictive performance**. Never claim an improved model without a fair comparison.

## Implementation sequence
1. Inspect paper and code; document data sources, screening conditions, licenses and metric definition.
2. Build a clean table of drug pairs, fingerprints, experimental synergy labels and identifiers.
3. Reproduce the simplest published baseline; fix seeds and dependency versions.
4. Implement the baseline independently.
5. Compare random pair splits with drug-held-out evaluation and explicitly inspect leakage.
6. Only then evaluate a graph model using the same split, or study stronger 2026 methods.
7. Publish results and methodological limitations even when the advanced model loses.

## Boundaries
Laboratory cell-line synergy is not clinical efficacy or treatment advice. No identifiable clinical records or employer-confidential data. The published teams' laboratory results are not claims about this portfolio.

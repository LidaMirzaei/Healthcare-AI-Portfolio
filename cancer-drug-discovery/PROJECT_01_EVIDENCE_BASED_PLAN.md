# Project 1: Reproducible Molecular Bioactivity Prediction

**Status: planning only. No experiment has been run yet.**

## Why this project?
Learn a real, reproducible drug-discovery ML workflow before moving to drug-combination research. Start with a well-documented cancer-related protein target (candidate: EGFR, subject to checking ChEMBL assay counts, target definition, measurement consistency and usage rights). Avoid implying that enzyme inhibition equals cancer treatment.

## Existing learning examples
- Kaggle ChEMBL bioactivity notebook: https://www.kaggle.com/code/owaistahir/bioactivity-project-for-drug-discovery-chembl
- Data Professor open-source bioactivity model demonstration (note older environments may require updating): https://github.com/dataprofessor/bioactivity-prediction-app
- DeepChem tutorials: https://deepchem.io/tutorials/
- ChEMBL workshop (EMBL-EBI): https://www.ebi.ac.uk/training/events/chembl-workshop-drug-design/

## Research baseline and papers
- Wu et al. (2018), MoleculeNet: https://doi.org/10.1039/C7SC02664A
- Sidorov et al. (2019), Predicting Synergism of Cancer Drug Combinations Using NCI-ALMANAC Data: https://doi.org/10.3389/fchem.2019.00509

## Milestones
1. **Understand and reproduce:** study the Kaggle notebook. Cite any reused code, and record exact versions and data source.
2. **Data audit:** query ChEMBL, isolate defensible comparable measurements (e.g. IC50 in nM with explicitly documented relations and assay criteria), identify duplicates, missing values, censored measurements and standardization issues. Freeze a versioned extraction; do not silently mix assay types.
3. **Baseline:** use RDKit descriptors/fingerprints and a simple regression model. Track metrics (MAE, RMSE, R2), dataset counts and seeds.
4. **Fair evaluation:** compare random splitting with molecular scaffold splitting, keep the test set held out until final evaluation, and prevent duplicate/scaffold leakage.
5. **Upgrade:** compare Random Forest with a graph neural network *only after* the baseline is reproducible. Report training cost, uncertainty and failure cases. Improvements must be demonstrated, not claimed.
6. **Communication:** prepare reproducible code, README, plots, model card and short presentation. A prediction is an assay hypothesis, never a proposed patient treatment.

## Later follow-on (not part of Project 1)
Reproduce NCI-ALMANAC drug-pair synergy modeling from Sidorov et al. (2019), then evaluate generalization on unseen drug pairs and cell lines. Existing modern comparison code: https://github.com/lcrawlab/cancer-drug-synergy-prediction

## Week 1 checklist
- [ ] Complete EMBL-EBI ChEMBL introduction: https://www.ebi.ac.uk/training/online/courses/chembl-quick-tour/
- [ ] Open the Kaggle example, identify its *actual target* and input/output columns (do not assume it already models cancer).
- [ ] Explain SMILES, target, assay, IC50 and pIC50.
- [ ] Write a short summary of the MolecularNet paper's random vs scaffold split.
- [ ] Run first pandas example; write an independent adaptation.

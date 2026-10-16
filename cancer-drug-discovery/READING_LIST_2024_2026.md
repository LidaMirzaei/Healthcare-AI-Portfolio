# Cancer Drug Discovery — Research Reading List (2024–2026 only)

**Updated:** October 16, 2026. **Status:** reading and project design; no models have been trained for this project.

## Selection rules
Only papers first published January 2024–October 16, 2026. Prioritize peer-reviewed journals, accessible methods, code, datasets, and rigorous held-out evaluation. Citation counts change; publisher counts are snapshots, not guarantees of quality.

## Reproducible anchor
1. **Pourmousa et al. (2025)**, *AI-driven discovery of synergistic drug combinations against pancreatic cancer*, Nature Communications. DOI: https://doi.org/10.1038/s41467-025-56818-6 . Public code and modeling data: https://github.com/ncats/PANC1 . The publisher reported 37 citations when checked. Reproduce a modest fingerprint + random forest baseline, not the laboratory experiments.

## Breast cancer-focused candidate
2. **Taoma et al. (2025)**, *Interpretable prediction of drug synergy for breast cancer by random forest with features from Boolean modeling of signaling pathways*, Scientific Reports. https://www.nature.com/articles/s41598-025-02444-7 . Code and data: https://github.com/Ktaoma/LogicForests . Inspect environment and data permissions before attempting replication.

## Further contemporary research
3. **Liu et al. (2025)**, *Building a unified model for drug synergy analysis powered by large language models*, Nature Communications. https://doi.org/10.1038/s41467-025-59822-y . Code: https://github.com/HelloWorldLTY/BAITSAO . Requires significant compute; study architecture and benchmark protocol first.
4. **(2025)**, *A Bayesian active learning platform for scalable combination drug screens* (BATCHIE), Nature Communications. https://www.nature.com/articles/s41467-024-55287-7 . Study how data acquisition can be optimized.
5. **(2025)**, *An open-source screening platform accelerates discovery of drug combinations* (Combocat), Nature Communications. https://www.nature.com/articles/s41467-025-66223-8 . Code: https://github.com/wcwr/combocat .
6. **(2026)**, *Interpretable graph deep learning framework for drug synergy prediction by integrating functional and clinical similarities* (DSimSynergy), npj Digital Medicine. https://www.nature.com/articles/s41746-026-02830-z .
7. **(2026)**, *DeepSynBa: actionable drug combination prediction with complete dose-response profiles*, Bioinformatics. https://doi.org/10.1093/bioinformatics/btag416 .
8. **Feng et al. (2026)**, *An ensemble framework for robust drug response prediction and large-scale sensitivity profiling across cancers*, Communications Biology. https://doi.org/10.1038/s42003-026-11124-9 .

## Concrete six-week starter experiment
- **Week 1:** Download/inspect the public PANC1 repository and paper. Document schema, target metric, assay context, potential leakage and licenses.
- **Week 2:** Reproduce published data cleaning and a basic baseline using the paper's documented split conditions.
- **Week 3:** Implement an independent fingerprint + random forest baseline; save run settings and seeds.
- **Week 4:** Compare random pair splitting with compound-held-out splitting; report data overlap and results.
- **Week 5:** Evaluate a small GNN against the identical held-out split, only if compute/data preparation allow.
- **Week 6:** Write a technical report with actual metrics, limitations and an honest outcome, regardless of improvement.

## Strict scientific caveats
Predicting synergy in vitro is not evidence of clinical effectiveness. Do not create treatment recommendations. Never report paper results as if they were personally reproduced. Changes to a model do not count as improvement unless compared using the same data, splits and metrics.

**Earlier exploratory reading notes using older literature are superseded by this list.**

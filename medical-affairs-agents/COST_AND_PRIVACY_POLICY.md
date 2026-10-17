# Zero-Spend Development Policy

**Effective:** 2026-10-17. **Owner approval required for all paid services.**

## Allowed without additional payment
- Standard GitHub-hosted `ubuntu-latest` Actions runner **while the repository remains public**.
- Public PubMed NCBI E-utilities for a bounded number of records.
- Python standard-library parsing, basic report generation and offline tests.
- GitHub Actions artifacts within the free plan's storage allowance.

## Not authorized — STOP and ask user first
- Anthropic/Claude API, OpenAI paid API, or any usage-metered AI provider.
- Buying credits, upgrading a plan, adding payment details or enabling auto-recharge.
- Paid cloud servers, larger runners, private repository billable CI, paid data feeds.
- Uploading confidential company content, protected health information or personal data.
- Automatically emailing or sending reports to any external person.

## Guardrails
1. The default job uses a standard public GitHub-hosted runner only.
2. Retrieval is bounded to at most 10 records per scheduled run (code supports an explicit upper bound of 50 for manual execution).
3. No paid API keys are needed or configured. Secrets must never be written to source, logs or artifacts.
4. A failed network request should fail the job visibly; it must not silently fabricate a success.
5. Save source-linked evidence, not unchecked generated medical conclusions.
6. Before any AI integration, require explicit consent to the provider, payment method, usage cap and hard-stop behavior.
7. If a future workflow would make the repository private, use a larger runner, increase storage, or attach a billing account, STOP and confirm the financial impact.

## Acceptance gates
- Offline Python tests pass.
- Cloud test workflow passes.
- Scheduled retrieval workflow executes successfully and produces a nonempty report with working PMID references.
- Human reviewer independently checks report accuracy and relevance.
- Any LLM summary must be validated separately; **100% scientific accuracy cannot be promised**.

This prototype is independent and not approved Medical Affairs content.

# Public Demo ↔ Enterprise Content Access Architecture

The **scientific extraction, evidence attribution, and reviewer gates must be identical** regardless of where an article originates. Access is a separate, pluggable component.

## Public demo (current)
- Europe PMC/open access content only when reuse terms are appropriate for this prototype.
- Confirm licensing **per article**; do not assume "open access" means commercial AI mining is allowed.
- Use a public GitHub repository only for open-source code and permissible evidence metadata; **never commit private full text or access tokens**.
- Missing permissions/uncertain provenance: **abstain** and require review.

## Enterprise deployment (future, not activated)
- A pharmaceutical company may have substantial journal subscriptions, but not blanket access to every article.
- Content ingress may use **publisher-approved API, licensed internal document management system, or library-provided service**, conditional on each provider/contract.
- Confirm **(1) the subscription entitlement, (2) automated text/data mining rights, (3) commercial/organizational use rights, (4) confidentiality and model-processing permissions**, and **(5) local retention and redistribution terms**.
- Execute content extraction only in company-approved private infrastructure, not public GitHub Actions. Never send full-text or confidential materials to a public/consumer AI app or external LLM without explicit organizational authorization.
- Keep credentials in a secret manager; do not receive/store corporate passwords, session cookies or access tokens in this public repository.
- Final reports may contain sourced *facts and references* within permitted usage; copyrighted source passages should not be broadly copied or exposed.
- The enterprise rights gate in `content_access.py` is an **authorization policy stub**, not a functioning institutional integration. Its boolean approvals must eventually come from a properly authenticated rights/entitlement service, not arbitrary end-user declarations.

## Controls not yet solved
- No licensed publisher connector or contracted TDM service is connected.
- No commercial approval/contract review, security review or patient/company-data agreement has taken place.
- Full-text parsing does not comprehensively handle supplements, figures or complex tables.
- Study-specific clinical reasoning still needs an independently reviewed evidence dataset.

## Original rights guidance
- [Elsevier text/data mining policy](https://www.elsevier.com/about/policies-and-standards/text-and-data-mining) says corporate subscribers should consult their account manager.
- [Elsevier TDM licence terms](https://www.elsevier.com/about/policies-and-standards/text-and-data-mining/license) show why merely being a subscriber is not a blanket commercial TDM grant.

**Cost policy:** no paid APIs, billing activation, or paid licensed content may be enabled without the project owner's explicit consent.

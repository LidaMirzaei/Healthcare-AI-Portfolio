"""Content access authorization for public demo vs enterprise deployments.

This is a permission gate, NOT a content provider / publisher downloader.
No corporate token is accepted or logged. No enterprise content belongs in
public GitHub, public Actions artifacts, or unapproved external AI services.
"""
from dataclasses import dataclass
from typing import Literal

Mode = Literal["public_demo", "enterprise"]
Environment = Literal["public_github", "approved_enterprise", "local_private"]
ALLOW = "ACCESS_APPROVED_FOR_AUTHORIZED_PIPELINE"
DENY = "ACCESS_BLOCKED_REQUIRE_RIGHTS_REVIEW"


@dataclass(frozen=True)
class Rights:
    provider: str
    mode: Mode
    license_id: str = ""
    # Enterprise rights are evaluated per publisher/contract and article.
    institutional_entitlement_confirmed: bool = False
    automated_text_mining_allowed: bool = False
    commercial_use_allowed: bool = False
    approved_processing_environment: bool = False
    no_external_distribution: bool = True
    environment: Environment = "public_github"


def decision(rights: Rights) -> dict:
    """Fail closed unless a specific approved source AND environment are known."""
    if rights.mode == "public_demo":
        approved = rights.license_id.strip().lower() in {
            "cc-by-4.0", "cc-by-3.0", "cc0-1.0"
        }
        if not approved:
            reason = "Public content license not explicitly approved for demo"
        elif rights.environment != "public_github":
            reason = "Demo configuration must use explicitly designated public environment"
        else:
            reason = "Approved public demo with citation/attribution obligations"
        return {"status":ALLOW if approved and rights.environment == "public_github" else DENY,
                "reason":reason, "store_fulltext_in_public_repo":False,
                "allow_paid_api":False}

    if rights.mode != "enterprise":
        return {"status":DENY, "reason":"Unknown mode", "store_fulltext_in_public_repo":False,
                "allow_paid_api":False}

    grants = (
        rights.provider.strip() != ""
        and rights.institutional_entitlement_confirmed
        and rights.automated_text_mining_allowed
        and rights.commercial_use_allowed
        and rights.approved_processing_environment
        and rights.environment in ("approved_enterprise", "local_private")
        and rights.no_external_distribution
    )
    return {
        "status":ALLOW if grants else DENY,
        "reason":("Approved enterprise entitlement/automation/use/environment confirmed for this item"
                  if grants else "Need article/provider-specific institutional access, TDM rights, commercial processing rights and approved private environment"),
        "store_fulltext_in_public_repo":False,
        "allow_paid_api":False,
    }


class UnauthorizedContentError(PermissionError):
    pass


def require_rights(rights: Rights) -> dict:
    evaluation = decision(rights)
    if evaluation["status"] != ALLOW:
        raise UnauthorizedContentError(evaluation["reason"])
    return evaluation

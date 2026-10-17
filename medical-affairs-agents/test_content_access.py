import unittest
from content_access import Rights, decision, require_rights, ALLOW, DENY, UnauthorizedContentError

class RightsTests(unittest.TestCase):
    def test_public_cc_by_allowed(self):
        r=decision(Rights(provider="Europe PMC",mode="public_demo",license_id="cc-by-4.0"))
        self.assertEqual(r["status"],ALLOW)
        self.assertFalse(r["store_fulltext_in_public_repo"])
    def test_demo_noncommercial_license_blocked(self):
        r=decision(Rights(provider="PMC",mode="public_demo",license_id="cc-by-nc-4.0"))
        self.assertEqual(r["status"],DENY)
    def test_enterprise_subscription_alone_not_sufficient(self):
        r=Rights(provider="Publisher",mode="enterprise",environment="approved_enterprise",
                 institutional_entitlement_confirmed=True)
        self.assertEqual(decision(r)["status"],DENY)
    def test_enterprise_rights_can_approve_licensed_article(self):
        r=Rights(provider="Publisher",mode="enterprise",environment="approved_enterprise",
                 institutional_entitlement_confirmed=True,
                 automated_text_mining_allowed=True,
                 commercial_use_allowed=True,
                 approved_processing_environment=True)
        self.assertEqual(require_rights(r)["status"],ALLOW)
        self.assertFalse(decision(r)["store_fulltext_in_public_repo"])
    def test_enterprise_cannot_run_on_public_github(self):
        r=Rights(provider="Publisher",mode="enterprise",environment="public_github",
                 institutional_entitlement_confirmed=True,
                 automated_text_mining_allowed=True,commercial_use_allowed=True,
                 approved_processing_environment=True)
        with self.assertRaises(UnauthorizedContentError):
            require_rights(r)
    def test_nonapproved_external_sharing_blocks(self):
        r=Rights(provider="Publisher",mode="enterprise",environment="local_private",
                 institutional_entitlement_confirmed=True,
                 automated_text_mining_allowed=True,commercial_use_allowed=True,
                 approved_processing_environment=True,no_external_distribution=False)
        self.assertEqual(decision(r)["status"],DENY)
    def test_no_paid_api_authorization(self):
        r=Rights(provider="PMC",mode="public_demo",license_id="cc-by-4.0")
        self.assertFalse(decision(r)["allow_paid_api"])

if __name__=="__main__":
    unittest.main()

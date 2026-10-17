"""Fully synthetic review-queue safety tests, not frozen holdout data."""
import copy
import unittest
from evidence_review_queue import triage, render

def row(pmcid="PMC70000001", registration="NCT12345678", status="EFFECT_CANDIDATES_UNVERIFIED"):
    return {
        "pmcid":pmcid,"title":"Synthetic randomized study",
        "status":status,
        "license":{"status":"CC_BY_OR_CC0_CONFIRMED"},
        "registration_candidate":registration,
        "article_kind":"POSSIBLY_RANDOMIZED_TRIAL_NEEDS_METHODS_REVIEW",
        "candidates":[{
            "source_url":"https://pmc.ncbi.nlm.nih.gov/articles/"+pmcid+"/#r1",
            "source_id":"r1","source_id_kind":"JATS_ID",
            "source_level":"FULLTEXT_RESULTS",
            "status":"NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED",
            "endpoint":"PFS", "measure":"HR","estimate":0.88,
            "ci_level":90,"ci_lower":0.70,"ci_upper":1.05,
            "arm_assignment_verified":False,
            "population_verified":False,
            "data_cutoff_verified":False,
        }],
    }

class QueueSafety(unittest.TestCase):
    def test_same_registry_families_not_counted_twice(self):
        a=row()
        b=row("PMC70000002")
        q=triage([a,b])
        self.assertEqual(q["article_count"],2)
        self.assertEqual(q["provisional_study_family_count"],1)
        self.assertEqual(len(q["repeated_registry_groups_needing_confirmation"]),1)
        self.assertEqual(q["clinical_claims_released"],0)
        self.assertIn("DO NOT double-count",render(q))
    def test_unknown_registration_does_not_merge_unrelated_papers(self):
        a=row(registration="UNKNOWN_OR_AMBIGUOUS_REVIEW_REQUIRED")
        b=row("PMC70000002",registration="UNKNOWN_OR_AMBIGUOUS_REVIEW_REQUIRED")
        q=triage([a,b])
        self.assertEqual(q["provisional_study_family_count"],2)
        self.assertEqual(q["unverified_registration_count"],2)
    def test_abstract_only_not_fulltext(self):
        a=row()
        a["candidates"][0]["source_level"]="ABSTRACT_RESULTS_ONLY"
        q=triage([a])
        self.assertEqual(q["abstract_only_candidate_count"],1)
        self.assertEqual(q["records"][0]["findings"][0]["review_priority"],
                         "ABSTRACT_ONLY_REQUIRES_ORIGINAL_RESULTS")
    def test_license_block_must_have_no_mined_data(self):
        a=row(status="BLOCKED_LICENSE_REVIEW_REQUIRED")
        a["license"]["status"]="BLOCKED_LICENSE_NOT_APPROVED"
        with self.assertRaises(ValueError):
            triage([a])
    def test_blocked_protocol_must_have_no_results(self):
        a=row(status="BLOCKED_PROTOCOL_NOT_OBSERVED_RESULTS")
        with self.assertRaises(ValueError):
            triage([a])
    def test_missing_citation_fails_closed(self):
        a=row()
        del a["candidates"][0]["source_url"]
        with self.assertRaises(ValueError):
            triage([a])
    def test_impossible_ci_fails_closed(self):
        a=row()
        a["candidates"][0]["ci_lower"]=1.30
        with self.assertRaises(ValueError):
            triage([a])
    def test_duplicate_pmcid_fails_closed(self):
        with self.assertRaises(ValueError):
            triage([row(),row()])
    def test_rights_block_output_empty_permitted(self):
        a=row(status="BLOCKED_LICENSE_REVIEW_REQUIRED")
        a["license"]["status"]="BLOCKED_LICENSE_NOT_APPROVED"
        a["candidates"]=[]
        q=triage([a])
        self.assertEqual(q["clinical_claims_released"],0)
        self.assertEqual(q["source_candidate_count"],0)
    def test_fulltext_candidate_still_not_approved(self):
        q=triage([row()])
        f=q["records"][0]["findings"][0]
        self.assertFalse(f["scientifically_validated"])
        self.assertFalse(f["clinical_release_authorized"])
        self.assertEqual(q["clinical_claims_released"],0)
        self.assertTrue(q["requires_qualified_reviewer"])
    def test_do_not_infer_os_from_pfs(self):
        q=triage([row()])
        s=render(q)
        self.assertIn("do not treat PFS as OS",s)
        self.assertNotIn("proven survival benefit",s)

if __name__=="__main__":
    unittest.main()

"""Synthetic tests for independent scientific review machinery, no clinical truth."""
import copy
import json
import unittest
from pathlib import Path
from clinical_reference_review import (
    make_review_queue, review_template, validate_review,
    compare_reviews, stable_json_sha256,
)
from adc_reference_dataset import DEFAULT_SEED

SEED=json.loads(DEFAULT_SEED.read_text(encoding="utf-8"))


def fake_source_audit():
    return {"studies":[{
        "pmid":s["pmid"],"source_doi":s["expected_doi"],
        "verification_status":"ABSTRACT_SOURCE_CHECK_INCOMPLETE_REVIEW_REQUIRED",
        "checks":{"pubmed_identity":True,"source_doi_identity":True,
                  "local_statistic_endpoint_candidate":False,
                  "nct_found_in_abstract":False}
    } for s in SEED["studies"]]}


def fake_queue():
    # Completely fabricated study and result, independent from all real trials.
    claim={
        "claim_id":"FICTIONAL|PFS|primary",
        "parent_trial_id":"NCT12345678",
        "source_pmid":"99990001",
        "source_doi":"10.7777/fictional.example",
        "candidate_only":{"endpoint":"PFS","estimate":0.82},
    }
    return {"schema":"breast-adc-review-candidates-v1",
            "candidate_set_sha256":stable_json_sha256([claim]),
            "claims":[claim]}


def completed_review(queue,who,accepted=False):
    r=review_template(queue,who)
    r["professional_qualification_externally_checked"]=True
    r["independent_review_performed"]=True
    for item in r["records"]:
        item["verdict"]="supported" if accepted else "unsupported"
        item["rationale"]="Synthetic hypothetical trial record explicitly reviewed for testing"
        item["methods_review_status"]="COMPLETE"
        item["harms_review_status"]="COMPLETE"
        item["negative_results_review_status"]="COMPLETE"
        if accepted:
            item["verified_fields"]={
                "study_family_id":"NCT12345678","pmid":"99990001",
                "doi":"10.7777/fictional.example","endpoint":"PFS",
                "measure":"HR","estimate":0.82,"ci_level":95,
                "ci_lower":0.7,"ci_upper":0.95,
                "population":"fictional participants",
                "intervention":"synthetic drug A",
                "comparator":"synthetic drug B",
                "analysis_cutoff":"2030-01-01",
                "analysis_denominator":"100 hypothetical adults",
                "endpoint_hierarchy":"prespecified primary",
                "source_url":"https://pubmed.ncbi.nlm.nih.gov/99990001/",
                "source_locator":"Results paragraph 4",
                "methods_limitations":"fictional blinding issues for unit test",
                "safety_review_completed":True,
                "corrections_checked":True,"source_checked":True
            }
    return r


class IndependentGoldWorkflowTests(unittest.TestCase):
    def test_ten_development_claims_plus_mandatory_safety_tasks(self):
        q=make_review_queue(SEED,fake_source_audit())
        self.assertEqual(q["reference_count"],10)
        self.assertEqual(q["target_minimum_review_tasks"],30)
        self.assertEqual(q["state"],"UNREVIEWED_NOT_GOLD")
        self.assertEqual(q["gold_claims"],0)
        self.assertFalse(any(x["two_human_reviews_complete"] for x in q["claims"]))
        self.assertFalse(any(x["adjudicated_gold"] for x in q["claims"]))

    def test_holdout_overlap_or_metadata_mismatch_blocks(self):
        with self.assertRaises(ValueError):
            make_review_queue(SEED,fake_source_audit(),reserved_families=["NCT05104866"])
        a=fake_source_audit()
        a["studies"][0]["checks"]["source_doi_identity"]=False
        with self.assertRaises(ValueError):
            make_review_queue(SEED,a)
        a=fake_source_audit()
        a["studies"].pop()
        with self.assertRaises(ValueError):
            make_review_queue(SEED,a)

    def test_blank_reviews_fail_validation(self):
        q=fake_queue()
        a=review_template(q,"a")
        self.assertFalse(a["professional_qualification_externally_checked"])
        with self.assertRaises(ValueError):
            validate_review(q,a)

    def test_two_different_declared_reviewers_do_not_create_gold(self):
        q=fake_queue()
        a=completed_review(q,"qualified-A",accepted=True)
        b=completed_review(q,"qualified-B",accepted=True)
        report=compare_reviews(q,a,b)
        self.assertEqual(report["agreement_count"],1)
        self.assertEqual(report["human_adjudicated_gold_count"],0)
        self.assertFalse(report["declarations_externally_authenticated_by_this_tool"])
        self.assertEqual(report["status"],"REVIEW_COMPARISON_ONLY_NOT_GOLD")

    def test_conflicting_arms_must_not_be_auto_adjudicated(self):
        q=fake_queue()
        a=completed_review(q,"a",accepted=True)
        b=completed_review(q,"b",accepted=True)
        b["records"][0]["verified_fields"]["comparator"]="different treatment"
        result=compare_reviews(q,a,b)
        self.assertEqual(result["disagreement_count"],1)
        self.assertTrue(result["items"][0]["requires_human_adjudication"])
        self.assertEqual(result["human_adjudicated_gold_count"],0)

    def test_same_reviewer_pseudonym_must_fail(self):
        q=fake_queue()
        a=completed_review(q,"Reviewer-A")
        b=completed_review(q,"reviewer-a")
        with self.assertRaises(ValueError):
            compare_reviews(q,a,b)

    def test_review_must_check_safety_negative_results_and_methods(self):
        q=fake_queue()
        a=completed_review(q,"a",accepted=True)
        a["records"][0]["harms_review_status"]="PENDING"
        with self.assertRaises(ValueError):
            validate_review(q,a)
        a=completed_review(q,"a",accepted=True)
        a["records"][0]["verified_fields"]["source_checked"]=False
        with self.assertRaises(ValueError):
            validate_review(q,a)

    def test_source_and_study_family_mismatch_rejected(self):
        q=fake_queue()
        a=completed_review(q,"a",accepted=True)
        a["records"][0]["verified_fields"]["doi"]="10.0000/unrelated"
        with self.assertRaises(ValueError):
            validate_review(q,a)
        a=completed_review(q,"a",accepted=True)
        a["records"][0]["verified_fields"]["study_family_id"]="NCT87654321"
        with self.assertRaises(ValueError):
            validate_review(q,a)

    def test_wrong_ci_or_missing_denominator_rejected(self):
        q=fake_queue()
        a=completed_review(q,"a",accepted=True)
        a["records"][0]["verified_fields"]["ci_lower"]=0.99
        with self.assertRaises(ValueError):
            validate_review(q,a)
        a=completed_review(q,"a",accepted=True)
        a["records"][0]["verified_fields"]["analysis_denominator"]=""
        with self.assertRaises(ValueError):
            validate_review(q,a)

    def test_hash_blocks_using_revised_set_as_old_reference(self):
        q=fake_queue()
        a=completed_review(q,"a")
        updated=copy.deepcopy(q)
        updated["candidate_set_sha256"]="abcdef"+q["candidate_set_sha256"][6:]
        with self.assertRaises(ValueError):
            validate_review(updated,a)

    def test_unknown_or_duplicate_reviews_rejected(self):
        q=fake_queue()
        a=completed_review(q,"a")
        a["records"].append(copy.deepcopy(a["records"][0]))
        with self.assertRaises(ValueError):
            validate_review(q,a)
        a=completed_review(q,"a")
        a["records"][0]["claim_id"]="unknown paper"
        with self.assertRaises(ValueError):
            validate_review(q,a)

    def test_unsupported_and_unverifiable_cannot_contain_accepted_fields(self):
        q=fake_queue()
        a=completed_review(q,"a")
        a["records"][0]["verified_fields"]={"estimate":0.82}
        with self.assertRaises(ValueError):
            validate_review(q,a)


if __name__=="__main__":
    unittest.main()

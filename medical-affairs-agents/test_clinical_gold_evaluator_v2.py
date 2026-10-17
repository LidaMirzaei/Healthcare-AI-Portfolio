"""Synthetic-only checks for v2 gold scoring, no medical authority implied."""
import copy
import unittest
from clinical_gold_evaluator_v2 import metrics, verify_gold, numeric_match

def reference(measure="HR",single=False):
    return {
        "claim_id":"FICTIONAL-CLAIM",
        "study_family_id":"NCT12345678",
        "pmid":"99990001",
        "endpoint":"PFS" if not single else "ORR",
        "measure":"percent" if single else measure,
        "estimate":62.1 if single else 0.79,
        "ci_level":95.01 if not single else 90,
        "ci_lower":48.4 if single else 0.64,
        "ci_upper":74.5 if single else 0.98,
        "intervention":"fictional therapy A",
        "comparator":None if single else "fictional therapy B",
        "study_design":"single_arm" if single else "randomized",
        "population":"simulated adult study group",
        "analysis_cutoff":"2030-01-01",
        "analysis_denominator":"n=100 in primary analysis",
        "endpoint_hierarchy":"primary",
        "source_url":"https://pubmed.ncbi.nlm.nih.gov/99990001/",
        "source_locator":"Results section - p4",
        "reviewer_ids":["reviewer-a","reviewer-b"],
        "adjudicated":True,"source_checked":True,
        "external_review_reference":"INTERNAL_ORGANIZATION_SIGNOFF_FIXTURE_NOT_REAL"
    }

def predictions(ref=None):
    r=ref or reference()
    return [{"pmid":r["pmid"],"status":"EFFECT_CANDIDATES_UNVERIFIED",
             "candidates":[{
                 "status":"NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED",
                 "endpoint":r["endpoint"],"measure":r["measure"],
                 "estimate":r["estimate"],"ci_level":r["ci_level"],
                 "ci_lower":r["ci_lower"],"ci_upper":r["ci_upper"],
                 "intervention":r["intervention"],"comparator":r["comparator"],
                 "population":r["population"],
                 "analysis_cutoff":r["analysis_cutoff"],
                 "analysis_denominator":r["analysis_denominator"],
                 "endpoint_hierarchy":r["endpoint_hierarchy"],
                 "source_locator":r["source_locator"],
                 "source_url":r["source_url"],
                 "source_context_verified":True
             }]}]


class StrictGoldMetricsTests(unittest.TestCase):
    def test_abstract_only_pubmed_articles_do_not_need_pmcid(self):
        r=reference()
        p=predictions(r)
        result=metrics([r],p)
        self.assertEqual(result["numeric_tuple"]["tp"],1)
        self.assertEqual(result["strict_clinical_context"]["tp"],1)
        self.assertTrue(result["qualified_independence_and_real_gold_not_cryptographically_authenticated"])

    def test_single_arm_response_has_no_invented_comparator(self):
        r=reference(single=True)
        scored=metrics([r],predictions(r))
        self.assertEqual(scored["strict_clinical_context"]["tp"],1)
        r["study_design"]="randomized"
        with self.assertRaises(ValueError):verify_gold([r])

    def test_ci_95_01_is_not_same_as_95(self):
        r=reference()
        p=predictions(r)
        p[0]["candidates"][0]["ci_level"]=95
        result=metrics([r],p)
        self.assertEqual(result["numeric_tuple"]["tp"],0)
        self.assertEqual(result["numeric_tuple"]["fn"],1)

    def test_correct_hr_wrong_population_is_not_full_claim(self):
        r=reference()
        p=predictions(r)
        p[0]["candidates"][0]["population"]="wrong subgroup"
        result=metrics([r],p)
        self.assertEqual(result["numeric_tuple"]["tp"],1)
        self.assertEqual(result["strict_clinical_context"]["tp"],0)

    def test_correct_hr_wrong_source_location_is_not_full_claim(self):
        r=reference()
        p=predictions(r)
        p[0]["candidates"][0]["source_locator"]="Discussion rather than Results"
        result=metrics([r],p)
        self.assertEqual(result["strict_clinical_context"]["tp"],0)

    def test_lacking_adjudication_or_reviewers_disables_metrics(self):
        r=reference()
        r["reviewer_ids"]=["same","same"]
        with self.assertRaises(ValueError):metrics([r],predictions(r))
        r=reference();r["adjudicated"]=False
        with self.assertRaises(ValueError):metrics([r],predictions(r))
        with self.assertRaises(ValueError):metrics([],predictions())

    def test_family_leakage_or_unreserved_trial_blocked(self):
        r=reference()
        with self.assertRaises(ValueError):
            metrics([r],predictions(r),training_families=["NCT12345678"])
        with self.assertRaises(ValueError):
            metrics([r],predictions(r),eligible_test_families=["NCT00000000"])

    def test_unsupported_claim_and_duplicates_counted_as_false_positives(self):
        r=reference()
        p=predictions(r)
        p[0]["candidates"].append(copy.deepcopy(p[0]["candidates"][0]))
        result=metrics([r],p)
        self.assertEqual(result["numeric_tuple"]["tp"],1)
        self.assertEqual(result["numeric_tuple"]["fp"],1)
        self.assertEqual(result["numeric_tuple"]["precision"],0.5)

    def test_missing_source_identity_blocks_match(self):
        r=reference()
        p=predictions(r)
        p[0].pop("pmid")
        p[0]["doi"]="10.1234/unrelated"
        self.assertEqual(metrics([r],p)["numeric_tuple"]["tp"],0)

    def test_source_identity_conflict_even_if_pmid_correct(self):
        r=reference();r["doi"]="10.5555/real"
        p=predictions(r)
        p[0]["doi"]="10.5555/wrong"
        self.assertFalse(numeric_match(r,dict(p[0]["candidates"][0],pmid="99990001",doi="10.5555/wrong")))

    def test_zero_predictions_count_missed_gold(self):
        r=reference()
        scored=metrics([r],[{"pmid":"99990001","status":"BLOCKED_LICENSE_REVIEW_REQUIRED","candidates":[]}])
        self.assertEqual(scored["numeric_tuple"]["fn"],1)
        self.assertEqual(scored["blocked_source_count"],1)
        self.assertIsNone(scored["numeric_tuple"]["precision"])

    def test_source_verification_flag_required_for_full_context(self):
        r=reference();p=predictions(r)
        p[0]["candidates"][0]["source_context_verified"]=False
        self.assertEqual(metrics([r],p)["strict_clinical_context"]["tp"],0)

if __name__=="__main__":
    unittest.main()

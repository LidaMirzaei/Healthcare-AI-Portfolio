"""Offline synthetic gold-data tests — no real patient or licensed study text."""
import copy
import unittest
from clinical_gold_evaluator import (validate_gold, evaluate, same_numeric_tuple,
                                     same_complete_claim)

def truth():
    return {"claim_id":"dummy-gold-1","pmcid":"PMC99990001",
            "study_family_id":"NCT12345678","endpoint":"PFS","measure":"HR",
            "estimate":0.82,"ci_level":90,"ci_lower":0.68,"ci_upper":0.97,
            "intervention":"fictional drug A","comparator":"fictional drug B",
            "population":"simulated adults","analysis_cutoff":"2030-01-01",
            "source_url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC99990001/#r1",
            "reviewer_1":"reviewer-A","reviewer_2":"reviewer-B",
            "adjudicated":True,"source_checked":True}

def prediction():
    return {"pmcid":"PMC99990001","status":"EFFECT_CANDIDATES_UNVERIFIED",
            "candidates":[{
                "status":"NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED",
                "source_url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC99990001/#r1",
                "endpoint":"PFS","measure":"HR","estimate":0.82,
                "ci_level":90,"ci_lower":0.68,"ci_upper":0.97,
                "source_context_verified":False,
            }]}

class ScientificMetricsTests(unittest.TestCase):
    def test_correct_numbers_not_equivalent_to_clinical_claim(self):
        result=evaluate([truth()],[prediction()])
        self.assertEqual(result["numeric_tuple_only"]["tp"],1)
        self.assertEqual(result["numeric_tuple_only"]["recall"],1.0)
        self.assertEqual(result["full_clinical_context_and_citation"]["tp"],0)
        self.assertEqual(result["full_clinical_context_and_citation"]["recall"],0.0)
        self.assertFalse(result["benchmark_minimum_for_accuracy_reporting_reached"])
    def test_context_verified_requires_complete_exact_arms_and_population(self):
        p=prediction();c=p["candidates"][0]
        g=truth()
        for field in ("intervention","comparator","population","analysis_cutoff"):
            c[field]=g[field]
        c["source_context_verified"]=True
        self.assertEqual(evaluate([g],[p])["full_clinical_context_and_citation"]["tp"],1)
        c["comparator"]="different arm"
        self.assertEqual(evaluate([g],[p])["full_clinical_context_and_citation"]["tp"],0)
    def test_pfs_cannot_match_os_even_numbers_same(self):
        g=truth();g["endpoint"]="OS"
        r=evaluate([g],[prediction()])
        self.assertEqual(r["numeric_tuple_only"]["tp"],0)
    def test_ci_level_difference_must_fail(self):
        p=prediction();p["candidates"][0]["ci_level"]=95
        self.assertEqual(evaluate([truth()],[p])["numeric_tuple_only"]["fn"],1)
    def test_missing_reviewer_blocks_metrics(self):
        g=truth();g["reviewer_2"]=g["reviewer_1"]
        with self.assertRaises(ValueError):evaluate([g],[prediction()])
    def test_unadjudicated_gold_blocks(self):
        g=truth();g["adjudicated"]=False
        with self.assertRaises(ValueError):evaluate([g],[prediction()])
    def test_no_gold_blocks_any_accuracy(self):
        with self.assertRaises(ValueError):evaluate([],[prediction()])
    def test_study_family_leakage_blocks(self):
        with self.assertRaises(ValueError):
            evaluate([truth()],[prediction()],train_families=["NCT12345678"])
    def test_missing_source_never_counted(self):
        p=prediction();p["candidates"][0].pop("source_url")
        with self.assertRaises(ValueError):evaluate([truth()],[p])
    def test_duplicate_prediction_does_not_inflate_score(self):
        r=evaluate([truth()],[prediction(),copy.deepcopy(prediction())]) if False else None
        with self.assertRaises(ValueError):
            evaluate([truth()],[prediction(),prediction()])
        p=prediction()
        p["candidates"].append(copy.deepcopy(p["candidates"][0]))
        scored=evaluate([truth()],[p])
        self.assertEqual(scored["numeric_tuple_only"]["tp"],1)
        self.assertEqual(scored["numeric_tuple_only"]["fp"],1)
        self.assertEqual(scored["numeric_tuple_only"]["precision"],0.5)
    def test_abstention_counts_and_recall_failure(self):
        p=prediction();p["candidates"][0]["status"]="ABSTAIN_ENDPOINT_NOT_SUPPORTED"
        r=evaluate([truth()],[p])
        self.assertEqual(r["abstentions_n"],1)
        self.assertEqual(r["numeric_tuple_only"]["fn"],1)
        self.assertIsNone(r["numeric_tuple_only"]["precision"])
    def test_blocked_article_must_not_include_candidates(self):
        p=prediction();p["status"]="BLOCKED_LICENSE_REVIEW_REQUIRED"
        with self.assertRaises(ValueError):evaluate([truth()],[p])
    def test_wrong_source_is_not_full_context_even_with_matching_tuple(self):
        g=truth();p=prediction()
        c=p["candidates"][0];c.update({
            "intervention":g["intervention"],"comparator":g["comparator"],
            "population":g["population"],"analysis_cutoff":g["analysis_cutoff"],
            "source_context_verified":True,"source_url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC99990001/#wrong"})
        r=evaluate([g],[p])
        self.assertEqual(r["numeric_tuple_only"]["tp"],1)
        self.assertEqual(r["full_clinical_context_and_citation"]["tp"],0)

if __name__=="__main__":
    unittest.main()

"""Fully synthetic scorer tests; DOES NOT import any frozen trial answers."""
import copy
import unittest
from evaluate_pubmed_shadow_v5 import score,render

def fixture():
    frozen={
        "status":"PUBLIC_ORIGINAL_ABSTRACT_ASSISTANT_SPOTCHECK_NOT_MEDICAL_GOLD",
        "training_families":["NCT00000001"],
        "reserved_v4_families_excluded":["NCT00000002"],
        "studies":[{
            "trial":"Imaginary Study A","nct":"NCT88881111",
            "pmid":"99992222","doi":"10.6666/fake",
            "source":"https://pubmed.ncbi.nlm.nih.gov/99992222/",
            "expected":[{"endpoint":"OS","measure":"HR","estimate":0.92,
                         "ci_level":95,"ci_lower":0.78,"ci_upper":1.08,
                         "scope":"imaginary overall study"}]
        }],
    }
    pred={"articles":[{
        "pmid":"99992222","doi":"10.6666/fake",
        "source_status":"ABSTRACT_RESULTS_ONLY",
        "candidates":[{
            "endpoint":"OS","measure":"HR","estimate":0.92,
            "ci_level":95,"ci_lower":0.78,"ci_upper":1.08,
            "status":"SOURCE_NUMERIC_TUPLE_CANDIDATE_REVIEW_REQUIRED"
        }],
        "abstentions":[]
    }]}
    return pred,frozen

class ShadowMetricsTests(unittest.TestCase):
    def test_exact_match_not_gold(self):
        p,f=fixture()
        s=score(p,f)
        self.assertEqual(s["exact_numeric_tuple_pairs_matched"],1)
        self.assertEqual(s["medically_adjudicated_claims"],0)
        self.assertTrue(s["statistical_clinical_precision_unmeasured"])
        self.assertIn("NOT clinical accuracy",render(s))
    def test_wrong_ci_level_is_miss(self):
        p,f=fixture()
        p["articles"][0]["candidates"][0]["ci_level"]=99
        self.assertEqual(score(p,f)["unmatched_predeclared_pairs"],1)
    def test_wrong_endpoint_is_miss(self):
        p,f=fixture()
        p["articles"][0]["candidates"][0]["endpoint"]="PFS"
        self.assertEqual(score(p,f)["exact_numeric_tuple_pairs_matched"],0)
    def test_duplicated_candidate_not_two_successes(self):
        p,f=fixture()
        p["articles"][0]["candidates"].append(copy.deepcopy(p["articles"][0]["candidates"][0]))
        r=score(p,f)
        self.assertEqual(r["exact_numeric_tuple_pairs_matched"],1)
        self.assertEqual(r["source_candidate_count_all"],2)
    def test_wrong_original_doi_does_not_match(self):
        p,f=fixture()
        p["articles"][0]["doi"]="10.7777/unrelated"
        self.assertEqual(score(p,f)["exact_numeric_tuple_pairs_matched"],0)
        self.assertEqual(score(p,f)["source_records_verified"],0)
    def test_study_family_leakage_blocks(self):
        p,f=fixture()
        f["training_families"].append(f["studies"][0]["nct"])
        with self.assertRaises(ValueError):score(p,f)
    def test_reserved_family_leakage_blocks(self):
        p,f=fixture()
        f["reserved_v4_families_excluded"].append(f["studies"][0]["nct"])
        with self.assertRaises(ValueError):score(p,f)
    def test_duplicate_source_must_fail(self):
        p,f=fixture()
        p["articles"].append(copy.deepcopy(p["articles"][0]))
        with self.assertRaises(ValueError):score(p,f)
    def test_unidentified_source_cannot_pass(self):
        p,f=fixture()
        p["articles"][0]["source_status"]="BLOCKED_ORIGINAL_PUBMED_MISSING"
        self.assertEqual(score(p,f)["source_records_verified"],0)

if __name__=="__main__":
    unittest.main()

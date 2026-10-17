"""Synthetic V6 source evaluation tests; never use frozen V6 facts here."""
import copy
import unittest
from evaluate_pubmed_shadow_v6 import run_check,to_markdown

def state():
    frozen={
        "status":"PUBLIC_SOURCE_SPOTCHECK_NOT_QUALIFIED_GOLD",
        "no_medical_gold":True,
        "sources":[{"pmid":"99991111","trial_id":"NCT11112222",
                   "name":"Imaginary trial","doi":"10.7777/dummy",
                   "source":"https://pubmed.ncbi.nlm.nih.gov/99991111/",
                   "expected":[{"endpoint":"PFS","measure":"HR","estimate":0.69,
                      "ci_level":99,"ci_lower":0.51,"ci_upper":0.87}],
                   "no_assumed_CI_controls":[{"measure":"HR","estimate":0.80,
                   "reason":"Fictional ratio with unlabeled interval"}]}],
    }
    extracted={"articles":[{
        "pmid":"99991111","doi":"10.7777/dummy",
        "source_status":"ORIGINAL_PUBMED_XML_RESULTS_TAGGED",
        "candidates":[{"endpoint":"PFS","measure":"HR","estimate":0.69,
             "ci_level":99,"ci_lower":0.51,"ci_upper":0.87,
             "status":"SOURCE_NUMERIC_TUPLE_CANDIDATE_REVIEW_REQUIRED"}],
        "abstentions":[{"status":"ABSTAIN_NO_UNIQUE_ATTACHED_CI"}]}]}
    return extracted,frozen

class V6SourceTests(unittest.TestCase):
    def test_tuple_and_abstention_source_only(self):
        p,g=state()
        r=run_check(p,g)
        self.assertEqual(r["tuples_matched"],1)
        self.assertEqual(r["no_fabricated_ci_controls_passed"],1)
        self.assertEqual(r["expert_medical_gold_claims"],0)
        self.assertFalse(r["clinical_accuracy_measured"])
        self.assertIn("Not expert gold",to_markdown(r))
    def test_wrong_confidence_level_causes_miss(self):
        p,g=state()
        p["articles"][0]["candidates"][0]["ci_level"]=95
        self.assertEqual(run_check(p,g)["tuples_not_matched"],1)
    def test_fabricated_ci_for_unlabeled_estimate_fails(self):
        p,g=state()
        z=copy.deepcopy(p["articles"][0]["candidates"][0])
        z["estimate"]=0.80
        p["articles"][0]["candidates"].append(z)
        self.assertEqual(run_check(p,g)["no_fabricated_ci_controls_passed"],0)
    def test_wrong_doi_does_not_verify(self):
        p,g=state();p["articles"][0]["doi"]="10.0000/else"
        r=run_check(p,g)
        self.assertEqual(r["pubmed_doi_sources_matched"],0)
        self.assertEqual(r["tuples_matched"],0)
    def test_duplicate_trial_source_rejected(self):
        p,g=state()
        g["sources"].append(copy.deepcopy(g["sources"][0]))
        with self.assertRaises(ValueError):run_check(p,g)
    def test_no_spurious_study_could_enter(self):
        p,g=state()
        p["articles"].append(dict(p["articles"][0],pmid="99992222"))
        with self.assertRaises(ValueError):run_check(p,g)

if __name__=="__main__":
    unittest.main()

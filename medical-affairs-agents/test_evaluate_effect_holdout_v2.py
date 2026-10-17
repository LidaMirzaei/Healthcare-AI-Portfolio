"""Evaluator tests use mock labels only; never depend on frozen V2 outcomes."""
import copy
import unittest
from evaluate_effect_holdout_v2 import score


def fake_manifest():
    return {
        "development_family_ids":["NCT_OLD"],
        "references":[
            {"pmcid":"PMC90000001","study_family":"NCT_NEW_ONE",
             "expected":{"kind":"numeric","endpoint":"PFS","measure":"HR",
                         "estimate":0.77,"ci_level":90,"ci_lower":0.61,"ci_upper":0.89}},
            {"pmcid":"PMC90000002","study_family":"NCT_NEW_TWO",
             "expected":{"kind":"license_block"}},
        ],
    }


class MetricTest(unittest.TestCase):
    def test_true_candidate_requires_exact_ci_level(self):
        expected={
            "pmcid":"PMC90000001",
            "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC90000001/",
            "status":"EFFECT_CANDIDATES_REVIEW_REQUIRED",
            "candidates":[{
                "status":"SOURCE_EFFECT_CANDIDATE_REVIEW_REQUIRED",
                "endpoint":"PFS","measure":"HR","point":0.77,
                "ci_level":90,"ci_lower":0.61,"ci_upper":0.89,
                "source_url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC90000001/"
            }],
        }
        blocked={"pmcid":"PMC90000002","status":"BLOCKED_LICENSE_REVIEW_REQUIRED",
                 "license":{"status":"BLOCKED_LICENSE_NOT_APPROVED"},"candidates":[]}
        metric=score([expected,blocked],fake_manifest())
        self.assertEqual(metric["correct_checks"],2)
        self.assertTrue(metric["clinical_precision_recall_not_measured"])
        wrong=copy.deepcopy(expected)
        wrong["candidates"][0]["ci_level"]=95
        metric=score([wrong,blocked],fake_manifest())
        self.assertEqual(metric["correct_checks"],1)

    def test_design_negative_control_failure_is_reported(self):
        scorecard=score([{"pmcid":"PMC90000002","status":"EFFECT_CANDIDATES_REVIEW_REQUIRED",
                          "license":{"status":"CC_BY_OR_CC0_CONFIRMED"},"candidates":[]}],
                        fake_manifest())
        self.assertEqual(scorecard["correct_checks"],0)

    def test_family_leakage_or_duplicate_is_error(self):
        manifest=fake_manifest()
        manifest["development_family_ids"]=["NCT_NEW_ONE"]
        with self.assertRaises(ValueError):
            score([],manifest)
        manifest=fake_manifest()
        manifest["references"][1]["study_family"]="NCT_NEW_ONE"
        with self.assertRaises(ValueError):
            score([],manifest)


if __name__=="__main__":
    unittest.main()

"""Adversarial synthetic abstract tests; never reuse clinical holdout scores."""
import unittest
from abstract_statistic_verifier import verify_local_result as check

BASE=dict(measure="HR",estimate=0.63,ci_level=95,ci_lower=0.52,
          ci_upper=0.76,endpoint="PFS")
def audit(text,**changes):
    return check(text,**{**BASE,**changes})

class LocalityTests(unittest.TestCase):
    def test_correct_same_context_ratio_ci(self):
        x=audit("Results: PFS by central review favored agent A (hazard ratio, "
                "0.63; 95% CI, 0.52 to 0.76; P < 0.001).")
        self.assertEqual(x["status"],"TUPLE_AND_ENDPOINT_CONTEXT_LOCATED_REVIEW_REQUIRED")
        self.assertTrue(x["matched"])
    def test_different_paragraph_numbers_do_not_pass(self):
        x=audit("Progression-free survival was investigated. "
                "Baseline BMI was 0.63, and age percentiles were 0.52 to 0.76. "
                "The unrelated OS analysis reported HR 0.88 (95% CI 0.52–0.76).")
        self.assertFalse(x["matched"])
    def test_matching_ratio_wrong_ci_does_not_pass(self):
        x=audit("PFS HR 0.63 (95% CI 0.41-0.70); "
                "unrelated OS HR 0.99 (95% CI 0.52-0.76).")
        self.assertEqual(x["status"],"POINT_CI_NOT_COLOCATED_OR_NOT_PRESENT")
    def test_wrong_endpoint_is_context_warning_not_verified(self):
        x=audit("An exploratory OS outcome had hazard ratio 0.63 "
                "(95% CI 0.52-0.76).")
        self.assertEqual(x["status"],"TUPLE_LOCATED_ENDPOINT_UNCONFIRMED")
        self.assertEqual(x["endpoint_bound_candidate_count"],0)
    def test_99_percent_pfs_and_95_01_percent_os(self):
        txt=("Median PFS was 10.8 months with experimental therapy and 5.6 months "
             "with chemotherapy [hazard ratio 0.57 (99% CI 0.44-0.73)]. "
             "Median OS was 23.7 months and 18.7 months, respectively "
             "[hazard ratio 0.79 (95.01% CI 0.64-0.98)].")
        p=check(txt,measure="HR",estimate=0.57,ci_level=99,
                ci_lower=0.44,ci_upper=0.73,endpoint="PFS")
        s=check(txt,measure="HR",estimate=0.79,ci_level=95.01,
                ci_lower=0.64,ci_upper=0.98,endpoint="OS")
        self.assertEqual(p["endpoint_bound_candidate_count"],1)
        self.assertEqual(s["endpoint_bound_candidate_count"],1)
        wrong=check(txt,measure="HR",estimate=0.79,ci_level=95,
                ci_lower=0.64,ci_upper=0.98,endpoint="OS")
        self.assertFalse(wrong["matched"])
    def test_observed_response_with_ci(self):
        x=check("The objective response rate (ORR) was 62.1% "
                "(95% confidence interval (CI): 48.4-74.5).",
                measure="percent",estimate=62.1,ci_level=95,
                ci_lower=48.4,ci_upper=74.5,endpoint="ORR")
        self.assertEqual(x["status"],"TUPLE_AND_ENDPOINT_CONTEXT_LOCATED_REVIEW_REQUIRED")
    def test_unreported_ci_never_guessed(self):
        x=check("PFS was improved (hazard ratio 0.51).",
                measure="HR",estimate=0.51,ci_level=None,
                ci_lower=None,ci_upper=None,endpoint="PFS")
        self.assertEqual(x["status"],"POINT_ONLY_CI_NOT_REPORTED_REVIEW_REQUIRED")
        self.assertFalse(x["matched"])
    def test_do_not_accept_os_for_pfs(self):
        x=audit("A separate overall survival (OS) result had "
                "HR 0.63 (95% CI 0.52-0.76).")
        self.assertFalse(x["endpoint_bound_candidate_count"])
    def test_no_partial_number(self):
        x=audit("PFS HR 10.63 (95% CI 0.52-0.76).")
        self.assertFalse(x["matched"])
    def test_original_trial_hazard_ratio_for_progression_or_death(self):
        x=audit("The median progression-free survival was longer with drug A "
                "(hazard ratio for disease progression or death from any cause, "
                "0.63; 95% CI, 0.52 to 0.76).")
        self.assertEqual(x["endpoint_bound_candidate_count"],1)

    def test_original_trial_hr_alias_in_parentheses(self):
        x=audit("In patients with PFS events, the hazard ratio (HR), "
                "0.63 [95% confidence interval (CI), 0.52 to 0.76].")
        self.assertEqual(x["full_local_tuple_count"],1)

    def test_invasive_disease_free_survival_not_mislabeled_dfs(self):
        x=check("Patients with invasive disease-free survival events "
                "(hazard ratio, 0.47; 95% CI 0.34 to 0.66).",
                measure="HR",estimate=0.47,ci_level=95,
                ci_lower=0.34,ci_upper=0.66,endpoint="iDFS")
        self.assertEqual(x["endpoint_bound_candidate_count"],1)
        y=check("Patients with invasive disease-free survival events "
                "(hazard ratio, 0.47; 95% CI 0.34 to 0.66).",
                measure="HR",estimate=0.47,ci_level=95,
                ci_lower=0.34,ci_upper=0.66,endpoint="DFS")
        self.assertEqual(y["endpoint_bound_candidate_count"],0)

    def test_missing_sources_never_are_clinically_verified(self):
        x=audit("PFS hazard ratio 0.63 (95% confidence interval, 0.52–0.76)")
        self.assertIs(x["human_adjudicated"],False)
        self.assertIs(x["clinical_context_verified"],False)

if __name__=="__main__":
    unittest.main()

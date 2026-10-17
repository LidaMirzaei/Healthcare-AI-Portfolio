"""Offline synthetic stress tests: never tuned on frozen clinical holdout labels."""
import unittest
from clinical_effects import (
    extract_article, analyze_sentence, detect_endpoint, design_from_title,
    render, compact,
)


def article(title="Example randomized phase 3 trial",
            body="Results", paragraph=None, license_url="https://creativecommons.org/licenses/by/4.0/"):
    if paragraph is None:
        paragraph = "Progression-free survival HR 0.93 (90% confidence interval 0.66–1.30) for trial arms."
    license_node = (f'<license xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="{license_url}">'
                    '<license-p>Creative Commons Attribution</license-p></license>') if license_url else ""
    return (f"""<article><front><article-meta>
      <article-id pub-id-type="pmc">99887766</article-id>
      <article-id pub-id-type="doi">10.1234/test.fake</article-id>
      <title-group><article-title>{title}</article-title></title-group>
      <abstract><p>In background literature HR 0.10 (95% CI 0.05–0.20).</p></abstract>
      <permissions>{license_node}</permissions>
      </article-meta></front><body>
      <sec><title>{body}</title>
      <p id="results-p1">{paragraph}</p>
      </sec><sec><title>Discussion</title>
      <p id="discussion-p1">Progression-free survival HR 0.10 (95% CI 0.05–0.20) occurred only in a cited other trial.</p>
      </sec></body></article>""").encode()


class EffectExtractionTests(unittest.TestCase):
    def test_preserve_90_percent_interval_not_assume_95(self):
        r=extract_article(article(),"PMC99887766")
        self.assertEqual(r["status"],"EFFECT_CANDIDATES_REVIEW_REQUIRED")
        self.assertEqual(r["accepted_candidate_count"],1)
        c=r["candidates"][0]
        self.assertEqual((c["endpoint"],c["measure"],c["ci_level"],c["point"]),("PFS","HR",90,0.93))
        self.assertEqual((c["ci_lower"],c["ci_upper"]),(0.66,1.30))
        self.assertEqual(c["source_id"],"results-p1")
        self.assertEqual(c["source_id_kind"],"JATS_ID")
        self.assertTrue(c["source_url"].endswith("#results-p1"))
        self.assertFalse(c["arm_assignment_verified"])
        self.assertFalse(c["automated_treatment_recommendation"])

    def test_95_percent_observational_odds_ratio_not_a_treatment_effect(self):
        r=extract_article(article(
            title="Prospective cohort study in breast cancer",
            paragraph="Adjusted odds ratio for pathologic complete response (pCR) OR 0.459, 95% CI 0.289–0.728 based on hormone receptor status."
        ),"PMC99887766")
        self.assertEqual(r["design"],"OBSERVATIONAL_OR_ASSOCIATION")
        self.assertEqual(r["candidates"][0]["endpoint"],"pCR")
        self.assertEqual(r["candidates"][0]["measure"],"OR")
        self.assertEqual(r["candidates"][0]["causal_status"],"ASSOCIATION_NOT_RANDOMIZED_TREATMENT_EFFECT")

    def test_mixed_endpoints_abstain(self):
        r=extract_article(article(paragraph=(
            "Progression-free survival and overall survival shared HR 0.50 (95% CI 0.30–0.70)."
        )),"PMC99887766")
        self.assertEqual(r["candidates"][0]["status"],"ABSTAIN_ENDPOINT_NOT_UNAMBIGUOUS")
        self.assertEqual(r["accepted_candidate_count"],0)

    def test_multiple_subgroup_estimates_abstain(self):
        r=extract_article(article(paragraph=(
            "PFS HR 0.44 (95% CI 0.24–0.81), HR 0.33 (95% CI 0.19–0.56), "
            "and HR 0.36 (95% CI 0.13–0.98) for high, medium and low expression."
        )),"PMC99887766")
        self.assertEqual(r["candidates"][0]["status"],"ABSTAIN_MULTIPLE_OR_MISSING_ESTIMATE_OR_CI")
        self.assertEqual(r["accepted_candidate_count"],0)

    def test_no_ci_abstains(self):
        r=extract_article(article(paragraph="Progression-free survival HR 0.70 was observed in the subgroup."),
                          "PMC99887766")
        self.assertEqual(r["candidates"][0]["status"],"ABSTAIN_MULTIPLE_OR_MISSING_ESTIMATE_OR_CI")

    def test_impossible_ci_abstains(self):
        r=extract_article(article(paragraph="Progression-free survival HR 0.93 (95% CI 1.01–1.20) with full data."),
                          "PMC99887766")
        self.assertEqual(r["candidates"][0]["status"],"ABSTAIN_INVALID_CI_OR_POINT")

    def test_restricted_license_blocks_before_numeric_extraction(self):
        r=extract_article(article(license_url="https://creativecommons.org/licenses/by-nc-nd/4.0/"),
                          "PMC99887766")
        self.assertEqual(r["status"],"BLOCKED_LICENSE_REVIEW_REQUIRED")
        self.assertFalse(r["candidates"])

    def test_no_license_blocks(self):
        r=extract_article(article(license_url=""),"PMC99887766")
        self.assertEqual(r["status"],"BLOCKED_LICENSE_REVIEW_REQUIRED")

    def test_background_and_discussion_never_pass(self):
        r=extract_article(article(paragraph="Results contain no numerical estimates in the studied population."),
                          "PMC99887766")
        self.assertEqual(r["accepted_candidate_count"],0)
        self.assertFalse(r["candidates"])

    def test_source_id_does_not_fake_publisher_anchor(self):
        fake=article().replace(b' id="results-p1"',b'')
        r=extract_article(fake,"PMC99887766")
        c=r["candidates"][0]
        self.assertEqual(c["source_id_kind"],"INTERNAL_ONLY")
        self.assertFalse("#" in c["source_url"])

    def test_wrong_pmc_identity_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_article(article().replace(b"99887766",b"11111111"),"PMC99887766")

    def test_no_auto_pooled_report(self):
        r=extract_article(article(),"PMC99887766")
        self.assertIn("NOT clinical evidence validation",render([r],1.0))
        self.assertIn("review_status" if False else "HUMAN_SCIENTIFIC_REVIEW_REQUIRED",
                      str(r["candidates"]))
        self.assertNotIn("proves increased survival",render([r],1.0))

    def test_endpoint_detector_conservative(self):
        self.assertEqual(detect_endpoint("OS and PFS HR 0.70","Results"),"AMBIGUOUS_MULTIPLE_ENDPOINTS")
        self.assertEqual(detect_endpoint("HR 0.70","Results / PFS"),"PFS")
        self.assertEqual(detect_endpoint("HR 0.70","Results"),"ENDPOINT_UNSPECIFIED")


if __name__=="__main__":
    unittest.main()

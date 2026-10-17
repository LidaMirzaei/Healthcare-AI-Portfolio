"""V3 development-unit tests use fully synthetic studies only, not frozen V3 gold."""
import unittest
from clinical_effects_v3 import extract_v3, mine_sentence, article_kind


def sample(title="Multicentre randomized trial of a hypothetical therapy",
           paragraph="The progression-free survival HR 0.77 (90% confidence interval 0.60–0.89) favored arm A.",
           abstract="The results demonstrated progression-free survival HR 0.77 (90% CI 0.60–0.89).",
           license_uri="http://creativecommons.org/licenses/by/4.0/",
           heading="Results"):
    license_tag=(f'<license xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="{license_uri}">'
                 '<license-p>CC BY 4.0</license-p></license>') if license_uri else ""
    return f"""<article><front><article-meta>
     <article-id pub-id-type="pmc">77777777</article-id>
     <article-id pub-id-type="doi">10.1234/synthetic.v3</article-id>
     <title-group><article-title>{title}</article-title></title-group>
     <abstract><p>{abstract}</p></abstract>
     <permissions>{license_tag}</permissions>
     </article-meta></front><body><sec><title>{heading}</title>
     <p id="r-test">{paragraph}</p></sec><sec><title>Discussion</title>
     <p>Random other trial had overall survival HR 0.22 (95% CI 0.10–0.33).</p>
     </sec></body></article>""".encode()


class GeneralExtractionTests(unittest.TestCase):
    def test_90_percent_tiered_and_de_duplicated(self):
        d=extract_v3(sample(),"PMC77777777")
        found=[x for x in d["candidates"] if x["status"]=="NUMERIC_SOURCE_CANDIDATE_NOT_CLINICALLY_VALIDATED"]
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["endpoint"],"PFS")
        self.assertEqual(found[0]["ci_level"],90)
        self.assertEqual(found[0]["source_level"],"FULLTEXT_RESULTS")
        self.assertFalse(found[0]["arm_assignment_verified"])

    def test_multiple_odds_ratios_each_get_own_ci(self):
        d=extract_v3(sample(
           title="International prospective cohort study in breast oncology",
           paragraph="Adjusted pathological complete response OR 0.41 (95% CI 0.24–0.60), and OR 0.68 (95% CI 0.44–0.90) in separate biomarkers.",
           abstract="Prospective cohort research."),
           "PMC77777777")
        values=[c["estimate"] for c in d["candidates"] if "estimate" in c]
        self.assertEqual(values,[0.41,0.68])
        self.assertTrue(all(c.get("causal_interpretation")=="OBSERVATIONAL_ASSOCIATION_ONLY"
                            for c in d["candidates"] if "estimate" in c))
        self.assertTrue(all(c["multiple_effects_in_sentence"] for c in d["candidates"]))

    def test_arm_confidence_interval_preceding_hr_not_mismatched(self):
        d=extract_v3(sample(paragraph=(
             "Overall survival was 84% (95% CI 76–90) vs 71% (95% CI 68–79); "
             "HR 0.76 (95% CI 0.59–0.92) in the analysis."
        )),"PMC77777777")
        c=next(c for c in d["candidates"] if "estimate" in c)
        self.assertEqual((c["estimate"],c["ci_lower"],c["ci_upper"]),(0.76,0.59,0.92))

    def test_abstract_only_candidate_is_explicitly_labeled(self):
        d=extract_v3(sample(paragraph="Safety follow-up included patients in the Results section.",
                abstract="The overall survival HR 0.81 (95% confidence interval 0.70–0.94)."),
                "PMC77777777")
        c=next(c for c in d["candidates"] if "estimate" in c)
        self.assertEqual(c["source_level"],"ABSTRACT_RESULTS_ONLY")

    def test_no_discussion_citation_as_primary_result(self):
        d=extract_v3(sample(paragraph="The Results section describes recruitment counts only.",
                 abstract="Background included no analyzed outcome."),
                "PMC77777777")
        self.assertFalse(any(c.get("estimate")==0.22 for c in d["candidates"]))

    def test_protocol_without_results_blocks(self):
        d=extract_v3(sample(title="A randomized clinical study protocol",
                             heading="Methods",
                             paragraph="This protocol will collect PFS at the final analysis.",
                             abstract="A trial is planned."),
                     "PMC77777777")
        self.assertEqual(d["status"],"BLOCKED_NO_OBSERVED_FULLTEXT_RESULTS")

    def test_review_not_original_trial(self):
        d=extract_v3(sample(title="Systematic review and network meta-analysis of trials"),
                     "PMC77777777")
        self.assertEqual(d["status"],"BLOCKED_SECONDARY_SYNTHESIS_AS_PRIMARY_STUDY")

    def test_license_rights_block(self):
        d=extract_v3(sample(license_uri="https://creativecommons.org/licenses/by-nc/4.0/"),
                     "PMC77777777")
        self.assertEqual(d["status"],"BLOCKED_LICENSE_REVIEW_REQUIRED")
        self.assertFalse(d["candidates"])

    def test_multiple_endpoints_not_laundered(self):
        d=extract_v3(sample(paragraph="PFS and OS HR 0.90 (95% CI 0.80–1.00) in one ambiguous model."),
                     "PMC77777777")
        self.assertEqual(d["matched_effect_count"],0)
        self.assertGreaterEqual(d["abstained_effect_count"],1)

    def test_article_design_not_assumed_from_review(self):
        self.assertEqual(article_kind("A network meta-analysis",""),"SECONDARY_REVIEW_NOT_NEW_TRIAL")


if __name__=="__main__":
    unittest.main()

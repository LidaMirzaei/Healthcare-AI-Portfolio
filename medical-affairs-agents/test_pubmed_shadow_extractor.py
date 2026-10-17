"""Entirely fictional source-text tests. No frozen V5 labels imported."""
import unittest
from unittest.mock import patch
from pubmed_shadow_extractor import (
    get_results_only,ratio_effects,interpret_original_record,
    collect,risk_language
)

def stub(text,pmid="99991111",doi="10.7777/fictional.v1"):
    return {"id":pmid,"source":"MED","doi":doi,
            "title":"Original randomized synthetic breast oncology study",
            "abstractText":text}

class GoldBlindPubMedTests(unittest.TestCase):
    def test_background_hr_cannot_be_assigned_to_new_trial(self):
        t=("Background: Earlier study PFS HR 0.21 (95% CI 0.11-0.43). "
           "Methods: We randomized adults. "
           "Results: Median PFS 5 months. "
           "Conclusions: The study is complete.")
        v=interpret_original_record("99991111",stub(t))
        self.assertEqual(v["candidates"],[])
        self.assertFalse(v["raw_abstract_saved"])

    def test_unstructured_no_results_heading_must_abstain(self):
        t="Participants were randomized and the PFS hazard ratio was 0.50; 95% CI 0.40-0.60."
        results,status=get_results_only(t)
        self.assertEqual(results,"")
        self.assertEqual(status,"ABSTAIN_NO_EXPLICIT_RESULTS_SECTION")

    def test_hazard_ratio_for_progression_and_death(self):
        t=("Results: Median PFS was 9.7 months versus 6.9 months "
           "(stratified hazard ratio for disease progression or death, 0.62; "
           "95% CI, 0.50 to 0.77; P<0.001).")
        v=interpret_original_record("99991111",stub(t))
        self.assertEqual(len(v["candidates"]),1)
        a=v["candidates"][0]
        self.assertEqual((a["endpoint"],a["measure"],a["estimate"]),("PFS","HR",0.62))
        self.assertEqual((a["ci_level"],a["ci_lower"],a["ci_upper"]),(95.,0.50,0.77))
        self.assertFalse(a["clinical_claim_approved"])

    def test_two_hr_in_one_sentence_are_two_not_mixed(self):
        t=("Results: The overall survival (OS) in all participants was "
           "HR 0.92, 95% confidence interval (CI) 0.78-1.08, P=0.32; "
           "and in mutated participants HR 1.05, 95% CI 0.77-1.43.")
        v=interpret_original_record("99991111",stub(t))
        self.assertEqual(len(v["candidates"]),2)
        self.assertEqual([x["endpoint"] for x in v["candidates"]],["OS","OS"])
        self.assertEqual([x["estimate"] for x in v["candidates"]],[0.92,1.05])

    def test_no_linking_ci_from_next_hr(self):
        t=("Results: PFS HR 0.70 and OS HR 0.50 (95% CI 0.40-0.60).")
        v=interpret_original_record("99991111",stub(t))
        self.assertEqual([x["estimate"] for x in v["candidates"]],[0.50])
        self.assertTrue(any(x["status"]=="ABSTAIN_NO_UNIQUE_ATTACHED_CI" for x in v["abstentions"]))

    def test_no_os_from_pfs_background_in_results(self):
        t="Results: Median PFS 4 months (HR 0.50; 95% CI 0.30-0.70)."
        v=interpret_original_record("99991111",stub(t))
        self.assertEqual(v["candidates"][0]["endpoint"],"PFS")

    def test_rare_ci_level_precise(self):
        t="Results: Overall survival OS HR 0.79 (95.01% CI 0.64-0.98)."
        v=interpret_original_record("99991111",stub(t))
        self.assertEqual(v["candidates"][0]["ci_level"],95.01)

    def test_impossible_ci_is_abstention(self):
        t="Results: PFS HR 0.91, 95% CI 1.10-1.50."
        v=interpret_original_record("99991111",stub(t))
        self.assertFalse(v["candidates"])
        self.assertEqual(v["abstentions"][0]["status"],"ABSTAIN_INVALID_CI")

    def test_ratio_without_endpoint_abstains(self):
        t="Results: HR 0.91, 95% CI 0.80-1.05."
        v=interpret_original_record("99991111",stub(t))
        self.assertFalse(v["candidates"])
        self.assertEqual(v["abstentions"][0]["status"],"ABSTAIN_ENDPOINT_UNCERTAIN")

    def test_false_significance_does_not_follow_from_point_estimate(self):
        t=("Results: Overall survival OS HR 0.92, 95% CI 0.78-1.08. "
           "Conclusions: Neither overall survival endpoint met "
           "the prespecified boundary for statistical significance.")
        r=risk_language("Overall survival HR 0.92, 95% CI 0.78-1.08.",t)
        # A text-only warning is not a formal multiplicity interpretation.
        self.assertIsInstance(r,list)

    def test_wrong_original_source_is_rejected(self):
        with self.assertRaises(ValueError):
            interpret_original_record("99991111",stub("Results: PFS HR 0.5 (95% CI 0.4-0.6).",
                                                     doi=""))
        with self.assertRaises(ValueError):
            interpret_original_record("99991111",stub("Results: PFS HR 0.5 (95% CI 0.4-0.6).",
                                                     pmid="88881111"))

    def test_one_network_batch_with_no_gold_in_predictor(self):
        ids=["99991111","99992222"]
        article=("Results: The PFS hazard ratio 0.63 (95% CI 0.52-0.76).")
        fake={i:stub(article,pmid=i) for i in ids}
        with patch("pubmed_shadow_extractor.fetch_pmids_batch",return_value=fake) as batch:
            with patch("pubmed_shadow_extractor.fetch_results_batch",return_value={}):
                value=collect(ids)
        batch.assert_called_once_with(ids)
        self.assertEqual(value["resolved"],2)
        self.assertTrue(all(x["clinical_approval_count"]==0 for x in value["articles"]))
        self.assertNotIn("expected",value)

    def test_original_tagged_results_take_priority_and_exclude_background(self):
        t=("Background: Prior PFS HR 0.01 (95% CI 0.001-0.02). "
           "Results: PFS HR 0.63 (95% CI 0.52-0.76).")
        pubmed_results={"status":"ORIGINAL_PUBMED_XML_RESULTS_TAGGED",
                        "verified_original_pmid":True,
                        "results":"PFS HR 0.63 (95% CI 0.52-0.76)."}
        d=interpret_original_record("99991111",stub(t),pubmed_results)
        self.assertEqual(d["source_status"],"ORIGINAL_PUBMED_XML_RESULTS_TAGGED")
        self.assertEqual([c["estimate"] for c in d["candidates"]],[0.63])

    def test_no_duplicate_trial_entries(self):
        with self.assertRaises(ValueError):
            collect(["99991111","99991111"])

    def test_abstract_not_in_output(self):
        raw="Results: PFS HR 0.63 (95% CI 0.52-0.76)."
        doc=interpret_original_record("99991111",stub(raw))
        self.assertNotIn(raw,str(doc))
        self.assertIn("source_offset_is_url_anchor",str(doc))

if __name__=="__main__":
    unittest.main()

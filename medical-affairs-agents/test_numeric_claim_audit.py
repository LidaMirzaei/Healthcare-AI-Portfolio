import unittest
from numeric_claim_audit import number_present,check_claim,render,audit

DOCUMENT={"pmcid":"PMC_TEST","url":"https://europepmc.org/articles/PMC_TEST",
          "sections":{"results":[{"id":"PMC_TEST-p1","heading":"Results",
                                  "text":"Median progression-free survival was 6.9 versus 4.9 months in the fictional study."}]}}
CLAIM={"id":"demo","pmcid":"PMC_TEST","statement":"Demo numbers 6.9 vs 4.9",
       "numbers":["6.9","4.9"],"concepts":["progression-free survival"]}

class ClaimGateTests(unittest.TestCase):
    def test_valid_source_text_candidate_needs_review(self):
        a=check_claim(CLAIM,DOCUMENT)
        self.assertEqual(a["status"],"SOURCE_TEXT_CANDIDATE_REVIEW_REQUIRED")
        self.assertIn("PMC_TEST-p1",render([a]))
        self.assertIn("6.9 versus 4.9",a["candidates"][0]["verbatim_paragraph"])
    def test_unfound_number_fails_closed(self):
        c=dict(CLAIM,numbers=["6.9","5.9"])
        self.assertEqual(check_claim(c,DOCUMENT)["status"],"NOT_LOCATED_REVIEW_REQUIRED")
    def test_no_partial_numeric_match(self):
        self.assertFalse(number_present("16.9 and 4.91 and 0.6300","6.9"))
        self.assertFalse(number_present("0.6300","0.63"))
        self.assertTrue(number_present("hazard ratio (0.63)","0.63"))
    def test_missing_document(self):
        self.assertEqual(check_claim(CLAIM,None)["status"],"SOURCE_MISSING")
    def test_external_context_never_marked_verified(self):
        x=check_claim({"id":"os","pmcid":None,"statement":"OS elsewhere",
                       "numbers":["18.6"],"concepts":["OS"]},None)
        self.assertEqual(x["status"],"NOT_INGESTED_EXTERNAL_SOURCE")
    def test_sources_are_not_pooled(self):
        self.assertEqual(audit({"PMC_TEST":DOCUMENT},[CLAIM])[0]["id"],"demo")

if __name__=="__main__":
    unittest.main()

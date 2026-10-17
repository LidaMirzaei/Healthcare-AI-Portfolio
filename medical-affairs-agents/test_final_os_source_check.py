import unittest
from final_os_source_check import validate_record,PMID,EXPECTED_DOI

def record(abst,doi=EXPECTED_DOI):
    return {"id":PMID,"doi":doi,
            "title":"Datopotamab deruxtecan versus chemotherapy: final overall survival analysis",
            "abstractText":abst}

class FinalOSSourceTests(unittest.TestCase):
    def test_original_paper_abst_support_only(self):
        a=validate_record(record("The primary overall survival analysis: hazard ratio 1.01 (95% CI 0.83-1.22). "
                                 "There was no statistically significant difference in OS, P = 0.9445."))
        self.assertEqual(a["status"],"ORIGINAL_ARTICLE_ABSTRACT_SUPPORT_REVIEW_REQUIRED")
        self.assertTrue(a["checks"]["no_significant_os"])
        self.assertFalse(a["checks"]["median_os_18_6"])
        self.assertTrue(a["cannot_claim_fulltext_verified"])
    def test_doi_mismatch_is_blocked(self):
        a=validate_record(record("OS hazard ratio 1.01; no statistically significant difference.",doi="10.bad/id"))
        self.assertEqual(a["status"],"BLOCKED_ORIGINAL_ABSTRACT_NOT_SUFFICIENT")
    def test_wrong_hr_blocks(self):
        a=validate_record(record("Overall survival hazard ratio 0.63; no significant difference."))
        self.assertEqual(a["status"],"BLOCKED_ORIGINAL_ABSTRACT_NOT_SUFFICIENT")
    def test_abstract_with_no_os_blocks(self):
        a=validate_record(record("Progression-free survival hazard ratio 1.01."))
        self.assertEqual(a["status"],"BLOCKED_ORIGINAL_ABSTRACT_NOT_SUFFICIENT")

if __name__=="__main__":
    unittest.main()

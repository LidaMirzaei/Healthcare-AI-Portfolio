import unittest
from source_audit import build_audit, render

SAMPLE=b"""<article><front><article-meta><article-id pub-id-type="pmc">PMC_TEST</article-id></article-meta></front><body>
<sec><title>Methods</title><p>Patients from NCT05104866 were randomized to either experimental treatment or chemotherapy.</p></sec>
<sec><title>Results</title><p>Progression-free survival is described; this is not a validated statistical conclusion.</p>
<table-wrap><label>Table 1</label><caption><p>Patient characteristics</p></caption><table><tr><td>10</td></tr></table></table-wrap>
</sec><sec><title>Limitations</title><p>Limitations were discussed in the original report with contextual details.</p></sec>
</body></article>"""

class SourceAuditTests(unittest.TestCase):
    def test_extracts_all_and_trial_id(self):
        x=build_audit(SAMPLE,"PMC_TEST")
        self.assertEqual(x["paragraph_count"],3)
        self.assertTrue(x["trial_id_in_fulltext"])
        self.assertEqual(x["fields"]["pfs"]["matching_paragraph_count"],1)
        self.assertEqual(x["structure"]["table_count"],1)
        self.assertEqual(x["structure"]["tables"][0]["label"],"Table 1")
    def test_no_fabricated_quality_grade(self):
        x=build_audit(SAMPLE,"PMC_TEST")
        text=render([x],0.125)
        self.assertIn("UNVALIDATED",text)
        self.assertIn("Quality-review gate (not passed automatically)",text)
        self.assertIn("one underlying randomized trial",text)
    def test_empty_body_fails_closed(self):
        with self.assertRaises(ValueError):
            build_audit(b"<article><body/></article>","PMC_NONE")
    def test_missing_trial_id_flag(self):
        x=build_audit(SAMPLE.replace(b"NCT05104866",b"no number here"),"PMC_TEST")
        self.assertFalse(x["trial_id_in_fulltext"])
        self.assertIn("NOT FOUND",render([x],1.2))
    def test_matching_does_not_assert_claim(self):
        x=build_audit(SAMPLE,"PMC_TEST")
        self.assertEqual(x["fields"]["pfs"]["examples"][0]["review_status"],
                         "UNVALIDATED_SOURCE_CANDIDATE")

if __name__=="__main__":
    unittest.main()

import unittest
from source_gated_brief import (
    verify_article_id, tables_from_xml, verify_claim, brief_markdown,
    CLAIMS, OS_SOURCE, reviewer_questions,
)

def mock_xml(doi="10.1200/JCO.24.00920", pmcid="PMC11771365"):
    return ("""<article><front><article-meta>
    <article-id pub-id-type="pmc">%s</article-id>
    <article-id pub-id-type="doi">%s</article-id>
    </article-meta></front><body>
    <sec><title>Results</title>
    <p>The median PFS by BICR was 6.9 months (95%% CI, 5.7 to 7.4) with Dato-DXd versus 4.9 months with ICC.</p>
    <table-wrap id="T1"><label>TABLE 1</label><caption><p>Summary</p></caption>
    <table><thead><tr><th>Measure</th><th>Dato-DXd</th><th>ICC</th></tr></thead>
    <tbody><tr><td>PFS</td><td>6.9</td><td>4.9</td></tr></tbody></table>
    </table-wrap></sec></body></article>""" % (pmcid,doi)).encode()

def fake_doc(text, category="results"):
    return {"pmcid":"PMC11771365","url":"https://europepmc.org/articles/PMC11771365",
            "sections":{category:[{"id":"PMC11771365-p3","heading":"Results","text":text}]}}

class StrictSourceReportTests(unittest.TestCase):
    def test_doi_and_pmc_identity(self):
        self.assertEqual(verify_article_id(mock_xml(),"PMC11771365")["doi"],
                         "10.1200/jco.24.00920")
    def test_reject_wrong_doi(self):
        with self.assertRaises(ValueError):
            verify_article_id(mock_xml(doi="10.9999/wrong"),"PMC11771365")
    def test_reject_wrong_pmc_id(self):
        with self.assertRaises(ValueError):
            verify_article_id(mock_xml(pmcid="PMC999999"),"PMC11771365")
    def test_tables_are_structural_not_verified_outcomes(self):
        table=tables_from_xml(mock_xml(),"PMC11771365")["tables"][0]
        self.assertEqual(table["row_count"],2)
        self.assertEqual(table["row_data"][1],["PFS","6.9","4.9"])
        self.assertEqual(table["url"],"https://pmc.ncbi.nlm.nih.gov/articles/PMC11771365/#T1")
    def test_pfs_context_matched(self):
        s=CLAIMS[0]
        d=fake_doc("The median PFS by BICR was 6.9 months (95% CI, 5.7 to 7.4) with Dato-DXd versus 4.9 months (95% CI, 4.2 to 5.5) with ICC.")
        a=verify_claim(s,{"PMC11771365":d})
        self.assertEqual(a["status"],"SOURCE_CONTEXT_MATCH_REVIEW_REQUIRED")
        self.assertEqual(a["candidates"][0]["paragraph_id"],"PMC11771365-p3")
        self.assertEqual(a["review_status"],"PENDING_CLINICAL_REVIEW")
    def test_swapped_arm_order_is_blocked(self):
        s=CLAIMS[0]
        d=fake_doc("The median PFS by BICR was 4.9 months with Dato-DXd versus 6.9 months with ICC.")
        self.assertEqual(verify_claim(s,{"PMC11771365":d})["status"],
                         "BLOCKED_CONTEXT_NOT_FOUND")
    def test_intro_does_not_count_as_new_efficacy_data(self):
        s=CLAIMS[0]
        d=fake_doc("The median PFS by BICR was 6.9 months with Dato-DXd versus 4.9 months with ICC.",category="other")
        self.assertEqual(verify_claim(s,{"PMC11771365":d})["status"],
                         "BLOCKED_CONTEXT_NOT_FOUND")
    def test_missing_source_is_not_success(self):
        self.assertEqual(verify_claim(CLAIMS[0],{})["status"],"BLOCKED_SOURCE_MISSING")
    def test_report_never_conflates_pfs_and_os(self):
        fake_struct={"PMC11771365":{"tables":[],"figures_count":0,"supplement_markers":0}}
        text=brief_markdown([],[],fake_struct,0.1)
        self.assertIn("No statistically significant overall-survival difference",text)
        self.assertIn("PFS conclusion BLOCKED",text)
        self.assertIn("NOT_MACHINE_INGESTED",text)
        self.assertIn("ONE phase III",text)
    def test_rob2_not_auto_scored(self):
        self.assertEqual(len(reviewer_questions()),5)
        text=brief_markdown([],[],{},1.0)
        self.assertIn("UNSCORED",text)
        self.assertIn("signalling-question judgments",text)
        self.assertNotIn("Low risk of bias: confirmed",text)

if __name__=="__main__":
    unittest.main()

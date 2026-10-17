import unittest
from fulltext_evidence import parse_xml
from compare_studies import candidate_matrix,render_matrix

SAMPLE=b"""<article><front><article-meta><title-group><article-title>Mock Research</article-title></title-group></article-meta></front><body><sec><title>Methods</title><p>This randomized trial enrolled 500 patients with synthetic observations.</p></sec><sec><title>Results</title><p>The primary endpoint was progression-free survival with a hazard ratio of 0.9.</p></sec><sec><title>Safety</title><p>Adverse events were reported in the illustrative study.</p></sec></body></article>"""

class CompareTests(unittest.TestCase):
    def test_evidence_identification(self):
        row=candidate_matrix(parse_xml(SAMPLE,"PMC100"))
        self.assertTrue(row["candidates"]["study_design"])
        self.assertTrue(row["candidates"]["sample_size"])
        self.assertTrue(row["candidates"]["effect_estimate"])
        self.assertTrue(row["candidates"]["safety"])
    def test_source_links_and_newline(self):
        r=render_matrix([candidate_matrix(parse_xml(SAMPLE,"PMC100"))])
        self.assertIn("https://europepmc.org/articles/PMC100",r)
        self.assertIn("PMC100-p1",r)
        self.assertIn("\n##",r)
if __name__=="__main__":
    unittest.main()

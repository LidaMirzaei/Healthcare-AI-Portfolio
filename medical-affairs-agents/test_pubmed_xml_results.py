import unittest
from pubmed_xml_results import parse_results_xml,fetch_results_batch

XML=b"""<PubmedArticleSet>
<PubmedArticle>
  <MedlineCitation><PMID>99991111</PMID><Article><Abstract>
    <AbstractText Label="Background" NlmCategory="BACKGROUND">A prior
       PFS trial had HR 0.01, 95% CI 0.001-0.02.</AbstractText>
    <AbstractText Label="Results" NlmCategory="RESULTS">In our PFS trial
       the hazard ratio was 0.75, 95% CI 0.60-0.90.</AbstractText>
    <AbstractText Label="Conclusions" NlmCategory="CONCLUSIONS">
        Interpretation depends on the population.</AbstractText>
  </Abstract></Article></MedlineCitation>
</PubmedArticle>
<PubmedArticle><MedlineCitation><PMID>99992222</PMID><Article><Abstract>
    <AbstractText>A fully unstructured original journal abstract;
    it has OS HR 0.50, 95% CI 0.30-0.70.</AbstractText>
</Abstract></Article></MedlineCitation></PubmedArticle>
</PubmedArticleSet>"""

class StructuredResultsTests(unittest.TestCase):
    def test_results_only_no_background_or_conclusion(self):
        r=parse_results_xml(XML,["99991111","99992222"])
        a=r["99991111"]
        self.assertEqual(a["status"],"ORIGINAL_PUBMED_XML_RESULTS_TAGGED")
        self.assertIn("0.75",a["results"])
        self.assertNotIn("0.01",a["results"])
        self.assertEqual(a["tagged_results_sections"],1)
    def test_unstructured_stays_blocked(self):
        r=parse_results_xml(XML,["99992222"])
        self.assertEqual(r["99992222"]["status"],"ORIGINAL_PUBMED_ABSTRACT_UNSTRUCTURED_ABSTAIN")
        self.assertEqual(r["99992222"]["results"],"")
    def test_reject_invalid_requested_pmids(self):
        with self.assertRaises(ValueError):fetch_results_batch(["bad"])
        with self.assertRaises(ValueError):fetch_results_batch(["99991111","99991111"])
    def test_duplicate_original_pmid_fails(self):
        from xml.etree import ElementTree as ET
        repeated=XML.replace(b"</PubmedArticleSet>",XML.split(b"<PubmedArticle>")[1].split(b"</PubmedArticle>")[0].join([]) if False else b"</PubmedArticleSet>")
        # Generate an actual duplicate original PubmedArticle to test strict dedup.
        original=XML.split(b"<PubmedArticle>",1)[1].split(b"</PubmedArticle>",1)[0]
        repeated=XML.replace(b"</PubmedArticleSet>",b"<PubmedArticle>"+original+b"</PubmedArticle></PubmedArticleSet>")
        with self.assertRaises(ValueError):
            parse_results_xml(repeated,["99991111","99992222"])
    def test_only_requested_source_returned(self):
        r=parse_results_xml(XML,["99992222"])
        self.assertEqual(set(r),{"99992222"})

if __name__=="__main__":
    unittest.main()

"""Offline unit tests; no network or private data."""
import unittest
from research_brief import parse_pubmed_xml, render_markdown

FIXTURE = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>12345</PMID><Article>
<ArticleTitle>Example &amp; trial of breast cancer therapy</ArticleTitle>
<Journal><JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue><Title>Test Journal</Title></Journal>
<Abstract><AbstractText Label="OBJECTIVE">This is synthetic test text.</AbstractText></Abstract>
</Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/example</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""

class BriefTests(unittest.TestCase):
    def test_parses_metadata(self):
        articles = parse_pubmed_xml(FIXTURE)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["pmid"], "12345")
        self.assertEqual(articles[0]["year"], "2025")
        self.assertIn("OBJECTIVE:", articles[0]["abstract"])

    def test_brief_has_sources_and_disclaimer(self):
        brief = render_markdown(parse_pubmed_xml(FIXTURE), "breast cancer", "2026-10-17")
        self.assertIn("https://pubmed.ncbi.nlm.nih.gov/12345/", brief)
        self.assertIn("human scientific review required", brief)
        self.assertIn("No LLM is used", brief)

    def test_empty_pubmed_response(self):
        self.assertEqual(parse_pubmed_xml(b"<PubmedArticleSet/>"), [])

    def test_no_results_rendered(self):
        text = render_markdown([], "breast cancer", "2026-10-17")
        self.assertIn("No matching articles retrieved.", text)

if __name__ == "__main__":
    unittest.main()

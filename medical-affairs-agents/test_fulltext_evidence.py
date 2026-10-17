"""Offline fixtures only, never confuse these with scientific validation."""
import unittest
from fulltext_evidence import parse_xml,evidence,markdown,section_type
XML=b"""<article><front><article-meta><title-group><article-title>Demo Trial</article-title></title-group></article-meta></front><body><sec><title>Methods</title><p>Twenty patients joined this entirely synthetic randomized study.</p></sec><sec><title>Results</title><p>Results are intentionally invented solely to test parsing logic.</p><sec><title>Safety</title><p>An adverse event was observed in this mock document.</p></sec></sec><sec><title>Limitations</title><p>This example does not provide real scientific evidence.</p></sec></body></article>"""
class Tests(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(section_type("Methods"),"methods")
    def test_sections(self):
        d=parse_xml(XML,"PMC123")
        self.assertEqual(len(d["sections"]["methods"]),1)
        self.assertEqual(len(d["sections"]["results"]),1)
        self.assertEqual(len(d["sections"]["safety"]),1)
    def test_evidence(self):
        output=markdown([evidence(parse_xml(XML,"PMC123"))])
        self.assertIn("PMC123-p1",output)
        self.assertIn("https://europepmc.org/articles/PMC123",output)
    def test_empty(self):
        d=parse_xml(b"<article><body/></article>","PMC0")
        self.assertIn("No matching heading found",markdown([evidence(d)]))
if __name__=="__main__":
    unittest.main()

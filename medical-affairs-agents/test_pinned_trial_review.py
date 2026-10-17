import unittest
from pinned_trial_review import PAPERS

class PinnedSelectionTests(unittest.TestCase):
    def test_unique_sources(self):
        ids=[paper["pmcid"] for paper in PAPERS]
        self.assertEqual(len(ids),3)
        self.assertEqual(len(ids),len(set(ids)))
    def test_expected_trial_publications(self):
        self.assertEqual({p["pmcid"] for p in PAPERS},
            {"PMC11771365","PMC13449377","PMC13583573"})
    def test_2024_online_date_transparency(self):
        self.assertIn("first online 2024", PAPERS[0]["label"])

if __name__=="__main__":
    unittest.main()

import copy
import json
import unittest
from adc_reviewer_worksheet import create_worksheet
from adc_reference_dataset import DEFAULT_SEED

SEED=json.loads(DEFAULT_SEED.read_text(encoding="utf-8"))

class ReviewerWorksheetTests(unittest.TestCase):
    def test_all_ten_families_get_review_checklist(self):
        a={"source_checks_completed":10,"studies":[
            {"pmid":s["pmid"],"verification_status":"PENDING_REVIEW"}
            for s in SEED["studies"]]}
        text=create_worksheet(SEED,a)
        self.assertEqual(text.count("Medically approved for any external use: NO"),10)
        self.assertIn("TROPION-Breast02",text)
        self.assertIn("99%",text)
        self.assertIn("95.01%",text)
        self.assertIn("Review",text)
        self.assertIn("NOT A GOLD STANDARD",text)
    def test_incomplete_original_sources_block(self):
        with self.assertRaises(ValueError):
            create_worksheet(SEED,{"source_checks_completed":9,"studies":[]})
    def test_worksheet_does_not_fake_human_adjudication(self):
        a={"source_checks_completed":10,"studies":[]}
        s=create_worksheet(SEED,a)
        self.assertIn("Reviewer 1 conclusion and source: PENDING",s)
        self.assertIn("Reviewer 2 conclusion and source: PENDING",s)
        self.assertIn("adjudication: PENDING",s)
    def test_no_duplicate_trials_masquerade(self):
        seed=copy.deepcopy(SEED)
        seed["studies"][4]["nct"]=seed["studies"][3]["nct"]
        with self.assertRaises(ValueError):
            create_worksheet(seed,{"source_checks_completed":10,"studies":[]})

if __name__=="__main__":
    unittest.main()

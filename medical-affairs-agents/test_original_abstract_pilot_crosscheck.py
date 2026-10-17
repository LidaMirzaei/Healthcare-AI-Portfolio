"""Integrity tests only; publicly sourced facts still require external experts."""
import json
import unittest
from pathlib import Path
from adc_reference_dataset import DEFAULT_SEED

HERE=Path(__file__).resolve().parent
SEED=json.loads(DEFAULT_SEED.read_text(encoding="utf-8"))
PILOT=json.loads((HERE/"benchmarks"/"ORIGINAL_ABSTRACT_PILOT_SOURCE_CROSSCHECK.json").read_text(encoding="utf-8"))

class PublicPilotSourceReviewTests(unittest.TestCase):
    def test_all_original_publications_match_pinned_dois(self):
        lookup={x["nct"]:x for x in SEED["studies"]}
        self.assertEqual(len(PILOT["studies"]),3)
        for source in PILOT["studies"]:
            original=lookup[source["trial_id"]]
            self.assertEqual(source["pmid"],original["pmid"])
            self.assertEqual(source["doi"].lower(),original["expected_doi"].lower())
            self.assertIn(original["pmid"],source["source"])
            self.assertGreater(len(source["gaps"]),2)
    def test_preliminary_never_misrepresented_as_gold(self):
        self.assertEqual(PILOT["scientifically_adjudicated_claim_count"],0)
        self.assertIsNone(PILOT["expert_reviewer_A"])
        self.assertIsNone(PILOT["expert_reviewer_B"])
    def test_consent_source_values_not_faked_by_coincidental_hr(self):
        study=next(x for x in PILOT["studies"] if x["trial"]=="DESTINY-Breast05")
        observed=[(x["endpoint"],x["measure"],x.get("value")) for x in study["entries"]]
        self.assertIn(("invasive disease-free survival","HR",0.47),observed)
        self.assertIn(("disease-free survival","HR",0.47),observed)
        self.assertNotEqual(observed[0][0],observed[1][0])
        self.assertTrue(any("erratum" in x.lower() for x in study["gaps"]))
    def test_unusual_interval_levels_are_not_mixed(self):
        study=next(x for x in PILOT["studies"] if x["trial"]=="TROPION-Breast02")
        outcomes={x["endpoint"]:x for x in study["entries"]}
        self.assertEqual(outcomes["OS"]["ci_level"],95.01)
        self.assertEqual(outcomes["PFS by blinded independent central review"]["ci_level"],99)
    def test_first_paper_os_is_immature(self):
        study=next(x for x in PILOT["studies"] if x["trial"]=="TROPION-Breast01")
        os=next(x for x in study["entries"] if x["endpoint"]=="OS")
        self.assertIn("Immature",os["qualifier"])
        self.assertTrue(any("Final OS" in x for x in study["gaps"]))

if __name__=="__main__":
    unittest.main()

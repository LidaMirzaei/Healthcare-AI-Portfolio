import copy
import json
import unittest
from pathlib import Path
from adc_reference_dataset import DEFAULT_SEED
from validate_reserved_holdout import validate_holdout

BASE=Path(__file__).resolve().parent
DEV=json.loads(DEFAULT_SEED.read_text(encoding="utf-8"))
POOL=json.loads((BASE/"benchmarks"/"RESERVED_V4_TRIAL_FAMILIES.json").read_text(encoding="utf-8"))

class ReservedClinicalHoldoutTests(unittest.TestCase):
    def test_six_distinct_trials_reserved_not_scored(self):
        info=validate_holdout(POOL,DEV)
        self.assertEqual(info["reserved_families"],6)
        self.assertEqual(info["clinical_gold_labels"],0)
        self.assertTrue(info["scoring_blocked_pending_expert_review"])
        self.assertTrue(info["unseen_outcome_labels"])
    def test_overlapping_parent_trial_rejected(self):
        pool=copy.deepcopy(POOL)
        pool["studies"][0]["trial_family_id"]="NCT05104866"
        with self.assertRaises(ValueError):
            validate_holdout(pool,DEV)
    def test_earlier_holdout_reuse_rejected(self):
        pool=copy.deepcopy(POOL)
        pool["studies"][0]["trial_family_id"]="NCT03725059"
        with self.assertRaises(ValueError):
            validate_holdout(pool,DEV)
    def test_outcome_field_prohibited(self):
        pool=copy.deepcopy(POOL)
        pool["studies"][0]["hazard_ratio"]=0.65
        with self.assertRaises(ValueError):
            validate_holdout(pool,DEV)
    def test_duplicate_trial_or_pmid_prohibited(self):
        pool=copy.deepcopy(POOL)
        pool["studies"][1]["trial_family_id"]=pool["studies"][0]["trial_family_id"]
        with self.assertRaises(ValueError):
            validate_holdout(pool,DEV)
        pool=copy.deepcopy(POOL)
        pool["studies"][1]["pmid"]=pool["studies"][0]["pmid"]
        with self.assertRaises(ValueError):
            validate_holdout(pool,DEV)
    def test_false_promotion_to_gold_rejected(self):
        pool=copy.deepcopy(POOL)
        pool["status"]="CLINICAL_GOLD_READY"
        with self.assertRaises(ValueError):
            validate_holdout(pool,DEV)

if __name__=="__main__":
    unittest.main()

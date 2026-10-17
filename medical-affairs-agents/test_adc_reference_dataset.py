"""Synthetic offline tests for candidate dataset audit, never claim clinical accuracy."""
import copy
import json
import unittest
from pathlib import Path
from adc_reference_dataset import (
    DEFAULT_SEED, check_reference_schema, evaluate_source,
    has_exact_number, norm, build_report
)

SEED=json.loads(DEFAULT_SEED.read_text(encoding="utf-8"))


def fake_record(seed, abstract=None):
    value=seed["estimate"]
    ci=(f" ({seed['ci_level']}% CI {seed['ci_lower']} to {seed['ci_upper']})"
        if seed["ci_level"] else "")
    if abstract is None:
        abstract=(f"This original randomized study {seed['nct']} reports {seed['endpoint']} "
                  f"hazard ratio {value}{ci} with results from analyzed participants.")
    return {"id":seed["pmid"],"source":"MED",
            "title":"Original clinical investigation with findings",
            "doi":"10.1234/example","firstPublicationDate":"2025-01-01",
            "abstractText":abstract}


class ADCReferenceTests(unittest.TestCase):
    def test_initial_seed_has_ten_unique_family_ids(self):
        self.assertEqual(check_reference_schema(SEED),10)
        self.assertEqual(len({x["nct"] for x in SEED["studies"]}),10)
    def test_reference_not_gold_and_not_holdout(self):
        self.assertEqual(SEED["status"],"PRELIMINARY_NOT_INDEPENDENTLY_ADJUDICATED")
        self.assertEqual(SEED["holdout_status"],"DEVELOPMENT_ONLY_NOT_FROZEN_HELDOUT")
        bad=copy.deepcopy(SEED)
        bad["status"]="EXPERT_VALIDATED_GOLD_STANDARD"
        with self.assertRaises(ValueError):check_reference_schema(bad)
    def test_duplicate_trials_rejected(self):
        bad=copy.deepcopy(SEED)
        bad["studies"][1]["nct"]=bad["studies"][0]["nct"]
        with self.assertRaises(ValueError):check_reference_schema(bad)
    def test_no_comparator_in_single_arm(self):
        bad=copy.deepcopy(SEED)
        bad["studies"][-1]["comparator"]="invented control arm"
        with self.assertRaises(ValueError):check_reference_schema(bad)
    def test_no_missing_ci_confidence_level_invented(self):
        study=next(x for x in SEED["studies"] if x["key"]=="DESTINY-Breast04")
        self.assertIsNone(study["ci_level"])
        bad=copy.deepcopy(SEED)
        b=next(x for x in bad["studies"] if x["key"]=="DESTINY-Breast04")
        b["ci_lower"]=0.50
        with self.assertRaises(ValueError):check_reference_schema(bad)
    def test_99_confidence_interval_preserved(self):
        study=next(x for x in SEED["studies"] if x["key"]=="TROPION-Breast02")
        self.assertEqual(study["ci_level"],99)
        a=evaluate_source(study,fake_record(study))
        self.assertTrue(a["checks"]["ci_level"])
        self.assertEqual(a["ci_level_provisional"],99)
        a=evaluate_source(study,fake_record(study,abstract=(
            f"{study['nct']} reports PFS HR 0.57 (95% CI 0.44 to 0.73).")))
        self.assertFalse(a["checks"]["ci_level"])
        self.assertEqual(a["verification_status"],"ABSTRACT_SOURCE_CHECK_INCOMPLETE_REVIEW_REQUIRED")
    def test_unicode_decimal_and_numeric_boundaries(self):
        self.assertTrue(has_exact_number("hazard ratio 0·79 and 95% CI",0.79))
        self.assertTrue(has_exact_number("response ORR 62.1%",62.1))
        self.assertFalse(has_exact_number("HR 10.63",0.63))
        self.assertFalse(has_exact_number("HR 0.6300",0.63))
    def test_nct_absence_stays_incomplete(self):
        study=SEED["studies"][0]
        rec=fake_record(study,abstract="PFS HR 0.63 95% CI 0.52 to 0.76.")
        item=evaluate_source(study,rec)
        self.assertFalse(item["checks"]["nct_found_in_abstract"])
        self.assertIn("INCOMPLETE",item["verification_status"])
        self.assertFalse(item["human_adjudicated"])
    def test_pmid_mismatch_not_accepted(self):
        study=SEED["studies"][0]
        wrong=fake_record(study)
        wrong["id"]="99999999"
        item=evaluate_source(study,wrong)
        self.assertFalse(item["checks"]["pubmed_identity"])
        self.assertIn("INCOMPLETE",item["verification_status"])
    def test_source_number_presence_not_scientific_validation(self):
        study=SEED["studies"][0]
        s=evaluate_source(study,fake_record(study))
        self.assertEqual(s["verification_status"],"ABSTRACT_NUMBER_TOKENS_LOCATED_REVIEW_REQUIRED")
        self.assertFalse(s["human_adjudicated"])
        self.assertTrue(s["not_for_treatment_comparison"])
        self.assertFalse(s["source_contains_original_full_text"])
    def test_packet_emphasizes_endpoint_and_population(self):
        draft=build_report(SEED,[],0.001)
        self.assertIn("not comparable effect sizes",draft)
        self.assertIn("single-arm",draft)
        self.assertIn("99%",draft)
        self.assertIn("NOT a gold standard",draft)
    def test_modified_ci_outside_estimate_rejected(self):
        b=copy.deepcopy(SEED)
        b["studies"][0]["ci_lower"]=0.80
        with self.assertRaises(ValueError):check_reference_schema(b)


if __name__=="__main__":
    unittest.main()

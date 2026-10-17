"""Offline tests for independent-trial evaluation and abstention, NOT clinical accuracy."""
import copy
import json
import unittest
from pathlib import Path

from independent_holdout import (
    MANIFEST, fingerprint, score_holdout, license_classification,
    infer_study_design, infer_disease_setting, infer_study_registration,
)
from xml.etree import ElementTree as ET


def fixture(license_uri="https://creativecommons.org/licenses/by/4.0/",
            doi="10.1038/s41591-024-03415-7",
            title="Pembrolizumab and chemotherapy in early-stage breast cancer: a randomized phase 3 trial",
            abstract="KEYNOTE-756 is a randomized study registered as NCT03725059.",
            methods=""):
    license_element = (
        f'<license xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'xlink:href="{license_uri}"><license-p>Creative Commons license</license-p></license>'
    ) if license_uri else ""
    return f"""<article><front><article-meta>
    <article-id pub-id-type="pmc">11835712</article-id>
    <article-id pub-id-type="doi">{doi}</article-id>
    <title-group><article-title>{title}</article-title></title-group>
    <abstract><p>{abstract}</p></abstract>
    <permissions>{license_element}</permissions>
    </article-meta></front><body>
    <sec><title>Methods</title><p>{methods}</p></sec>
    </body></article>""".encode()


class IndependentEvaluationTests(unittest.TestCase):
    def test_ccby_is_permitted_for_local_prototype(self):
        self.assertEqual(license_classification(ET.fromstring(fixture()))["status"],
                         "CC_BY_OR_CC0_CONFIRMED")
    def test_nc_license_blocks_redistribution_mining(self):
        xml=fixture(license_uri="https://creativecommons.org/licenses/by-nc/4.0/")
        self.assertEqual(license_classification(ET.fromstring(xml))["status"],
                         "BLOCKED_LICENSE_NOT_APPROVED")
    def test_nd_license_blocks(self):
        xml=fixture(license_uri="https://creativecommons.org/licenses/by-nd/4.0/")
        self.assertEqual(license_classification(ET.fromstring(xml))["status"],
                         "BLOCKED_LICENSE_NOT_APPROVED")
    def test_unknown_license_blocks(self):
        self.assertEqual(license_classification(ET.fromstring(fixture(license_uri="")))["status"],
                         "BLOCKED_UNKNOWN_LICENSE")
    def test_identity_and_setting_inference(self):
        r=fingerprint(fixture(),"PMC11835712")
        self.assertEqual(r["doi"],"10.1038/s41591-024-03415-7")
        self.assertEqual(r["design"],"randomized")
        self.assertEqual(r["setting"],"early")
        self.assertEqual(r["registration"],"NCT03725059")
    def test_noninterventional_not_randomized(self):
        title="Real-world outcomes in advanced breast cancer: observational RIBANNA study"
        self.assertEqual(infer_study_design(title,"", "The study is prospective."),"observational")
        self.assertEqual(infer_disease_setting(title),"advanced")
    def test_ambiguous_registrations_abstain(self):
        trial,location=infer_study_registration(
            "We cite trials NCT12345678 and NCT87654321","")
        self.assertEqual(trial,"AMBIGUOUS_REVIEW_REQUIRED")
    def test_no_clinical_inference_from_unknown_title(self):
        self.assertEqual(infer_disease_setting("Clinical response to an unnamed therapy"),
                         "UNKNOWN_REVIEW_REQUIRED")
        self.assertEqual(infer_study_design("Observations in cancer","", ""),
                         "UNKNOWN_REVIEW_REQUIRED")
    def test_frozen_trial_leakage_fails(self):
        m=json.loads(MANIFEST.read_text())
        m["train_trials"]=[m["holdout"][0]["trial_id"]]
        with self.assertRaises(ValueError):
            score_holdout([],m)
    def test_identity_scores_do_not_claim_clinical_accuracy(self):
        manifest=json.loads(MANIFEST.read_text())
        r=score_holdout([],manifest)
        self.assertTrue(r["not_a_clinical_accuracy_metric"])
        self.assertEqual(r["correct_labels"],0)
        self.assertEqual(r["assessed_labels"],12)
    def test_outcome_label_not_available_to_predictor(self):
        r=fingerprint(fixture(),"PMC11835712")
        self.assertEqual(r["automated_efficacy_or_safety_conclusion"],"NOT_PERFORMED")


if __name__=="__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from rights_preflight import authorize_license,write_status

class RightsPreflightTests(unittest.TestCase):
    def test_cc_by_passes(self):
        self.assertTrue(authorize_license("CC BY 4.0"))
        self.assertTrue(authorize_license("cc0"))
    def test_nc_nd_explicitly_blocks(self):
        for s in ["CC BY-NC-ND 4.0","CC BY-NC","CC BY-ND","non-commercial",
                  "CC BY-SA","not identified",""]:
            self.assertFalse(authorize_license(s),s)
    def test_missing_or_nontext_license_blocks(self):
        self.assertFalse(authorize_license(None))
        self.assertFalse(authorize_license({"license":"CC BY"}))
    def test_github_output_status_is_boolean_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"output"
            write_status(p,False)
            self.assertEqual(p.read_text(),"authorized=false\n")
            write_status(p,True)
            self.assertEqual(p.read_text(),"authorized=false\nauthorized=true\n")

if __name__=="__main__":
    unittest.main()

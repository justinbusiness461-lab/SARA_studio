"""Round 22 regression gate: branch and test coverage before MAIN promotion."""
from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1]/'.github/workflows/m045-native-browser-regression.yml'

class R22CiDestinationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow=WORKFLOW.read_text()

    def test_feature_branch_and_pull_request_main_triggers(self):
        self.assertIn('      - feat/platform-identity-and-catalog',self.workflow)
        self.assertIn('  pull_request:',self.workflow)
        self.assertIn('      - main',self.workflow)

    def test_no_stale_22_case_limit_and_zero_skips(self):
        self.assertNotIn('# tests 22$',self.workflow)
        self.assertIn("NODE_MIN_TESTS: '51'",self.workflow)
        self.assertIn("PYTHON_MIN_TESTS: '635'",self.workflow)
        self.assertIn("BROWSER_MIN_TESTS: '34'",self.workflow)
        self.assertIn('skipped',self.workflow)

    def test_python_node_browser_are_separately_reported(self):
        self.assertIn('m045-python.log',self.workflow)
        self.assertIn('m045-node.log',self.workflow)
        self.assertIn('m045-browser.log',self.workflow)
        self.assertIn('tests/*.browser.cjs',self.workflow)

if __name__=='__main__':unittest.main()

"""Fail-closed runner regression tests; no live model or media implied."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "tools" / "run_pr33_closure_suite.py"
SPEC = importlib.util.spec_from_file_location("pr33_gate", MODULE)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class TestPr33FailClosedGate(unittest.TestCase):
    def test_missing_sources_block_before_tests(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(gate.subprocess, "run", side_effect=AssertionError("unexpected test run")):
                report = gate.execute(Path(d), 1)
            self.assertEqual(report["stage"], "BLOCKED_SOURCE_MISSING")
            self.assertFalse(report["all_tests_passed"])
            self.assertTrue(report["missing"])

    def test_skipped_tests_do_not_earn_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for repo, paths in gate.REQUIRED.items():
                for rel in paths:
                    path = root / repo / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("pass")
            class Fake:
                returncode = 0
                stdout = "Ran 4 tests in 0.01s\\nOK (skipped=2)"
                stderr = ""
            with patch.object(gate.subprocess, "run", return_value=Fake()):
                report = gate.execute(root, 1)
            self.assertEqual(report["stage"], "BLOCKED_TESTS")
            self.assertFalse(report["all_tests_passed"])
            self.assertTrue(all(t["status"] == "FAIL_OR_SKIPPED" for t in report["tests"].values()))


if __name__ == "__main__":
    unittest.main()

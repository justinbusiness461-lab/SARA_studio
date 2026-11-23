"""R27: strict real-media certification must refuse synthetic fixture fallback."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "tests" / "r25_three_song_fixture_server.py"
VARIABLES = ("SARA_R25_REAL_MEDIA_STRICT", "SARA_R25_REAL_MEDIA_ROOT",
             "SARA_R25_REAL_MEDIA_RECEIPTS")


class StrictThreeSongMediaGateTests(unittest.TestCase):
    def check_denied(self, values, expected_error):
        with tempfile.TemporaryDirectory(prefix="r27-strict-gate-") as temporary:
            folder = Path(temporary)
            env = dict(os.environ)
            for key in VARIABLES:
                env.pop(key, None)
            env.update(values)
            result = subprocess.run(
                [sys.executable, "-u", str(SERVER), str(folder / "studio")],
                cwd=str(REPO), env=env, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, timeout=12, check=False,
            )
            self.assertNotEqual(result.returncode, 0, "strict gate started a server")
            self.assertIn(expected_error, result.stderr)
            self.assertFalse(list(folder.glob("r25-demo-*.wav")),
                             "strict mode wrote synthetic fixture audio")

    def test_strict_requires_real_root_and_receipts(self):
        self.check_denied({"SARA_R25_REAL_MEDIA_STRICT": "1"},
                          "R27_REAL_MEDIA_REQUIRED")

    def test_strict_rejects_missing_receipts_before_fallback(self):
        with tempfile.TemporaryDirectory(prefix="r27-real-root-") as real_root:
            self.check_denied({
                "SARA_R25_REAL_MEDIA_STRICT": "1",
                "SARA_R25_REAL_MEDIA_ROOT": real_root,
                "SARA_R25_REAL_MEDIA_RECEIPTS": str(Path(real_root) / "missing"),
            }, "R27_REAL_MEDIA_RECEIPT_MISSING")

    def test_strict_rejects_missing_real_root_before_fallback(self):
        with tempfile.TemporaryDirectory(prefix="r27-receipt-root-") as receipt_root:
            receipt = Path(receipt_root)
            (receipt / "private_ingestion_receipt.json").write_text("{}", encoding="utf-8")
            (receipt / "private_r2_receipt.json").write_text("{}", encoding="utf-8")
            self.check_denied({
                "SARA_R25_REAL_MEDIA_STRICT": "1",
                "SARA_R25_REAL_MEDIA_ROOT": str(receipt / "nonexistent"),
                "SARA_R25_REAL_MEDIA_RECEIPTS": receipt_root,
            }, "R27_REAL_MEDIA_ROOT_NOT_FOUND")

    def test_rejects_ambiguous_strict_mode_flag(self):
        self.check_denied({"SARA_R25_REAL_MEDIA_STRICT": "true"},
                          "R27_REAL_MEDIA_STRICT_INVALID")


if __name__ == "__main__":
    unittest.main()

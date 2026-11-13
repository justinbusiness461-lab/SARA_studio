import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

class PostMergeHarnessContract(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / 'tools' / 'runnable_m044_postmerge.sh').read_text(encoding='utf-8')

    def test_pins_exact_postmerge_main(self):
        self.assertIn('749127ce0ce2cd08cdc5a6354626a078064f4704', self.text)

    def test_requires_exact_head_not_branch_name(self):
        self.assertIn('HEAD" != "$EXPECTED_MAIN_SHA', self.text)

    def test_requires_clean_tree(self):
        self.assertIn('git status --porcelain', self.text)

    def test_runs_all_four_browser_product_suites(self):
        for name in (
            'tests/r1-playback.browser.cjs',
            'tests/prompt-generate.browser.cjs',
            'tests/r2-ab.browser.cjs',
            'tests/r2-cold-reopen.browser.cjs',
        ):
            self.assertIn(name, self.text)

    def test_does_not_claim_release_certification(self):
        self.assertIn('RELEASE_CERTIFIED=false', self.text)

if __name__ == '__main__':
    unittest.main()

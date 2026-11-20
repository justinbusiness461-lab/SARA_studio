import pathlib, sys, tempfile, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))

class AceStepAdmissionTests(unittest.TestCase):

    def test_legacy_custom_infer_endpoint_is_not_native_api(self):
        from m045_acestep_provider import AceStepProvider, ProviderUnavailable
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            client = AceStepProvider(endpoint_url="https://approved.example/infer", checkpoint_dir="",
                                      checkpoint_sha256="a"*64)
            with patch("m045_acestep_provider.urllib.request.urlopen") as remote:
                with self.assertRaises(ProviderUnavailable):
                    client(pathlib.Path(d), {}, "demo", "", 1, {"music_length_ms":12000})
                remote.assert_not_called()

    def test_missing_checkpoint_and_endpoint_fails_closed(self):
        from m045_acestep_provider import AceStepProvider, ProviderUnavailable
        with self.assertRaises(ProviderUnavailable):
            AceStepProvider(endpoint_url="",checkpoint_dir="")(pathlib.Path(tempfile.gettempdir()),{}, "demo","",1,{"music_length_ms":3000})

    def test_local_checkpoint_without_qualified_runtime_fails_closed(self):
        from m045_acestep_provider import AceStepProvider, ProviderUnavailable
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ProviderUnavailable):
                AceStepProvider(endpoint_url="",checkpoint_dir=d)(pathlib.Path(d),{}, "demo","",1,{"music_length_ms":3000})

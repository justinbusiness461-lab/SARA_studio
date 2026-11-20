import io
import json
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_m045_native_attempt as native_tests
from m045_eleven_music_provider import ElevenMusicProvider, ProviderUnavailable

class FakeResponse:
    def __init__(self, data, content_type="audio/mpeg", song_id="song-provider-1"):
        self.data = data
        self.headers = {"Content-Type": content_type, "song-id": song_id}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size=-1):
        if size < 0:
            data, self.data = self.data, b""
            return data
        data, self.data = self.data[:size], self.data[size:]
        return data

class ElevenProviderTests(unittest.TestCase):
    def setUp(self):
        self.native = native_tests.NativeAttemptTests()
        self.native.setUp()
    def tearDown(self):
        self.native.tearDown()
    def _run(self, provider, key="idem-eleven-1"):
        owner, _ = self.native._owner()
        params = {"music_length_ms": 3000}
        return owner.execute_attempt(**self.native._kwargs(
            idempotency_key=key, model_id="music_v2_5", model_version="elevenlabs-music-v2.5",
            params=params, synthesize_to_stage_fn=provider))
    def test_missing_credential_persists_failed_pre_commit(self):
        p = ElevenMusicProvider(api_key="")
        with self.assertRaises(ProviderUnavailable):
            self._run(p)
        owner, _ = self.native._owner()
        rec = owner.reconcile_attempt(headers=self.native._kwargs()["headers"],
            project_id=self.native.pid, idempotency_key="idem-eleven-1")
        self.assertEqual(rec["state"], "FAILED_PRE_COMMIT")
        self.assertEqual(len(owner.list_project_revisions(self.native.pid)), 1)
    def test_malformed_upstream_rejected_before_cas_or_revision(self):
        p = ElevenMusicProvider(api_key="test-only-token")
        with patch("m045_eleven_music_provider.urllib.request.urlopen", return_value=FakeResponse(b'{"error":"bad"}',"application/json")):
            with self.assertRaises(ValueError):
                self._run(p, "idem-eleven-bad")
        owner, _ = self.native._owner()
        self.assertEqual(len(owner.list_project_revisions(self.native.pid)), 1)
    def test_real_mp3_transport_normalizes_and_survives_cold_restart(self):
        import subprocess
        fixture = self.native.bytes
        encoded = subprocess.run(["ffmpeg","-nostdin","-v","error","-f","wav","-i","pipe:0",
                                  "-codec:a","libmp3lame","-b:a","128k","-f","mp3","pipe:1"],
                                  input=fixture,capture_output=True,check=True).stdout
        p = ElevenMusicProvider(api_key="test-only-token")
        with patch("m045_eleven_music_provider.urllib.request.urlopen", return_value=FakeResponse(encoded)):
            result = self._run(p, "idem-eleven-valid")
        self.assertEqual(result["state"], "COMMITTED")
        self.assertEqual(result["attempt"]["provenance"]["preservation_tier"], "P3")
        self.assertEqual(result["attempt"]["provenance"]["rights_status"], "PROVIDER_TERMS_UNVERIFIED")
        self.assertEqual(result["attempt"]["provenance"]["model_id"], "music_v2_5")
        self.assertEqual(result["attempt"]["provenance"]["provider_song_id"], "song-provider-1")
        self.assertEqual(result["attempt"]["media"]["sample_rate"], 44100)
        self.assertEqual(result["attempt"]["media"]["channels"], 2)
        owner, _ = self.native._owner()
        reopened = owner.reconcile_attempt(headers=self.native._kwargs()["headers"],
            project_id=self.native.pid, idempotency_key="idem-eleven-valid")
        self.assertEqual(reopened["revision"]["revisionId"], result["revision"]["revisionId"])
        self.assertEqual(reopened["attempt"]["artifact_digest"], result["attempt"]["artifact_digest"])
        digest = result["attempt"]["artifact_digest"]
        blob = self.native.root / "objects" / digest[:2] / digest
        self.assertTrue(blob.is_file())
    def test_user_model_spoof_rejected_by_native_http_route(self):
        import socketserver
        import threading
        import urllib.error
        import urllib.request
        import studio_server as server
        owner, _ = self.native._owner()
        p = ElevenMusicProvider(api_key="")
        server.configure_m045_generation(owner, p)
        old_root, old_port = server.EXPORT_ROOT, server.PORT
        httpd = socketserver.TCPServer(("127.0.0.1", 0), server.StudioHandler)
        server.EXPORT_ROOT = self.native.root
        server.PORT = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            payload = self.native._kwargs(idempotency_key="spoof-model", model_id="unqualified-model",
                                           model_version="forged", synthesize_to_stage_fn=None)
            payload.pop("headers")
            payload.pop("synthesize_to_stage_fn")
            url = f"http://127.0.0.1:{server.PORT}/api/m045/attempts"
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
                "Content-Type": "application/json",
                "Origin": f"http://127.0.0.1:{server.PORT}",
                "X-Studio-Capability": server.CAPABILITY,
                "Authorization": "Bearer " + self.native.session,
            })
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(req, timeout=2)
            self.assertEqual(denied.exception.code, 400)
            self.assertEqual(len(owner.list_project_revisions(self.native.pid)), 1)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)
            server.EXPORT_ROOT, server.PORT = old_root, old_port


if __name__ == "__main__": unittest.main()

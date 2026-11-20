import io
import pathlib
import sys
import tempfile
import unittest
import wave
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from m045_generation_attempt import _verify_wav

class FullSongBoundaryTests(unittest.TestCase):
    def _wav(self, path, seconds):
        with wave.open(str(path), "wb") as out:
            out.setnchannels(2)
            out.setsampwidth(2)
            out.setframerate(44100)
            one_second=b"\0"*(44100*4)
            for _ in range(seconds):
                out.writeframesraw(one_second)

    def test_locked_track_blocks_synthesis(self):
        import studio_server as server
        import test_m045_native_attempt as fixture_module
        fixture=fixture_module.NativeAttemptTests()
        fixture.setUp()
        try:
            spec={**fixture.fixture.spec, "tracks":[{**t,"sonic_lock":True} for t in fixture.fixture.spec["tracks"]]}
            latest=server.project_operation(fixture.root,{"projectId":fixture.pid,"expectedCurrentRevisionId":fixture.r1["revision"]["revisionId"],"songSpec":spec,"sourceAssetDigests":[],"outputArtifactIds":[]},commit=True)
            owner,synth=fixture._owner()
            with self.assertRaisesRegex(server.ProjectConflict,"Sonic Lock"):
                owner.execute_attempt(**fixture._kwargs(base_revision_id=latest["revision"]["revisionId"],expected_current_revision_id=latest["revision"]["revisionId"],song_spec=spec,synthesize_to_stage_fn=synth))
            self.assertEqual(fixture.synth_calls,0)
        finally:
            fixture.tearDown()

    def test_change_only_this_requires_qualified_backend(self):
        import studio_server as server
        import test_m045_native_attempt as fixture_module
        fixture=fixture_module.NativeAttemptTests()
        fixture.setUp()
        try:
            owner,synth=fixture._owner()
            with self.assertRaisesRegex(server.ProjectConflict,"Change ONLY This"):
                owner.execute_attempt(**fixture._kwargs(params={"target_bar_range":[8,16]},synthesize_to_stage_fn=synth))
            self.assertEqual(fixture.synth_calls,0)
        finally:
            fixture.tearDown()


    def test_http_reconcile_requires_bearer_and_returns_committed(self):
        import test_m045_native_attempt as fixture_module
        import studio_server as server
        import socketserver
        import threading
        import json
        import urllib.request
        import urllib.error
        fixture=fixture_module.NativeAttemptTests()
        fixture.setUp()
        owner,synth=fixture._owner()
        outcome=owner.execute_attempt(**fixture._kwargs(
            idempotency_key="recover-http-1",synthesize_to_stage_fn=synth))
        server.configure_m045_generation(owner,synth)
        old_root,old_port=server.EXPORT_ROOT,server.PORT
        httpd=socketserver.TCPServer(("127.0.0.1",0),server.StudioHandler)
        server.EXPORT_ROOT=fixture.root
        server.PORT=httpd.server_address[1]
        worker=threading.Thread(target=httpd.serve_forever,daemon=True)
        worker.start()
        try:
            url=f"http://127.0.0.1:{server.PORT}/api/m045/attempts/reconcile"
            payload=json.dumps({"project_id":fixture.pid,"idempotency_key":"recover-http-1"}).encode()
            headers={"Content-Type":"application/json","Origin":f"http://127.0.0.1:{server.PORT}","X-Studio-Capability":server.CAPABILITY}
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(urllib.request.Request(url,data=payload,headers=headers),timeout=2)
            self.assertEqual(denied.exception.code,403)
            with urllib.request.urlopen(urllib.request.Request(url,data=payload,headers={
                **headers,"Authorization":"Bearer "+fixture.session}),timeout=2) as response:
                recovered=json.loads(response.read())
            self.assertEqual(recovered["state"],"COMMITTED")
            self.assertEqual(recovered["revision"]["revisionId"],outcome["revision"]["revisionId"])
        finally:
            httpd.shutdown()
            httpd.server_close()
            worker.join(timeout=2)
            server.EXPORT_ROOT,server.PORT=old_root,old_port
            fixture.tearDown()

    def test_three_minute_native_cas_and_authorized_audio_reopen(self):
        import test_m045_native_attempt as fixture_module
        import studio_server as server
        import hashlib
        fixture=fixture_module.NativeAttemptTests()
        fixture.setUp()
        try:
            owner=server.make_m045_native_owner(fixture.root)
            def full_length(stage_dir, spec, prompt, lyrics, seed, params):
                output=pathlib.Path(stage_dir)/"output.wav"
                self._wav(output,180)
                return output
            result=owner.execute_attempt(**fixture._kwargs(
                idempotency_key="song-180-1",synthesize_to_stage_fn=full_length))
            self.assertEqual(result["state"],"COMMITTED")
            digest=result["attempt"]["artifact_digest"]
            self.assertEqual(result["attempt"]["media"]["frames"],180*44100)
            physical=server.project_audio_bytes(fixture.root,{
                "projectId":fixture.pid,"revisionId":result["revision"]["revisionId"],
                "artifactId":digest})
            self.assertEqual(hashlib.sha256(physical).hexdigest(),digest)
            new_owner=server.make_m045_native_owner(fixture.root)
            history=new_owner.reconcile_attempt(headers=fixture._kwargs()["headers"],
                project_id=fixture.pid,idempotency_key="song-180-1")
            self.assertEqual(history["revision"]["revisionId"],result["revision"]["revisionId"])
        finally:
            fixture.tearDown()
    def test_three_minutes_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            p=pathlib.Path(directory)/"180.wav"
            self._wav(p,180)
            result=_verify_wav(p)
            self.assertEqual(result["frames"], 180*44100)
            self.assertEqual(result["sample_rate"],44100)

    def test_more_than_210_seconds_rejected_before_decoding(self):
        with tempfile.TemporaryDirectory() as directory:
            p=pathlib.Path(directory)/"211.wav"
            self._wav(p,211)
            with self.assertRaisesRegex(ValueError,"duration|large|boundary"):
                _verify_wav(p)

    def test_provider_supports_210_seconds_not_211(self):
        from m045_eleven_music_provider import ElevenMusicProvider
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            p=ElevenMusicProvider(api_key="test-only")
            with patch("m045_eleven_music_provider.urllib.request.urlopen") as request:
                request.side_effect=RuntimeError("transport invoked")
                with self.assertRaisesRegex(RuntimeError,"transport invoked"):
                    p(directory, {}, "Prompt", "", 0, {"music_length_ms":210000})
                with self.assertRaisesRegex(ValueError,"DURATION"):
                    p(directory, {}, "Prompt", "", 0, {"music_length_ms":211000})

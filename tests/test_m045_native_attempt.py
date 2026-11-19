import hashlib
import io
import json
import pathlib
import sys
import tempfile
import threading
import unittest
import wave
import socketserver
import urllib.error
import urllib.request
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import studio_server as server
from test_m044_operations import OperationTests
from m045_generation_attempt import (
    AttemptLifecycleState,
    AttemptSecurityError,
    GenerationAttemptOwner,
    native_atomic_write_bytes,
)


class NativeAttemptTests(unittest.TestCase):
    def setUp(self):
        self.fixture = OperationTests()
        self.fixture.setUp()
        self.root = self.fixture.root
        self.pid = self.fixture.pid
        self.r1 = self.fixture.r1
        self.bytes = self.fixture.wav()
        self.session = server.issue_studio_session(server.LOCAL_PRINCIPAL_ID)
        self.synth_calls = 0
        self.synth_lock = threading.Lock()

    def tearDown(self):
        server.M045_ATTEMPT_OWNER = None
        server.M045_SYNTHESIZE_TO_STAGE = None
        self.fixture.tearDown()

    def _owner(self, commit_hook=None):
        store = self

        def read_revision(project_id, revision_id):
            manifest = server.project_operation(store.root, {"projectId": project_id})["manifest"]
            directory = store.root / "projects" / project_id
            rid = manifest["currentRevisionId"] if revision_id == "CURRENT" else revision_id
            try:
                revision, _, _ = server.project_revision(store.root, directory, project_id, rid)
            except (ValueError, FileNotFoundError):
                return None
            revision = dict(revision)
            revision["is_current"] = rid == manifest["currentRevisionId"]
            return revision

        def list_revisions(project_id):
            directory = store.root / "projects" / project_id
            manifest = server.project_operation(store.root, {"projectId": project_id})["manifest"]
            out = {}
            for path in sorted((directory / "revisions").glob("*.json")):
                rid = path.stem
                revision, _, _ = server.project_revision(store.root, directory, project_id, rid)
                revision = dict(revision)
                revision["is_current"] = rid == manifest["currentRevisionId"]
                out[rid] = revision
            return out

        def authorize(principal, project_id, capability):
            directory = store.root / "projects" / project_id
            server.authorize_project_owner(directory, project_id, principal, create=False)
            return True

        def publish(data):
            digest = hashlib.sha256(data).hexdigest()
            server._publish_cas_exact(store.root, digest, data)
            return digest

        def commit(**kwargs):
            request = {
                "projectId": kwargs["project_id"],
                "expectedCurrentRevisionId": kwargs["expected_current_revision_id"],
                "songSpec": kwargs["song_spec"],
                "sourceAssetDigests": kwargs.get("source_asset_digests", []),
                "outputArtifactIds": [kwargs["artifact_digest"]],
                "operationId": "m045:" + kwargs["attempt_id"],
                "operationContext": {"kind": "m045_generation", "attemptId": kwargs["attempt_id"]},
            }
            return server.project_operation(store.root, request, commit=True, principal_id=server.LOCAL_PRINCIPAL_ID)

        def synth(stage_dir, song_spec, prompt, lyrics, seed, params):
            with store.synth_lock:
                store.synth_calls += 1
            path = pathlib.Path(stage_dir) / "output.wav"
            path.write_bytes(store.bytes)
            return path

        return GenerationAttemptOwner(
            data_root=self.root,
            resolve_session_principal=lambda token: server.resolve_studio_session(token),
            authorize_project=authorize,
            read_revision=read_revision,
            list_project_revisions=list_revisions,
            publish_cas_object=publish,
            associate_and_commit_revision=commit_hook or commit,
            atomic_write_fn=native_atomic_write_bytes,
        ), synth

    def _kwargs(self, **extra):
        value = {
            "headers": {"Authorization": "Bearer " + self.session},
            "project_id": self.pid,
            "base_revision_id": self.r1["revision"]["revisionId"],
            "expected_current_revision_id": self.r1["revision"]["revisionId"],
            "idempotency_key": "idem-native-1",
            "model_id": "fixture-provider",
            "model_version": "test-1",
            "seed": 7,
            "song_spec": self.fixture.spec,
            "prompt": "native test",
            "synthesize_to_stage_fn": None,
        }
        value.update(extra)
        return value

    def test_missing_auth_and_spoofed_principal_are_rejected(self):
        owner, synth = self._owner()
        kwargs = self._kwargs(synthesize_to_stage_fn=synth)
        with self.assertRaises(AttemptSecurityError):
            owner.execute_attempt(**{**kwargs, "headers": {"X-Sara-Principal": server.LOCAL_PRINCIPAL_ID}})
        with self.assertRaises(AttemptSecurityError):
            owner.execute_attempt(**{**kwargs, "headers": {"Authorization": "Bearer invalid", "X-Sara-Principal": server.LOCAL_PRINCIPAL_ID}})

    def test_identical_idempotency_submissions_execute_once(self):
        owner, synth = self._owner()
        kwargs = self._kwargs(synthesize_to_stage_fn=synth)
        results = []
        errors = []
        def submit():
            try:
                results.append(owner.execute_attempt(**kwargs))
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=submit) for _ in range(4)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertFalse(errors, errors)
        self.assertEqual(self.synth_calls, 1)
        self.assertEqual(len(results), 4)
        self.assertEqual(len({r["revision"]["revisionId"] for r in results}), 1)

    def test_divergent_payload_reusing_idempotency_key_is_rejected(self):
        owner, synth = self._owner()
        owner.execute_attempt(**self._kwargs(synthesize_to_stage_fn=synth))
        with self.assertRaises(server.ProjectConflict):
            owner.execute_attempt(**self._kwargs(prompt="different", synthesize_to_stage_fn=synth))

    def test_stale_expected_revision_is_rejected(self):
        owner, synth = self._owner()
        newer = server.project_operation(self.root, {
            "projectId": self.pid,
            "expectedCurrentRevisionId": self.r1["revision"]["revisionId"],
            "songSpec": self.fixture.spec,
            "sourceAssetDigests": [],
            "outputArtifactIds": [],
        }, commit=True)
        with self.assertRaises(server.ProjectConflict):
            owner.execute_attempt(**self._kwargs(
                expected_current_revision_id=self.r1["revision"]["revisionId"],
                base_revision_id=self.r1["revision"]["revisionId"],
                idempotency_key="stale",
                synthesize_to_stage_fn=synth,
            ))
        self.assertNotEqual(newer["revision"]["revisionId"], self.r1["revision"]["revisionId"])

    def test_synthesis_failure_is_durable_failed_pre_commit(self):
        owner, _ = self._owner()
        def fail(*args):
            raise RuntimeError("GPU_OOM")
        with self.assertRaises(RuntimeError):
            owner.execute_attempt(**self._kwargs(synthesize_to_stage_fn=fail))
        record = owner.reconcile_attempt(
            headers={"Authorization": "Bearer " + self.session},
            project_id=self.pid,
            idempotency_key="idem-native-1",
        )
        self.assertEqual(record["attempt"]["state"], AttemptLifecycleState.FAILED_PRE_COMMIT.value)
        self.assertEqual(record["attempt"]["error_code"], "GPU_OOM")

    def test_post_commit_exception_reconciles_lost_response(self):
        owner, synth = self._owner()
        first = {"done": False}
        real_owner, _ = self._owner()
        def crash_after_commit(**kwargs):
            result = self._owner()[0]  # keep callback path independent of in-memory result
            committed = server.project_operation(self.root, {
                "projectId": self.pid,
                "expectedCurrentRevisionId": kwargs["expected_current_revision_id"],
                "songSpec": kwargs["song_spec"],
                "sourceAssetDigests": [],
                "outputArtifactIds": [kwargs["artifact_digest"]],
                "operationId": "m045:" + kwargs["attempt_id"],
                "operationContext": {"kind": "m045_generation", "attemptId": kwargs["attempt_id"]},
            }, commit=True, principal_id=server.LOCAL_PRINCIPAL_ID)
            raise ConnectionAbortedError("lost response")
        owner, synth = self._owner(commit_hook=crash_after_commit)
        result = owner.execute_attempt(**self._kwargs(synthesize_to_stage_fn=synth))
        self.assertEqual(result["state"], AttemptLifecycleState.COMMITTED.value)
        self.assertTrue(result["reconciled"])

    def test_cold_restart_recovers_historical_revision_and_audio_binding(self):
        owner, synth = self._owner()
        first = owner.execute_attempt(**self._kwargs(synthesize_to_stage_fn=synth))
        r2 = first["revision"]["revisionId"]
        # Advance the project through the canonical owner so r2 becomes historical.
        server.project_operation(self.root, {
            "projectId": self.pid,
            "expectedCurrentRevisionId": r2,
            "songSpec": self.fixture.spec,
            "sourceAssetDigests": [],
            "outputArtifactIds": [],
        }, commit=True)
        owner2, _ = self._owner()
        recovered = owner2.reconcile_attempt(
            headers={"Authorization": "Bearer " + self.session},
            project_id=self.pid,
            idempotency_key="idem-native-1",
        )
        self.assertEqual(recovered["attempt"]["state"], AttemptLifecycleState.ASSOCIATED_HISTORICAL.value)
        artifact = recovered["revision"]["outputArtifactIds"][0]
        self.assertEqual(server.artifact_bytes(self.root, artifact), self.bytes)

    def test_http_endpoint_uses_bearer_session_and_returns_fenced_conflict(self):
        owner, synth = self._owner()
        server.configure_m045_generation(owner, synth)
        old_root, old_port = server.EXPORT_ROOT, server.PORT
        httpd = socketserver.TCPServer(("127.0.0.1", 0), server.StudioHandler)
        server.EXPORT_ROOT = self.root
        server.PORT = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.PORT}/api/m045/attempts"
            payload = {
                "project_id": self.pid,
                "base_revision_id": self.r1["revision"]["revisionId"],
                "expected_current_revision_id": self.r1["revision"]["revisionId"],
                "idempotency_key": "http-idem-1",
                "model_id": "fixture-provider",
                "model_version": "test-1",
                "seed": 9,
                "song_spec": self.fixture.spec,
                "prompt": "http native test",
            }
            base_headers = {
                "Content-Type": "application/json",
                "Origin": f"http://127.0.0.1:{server.PORT}",
                "X-Studio-Capability": server.CAPABILITY,
            }
            body = json.dumps(payload).encode()
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(urllib.request.Request(url, data=body, headers=base_headers), timeout=2)
            self.assertEqual(denied.exception.code, 403)

            spoofed = {**base_headers, "Authorization": "Bearer " + self.session, "X-Sara-Principal": "attacker"}
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=spoofed), timeout=2) as response:
                result = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(result["state"], AttemptLifecycleState.COMMITTED.value)

            stale = {**payload, "idempotency_key": "http-idem-stale", "expected_current_revision_id": self.r1["revision"]["revisionId"]}
            with self.assertRaises(urllib.error.HTTPError) as conflict:
                urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(stale).encode(), headers=spoofed), timeout=2)
            self.assertEqual(conflict.exception.code, 409)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)
            server.EXPORT_ROOT = old_root
            server.PORT = old_port


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import pathlib
import sys
import unittest
import threading
import socketserver
import urllib.error
import urllib.request
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import studio_server as server
from test_m044_operations import OperationTests


class R3RenderDurability(unittest.TestCase):
    def setUp(self):
        self.fixture = OperationTests()
        self.fixture.setUp()
        self.root = self.fixture.root
        self.pid = self.fixture.pid
        self.r1 = self.fixture.r1
        self.r2 = server.project_operation(self.root, self.fixture.request, commit=True)
        self.bytes = self.fixture.wav()
        self.digest = hashlib.sha256(self.bytes).hexdigest()
        self.request = {
            "projectId": self.pid,
            "sourceRevisionId": self.r1["revision"]["revisionId"],
            "operationId": "r3-late-render",
            "filename": "r3-late.wav",
            "subdirectory": "m044",
            "data_bytes": list(self.bytes),
        }

    def tearDown(self):
        self.fixture.tearDown()

    def attempt(self):
        path = self.root / "projects" / self.pid / "render-attempts" / "r3-late-render.json"
        return json.loads(path.read_text())

    def historical_ids(self):
        directory = self.root / "projects" / self.pid
        manifest = json.loads((directory / "ProjectManifest.json").read_text())
        revision, spec, timeline = server.project_revision(
            self.root, directory, self.pid, self.r1["revision"]["revisionId"])
        result = server.historical_result(self.root, directory, manifest, revision, spec, timeline)
        return [x["artifactId"] for x in result.get("historicalOutputBindings", [])]

    def current_revision(self):
        directory = self.root / "projects" / self.pid
        manifest = json.loads((directory / "ProjectManifest.json").read_text())
        return manifest["currentRevisionId"]

    def test_crash_a_identity_is_durable_before_cas_and_history_stays_empty(self):
        def stop(name):
            if name == "render_attempt_validated_not_published":
                raise OSError("crash-a")
        with patch.object(server, "project_boundary", stop):
            with self.assertRaises(OSError):
                server.render_publish_operation(self.root, self.request)
        attempt = self.attempt()
        self.assertEqual(attempt["state"], "VALIDATED_NOT_PUBLISHED")
        self.assertEqual(attempt["artifactDigest"], self.digest)
        self.assertEqual(attempt["intendedCas"], f"objects/{self.digest[:2]}/{self.digest}")
        self.assertFalse((self.root / attempt["intendedCas"]).exists())
        self.assertEqual(self.historical_ids(), [])
        self.assertEqual(self.current_revision(), self.r2["revision"]["revisionId"])
        with self.assertRaises(server.ProjectConflict):
            server.project_audio_bytes(self.root, {
                "projectId": self.pid,
                "revisionId": self.r1["revision"]["revisionId"],
                "artifactId": self.digest,
            })

    def test_crash_b_cas_is_denied_until_fresh_open_reconciles_exactly_once(self):
        def stop(name):
            if name == "render_attempt_artifact_durable":
                raise OSError("crash-b")
        with patch.object(server, "project_boundary", stop):
            with self.assertRaises(OSError):
                server.render_publish_operation(self.root, self.request)
        attempt = self.attempt()
        self.assertEqual(attempt["state"], "ARTIFACT_DURABLE")
        self.assertEqual(server.artifact_bytes(self.root, self.digest), self.bytes)
        self.assertEqual(self.historical_ids(), [])
        with self.assertRaises(server.ProjectConflict):
            server.project_audio_bytes(self.root, {
                "projectId": self.pid,
                "revisionId": self.r1["revision"]["revisionId"],
                "artifactId": self.digest,
            })
        first = server.project_operation(self.root, {"projectId": self.pid})
        self.assertEqual(first["revision"]["revisionId"], self.r2["revision"]["revisionId"])
        self.assertEqual(self.historical_ids(), [self.digest])
        self.assertEqual(server.project_audio_bytes(self.root, {
            "projectId": self.pid,
            "revisionId": self.r1["revision"]["revisionId"],
            "artifactId": self.digest,
        }), self.bytes)
        server.project_operation(self.root, {"projectId": self.pid})
        self.assertEqual(self.historical_ids(), [self.digest])
        self.assertEqual(self.current_revision(), self.r2["revision"]["revisionId"])

    def test_crash_c_bound_history_survives_without_duplicate_or_current_change(self):
        def stop(name):
            if name == "render_attempt_historically_bound":
                raise OSError("crash-c")
        with patch.object(server, "project_boundary", stop):
            with self.assertRaises(OSError):
                server.render_publish_operation(self.root, self.request)
        self.assertEqual(self.historical_ids(), [self.digest])
        server.project_operation(self.root, {"projectId": self.pid})
        server.project_operation(self.root, {"projectId": self.pid})
        self.assertEqual(self.historical_ids(), [self.digest])
        self.assertEqual(self.current_revision(), self.r2["revision"]["revisionId"])

    def test_http_denies_orphan_then_serves_exact_bytes_after_reconciliation(self):
        def stop(name):
            if name == "render_attempt_artifact_durable":
                raise OSError("crash-b")
        with patch.object(server, "project_boundary", stop):
            with self.assertRaises(OSError):
                server.render_publish_operation(self.root, self.request)

        old_root, old_port = server.EXPORT_ROOT, server.PORT
        httpd = socketserver.TCPServer(("127.0.0.1", 0), server.StudioHandler)
        server.EXPORT_ROOT = self.root
        server.PORT = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.PORT}/api/projects/audio"
            payload = json.dumps({
                "projectId": self.pid,
                "revisionId": self.r1["revision"]["revisionId"],
                "artifactId": self.digest,
            }).encode()
            local_session = server.issue_studio_session(server.LOCAL_PRINCIPAL_ID)
            headers = {
                "Content-Type": "application/json",
                "Origin": f"http://127.0.0.1:{server.PORT}",
                "X-Studio-Capability": server.CAPABILITY,
                "X-Studio-Session": local_session,
            }
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(urllib.request.Request(url, data=payload, headers=headers), timeout=2)
            self.assertEqual(denied.exception.code, 403)

            server.project_operation(self.root, {"projectId": self.pid})
            with urllib.request.urlopen(
                    urllib.request.Request(url, data=payload, headers=headers), timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), "audio/wav")
                self.assertEqual(response.read(), self.bytes)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)
            server.EXPORT_ROOT = old_root
            server.PORT = old_port

    def test_concurrent_first_owner_claim_is_immutable(self):
        explicit_pid = "a" * 32
        request = {
            "projectId": explicit_pid,
            "expectedCurrentRevisionId": None,
            "songSpec": self.fixture.spec,
            "sourceAssetDigests": [],
            "outputArtifactIds": [],
        }
        start_gate = threading.Barrier(3)
        outcomes = []
        outcome_lock = threading.Lock()

        def create(principal):
            start_gate.wait(timeout=2)
            try:
                result = server.project_operation(
                    self.root, dict(request), commit=True, principal_id=principal)
                outcome = ("PASS", principal, result["revision"]["revisionId"])
            except server.ProjectConflict as exc:
                outcome = ("DENY", principal, str(exc))
            except Exception as exc:
                outcome = ("ERROR", principal, type(exc).__name__ + ":" + str(exc))
            with outcome_lock:
                outcomes.append(outcome)

        a = threading.Thread(target=create, args=("principal-a",))
        b = threading.Thread(target=create, args=("principal-b",))
        a.start(); b.start(); start_gate.wait(timeout=2)
        a.join(timeout=5); b.join(timeout=5)

        self.assertFalse(a.is_alive() or b.is_alive(), outcomes)
        passes = [row for row in outcomes if row[0] == "PASS"]
        denies = [row for row in outcomes if row[0] == "DENY"]
        self.assertEqual(len(passes), 1, outcomes)
        self.assertEqual(len(denies), 1, outcomes)
        self.assertFalse([row for row in outcomes if row[0] == "ERROR"], outcomes)

        directory = self.root / "projects" / explicit_pid
        owner = json.loads((directory / "ProjectOwner.json").read_text())
        self.assertEqual(owner["principalId"], passes[0][1])

        manifest = json.loads((directory / "ProjectManifest.json").read_text())
        self.assertEqual(manifest["currentRevisionId"], passes[0][2])
        revisions = list((directory / "revisions").glob("*.json"))
        self.assertEqual(len(revisions), 1)

        # Ownership is immutable after first claim.
        with self.assertRaises(server.ProjectConflict):
            server.project_operation(
                self.root, {"projectId": explicit_pid},
                principal_id=denies[0][1])
        owner_after = json.loads((directory / "ProjectOwner.json").read_text())
        self.assertEqual(owner_after, owner)

    def test_two_principal_http_audio_authorization(self):
        principal_a = "principal-a"
        principal_b = "principal-b"
        session_a = server.issue_studio_session(principal_a)
        session_b = server.issue_studio_session(principal_b)

        project_a = server.project_operation(self.root, {
            "expectedCurrentRevisionId": None,
            "songSpec": self.fixture.spec,
            "sourceAssetDigests": [],
            "outputArtifactIds": [],
        }, commit=True, principal_id=principal_a)
        project_b = server.project_operation(self.root, {
            "expectedCurrentRevisionId": None,
            "songSpec": self.fixture.spec,
            "sourceAssetDigests": [],
            "outputArtifactIds": [],
        }, commit=True, principal_id=principal_b)

        bytes_a = self.fixture.wav()
        bytes_b = self.fixture.wav()[:44] + bytes([7, 0, 8, 0]) * 32
        out_a = server.render_publish_operation(self.root, {
            "projectId": project_a["manifest"]["projectId"],
            "sourceRevisionId": project_a["revision"]["revisionId"],
            "operationId": "principal-a-render",
            "filename": "a.wav", "subdirectory": "m044", "data_bytes": list(bytes_a),
        }, principal_id=principal_a)
        out_b = server.render_publish_operation(self.root, {
            "projectId": project_b["manifest"]["projectId"],
            "sourceRevisionId": project_b["revision"]["revisionId"],
            "operationId": "principal-b-render",
            "filename": "b.wav", "subdirectory": "m044", "data_bytes": list(bytes_b),
        }, principal_id=principal_b)

        aid_a = out_a["revision"]["outputArtifactIds"][0]
        aid_b = out_b["revision"]["outputArtifactIds"][0]

        old_root, old_port = server.EXPORT_ROOT, server.PORT
        httpd = socketserver.TCPServer(("127.0.0.1", 0), server.StudioHandler)
        server.EXPORT_ROOT = self.root
        server.PORT = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        def request(project, revision, artifact, session=None):
            url = f"http://127.0.0.1:{server.PORT}/api/projects/audio"
            payload = json.dumps({
                "projectId": project, "revisionId": revision, "artifactId": artifact
            }).encode()
            headers = {
                "Content-Type": "application/json",
                "Origin": f"http://127.0.0.1:{server.PORT}",
                "X-Studio-Capability": server.CAPABILITY,
            }
            if session is not None:
                headers["X-Studio-Session"] = session
            return urllib.request.urlopen(
                urllib.request.Request(url, data=payload, headers=headers), timeout=2)

        try:
            with request(project_a["manifest"]["projectId"], out_a["revision"]["revisionId"], aid_a, session_a) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), bytes_a)
            with request(project_b["manifest"]["projectId"], out_b["revision"]["revisionId"], aid_b, session_b) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), bytes_b)

            for session, project, revision, artifact in [
                (session_a, project_b["manifest"]["projectId"], out_b["revision"]["revisionId"], aid_b),
                (session_b, project_a["manifest"]["projectId"], out_a["revision"]["revisionId"], aid_a),
                (None, project_a["manifest"]["projectId"], out_a["revision"]["revisionId"], aid_a),
                (None, project_b["manifest"]["projectId"], out_b["revision"]["revisionId"], aid_b),
            ]:
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    request(project, revision, artifact, session)
                self.assertEqual(denied.exception.code, 403)

            # Exact identifiers do not override caller ownership.
            with self.assertRaises(urllib.error.HTTPError) as denied:
                request(project_b["manifest"]["projectId"], out_b["revision"]["revisionId"], aid_b, session_a)
            self.assertEqual(denied.exception.code, 403)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)
            server.EXPORT_ROOT = old_root
            server.PORT = old_port

    def test_digest_knowledge_alone_is_never_authorization(self):
        other = server.project_operation(self.root, {
            "expectedCurrentRevisionId": None,
            "songSpec": self.fixture.spec,
            "sourceAssetDigests": [],
            "outputArtifactIds": [],
        }, commit=True)
        server.persist_export(self.root, "known.wav", "m044", self.bytes)
        with self.assertRaises(server.ProjectConflict):
            server.project_audio_bytes(self.root, {
                "projectId": other["manifest"]["projectId"],
                "revisionId": other["revision"]["revisionId"],
                "artifactId": self.digest,
            })


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import pathlib
import sys
import unittest
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

    def test_digest_knowledge_alone_is_never_authorization(self):
        other = OperationTests()
        other.setUp()
        try:
            server.persist_export(self.root, "known.wav", "m044", self.bytes)
            with self.assertRaises(server.ProjectConflict):
                server.project_audio_bytes(self.root, {
                    "projectId": other.pid,
                    "revisionId": other.r1["revision"]["revisionId"],
                    "artifactId": self.digest,
                })
        finally:
            other.tearDown()


if __name__ == "__main__":
    unittest.main()

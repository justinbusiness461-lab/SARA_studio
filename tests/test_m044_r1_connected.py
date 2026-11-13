import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import studio_server as server
import test_m044_operations as ops


class ConnectedR1RenderTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ops.OperationTests()
        self.fixture.setUp()
        self.root = self.fixture.root
        self.r1 = self.fixture.r1
        self.pid = self.fixture.pid

    def tearDown(self):
        self.fixture.tearDown()

    def test_render_endpoint_can_derive_exact_wav_from_authoritative_revision(self):
        wav = self.fixture.wav()
        with patch.object(server, "render_authoritative_revision_bytes", return_value=wav, create=True):
            result = server.render_publish_operation(self.root, {
                "projectId": self.pid,
                "sourceRevisionId": self.r1["revision"]["revisionId"],
                "operationId": "render:" + self.r1["revision"]["revisionId"],
                "filename": "r1.wav",
                "subdirectory": "m044",
            })
        self.assertEqual(result["manifest"]["currentRevisionId"], result["revision"]["revisionId"])
        self.assertEqual(len(result["revision"]["outputArtifactIds"]), 1)
        artifact = result["revision"]["outputArtifactIds"][0]
        self.assertEqual(server.artifact_bytes(self.root, artifact), wav)
        self.assertEqual(server.project_audio_bytes(self.root, {
            "projectId": self.pid,
            "revisionId": result["revision"]["revisionId"],
            "artifactId": artifact,
        }), wav)


if __name__ == "__main__":
    unittest.main()
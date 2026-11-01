"""Operation receipts extend the existing immutable ProjectRevision owner."""
import copy
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
import studio_server as server


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.spec = {'timebase': {}, 'structure': {'sections': []}, 'tracks': []}
        self.r1 = server.project_operation(self.root, {'songSpec': self.spec, 'expectedCurrentRevisionId': None}, commit=True)
        self.pid = self.r1['manifest']['projectId']
        self.request = {'projectId': self.pid, 'expectedCurrentRevisionId': self.r1['revision']['revisionId'],
                        'songSpec': {**self.spec, 'title': 'edited'}, 'operationId': 'bass-edit-001'}

    def test_same_request_replay_returns_original_revision_without_advancing(self):
        first = server.project_operation(self.root, self.request, commit=True)
        replay = server.project_operation(self.root, self.request, commit=True)
        self.assertEqual(first, replay)

    def test_changed_payload_same_id_rejects(self):
        server.project_operation(self.root, self.request, commit=True)
        changed = copy.deepcopy(self.request)
        changed['songSpec']['title'] = 'different'
        with self.assertRaisesRegex(server.ProjectConflict, 'operation'):
            server.project_operation(self.root, changed, commit=True)

    def test_replay_after_later_revision_does_not_reselect_old_revision(self):
        first = server.project_operation(self.root, self.request, commit=True)
        next_revision = server.project_operation(self.root, {**self.request, 'operationId': 'second',
            'expectedCurrentRevisionId': first['revision']['revisionId']}, commit=True)
        replay = server.project_operation(self.root, self.request, commit=True)
        self.assertEqual(replay['revision']['revisionId'], first['revision']['revisionId'])
        self.assertEqual(replay['manifest'], next_revision['manifest'])

    def test_stale_render_cannot_bind_to_new_composition(self):
        first = server.project_operation(self.root, self.request, commit=True)
        audio = server.persist_export(self.root, 'old.wav', 'test', b'old-render')['sha256']
        with self.assertRaises(server.ProjectConflict):
            server.project_operation(self.root, {'projectId': self.pid, 'expectedCurrentRevisionId': self.r1['revision']['revisionId'],
                'songSpec': self.spec, 'outputArtifactIds': [audio], 'operationId': 'late-render'}, commit=True)
        opened = server.project_operation(self.root, {'projectId': self.pid})
        self.assertEqual(opened['revision'], first['revision'])

    def test_invalid_operation_id_rejects(self):
        with self.assertRaises(ValueError):
            server.project_operation(self.root, {**self.request, 'operationId': '../unsafe'}, commit=True)

    def test_interruption_before_pointer_promotion_keeps_previous_authority(self):
        def interrupt(boundary):
            if boundary == 'before_manifest_promotion': raise OSError('interrupted')
        with patch.object(server, 'project_boundary', interrupt):
            with self.assertRaises(OSError): server.project_operation(self.root, self.request, commit=True)
        self.assertEqual(server.project_operation(self.root, {'projectId': self.pid})['revision'], self.r1['revision'])
        retried = server.project_operation(self.root, self.request, commit=True)
        self.assertEqual(retried['revision']['parentRevisionId'], self.r1['revision']['revisionId'])

    def test_uncertain_result_after_promotion_recovers_by_replay(self):
        def interrupt(boundary):
            if boundary == 'after_manifest_promotion': raise OSError('reply lost')
        with patch.object(server, 'project_boundary', interrupt):
            with self.assertRaises(OSError): server.project_operation(self.root, self.request, commit=True)
        current = server.project_operation(self.root, {'projectId': self.pid})
        self.assertEqual(server.project_operation(self.root, self.request, commit=True), current)

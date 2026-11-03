"""M044 operation identity, replay, and late-render fencing."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import studio_server as server


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.spec = {
            'song_id': 'm044-ops', 'title': 'ops',
            'timebase': {'ticks_per_quarter_note': 960, 'initial_bpm': 96, 'key': 'E minor', 'meter': '4/4', 'sample_rate': 44100},
            'structure': {'sections': [{'id': 's0', 'name': 'A', 'start_tick': 0, 'end_tick': 3840},
                                       {'id': 's1', 'name': 'B', 'start_tick': 3840, 'end_tick': 7680}]},
            'tracks': [{'track_id': 'bass', 'type': 'INSTRUMENT', 'events': [
                {'type': 'NOTE_ON', 'tick': 0, 'note_number': 36, 'velocity': 100, 'duration_ticks': 480},
                {'type': 'NOTE_ON', 'tick': 4000, 'note_number': 40, 'velocity': 100, 'duration_ticks': 480}]}]}
        self.r1 = server.project_operation(self.root, {'songSpec': self.spec, 'sourceAssetDigests': [], 'outputArtifactIds': []}, commit=True)
        self.pid = self.r1['manifest']['projectId']
        edited = {
            **self.spec,
            'tracks': [{'track_id': 'bass', 'type': 'INSTRUMENT', 'events': [
                {'type': 'NOTE_ON', 'tick': 0, 'note_number': 36, 'velocity': 100, 'duration_ticks': 480},
                {'type': 'NOTE_ON', 'tick': 4000, 'note_number': 28, 'velocity': 100, 'duration_ticks': 480}]}]}
        self.request = {
            'projectId': self.pid,
            'expectedCurrentRevisionId': self.r1['revision']['revisionId'],
            'songSpec': edited,
            'sourceAssetDigests': [],
            'outputArtifactIds': [],
            'operationId': 'bass-octave-001',
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_request_replay_returns_original_revision_without_advancing(self):
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

    def test_changed_payload_same_id_rejects(self):
        server.project_operation(self.root, self.request, commit=True)
        with self.assertRaises(server.ProjectConflict):
            server.project_operation(self.root, {**self.request, 'songSpec': {**self.request['songSpec'], 'title': 'other'}}, commit=True)

    def test_replay_after_later_revision_does_not_reselect_old_revision(self):
        first = server.project_operation(self.root, self.request, commit=True)
        server.project_operation(self.root, {**self.request, 'operationId': 'second',
            'expectedCurrentRevisionId': first['revision']['revisionId']}, commit=True)
        replay = server.project_operation(self.root, self.request, commit=True)
        self.assertEqual(replay['revision']['revisionId'], first['revision']['revisionId'])

    def test_late_render_binds_historical_artifact_to_r1(self):
        """Late R1 render must not promote R2, but must remain retrievable on R1."""
        r1 = self.r1
        r2 = server.project_operation(self.root, self.request, commit=True)
        self.assertEqual(r2['manifest']['currentRevisionId'], r2['revision']['revisionId'])
        self.assertNotEqual(r2['revision']['revisionId'], r1['revision']['revisionId'])
        audio = server.persist_export(self.root, 'late-r1.wav', 'test', b'late-r1-pcm-bytes')['sha256']
        bound = server.project_operation(self.root, {
            'projectId': self.pid,
            'expectedCurrentRevisionId': r1['revision']['revisionId'],
            'songSpec': r1['songSpec'],
            'sourceAssetDigests': r1['revision'].get('sourceAssetDigests', []),
            'outputArtifactIds': [audio],
            'operationId': 'late-r1-render',
            'operationContext': {'kind': 'render', 'sourceRevisionId': r1['revision']['revisionId']},
        }, commit=True)
        opened = server.project_operation(self.root, {'projectId': self.pid})
        self.assertEqual(opened['manifest']['currentRevisionId'], r2['revision']['revisionId'])
        self.assertEqual(opened['revision']['revisionId'], r2['revision']['revisionId'])
        hist = server.project_operation(self.root, {'projectId': self.pid, 'revisionId': r1['revision']['revisionId']})
        self.assertEqual(hist['revision']['revisionId'], r1['revision']['revisionId'])
        self.assertIn(audio, hist['revision']['outputArtifactIds'])
        self.assertEqual(server.artifact_bytes(self.root, audio), b'late-r1-pcm-bytes')
        again = server.project_operation(self.root, {
            'projectId': self.pid,
            'expectedCurrentRevisionId': r1['revision']['revisionId'],
            'songSpec': r1['songSpec'],
            'sourceAssetDigests': r1['revision'].get('sourceAssetDigests', []),
            'outputArtifactIds': [audio],
            'operationId': 'late-r1-render',
            'operationContext': {'kind': 'render', 'sourceRevisionId': r1['revision']['revisionId']},
        }, commit=True)
        self.assertEqual(again['manifest']['currentRevisionId'], r2['revision']['revisionId'])
        self.assertIn(audio, again['revision']['outputArtifactIds'])
        other = server.persist_export(self.root, 'other.wav', 'test', b'other-bytes')['sha256']
        with self.assertRaises(server.ProjectConflict):
            server.project_operation(self.root, {
                'projectId': self.pid,
                'expectedCurrentRevisionId': r1['revision']['revisionId'],
                'songSpec': r1['songSpec'],
                'outputArtifactIds': [other],
                'operationId': 'late-r1-render',
                'operationContext': {'kind': 'render', 'sourceRevisionId': r1['revision']['revisionId']},
            }, commit=True)

    def test_stale_non_render_still_rejects(self):
        r1 = self.r1
        server.project_operation(self.root, self.request, commit=True)
        with self.assertRaises(server.ProjectConflict):
            server.project_operation(self.root, {
                'projectId': self.pid,
                'expectedCurrentRevisionId': r1['revision']['revisionId'],
                'songSpec': r1['songSpec'],
                'outputArtifactIds': [],
                'operationId': 'stale-edit',
            }, commit=True)

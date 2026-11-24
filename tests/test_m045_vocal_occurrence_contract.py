"""Engineer #1 R30: Studio lyric-to-vocal occurrence contract (fail closed)."""
import copy
import unittest
from m045_vocal_occurrence_contract import (
    VocalOccurrenceHeld, project_occurrences, require_verified_vocal_onsets,
)


def studio_snapshot():
    # Grounded in the existing M043 LyricTimelineRevision key contract.
    return {
        'manifest': {'projectId': 'p' * 32, 'currentRevisionId': 'r' * 64},
        'revision': {'projectId': 'p' * 32, 'revisionId': 'r' * 64,
                     'lyricTimelineDigest': 'l' * 64},
        'lyricTimeline': {
            'revisionId': 'q' * 64, 'sourceArtifactId': 'a' * 64,
            'sourceAudioDigest': 'b' * 64, 'sourceSampleRate': 44100,
            'sourceChannels': 2, 'decodedFrameCount': 441000,
            'status': 'corrected', 'words': [
                {'id': 'w0', 'text': 'rise', 'decodedSampleStart': 44100,
                 'decodedSampleEnd': 55000},
                {'id': 'w1', 'text': 'rise', 'decodedSampleStart': 90000,
                 'decodedSampleEnd': 105000},
                {'id': 'w2', 'text': 'again', 'decodedSampleStart': 120000,
                 'decodedSampleEnd': 144000},
            ]}}


def proposal():
    return {'expectedProjectRevisionId': 'r' * 64,
            'expectedLyricRevisionId': 'q' * 64,
            'expectedSourceArtifactId': 'a' * 64,
            'expectedSourceAudioDigest': 'b' * 64,
            'occurrences': [
                {'wordId': 'w0', 'proposedOnsetSample': 44500, 'proposedEndSample': 54000,
                 'method': 'candidate_audio_assisted'},
                {'wordId': 'w1', 'proposedOnsetSample': 90100, 'proposedEndSample': 104000,
                 'method': 'candidate_audio_assisted'},
            ]}


class StudioVocalOccurrenceContract(unittest.TestCase):
    def test_same_word_text_keeps_separate_studio_word_identity(self):
        x = project_occurrences(studio_snapshot(), proposal())
        self.assertEqual([v['wordId'] for v in x['candidateOccurrences']], ['w0','w1'])
        self.assertEqual(x['verificationState'], 'VOCAL_ONSET_UNVERIFIED')
        self.assertEqual(x['sourceSampleRate'], 44100)
        self.assertEqual(x['lyricTimelineRevisionId'], 'q' * 64)
        self.assertEqual(x['projectRevisionId'], 'r' * 64)
        self.assertFalse(x['productionQualified'])

    def test_wrong_lyric_revision_rejected(self):
        q = proposal(); q['expectedLyricRevisionId'] = 'z' * 64
        with self.assertRaises(VocalOccurrenceHeld): project_occurrences(studio_snapshot(), q)

    def test_wrong_studio_project_revision_rejected(self):
        q = proposal(); q['expectedProjectRevisionId'] = 'z' * 64
        with self.assertRaises(VocalOccurrenceHeld): project_occurrences(studio_snapshot(), q)

    def test_cross_artifact_or_decoded_audio_rejected(self):
        for key in ['expectedSourceArtifactId', 'expectedSourceAudioDigest']:
            q = proposal(); q[key] = 'z' * 64
            with self.subTest(key=key), self.assertRaises(VocalOccurrenceHeld):
                project_occurrences(studio_snapshot(), q)

    def test_unknown_or_absent_lyric_words_fail_closed(self):
        for status, words in [('unknown', []), ('guided_candidate', [])]:
            s = studio_snapshot(); s['lyricTimeline']['status'] = status; s['lyricTimeline']['words'] = words
            with self.subTest(status=status), self.assertRaises(VocalOccurrenceHeld):
                project_occurrences(s, proposal())

    def test_unlisted_occurrence_rejected_not_text_matched(self):
        q = proposal(); q['occurrences'][0]['wordId'] = 'new-rise'
        with self.assertRaises(VocalOccurrenceHeld): project_occurrences(studio_snapshot(), q)

    def test_duplicate_occurrence_identity_rejected(self):
        q = proposal(); q['occurrences'][1]['wordId'] = 'w0'
        with self.assertRaises(VocalOccurrenceHeld): project_occurrences(studio_snapshot(), q)

    def test_out_of_range_and_impossible_onset_rejected(self):
        for bad in [-1, 0, 441000, True, 44.1]:
            q = proposal(); q['occurrences'][0]['proposedOnsetSample'] = bad
            with self.subTest(bad=bad), self.assertRaises(VocalOccurrenceHeld):
                project_occurrences(studio_snapshot(), q)
        q = proposal(); q['occurrences'][0]['proposedEndSample'] = 44500
        with self.assertRaises(VocalOccurrenceHeld): project_occurrences(studio_snapshot(), q)

    def test_proposals_cannot_claim_verified_or_trust_fake_certificate(self):
        for forgery in [{'verificationState': 'VERIFIED'},
                        {'productionQualified': True},
                        {'independentGroundTruth': True},
                        {'attestation': {'verified': True}}]:
            q = {**proposal(), **forgery}
            with self.subTest(forgery=forgery), self.assertRaises(VocalOccurrenceHeld):
                project_occurrences(studio_snapshot(), q)

    def test_candidate_cannot_be_exported_as_qualified_cinema_timing(self):
        p = project_occurrences(studio_snapshot(), proposal())
        with self.assertRaisesRegex(VocalOccurrenceHeld, 'VOCAL_ONSET_UNVERIFIED'):
            require_verified_vocal_onsets(p)

    def test_studio_word_boundaries_not_confused_with_verified_vocal_attack(self):
        q = proposal(); q['occurrences'][0]['proposedOnsetSample'] = 54500; q['occurrences'][0]['proposedEndSample'] = 54999
        p = project_occurrences(studio_snapshot(), q)
        self.assertEqual(p['candidateOccurrences'][0]['proposedOnsetSample'], 54500)
        self.assertEqual(p['verificationState'], 'VOCAL_ONSET_UNVERIFIED')

    def test_no_mutation_of_studio_immutable_project_or_input(self):
        s, q = studio_snapshot(), proposal(); old_s, old_q = copy.deepcopy(s), copy.deepcopy(q)
        project_occurrences(s, q)
        self.assertEqual(s, old_s); self.assertEqual(q, old_q)

    def test_no_client_supplied_revision_identity_or_reference_confidence(self):
        q = proposal()
        for key, value in [('sourceSampleRate', 48000),('confidence',.99),('lyricTimelineRevisionId','z'*64),('frame24', 2)]:
            with self.subTest(key=key), self.assertRaises(VocalOccurrenceHeld):
                project_occurrences(studio_snapshot(), {**q, key:value})


if __name__ == '__main__': unittest.main()

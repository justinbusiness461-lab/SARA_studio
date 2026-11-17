import io
import struct
import unittest
import wave

from studio_acceptance import ContractFailure, verify_wav, compare_revisions, verify_tenant_observations


def wav(frames, channels=2, rate=44100):
    out=io.BytesIO()
    with wave.open(out,'wb') as f:
        f.setnchannels(channels);f.setsampwidth(2);f.setframerate(rate)
        f.writeframes(b''.join(struct.pack('<h',v) * channels for v in frames))
    return out.getvalue()


def sample_events():
    return {'evidence_kind':'OBSERVED_HTTP', 'target_commit':'abc123def456', 'target_url_id':'local-nasa-studio',
            'observations':[{'case':k, 'status':(200 if k=='A_READ_OWN' else 401 if k.startswith('ANON') else 404), 'response_excerpt':''} for k in
            ['A_READ_OWN','B_READ_A','ANON_READ_A','B_MUTATE_A','ANON_MUTATE_A','B_ARTIFACT_A','B_HISTORY_A','B_FORGED_OWNER_A']]}


class AudioAdmission(unittest.TestCase):
    def test_actual_stereo_pcm16_decodes(self):
        r=verify_wav(wav([0,400,-500,1000]))
        self.assertEqual((r['sample_rate'],r['channels'],r['frames']), (44100,2,4))
        self.assertFalse(r['silent'])
        self.assertEqual(r['left_right_correlation'],1)

    def test_filename_cannot_upgrade_non_wav_bytes(self):
        with self.assertRaises(ContractFailure): verify_wav(b'late-r1-pcm-bytes')

    def test_truncated_wav_rejected(self):
        with self.assertRaises(ContractFailure): verify_wav(wav([100]*10)[:-1])

    def test_riff_size_mismatch_rejected(self):
        blob=bytearray(wav([100]*10));struct.pack_into('<I',blob,4,42)
        with self.assertRaisesRegex(ContractFailure,'RIFF byte count'):verify_wav(bytes(blob))

    def test_invalid_channel_metadata_rejected(self):
        blob=bytearray(wav([100]*10));struct.pack_into('<H',blob,22,3)
        with self.assertRaises(ContractFailure):verify_wav(bytes(blob))

    def test_invalid_block_align_rejected(self):
        blob=bytearray(wav([100]*10));struct.pack_into('<H',blob,32,2)
        with self.assertRaises(ContractFailure):verify_wav(bytes(blob))

    def test_valid_distinct_r1_r2_target_edit(self):
        original=[100]*100;edited=original[:];edited[40:60]=[200]*20
        r=compare_revisions(wav(original),wav(edited),40,60)
        self.assertEqual((r['target_changed_frames'],r['outside_changed_frames']),(20,0))

    def test_unrelated_frames_changed_is_rejected(self):
        original=[100]*100;edited=original[:];edited[10]=200;edited[40]=200
        with self.assertRaisesRegex(ContractFailure,'unrelated PCM'): compare_revisions(wav(original),wav(edited),40,60)

    def test_identical_audio_is_not_a_real_edit(self):
        data=wav([100]*100)
        with self.assertRaisesRegex(ContractFailure,'identical audio'): compare_revisions(data,data,40,60)

    def test_tail_window_is_explicit(self):
        original=[100]*100;edited=original[:];edited[41]=200;edited[61]=200
        self.assertEqual(compare_revisions(wav(original),wav(edited),40,60,2)['outside_changed_frames'],0)
        with self.assertRaises(ContractFailure):compare_revisions(wav(original),wav(edited),40,60)


class TenantContract(unittest.TestCase):
    def test_complete_two_principal_observation(self):
        self.assertEqual(verify_tenant_observations(sample_events())['observed_case_count'],8)

    def test_no_evidence_without_observations(self):
        d=sample_events();d['observations']=[]
        with self.assertRaisesRegex(ContractFailure,'incomplete'):verify_tenant_observations(d)

    def test_cross_tenant_read_success_fails(self):
        d=sample_events();next(x for x in d['observations'] if x['case']=='B_READ_A')['status']=200
        with self.assertRaisesRegex(ContractFailure,'B_READ_A'):verify_tenant_observations(d)

    def test_response_leaking_protected_canary_fails(self):
        d=sample_events();next(x for x in d['observations'] if x['case']=='B_READ_A')['response_excerpt']='TENANT_A_SECRET_CANARY'
        with self.assertRaisesRegex(ContractFailure,'leaked'):verify_tenant_observations(d)

    def test_duplicate_observation_is_rejected(self):
        d=sample_events();d['observations'].append(d['observations'][0])
        with self.assertRaisesRegex(ContractFailure,'duplicate'):verify_tenant_observations(d)


if __name__=='__main__':unittest.main()

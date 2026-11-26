"""E2 only: synthetic trusted keys and artificial Studio WAV; NEVER real DENIAL_01."""
import base64, hashlib, io, json, sys, unittest, wave, types
from unittest.mock import patch
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m045_v3_signed_occurrence import (
    StudioEvidenceDenied, canonical_bytes, digest_hex,
    verify_vocal_evidence, verify_vocal_evidence_from_studio, sign_studio_receipt, verify_studio_receipt,
)

def fixture():
    issuer=Ed25519PrivateKey.generate(); observer=Ed25519PrivateKey.generate()
    raw=b'RAW RECORDING BYTES\0NONPRODUCTION'; sr=48000; channels=2; frames=48000*5
    output=io.BytesIO()
    with wave.open(output,'wb') as w:
        w.setnchannels(channels);w.setsampwidth(2);w.setframerate(sr);w.writeframes((b'\x00\x01'*channels)*frames)
    wav=output.getvalue(); pcm=(b'\x00\x01'*channels)*frames
    original=hashlib.sha256(raw).hexdigest(); wavsha=hashlib.sha256(wav).hexdigest(); pcmsha=hashlib.sha256(pcm).hexdigest()
    project={
        'manifest':{'projectId':'project-1','currentRevisionId':'revision-1'},
        'revision':{'projectId':'project-1','revisionId':'revision-1','sourceAssetDigests':[original,wavsha],
                    'outputArtifactIds':[wavsha],'lyricTimelineDigest':'l'*64},
        'lyricTimeline':{'revisionId':'lyric-1','sourceArtifactId':wavsha,'sourceAudioDigest':pcmsha,
                         'sourceSampleRate':sr,'sourceChannels':channels,'decodedFrameCount':frames,
                         'words':[{'id':'denial-chorus-w001','text':'denial','decodedSampleStart':2400,'decodedSampleEnd':5000}]}
    }
    window={'observationWindowId':'window-1','occurrenceId':'DENIAL_01',
            'sourceDecodedAudioArtifactId':wavsha,'sourcePcmDigest':pcmsha,
            'sourceStartSample':'0','sourceEndSampleExclusive':str(9000), 'boundaryStatus':'FULLY_OBSERVED'}
    observation={'observationWindowId':'window-1','occurrenceId':'DENIAL_01',
        'localOnsetSample':'3000','preOnsetContextSample':'2400','onsetVisibility':'OBSERVED_INSIDE_WINDOW',
        'sourcePcmDigest':pcmsha, 'windowDigestHex':digest_hex(window),
        'observerPrincipalId':'independent-observer','observerEvidenceRefs':['review-evidence-hash']}
    obsSig=base64.b64encode(observer.sign(canonical_bytes(observation))).decode('ascii')
    evidence={'window':window,'observation':observation,'witnessAttestation':{'algorithm':'ED25519','keyId':'observer-key','signatureBase64':obsSig}}
    grant={'authorizationGrantId':'issuer-grant','principalId':'studio-issuer','current':True,
           'revocationEpoch':'3','observedAtEpochMs':'100','expiresAtEpochMs':'1000'}
    payload={'occurrenceId':'DENIAL_01','lyricTokenRef':'denial-chorus-w001',
        'sourceProjectRevisionId':'revision-1','sourceAudioArtifactId':original,'sourceAudioArtifactDigest':original,
        'decodedAudioArtifactId':wavsha,'decodedPcmDigest':pcmsha,'sourceSampleRate':'48000','onsetSample':'3000',
        'coordinateSystem':'PCM_ARTIFACT_START','observationWindowId':'window-1',
        'boundaryStatus':'FULLY_OBSERVED','onsetVisibility':'OBSERVED_INSIDE_WINDOW',
        'issuerPrincipalId':'studio-issuer','issuerVersion':'3','authorizationGrantId':'issuer-grant',
        'observationEvidenceDigest':digest_hex(observation)}
    signed={'schemaId':'sj3.studio.vocal-occurrence','schemaVersion':3,'payload':payload,
        'payloadDigestHex':digest_hex(payload),
        'attestation':{'algorithm':'ED25519','keyId':'issuer-key','signatureBase64':base64.b64encode(issuer.sign(canonical_bytes(payload))).decode('ascii')}}
    keys={'issuer':issuer.public_key(), 'observer':observer.public_key()}
    return locals()

class SignedStudioV3(unittest.TestCase):
    def check(self,x):
        return verify_vocal_evidence(x['signed'],studio_project=x['project'],source_audio_bytes=x['raw'],
            decoded_wav_bytes=x['wav'],evidence=x['evidence'],grant=x['grant'],
            trusted_issuer_key=x['keys']['issuer'],trusted_observer_key=x['keys']['observer'],trusted_issuer_key_id='issuer-key',trusted_observer_key_id='observer-key')
    def test_lawful_host_authorization_denial_precedes_any_cas_read(self):
        x=fixture();reads=[]
        def denial(*args,**kw):
            reads.append('auth');raise PermissionError('not project member')
        stub=types.SimpleNamespace(project_operation=denial,
            project_audio_bytes=lambda *a,**k:reads.append('audio'),
            artifact_bytes=lambda *a,**k:reads.append('cas'))
        with patch.dict(sys.modules,{'studio_server':stub}):
            with self.assertRaisesRegex(StudioEvidenceDenied,'STUDIO_PROJECT_AUTHORIZATION_DENIED'):
                verify_vocal_evidence_from_studio('private-root','principal-1','project-1','revision-1',
                    x['signed'],x['evidence'],x['grant'],x['keys']['issuer'],x['keys']['observer'],
                    'issuer-key','observer-key')
        self.assertEqual(reads,['auth'])
    def test_host_reads_exact_selected_revision_before_authorized_cas(self):
        x=fixture();reads=[]
        def project(root,req,principal_id=None):
            reads.append('auth')
            self.assertEqual((principal_id,req),('principal-1',{'projectId':'project-1','revisionId':'revision-1'}))
            return x['project']
        def audio(root,req,principal_id=None):
            reads.append('wav');self.assertEqual(req['artifactId'],hashlib.sha256(x['wav']).hexdigest());return x['wav']
        def cas(root,aid):
            reads.append('cas');self.assertEqual(aid,hashlib.sha256(x['raw']).hexdigest());return x['raw']
        stub=types.SimpleNamespace(project_operation=project,project_audio_bytes=audio,artifact_bytes=cas)
        with patch.dict(sys.modules,{'studio_server':stub}):
            p=verify_vocal_evidence_from_studio('private-root','principal-1','project-1','revision-1',
                x['signed'],x['evidence'],x['grant'],x['keys']['issuer'],x['keys']['observer'],
                'issuer-key','observer-key')
        self.assertEqual(p['onsetSample'],'3000')
        self.assertEqual(reads,['auth','wav','cas'])

    def test_authentic_synthetic_structural_evidence(self):
        x=fixture();p=self.check(x);self.assertEqual(p['onsetSample'],'3000')
    def test_forged_issuer_signature_fails(self):
        x=fixture();x['signed']['attestation']['signatureBase64']=base64.b64encode(b'0'*64).decode()
        with self.assertRaisesRegex(StudioEvidenceDenied,'OCCURRENCE_SIGNATURE_INVALID'):self.check(x)
    def test_forged_independent_witness_fails(self):
        x=fixture();x['evidence']['witnessAttestation']['signatureBase64']=base64.b64encode(b'0'*64).decode()
        with self.assertRaisesRegex(StudioEvidenceDenied,'WITNESS_SIGNATURE_INVALID'):self.check(x)
    def test_same_observer_and_issuer_key_not_independent(self):
        x=fixture();x['keys']['observer']=x['keys']['issuer']
        with self.assertRaises(StudioEvidenceDenied):self.check(x)
    def test_observation_onset_derived_not_asserted(self):
        x=fixture();x['signed']['payload']['onsetSample']='3001'
        x['signed']['payloadDigestHex']=digest_hex(x['signed']['payload'])
        x['signed']['attestation']['signatureBase64']=base64.b64encode(x['issuer'].sign(canonical_bytes(x['signed']['payload']))).decode()
        with self.assertRaisesRegex(StudioEvidenceDenied,'ONSET_NOT_DERIVED'):self.check(x)
    def test_reject_head_truncated_even_signed(self):
        x=fixture();x['evidence']['window']['boundaryStatus']='POSSIBLE_HEAD_TRUNCATION'
        with self.assertRaises(StudioEvidenceDenied):self.check(x)
    def test_no_pre_onset_context_rejected(self):
        x=fixture();x['evidence']['observation']['preOnsetContextSample']='3000'
        with self.assertRaises(StudioEvidenceDenied):self.check(x)
    def test_wrong_audio_pcm_is_not_recovered_by_matching_claims(self):
        x=fixture();x['decoded_wav_bytes']=x['wav']+b'x'
        with self.assertRaises(StudioEvidenceDenied):verify_vocal_evidence(x['signed'],studio_project=x['project'],source_audio_bytes=x['raw'],decoded_wav_bytes=x['decoded_wav_bytes'],evidence=x['evidence'],grant=x['grant'],trusted_issuer_key=x['keys']['issuer'],trusted_observer_key=x['keys']['observer'],trusted_issuer_key_id='issuer-key',trusted_observer_key_id='observer-key')
    def test_wrong_immutable_project_association_rejected(self):
        x=fixture();x['project']['revision']['outputArtifactIds']=[]
        with self.assertRaisesRegex(StudioEvidenceDenied,'ARTIFACT_NOT_IN_REVISION'):self.check(x)
    def test_lyric_word_must_be_in_authorized_timeline(self):
        x=fixture();x['project']['lyricTimeline']['words']=[]
        with self.assertRaisesRegex(StudioEvidenceDenied,'WORD_NOT_IN_STUDIO_LYRIC_TIMELINE'):self.check(x)
    def test_revoked_or_expired_grant_fails(self):
        for change in [{'current':False},{'observedAtEpochMs':'1000'},{'authorizationGrantId':'other'}]:
            x=fixture();x['grant'].update(change)
            with self.assertRaises(StudioEvidenceDenied):self.check(x)
    def test_source_clock_cannot_be_absent_from_signed_studio_evidence(self):
        x=fixture();p=self.check(x)
        self.assertEqual(p.get('sourceSampleRate'),'48000')

    def test_lyric_wav_must_be_project_source_not_merely_render_output(self):
        x=fixture()
        wavsha=hashlib.sha256(x['wav']).hexdigest()
        self.assertIn(wavsha,x['project']['revision']['sourceAssetDigests'])
        x['project']['revision']['sourceAssetDigests'].remove(wavsha)
        with self.assertRaisesRegex(StudioEvidenceDenied,'LYRIC_WAV_NOT_PROJECT_SOURCE'):
            self.check(x)

    def test_canonical_receipt_sign_and_tamper_detection(self):
        x=fixture();p=self.check(x)
        receipt=sign_studio_receipt('receipt-1',x['signed'],p,x['grant'],x['issuer'],key_id='issuer-key',issued_at_epoch_ms=200)
        q=verify_studio_receipt(receipt,x['keys']['issuer'],trusted_key_id='issuer-key',authorized_principal='studio-issuer')
        self.assertEqual(q['onsetSample'],'3000')
        receipt['payload']['decodedPcmDigest']='b'*64
        with self.assertRaises(StudioEvidenceDenied):verify_studio_receipt(receipt,x['keys']['issuer'],trusted_key_id='issuer-key',authorized_principal='studio-issuer')
    def test_attestation_key_id_must_match_host_registry(self):
        x=fixture();x['signed']['attestation']['keyId']='forged-key-id'
        with self.assertRaisesRegex(StudioEvidenceDenied,'ISSUER_KEY_ID_MISMATCH'):self.check(x)
        x=fixture();x['evidence']['witnessAttestation']['keyId']='forged-witness-id'
        with self.assertRaisesRegex(StudioEvidenceDenied,'WITNESS_KEY_ID_MISMATCH'):self.check(x)
    def test_studio_receipt_host_key_id_is_binding_not_untrusted_label(self):
        x=fixture();p=self.check(x)
        receipt=sign_studio_receipt('receipt-1',x['signed'],p,x['grant'],x['issuer'],key_id='issuer-key',issued_at_epoch_ms=200)
        receipt['receiptAttestation']['keyId']='forged-label'
        with self.assertRaisesRegex(StudioEvidenceDenied,'RECEIPT_KEY_ID_MISMATCH'):
            verify_studio_receipt(receipt,x['keys']['issuer'],trusted_key_id='issuer-key',authorized_principal='studio-issuer')

    def test_arbitrary_prebuilt_verified_boolean_no_bypass(self):
        x=fixture();x['signed']['verification']='AUTHENTICATED'
        with self.assertRaises(StudioEvidenceDenied):self.check(x)

if __name__=='__main__':unittest.main()

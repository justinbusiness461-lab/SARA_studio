"""RED→GREEN tests; synthetic bytes are ONLY local negative fixtures, never certification."""
from __future__ import annotations
import hashlib, io, struct, unittest, wave
from unittest.mock import patch
from r25_strict_staging_binding import (EXPECTED_MASTERS, StrictStagingDenied, verify_real_staging)

TITLES = tuple(EXPECTED_MASTERS)
PRINCIPAL = 'artist-r25-private-staging'

def make_wav(frames, scale):
    out=io.BytesIO()
    with wave.open(out,'wb') as wav:
        wav.setframerate(44100);wav.setnchannels(2);wav.setsampwidth(2)
        wav.writeframes(struct.pack('<hh',scale,-scale)*frames)
    return out.getvalue()

class StrictBinding(unittest.TestCase):
    def setUp(self):
        self.wavs={t:make_wav(44100,i+100) for i,t in enumerate(TITLES)}
        self.oracles={}
        self.snapshots={}
        for i,title in enumerate(TITLES):
            raw=self.wavs[title]
            with wave.open(io.BytesIO(raw),'rb') as f:
                pcm=f.readframes(f.getnframes())
            pid=str(i+1)*32;rid=str(i+4)*64;artifact=hashlib.sha256(raw).hexdigest()
            self.oracles[title]={
                'sourceSha256':hashlib.sha256(('source:'+title).encode()).hexdigest(),
                'wavSha256':artifact,'pcmSha256':hashlib.sha256(pcm).hexdigest(),
                'frames':44100,
            }
            self.snapshots[pid]={'manifest':{'projectId':pid,'currentRevisionId':rid},
                'revision':{'revisionId':rid,'projectId':pid,'parentRevisionId':None,
                    'sourceAssetDigests':[self.oracles[title]['sourceSha256']],
                    'outputArtifactIds':[artifact]},
                'songSpec':{'artistMasterImport':{
                    'sourceSha256':self.oracles[title]['sourceSha256'],
                    'rightsStatus':'UNVERIFIED_HELD',
                    'privatePilotAuthorized':True,'commercialReleaseAuthorized':False}}}
        self.originals=[dict(title=t,sourceSha256=self.oracles[t]['sourceSha256'],
            projectId=str(i+1)*32,revisionId=str(i+4)*64,
            artifactId=self.oracles[t]['wavSha256'],rightsStatus='UNVERIFIED_HELD',
            privatePilotAuthorized=True,commercialReleaseAuthorized=False,
            decoded44100Frames=44100,decoded44100PcmSha256=self.oracles[t]['pcmSha256'])
            for i,t in enumerate(TITLES)]
        self.r2_audio=make_wav(44100,900)
        self.r2id=hashlib.sha256(self.r2_audio).hexdigest()
        first=self.originals[0]
        self.r2=dict(state='EDITED_UNAPPROVED',projectId=first['projectId'],
            sourceRevisionId=first['revisionId'],revisionId='f'*64,
            artifactId=self.r2id,creativeApproved=False,productionQualified=False)
        r2rev={**self.snapshots[first['projectId']]['revision'],
            'revisionId':'f'*64,'parentRevisionId':first['revisionId'],
            'outputArtifactIds':[self.r2id]}
        self.snapshots['f'*64]={**self.snapshots[first['projectId']],
            'revision':r2rev,'manifest':{**self.snapshots[first['projectId']]['manifest'],
                'currentRevisionId':'f'*64}}
        self.snapshots[first['projectId']]['manifest']['currentRevisionId']='f'*64
        self._expected_patch=patch('r25_strict_staging_binding.EXPECTED_MASTERS',self.oracles)
        self._expected_patch.start();self.addCleanup(self._expected_patch.stop)

    def project(self,root,request,principal_id=None):
        if principal_id!=PRINCIPAL: raise PermissionError('denied')
        pid=request['projectId'];rid=request.get('revisionId')
        if pid!=self.originals[0]['projectId'] and rid is None:
            return self.snapshots[pid]
        if pid==self.originals[0]['projectId']:
            return self.snapshots['f'*64] if rid is None or rid=='f'*64 else self.snapshots[pid]
        return self.snapshots[pid]

    def audio(self,root,request,principal_id=None):
        if principal_id!=PRINCIPAL: raise PermissionError('denied')
        if request['revisionId']=='f'*64:
            return self.r2_audio
        for song in self.originals:
            if song['projectId']==request['projectId'] and song['revisionId']==request['revisionId']:
                if request['artifactId']!=song['artifactId']:raise PermissionError('wrong artifact')
                return self.wavs[song['title']]
        raise PermissionError('not lawfully bound')

    def check(self, originals=None, latest=None, project=None, audio=None):
        return verify_real_staging('local-staging-root',PRINCIPAL,
            self.originals if originals is None else originals,
            self.r2 if latest is None else latest,
            self.project if project is None else project,
            self.audio if audio is None else audio)

    def test_valid_test_fixture_is_only_local_unit_input_not_production_proof(self):
        self.assertEqual(self.check()['verifiedMasterCount'],3)

    def test_forged_source_hash_is_rejected(self):
        d=[dict(x) for x in self.originals];d[1]['sourceSha256']='a'*64
        with self.assertRaisesRegex(StrictStagingDenied,'SOURCE_IDENTITY'):self.check(originals=d)

    def test_forged_rights_status_is_rejected(self):
        d=[dict(x) for x in self.originals];d[0]['rightsStatus']='ARTIST_OWNED'
        with self.assertRaisesRegex(StrictStagingDenied,'RIGHTS'):self.check(originals=d)

    def test_wrong_project_source_graph_rejected(self):
        self.snapshots[self.originals[1]['projectId']]['revision']['sourceAssetDigests']=['0'*64]
        with self.assertRaisesRegex(StrictStagingDenied,'REVISION_SOURCE'):self.check()

    def test_same_title_duplicate_or_missing_rejected(self):
        for arr in [self.originals[:2],[self.originals[0],self.originals[0],self.originals[1]]]:
            with self.assertRaisesRegex(StrictStagingDenied,'INVENTORY'):self.check(originals=arr)

    def test_fake_r1_wav_rejected_even_if_receipt_is_truthful(self):
        def corrupt(root,request,principal_id=None):
            good=self.audio(root,request,principal_id=principal_id)
            return good[:-4]+b'\x12\x34\x56\x78'
        with self.assertRaisesRegex(StrictStagingDenied,'WAV|PCM'):self.check(audio=corrupt)

    def test_foreign_or_unbound_artifact_rejected(self):
        def denied(*args,**kwargs): raise PermissionError('foreign')
        with self.assertRaisesRegex(StrictStagingDenied,'LAWFUL_AUDIO'):self.check(audio=denied)

    def test_r2_duplicate_or_stale_rejected(self):
        first=self.originals[0]
        for mutate in [{'artifactId':first['artifactId']},
                       {'sourceRevisionId':'e'*64},
                       {'projectId':self.originals[1]['projectId']},
                       {'revisionId':first['revisionId']}]:
            with self.subTest(mutate=mutate),self.assertRaises(StrictStagingDenied):
                self.check(latest={**self.r2,**mutate})

    def test_r2_forged_current_pointer_rejected(self):
        self.snapshots['f'*64]['manifest']['currentRevisionId']='e'*64
        with self.assertRaisesRegex(StrictStagingDenied,'CURRENT'):self.check()

    def test_r2_without_rightful_parent_rejected(self):
        self.snapshots['f'*64]['revision']['parentRevisionId']='e'*64
        with self.assertRaisesRegex(StrictStagingDenied,'ANCESTRY'):self.check()

    def test_wrong_r2_wav_digest_rejected(self):
        def swapped(root,request,principal_id=None):
            if request['revisionId']=='f'*64:return self.wavs[TITLES[0]]
            return self.audio(root,request,principal_id=principal_id)
        with self.assertRaisesRegex(StrictStagingDenied,'R2_WAV'):self.check(audio=swapped)

    def test_r2_unqualified_state_rejected(self):
        with self.assertRaisesRegex(StrictStagingDenied,'R2_PROVENANCE'):
            self.check(latest={**self.r2,'state':'APPROVED'})

    def test_r2_different_length_rejected(self):
        self.r2_audio=make_wav(22050,900);self.r2['artifactId']=hashlib.sha256(self.r2_audio).hexdigest();
        self.snapshots['f'*64]['revision']['outputArtifactIds']=[self.r2['artifactId']]
        with self.assertRaisesRegex(StrictStagingDenied,'R2_WAV'):self.check()

    def test_unsafe_boolean_sample_count_rejected(self):
        self.originals[0]['decoded44100Frames']=True
        with self.assertRaisesRegex(StrictStagingDenied,'SOURCE_IDENTITY'):self.check()

if __name__=='__main__':unittest.main()

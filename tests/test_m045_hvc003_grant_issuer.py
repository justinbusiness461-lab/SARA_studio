"""Fail-closed accepted-audio grant issuance against host-owned readbacks."""
import hashlib
import hmac
import io
import json
import struct
import unittest
import wave

from m045_soundtrack_grant import (HostSigningKeyRing, GrantIssuerDenied, issue_authorized_grant,
                                   verify_issued_grant_signature)

PID='a'*32
R1='1'*64
R2='2'*64
AID='3'*64
KEY=b'studio_host_only_signing_key_32bytes_xxxxx'


def wav_bytes(rate=48000,seconds=15):
    io_buf=io.BytesIO()
    with wave.open(io_buf,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(struct.pack('<h',3000)*rate*seconds)
    return io_buf.getvalue()


class GrantIssuerContract(unittest.TestCase):
    def setUp(self):
        self.wav=wav_bytes()
        self.aid=hashlib.sha256(self.wav).hexdigest()
        self.ring=HostSigningKeyRing(active_key_id='studio-k1',keys_by_id={'studio-k1':KEY},revoked_key_ids=frozenset())
        self.source={'projectId':PID,'manifest':{'projectId':PID,'currentRevisionId':R2},
           'revision':{'projectId':PID,'revisionId':R1,'lyricTimelineDigest':None,
                       'outputArtifactIds':[self.aid]},
           'productionTimeline':{'timebase':{'initial_bpm':120,'ticks_per_quarter_note':960},
                       'sections':[{'id':'intro','start_tick':0,'end_tick':28800}], 'tracks':[]},
           'songSpec':{'tracks':[]}}
        self.seen=[]

    def read_project(self,root,req,principal_id):
        self.seen.append(('project',req.copy(),principal_id))
        if principal_id!='owner' or req.get('projectId')!=PID or req.get('revisionId')!=R1:
            raise PermissionError('PRINCIPAL_OR_REVISION_DENIED')
        return self.source

    def read_audio(self,root,req,principal_id):
        self.seen.append(('audio',req.copy(),principal_id))
        if principal_id!='owner' or req!={'projectId':PID,'revisionId':R1,'artifactId':self.aid}:
            raise PermissionError('ARTIFACT_BINDING_DENIED')
        return self.wav

    def policy(self,pid,rid,aid,principal):
        return 'ARTIST_OWNED' if (pid,rid,aid,principal)==(PID,R1,self.aid,'owner') else None

    def issue(self,request=None,**opts):
        req={'projectId':PID,'revisionId':R1,'artifactId':self.aid,
             'cinemaProjectId':'cinema-1','sectionId':'intro','fps':'24/1'}
        if request:req.update(request)
        return issue_authorized_grant(root='/tmp/unused', request=req, principal_id='owner',
            ring=self.ring,read_project=self.read_project,read_audio=self.read_audio,
            rights_policy=opts.pop('rights_policy',self.policy),now=1000,**opts)

    def test_host_signed_15_second_historical_r1_binding_and_no_promotion(self):
        grant=self.issue()
        self.assertEqual(grant['schema_version'],'sara.soundtrack.grant.v1')
        self.assertEqual(grant['audience'],'pulseforge_cinema')
        self.assertEqual(grant['source_project_revision_id'],R1)
        self.assertEqual(grant['resolved_start_sample'],0)
        self.assertEqual(grant['resolved_end_sample_exclusive'],720000)
        self.assertEqual(grant['resolved_start_frame'],0)
        self.assertEqual(grant['resolved_end_frame_exclusive'],360)
        self.assertEqual(grant['decoded_pcm_sha256'],hashlib.sha256(struct.pack('<h',3000)*720000).hexdigest())
        self.assertTrue(verify_issued_grant_signature(grant,self.ring))
        self.assertEqual(self.source['manifest']['currentRevisionId'],R2)
        self.assertIn(('audio',{'projectId':PID,'revisionId':R1,'artifactId':self.aid},'owner'),self.seen)

    def test_numeric_start_and_end_from_client_are_rejected(self):
        with self.assertRaisesRegex(GrantIssuerDenied,'CLIENT_SAMPLE_COORDINATES_DENIED'):
            self.issue({'resolved_start_sample':0,'resolved_end_sample_exclusive':720000})

    def test_rights_and_wrong_artifact_reject(self):
        with self.assertRaisesRegex(GrantIssuerDenied,'RIGHTS_NOT_HOST_ATTESTED'):
            self.issue(rights_policy=lambda *_:None)
        with self.assertRaises(PermissionError):
            self.issue({'artifactId':'f'*64})

    def test_frame_mapping_rational_and_exact_section_start(self):
        # A song segment at 03:49 corresponds to tick 439680 at 120 BPM.
        seconds=246
        self.wav=wav_bytes(seconds=seconds)
        self.aid=hashlib.sha256(self.wav).hexdigest()
        self.source['revision']['outputArtifactIds']=[self.aid]
        self.source['productionTimeline']['sections']=[{'id':'s15','start_tick':439680,'end_tick':500000}]
        grant=self.issue({'sectionId':'s15','fps':'30000/1001'})
        self.assertEqual(grant['resolved_start_sample'],10992000)
        self.assertEqual(grant['resolved_end_sample_exclusive'],11712000)
        self.assertEqual(grant['resolved_start_frame'],6863)
        self.assertEqual(grant['resolved_end_frame_exclusive'],7313)
        self.assertTrue(verify_issued_grant_signature(grant,self.ring))

    def test_signature_cannot_be_edited_or_revoked(self):
        grant=self.issue()
        self.assertFalse(verify_issued_grant_signature({**grant,'source_project_revision_id':R2},self.ring))
        revoked=HostSigningKeyRing('studio-k1',{'studio-k1':KEY},frozenset({'studio-k1'}))
        self.assertFalse(verify_issued_grant_signature(grant,revoked))

if __name__=='__main__':unittest.main()

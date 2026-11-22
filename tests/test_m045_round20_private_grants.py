"""Round 20: host-scoped private music pilots; no Drive or release authority."""
import hashlib
import io
import unittest
import wave
from m045_soundtrack_grant import HostSigningKeyRing, GrantIssuerDenied, issue_authorized_grant, verify_issued_grant_signature

RATE=44100
START=252*RATE
END=272*RATE
PID='1'*32
RID='a'*64
PRINCIPAL='artist-host'
CINEMA='cinema-private'

class HostPrivatePilotRights(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        stream=io.BytesIO()
        with wave.open(stream,'wb') as writer:
            writer.setnchannels(2);writer.setsampwidth(2);writer.setframerate(RATE)
            writer.writeframes(b'\x00\x00\x00\x00'*(END+32))
        cls.audio=stream.getvalue()
        cls.aid=hashlib.sha256(cls.audio).hexdigest()

    def setUp(self):
        self.keyring=HostSigningKeyRing('test-host-key',{'test-host-key':b'R'*32},frozenset())
        self.request={'projectId':PID,'revisionId':RID,'artifactId':self.aid,
                      'cinemaProjectId':CINEMA,'sectionId':'pilot','fps':'24/1',
                      'scope':'private_cinema_pilot'}
        self.timeline={'timebase':{'initial_bpm':120,'ticks_per_quarter_note':960},
            'sections':[{'id':'pilot','sample_rate':RATE,'start_sample':START,'end_sample_exclusive':END}]}
        self.rights={'rights_status':'UNVERIFIED_HELD','private_pilot_authorized':True,
            'principal_id':PRINCIPAL,'revision_id':RID,'artifact_id':self.aid,
            'cinema_project_id':CINEMA,'approved_start_sample':START,
            'approved_end_sample_exclusive':END}

    def issue(self, rights=None, request=None):
        return issue_authorized_grant(root='host-fixture',principal_id=PRINCIPAL,
            request=self.request if request is None else request,ring=self.keyring,
            read_project=lambda *_args,**_kw: {
                'manifest':{'projectId':PID},'revision':{'projectId':PID,'revisionId':RID},
                'productionTimeline':self.timeline},
            read_audio=lambda *_args,**_kw: self.audio,
            rights_policy=lambda *_args:self.rights if rights is None else rights,
            now=1840000000)

    def test_signs_held_20_second_exact_window_without_bpm_or_release_clearance(self):
        grant=self.issue()
        self.assertEqual((grant['resolved_start_sample'],grant['resolved_end_sample_exclusive']), (START,END))
        self.assertEqual((grant['resolved_start_frame'],grant['resolved_end_frame_exclusive']),(6048,6528))
        self.assertEqual(grant['rights_status'],'UNVERIFIED_HELD')
        self.assertEqual(grant['scope'],'private_cinema_pilot')
        self.assertIs(grant['commercial_release_authorized'],False)
        self.assertTrue(verify_issued_grant_signature(grant,self.keyring))

    def test_rejects_unbound_rights_and_private_authority_spoofing(self):
        for name,value in [('private_pilot_authorized',False),('principal_id','foreign'),
                           ('revision_id','f'*64),('artifact_id','f'*64),
                           ('cinema_project_id','foreign'),('rights_status','ARTIST_OWNED'),
                           ('approved_start_sample',START+1)]:
            with self.subTest(name=name):
                with self.assertRaises(GrantIssuerDenied):self.issue({**self.rights,name:value})
        for key,value in [('private_pilot_authorized',True),('resolved_start_sample',START),
                          ('commercial_release_authorized',True),('signature','forged')]:
            with self.subTest(key=key):
                with self.assertRaises(GrantIssuerDenied):self.issue(request={**self.request,key:value})

    def test_rejects_unsupported_scope_and_15_second_section(self):
        with self.assertRaises(GrantIssuerDenied):self.issue(request={**self.request,'scope':'commercial_release'})
        self.timeline['sections'][0]['end_sample_exclusive']=START+15*RATE
        with self.assertRaises(GrantIssuerDenied):self.issue()

    def test_signature_tampering_invalid(self):
        grant=self.issue()
        self.assertFalse(verify_issued_grant_signature({**grant,'scope':'commercial_release'},self.keyring))
        self.assertFalse(verify_issued_grant_signature({**grant,'resolved_start_sample':START+1},self.keyring))

    def test_legacy_artist_owned_grant_retains_15_second_behavior(self):
        self.timeline['sections']=[{'id':'pilot','start_tick':0,'end_tick':60000}]
        grant=self.issue(rights='ARTIST_OWNED',request={k:v for k,v in self.request.items() if k!='scope'})
        self.assertEqual(grant['rights_status'],'ARTIST_OWNED')
        self.assertNotIn('scope',grant)
        self.assertEqual((grant['resolved_start_sample'],grant['resolved_end_sample_exclusive']), (0,15*RATE))
        self.assertTrue(verify_issued_grant_signature(grant,self.keyring))

if __name__=='__main__':unittest.main()

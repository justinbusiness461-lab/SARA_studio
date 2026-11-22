"""R21 host-held artist masters use the existing ProjectManifest/CAS authority.

Synthetic audio only. Real artist files are NEVER committed to the public repo.
All signers in this file are test keys. No commercial clearance is asserted.
"""
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from m045_artist_master_ingestion import (
    ArtistMasterDenied, ingest_original_master, ingest_three_song_batch,
    issue_accepted_master_grant,
)
from m045_soundtrack_grant import HostSigningKeyRing, GrantIssuerDenied, verify_issued_grant_signature
from studio_server import project_operation, project_audio_bytes

TITLES=('Turn The Noise Back On','If This Is All I Get','Outlaws and Echoes')
PRINCIPAL='round21-private-host-fixture'

def source_wav(seconds=21,rate=44100,level=203):
    buff=io.BytesIO()
    with wave.open(buff,'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(struct.pack('<hh',level,-level)*(seconds*rate))
    return buff.getvalue()

class Round21HeldPrivateHost(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'studio'
        self.source=Path(self.temp.name)/'artist.wav'
        self.source.write_bytes(source_wav())
        self.digest=hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.pid='1'*32
    def catalog(self,principal,title,digest):
        if principal!=PRINCIPAL or title!=TITLES[0] or digest!=self.digest:
            raise PermissionError('HOST_CATALOG_SOURCE_NOT_MATCHED')
        return {'principalId':principal,'title':title,'sourceSha256':digest,
                'projectId':self.pid,'rightsEvidenceSha256':'a'*64,
                'rightsStatus':'UNVERIFIED_HELD','privatePilotAuthorized':True,
                'commercialReleaseAuthorized':False,
                'pilotSection':{'id':'pilot','sampleRate':44100,
                                'startSample':44100,'endSampleExclusive':926100}}
    def ingest(self,catalog=None):
        return ingest_original_master(root=self.root,principal_id=PRINCIPAL,
             title=TITLES[0],source_path=self.source,
             host_catalog_lookup=self.catalog if catalog is None else catalog)

    def test_held_rights_require_host_policy_before_any_project_or_cas(self):
        for key,value in [('rightsStatus','ARTIST_ORIGINAL'),
                          ('privatePilotAuthorized',False),
                          ('commercialReleaseAuthorized',True),
                          ('principalId','foreign')]:
            with self.subTest(key=key):
                with self.assertRaises((ArtistMasterDenied,PermissionError)):
                    self.ingest(catalog=lambda *args,key=key,value=value:{
                       **self.catalog(*args),key:value})
                self.assertFalse((self.root/'projects'/self.pid/'ProjectManifest.json').exists())
    def test_bad_or_client_like_host_window_denied_without_commit(self):
        for key,value in [('startSample',44101),('endSampleExclusive',926101),
                          ('sampleRate',48000),('startSample',True)]:
            with self.subTest(key=key):
                def invalid(*args,key=key,value=value):
                    base=self.catalog(*args)
                    return {**base,'pilotSection':{**base['pilotSection'],key:value}}
                with self.assertRaises(ArtistMasterDenied):
                    self.ingest(catalog=invalid)
                self.assertFalse((self.root/'projects'/self.pid/'ProjectManifest.json').exists())
    def test_44100_cas_canonical_timeline_and_exact_cold_process(self):
        first=self.ingest()
        self.assertEqual(first['rightsStatus'],'UNVERIFIED_HELD')
        self.assertFalse(first['commercialReleaseAuthorized'])
        self.assertEqual(first['audioSampleRate'],44100)
        self.assertEqual(first['decoded44100Frames'],926100)
        observation=project_operation(self.root,{'projectId':self.pid,
            'revisionId':first['revisionId']},principal_id=PRINCIPAL)
        self.assertEqual(observation['productionTimeline']['sections'],
           [{'id':'pilot','sample_rate':44100,
             'start_sample':44100,'end_sample_exclusive':926100}])
        self.assertFalse(observation['songSpec']['artistMasterImport']['musicalTimingQualified'])
        audio=project_audio_bytes(self.root,{'projectId':self.pid,
           'revisionId':first['revisionId'],'artifactId':first['artifactId']},
           principal_id=PRINCIPAL)
        self.assertEqual(hashlib.sha256(audio).hexdigest(),first['artifactId'])
        with wave.open(io.BytesIO(audio),'rb') as wav:
            self.assertEqual((wav.getframerate(),wav.getnchannels(),wav.getnframes()),
                             (44100,2,926100))
        self.assertEqual(self.ingest()['revisionId'],first['revisionId'])
        # New interpreter proves this isn't an in-memory-only revision.
        script="""import hashlib,sys
from studio_server import project_operation,project_audio_bytes
root,pid,rid,aid,principal=sys.argv[1:]
x=project_operation(root,{'projectId':pid,'revisionId':rid},principal_id=principal)
b=project_audio_bytes(root,{'projectId':pid,'revisionId':rid,'artifactId':aid},principal_id=principal)
assert x['revision']['revisionId']==rid and hashlib.sha256(b).hexdigest()==aid
print('R21_COLD_READ_OK')"""
        env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)}
        read=subprocess.run([sys.executable,'-c',script,str(self.root),self.pid,
            first['revisionId'],first['artifactId'],PRINCIPAL],
            env=env,capture_output=True,text=True,check=True)
        self.assertIn('R21_COLD_READ_OK',read.stdout)
    def test_exact_window_host_test_key_grant_never_commercial(self):
        record=self.ingest()
        ring=HostSigningKeyRing('r21-fixture-only',
            {'r21-fixture-only':b'x'*32},frozenset())
        def policy(pid,rid,aid,principal):
            return {'rights_status':'UNVERIFIED_HELD',
                    'private_pilot_authorized':True,'principal_id':principal,
                    'revision_id':rid,'artifact_id':aid,
                    'cinema_project_id':'private-cinema-fixture',
                    'approved_start_sample':44100,
                    'approved_end_sample_exclusive':926100}
        request=dict(root=self.root,principal_id=PRINCIPAL,project_id=self.pid,
            revision_id=record['revisionId'],artifact_id=record['artifactId'],
            cinema_project_id='private-cinema-fixture',section_id='pilot',
            host_signing_ring=ring,host_rights_policy=policy,now=1840000000)
        signed=issue_accepted_master_grant(**request)
        self.assertEqual((signed['resolved_start_sample'],
             signed['resolved_end_sample_exclusive']),(44100,926100))
        self.assertEqual((signed['resolved_start_frame'],
             signed['resolved_end_frame_exclusive']),(24,504))
        self.assertEqual(signed['scope'],'private_cinema_pilot')
        self.assertIs(signed['commercial_release_authorized'],False)
        self.assertTrue(verify_issued_grant_signature(signed,ring))
        with self.assertRaises(GrantIssuerDenied):
            issue_accepted_master_grant(**{**request,
                'host_rights_policy':lambda *_:{
                   **policy(self.pid,record['revisionId'],record['artifactId'],PRINCIPAL),
                   'private_pilot_authorized':False}})
    def test_foreign_principal_cannot_read_cas_by_digest(self):
        result=self.ingest()
        with self.assertRaises((ValueError,PermissionError)):
            project_audio_bytes(self.root,{'projectId':self.pid,
                'revisionId':result['revisionId'],'artifactId':result['artifactId']},
                principal_id='foreign')
    def test_three_song_batch_preflights_all_rights_before_writing(self):
        paths={}
        hashes={}
        for index,title in enumerate(TITLES):
            path=Path(self.temp.name)/('master%d.wav'%index)
            path.write_bytes(source_wav(level=300+index))
            paths[title]=path
            hashes[title]=hashlib.sha256(path.read_bytes()).hexdigest()
        def catalog(principal,title,digest):
            if digest!=hashes[title]:raise PermissionError('HOST_IDENTITY')
            index=TITLES.index(title)
            return {'principalId':principal,'title':title,'sourceSha256':digest,
                'projectId':str(index+1)*32,'rightsEvidenceSha256':str(index+1)*64,
                'rightsStatus':'UNVERIFIED_HELD','privatePilotAuthorized':True,
                'commercialReleaseAuthorized':False,'pilotSection':{
                  'id':'pilot','sampleRate':44100,
                  'startSample':44100,'endSampleExclusive':926100}}
        broken=dict(paths);broken[TITLES[2]]=Path(self.temp.name)/'missing.wav'
        with self.assertRaises((ValueError,PermissionError,FileNotFoundError)):
            ingest_three_song_batch(root=self.root,principal_id=PRINCIPAL,
                sources_by_title=broken,host_catalog_lookup=catalog)
        self.assertFalse((self.root/'projects'/('1'*32)/'ProjectManifest.json').exists())
        done=ingest_three_song_batch(root=self.root,principal_id=PRINCIPAL,
            sources_by_title=paths,host_catalog_lookup=catalog)
        self.assertEqual(len(done['songs']),3)
        self.assertEqual(done['issuedGrantCount'],0)
        for song in done['songs']:
            self.assertEqual(song['rightsStatus'],'UNVERIFIED_HELD')
            self.assertEqual(song['audioSampleRate'],44100)

if __name__=='__main__':unittest.main()

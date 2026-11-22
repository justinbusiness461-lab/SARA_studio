"""R18 RED — host-only real-media ingestion, no simulated-artist milestone."""
import hashlib
import io
import json
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from studio_server import project_audio_bytes, project_operation

TITLES=('Turn The Noise Back On','If This Is All I Get','Outlaws and Echoes')
PIDS=('1'*32,'2'*32,'3'*32)
PRINCIPAL='artist-r18'
def source_audio(seconds=1,rate=48000):
    buff=io.BytesIO()
    with wave.open(buff,'wb') as wf:
        wf.setnchannels(2);wf.setsampwidth(2);wf.setframerate(rate)
        wf.writeframes(struct.pack('<hh',2800,-2800)*seconds*rate)
    return buff.getvalue()

class IngestContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'data'
        self.source=Path(self.tmp.name)/'master.wav'
        self.source.write_bytes(source_audio())
        self.digest=hashlib.sha256(self.source.read_bytes()).hexdigest()
    def catalog(self,principal,title,digest):
        if principal!=PRINCIPAL or title!=TITLES[0] or digest!=self.digest:
            raise PermissionError('OWNER_SOURCE_CATALOG_MISMATCH')
        return {'title':title,'principalId':principal,'projectId':PIDS[0],
                'sourceSha256':digest,'rightsStatus':'ARTIST_OWNED',
                'rightsEvidenceSha256':'a'*64}
    def ingest(self,**overrides):
        from m045_artist_master_ingestion import ingest_original_master
        settings=dict(root=self.root,principal_id=PRINCIPAL,title=TITLES[0],
           source_path=self.source,host_catalog_lookup=self.catalog)
        settings.update(overrides)
        return ingest_original_master(**settings)
    def test_missing_file_and_unattested_rights_denied_before_project_or_cas(self):
        from m045_artist_master_ingestion import ingest_original_master
        absent=self.source.with_name('missing-master.m4a')
        with self.assertRaises((ValueError,PermissionError,FileNotFoundError)):
            ingest_original_master(root=self.root,principal_id=PRINCIPAL,
             title=TITLES[0],source_path=absent,host_catalog_lookup=self.catalog)
        with self.assertRaises((ValueError,PermissionError)):
            self.ingest(host_catalog_lookup=None)
        with self.assertRaises((ValueError,PermissionError)):
            self.ingest(host_catalog_lookup=lambda *_:{**self.catalog(PRINCIPAL,TITLES[0],self.digest),
                                                       'rightsStatus':'UNVERIFIED_HELD'})
        self.assertFalse((self.root/'objects').exists())
    def test_host_attested_import_exact_raw_plus_44_48_pcm_and_lawful_cold_reopen(self):
        from m045_artist_master_ingestion import ingest_original_master
        got=self.ingest()
        self.assertEqual(got['status'],'IMPORTED_UNAPPROVED')
        self.assertEqual(got['rightsStatus'],'ARTIST_ORIGINAL')
        self.assertEqual(got['sourceSha256'],self.digest)
        self.assertEqual(got['projectId'],PIDS[0])
        self.assertEqual(got['decoded48000Frames'],48000)
        self.assertEqual(got['decoded44100Frames'],44100)
        self.assertEqual(got['audioSampleRate'],48000)
        self.assertFalse(got['musicalTimingQualified'])
        self.assertFalse(got['creativeApproved'])
        self.assertFalse(got['productionQualified'])
        self.assertEqual((self.root/'objects'/self.digest[:2]/self.digest).read_bytes(),
                          self.source.read_bytes())
        current=project_operation(self.root,{'projectId':PIDS[0]},principal_id=PRINCIPAL)
        self.assertEqual(current['manifest']['currentRevisionId'],got['revisionId'])
        self.assertIn(self.digest,current['revision']['sourceAssetDigests'])
        self.assertIn(got['artifactId'],current['revision']['outputArtifactIds'])
        raw=project_audio_bytes(self.root,{'projectId':PIDS[0],
             'revisionId':got['revisionId'],'artifactId':got['artifactId']},
             principal_id=PRINCIPAL)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),got['artifactId'])
        self.assertEqual(project_operation(self.root,{'projectId':PIDS[0]},
                 principal_id=PRINCIPAL)['songSpec']['title'],TITLES[0])
        # Cold new import invocation cannot drift identity or promote R2.
        again=self.ingest()
        self.assertEqual(again['status'],'ALREADY_IMPORTED')
        self.assertEqual(again['revisionId'],got['revisionId'])
    def test_local_http_player_r1_bytes_serve_after_new_handler_with_foreign_403(self):
        import json,socketserver,threading,urllib.request,urllib.error
        import studio_server as studio
        original=(studio.EXPORT_ROOT,studio.PORT,studio.PLATFORM_MODE)
        result=self.ingest()
        server=socketserver.ThreadingTCPServer(('127.0.0.1',0),studio.StudioHandler)
        self.addCleanup(server.server_close)
        studio.EXPORT_ROOT=self.root
        studio.PORT=server.server_address[1]
        studio.PLATFORM_MODE=False
        self.addCleanup(lambda:setattr(studio,'PLATFORM_MODE',original[2]))
        self.addCleanup(lambda:setattr(studio,'PORT',original[1]))
        self.addCleanup(lambda:setattr(studio,'EXPORT_ROOT',original[0]))
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(lambda:(server.shutdown(),thread.join(timeout=3)))
        def play(principal):
            token=studio.issue_studio_session(principal)
            uri='http://127.0.0.1:'+str(studio.PORT)+'/api/projects/audio'
            req=urllib.request.Request(uri,method='POST',
              headers={'Origin':'http://127.0.0.1:'+str(studio.PORT),
                       'X-Studio-Capability':studio.CAPABILITY,
                       'X-Studio-Session':token,'Content-Type':'application/json'},
              data=json.dumps({'projectId':result['projectId'],
                  'revisionId':result['revisionId'],
                  'artifactId':result['artifactId']}).encode())
            try:
                with urllib.request.urlopen(req,timeout=8) as response:
                    return response.status,response.read()
            except urllib.error.HTTPError as error:
                return error.code,error.read()
        owner_code,owner_wav=play(PRINCIPAL)
        self.assertEqual(owner_code,200)
        self.assertEqual(hashlib.sha256(owner_wav).hexdigest(),result['artifactId'])
        foreign_code,_=play('foreign-r18')
        self.assertEqual(foreign_code,403)

    def test_foreign_principal_and_mutated_raw_source_denied(self):
        got=self.ingest()
        with self.assertRaises((ValueError,PermissionError)):
            project_audio_bytes(self.root,{'projectId':PIDS[0],
                'revisionId':got['revisionId'],'artifactId':got['artifactId']},
                principal_id='foreign')
        self.source.write_bytes(source_audio(seconds=2))
        with self.assertRaises((ValueError,PermissionError)):
            self.ingest()
        original=project_operation(self.root,{'projectId':PIDS[0]},principal_id=PRINCIPAL)
        self.assertEqual(original['revision']['revisionId'],got['revisionId'])
    def test_decoding_uses_exact_verified_bytes_even_if_input_path_changes(self):
        from unittest.mock import patch
        import m045_artist_master_ingestion as importer
        real=importer._decode_rates
        def swap_file_between_identity_and_decoder(source):
            self.source.write_bytes(source_audio(seconds=2))
            return real(source)
        with patch.object(importer,'_decode_rates',side_effect=swap_file_between_identity_and_decoder):
            inspected=importer.inspect_host_attested_master(
                principal_id=PRINCIPAL,title=TITLES[0],source_path=self.source,
                host_catalog_lookup=self.catalog)
        self.assertEqual(inspected['sha'],self.digest)
        self.assertEqual(inspected['physical']['byRate'][48000]['frames'],48000)
        self.assertEqual(inspected['physical']['byRate'][44100]['frames'],44100)

    def test_crash_after_initial_project_before_cas_recovers_without_shadow_revision(self):
        from unittest.mock import patch
        import m045_artist_master_ingestion as importer
        real=importer._publish_cas_exact
        calls=[]
        def fault(root,sha,data):
            calls.append(sha)
            if len(calls)==1:
                raise OSError('R18_FAULT_AFTER_R0_BEFORE_CAS')
            return real(root,sha,data)
        with patch.object(importer,'_publish_cas_exact',side_effect=fault):
            with self.assertRaises(OSError):
                self.ingest()
        snapshot=project_operation(self.root,{'projectId':PIDS[0]},principal_id=PRINCIPAL)
        self.assertEqual(snapshot['revision']['outputArtifactIds'],[])
        result=self.ingest()
        self.assertEqual(result['status'],'IMPORTED_UNAPPROVED')
        accepted=project_operation(self.root,{'projectId':PIDS[0]},principal_id=PRINCIPAL)
        self.assertEqual(accepted['revision']['parentRevisionId'],snapshot['revision']['revisionId'])
        self.assertEqual(accepted['manifest']['currentRevisionId'],result['revisionId'])

    def test_crash_after_durable_r1_before_receipt_finalization_recovers_exactly(self):
        from unittest.mock import patch
        import m045_artist_master_ingestion as importer
        real=importer.atomic_write_bytes
        def fault(path,payload):
            if str(path).endswith(self.digest+'.json') and b'COMMITTED' in payload:
                raise OSError('R18_FAULT_AFTER_COMMIT_BEFORE_RECEIPT')
            return real(path,payload)
        with patch.object(importer,'atomic_write_bytes',side_effect=fault):
            with self.assertRaises(OSError):
                self.ingest()
        before=project_operation(self.root,{'projectId':PIDS[0]},principal_id=PRINCIPAL)
        result=self.ingest()
        self.assertEqual(result['status'],'ALREADY_IMPORTED')
        self.assertEqual(before['revision']['revisionId'],result['revisionId'])
        after=project_operation(self.root,{'projectId':PIDS[0]},principal_id=PRINCIPAL)
        self.assertEqual(after['manifest']['currentRevisionId'],before['revision']['revisionId'])
        stage=self.root/'projects'/PIDS[0]/'artist-master-intakes'/(self.digest+'.json')
        self.assertEqual(json.loads(stage.read_text())['state'],'COMMITTED')
    def test_host_edited_r2_requires_real_changed_audio_and_provenance(self):
        from m045_artist_master_ingestion import commit_verified_edit
        r1=self.ingest()
        edited=self.source.with_name('edited.wav');edited.write_bytes(source_audio(seconds=2))
        with self.assertRaises((ValueError,PermissionError)):
            commit_verified_edit(root=self.root,principal_id=PRINCIPAL,
               project_id=PIDS[0],expected_r1_revision_id=r1['revisionId'],
               edited_wav_path=edited,host_edit_verifier=None)
        def provenanced(data):
            return data['projectId']==PIDS[0] and data['sourceRevisionId']==r1['revisionId']
        r2=commit_verified_edit(root=self.root,principal_id=PRINCIPAL,
               project_id=PIDS[0],expected_r1_revision_id=r1['revisionId'],
               edited_wav_path=edited,host_edit_verifier=provenanced)
        self.assertEqual(r2['state'],'EDITED_UNAPPROVED')
        self.assertNotEqual(r2['artifactId'],r1['artifactId'])
        now=project_operation(self.root,{'projectId':PIDS[0]},principal_id=PRINCIPAL)
        self.assertEqual(now['manifest']['currentRevisionId'],r2['revisionId'])
        assert_now=project_audio_bytes(self.root,{'projectId':PIDS[0],
            'revisionId':r1['revisionId'],'artifactId':r1['artifactId']},
            principal_id=PRINCIPAL)
        self.assertEqual(hashlib.sha256(assert_now).hexdigest(),r1['artifactId'])
        with self.assertRaises((ValueError,PermissionError)):
            commit_verified_edit(root=self.root,principal_id=PRINCIPAL,
               project_id=PIDS[0],expected_r1_revision_id=r1['revisionId'],
               edited_wav_path=edited,host_edit_verifier=provenanced)
    def test_no_signature_or_unverified_timeline_never_emits_grant(self):
        from m045_artist_master_ingestion import issue_accepted_master_grant
        r1=self.ingest()
        with self.assertRaises((ValueError,PermissionError)):
            issue_accepted_master_grant(root=self.root,principal_id=PRINCIPAL,
               project_id=PIDS[0],revision_id=r1['revisionId'],artifact_id=r1['artifactId'],
               cinema_project_id='dj-rezrxtion-film',section_id='pilot-0',
               host_signing_ring=None,host_rights_policy=lambda *_:'ARTIST_OWNED')
        from m045_soundtrack_grant import HostSigningKeyRing
        ring=HostSigningKeyRing('test-only-key',{'test-only-key':b'k'*40},frozenset())
        with self.assertRaises((ValueError,PermissionError)):
            issue_accepted_master_grant(root=self.root,principal_id=PRINCIPAL,
               project_id=PIDS[0],revision_id=r1['revisionId'],artifact_id=r1['artifactId'],
               cinema_project_id='dj-rezrxtion-film',section_id='pilot-0',
               host_signing_ring=ring,host_rights_policy=lambda *_:'ARTIST_OWNED')


class ThreeSongBatchContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'exports'
        self.paths={}
        self.observed={}
        for index,title in enumerate(TITLES):
            path=Path(self.tmp.name)/('audio-'+str(index)+'.wav')
            path.write_bytes(source_audio(seconds=index+1))
            self.paths[title]=path
            self.observed[title]=hashlib.sha256(path.read_bytes()).hexdigest()
    def catalog(self,principal,title,digest):
        index=TITLES.index(title)
        if principal!=PRINCIPAL or digest!=self.observed[title]:
            raise PermissionError('CATALOG_NOT_ATTESTED')
        return {'title':title,'principalId':principal,
                'projectId':PIDS[index],'sourceSha256':digest,
                'rightsStatus':'ARTIST_OWNED',
                'rightsEvidenceSha256':str(index+1)*64}
    def test_batch_preflight_rejects_missing_third_before_any_project_exists(self):
        from m045_artist_master_ingestion import ingest_three_song_batch
        missing=dict(self.paths)
        missing[TITLES[2]]=Path(self.tmp.name)/'absent-master.m4a'
        with self.assertRaises((PermissionError,FileNotFoundError,ValueError)):
            ingest_three_song_batch(root=self.root,principal_id=PRINCIPAL,
                sources_by_title=missing,host_catalog_lookup=self.catalog)
        self.assertFalse((self.root/'projects').exists())
    def test_all_three_real_file_slots_bind_distinct_cas_revisions(self):
        from m045_artist_master_ingestion import ingest_three_song_batch
        result=ingest_three_song_batch(root=self.root,principal_id=PRINCIPAL,
            sources_by_title=self.paths,host_catalog_lookup=self.catalog)
        self.assertEqual(result['status'],'THREE_MASTERS_IMPORTED_UNAPPROVED')
        self.assertEqual(len(result['songs']),3)
        self.assertEqual(len({x['artifactId'] for x in result['songs']}),3)
        self.assertEqual(len({x['projectId'] for x in result['songs']}),3)
        self.assertEqual(result['issuedGrantCount'],0)
        self.assertTrue(all(not x['productionQualified'] for x in result['songs']))
        for song in result['songs']:
            found=project_operation(self.root,{'projectId':song['projectId']},
                                    principal_id=PRINCIPAL)
            self.assertEqual(found['manifest']['currentRevisionId'],song['revisionId'])
            wav=project_audio_bytes(self.root,{'projectId':song['projectId'],
                'revisionId':song['revisionId'],'artifactId':song['artifactId']},
                principal_id=PRINCIPAL)
            self.assertEqual(hashlib.sha256(wav).hexdigest(),song['artifactId'])
    def test_duplicate_unchanged_audio_cannot_fake_three_distinct_song_masters(self):
        from m045_artist_master_ingestion import ingest_three_song_batch
        copied=dict(self.paths);copied[TITLES[1]]=self.paths[TITLES[0]]
        with self.assertRaises((ValueError,PermissionError)):
            ingest_three_song_batch(root=self.root,principal_id=PRINCIPAL,
                sources_by_title=copied,host_catalog_lookup=lambda principal,title,digest:
                  {'title':title,'principalId':principal,
                   'projectId':PIDS[TITLES.index(title)],
                   'sourceSha256':digest,'rightsStatus':'ARTIST_OWNED',
                   'rightsEvidenceSha256':'f'*64})
        self.assertFalse((self.root/'projects').exists())
    def test_blocked_manifest_contains_no_fabricated_grants_or_song_hashes(self):
        from m045_artist_master_ingestion import make_unavailable_three_song_manifest
        manifest=make_unavailable_three_song_manifest('EXECUTOR_VANTAGE_MISSING=THREE_SONG_MEDIA_BYTES')
        self.assertEqual(manifest['issuedGrantCount'],0)
        self.assertEqual(manifest['grants'],[])
        self.assertEqual(len(manifest['songs']),3)
        self.assertTrue(all(s['acceptedAudioArtifactId'] is None for s in manifest['songs']))
    def test_full_length_master_above_40mib_pcm_still_lawfully_plays(self):
        # Full-size engineering media, NOT the artist's creative master.
        import subprocess
        from m045_artist_master_ingestion import ingest_original_master
        source=Path(self.tmp.name)/'five-minute-engineering-input.mp3'
        subprocess.run(['ffmpeg','-nostdin','-hide_banner','-v','error',
             '-f','lavfi','-i','sine=frequency=223:sample_rate=48000:duration=296.4',
             '-ac','2','-c:a','libmp3lame','-b:a','160k','-y',str(source)],
             check=True,timeout=75)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        title=TITLES[0]
        def catalog(principal,title_arg,source_digest):
            self.assertEqual((principal,title_arg,source_digest),
                             (PRINCIPAL,title,digest))
            return {'title':title,'principalId':PRINCIPAL,
                    'projectId':PIDS[0],'sourceSha256':digest,
                    'rightsStatus':'ARTIST_OWNED','rightsEvidenceSha256':'a'*64}
        result=ingest_original_master(root=self.root,principal_id=PRINCIPAL,
            title=title,source_path=source,host_catalog_lookup=catalog)
        self.assertEqual(result['decoded48000Frames'],14227200)
        self.assertGreater((self.root/'objects'/result['artifactId'][:2]/
                            result['artifactId']).stat().st_size,40*1024*1024)
        self.assertEqual(result['status'],'IMPORTED_UNAPPROVED')
        exact=project_audio_bytes(self.root,{'projectId':PIDS[0],
            'revisionId':result['revisionId'],'artifactId':result['artifactId']},
            principal_id=PRINCIPAL)
        self.assertEqual(hashlib.sha256(exact).hexdigest(),result['artifactId'])

    def test_real_local_mp3_and_m4a_decode_contract_without_provider_requests(self):
        from m045_artist_master_ingestion import inspect_host_attested_master
        import subprocess
        for index,(suffix,codec) in enumerate((('.mp3','libmp3lame'),('.m4a','aac'))):
            wav=self.paths[TITLES[index]]
            packed=Path(self.tmp.name)/('encoded-'+str(index)+suffix)
            subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-i',str(wav),
                            '-c:a',codec,str(packed)],check=True,timeout=15)
            raw=packed.read_bytes()
            digest=hashlib.sha256(raw).hexdigest()
            title=TITLES[index]
            accepted=inspect_host_attested_master(principal_id=PRINCIPAL,title=title,
              source_path=packed,host_catalog_lookup=lambda p,t,d:{
                'title':t,'principalId':p,'sourceSha256':d,
                'projectId':PIDS[index],'rightsStatus':'ARTIST_OWNED',
                'rightsEvidenceSha256':'e'*64})
            self.assertEqual(accepted['sha'],digest)
            self.assertLessEqual(abs(accepted['physical']['byRate'][48000]['frames']-(index+1)*48000),2048)
            self.assertLessEqual(abs(accepted['physical']['byRate'][44100]['frames']-(index+1)*44100),2048)

if __name__=='__main__':unittest.main()

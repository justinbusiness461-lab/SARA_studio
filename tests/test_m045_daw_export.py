"""R10-B RED: exact owner-and-revision-bound DAW bundle; no invented stems or notes."""
import copy,hashlib,io,json,struct,unittest,wave,zipfile
import studio_server as studio
from test_platform_identity_and_catalog import PlatformHTTP
from m045_stem_reconstruction_owner import authorized_reconstruct_mix

class DawHttp(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.owner=self.fx.signup();self.cookie,_=self.fx.login()
  self.base=self.fx.project(self.owner['principalId'])
  self.request={k:self.base[k] for k in ('projectId','revisionId','artifactId')}
 def request_bundle(self,payload=None,cookie=None):
  return self.fx.req('/api/m045/export-daw-bundle',payload or self.request,cookie=self.cookie if cookie is None else cookie)
 def build_canonical_mix(self):
  frames=6000;sample=struct.pack('<dd',.08,-.12)*frames
  digest=hashlib.sha256(sample).hexdigest()
  studio._publish_cas_exact(self.fx.root,digest,sample)
  spec=copy.deepcopy(studio.project_operation(self.fx.root,{'projectId':self.base['projectId']},
    principal_id=self.owner['principalId'])['songSpec'])
  # Real SongSpec notes remain authoritative; no transcribed or invented pitches.
  spec['timebase']['meter']='4/4'
  spec['tracks'][0]['events']=[{'type':'NOTE','tick':0,'duration_ticks':120,'midi_note':60,'velocity':92}]
  revision=studio.project_operation(self.fx.root,{'projectId':self.base['projectId'],
     'expectedCurrentRevisionId':self.base['revisionId'],'songSpec':spec,
     'sourceAssetDigests':[digest],'outputArtifactIds':[self.base['artifactId']]},
    commit=True,principal_id=self.owner['principalId'])
  parent=revision['revision'];recipe={'schema_version':'sara.mix.recipe.v1',
    'source_project_revision_id':parent['revisionId'],
    'production_timeline_digest':parent['productionTimelineDigest'],
    'stem_artifact_ids':[digest], 'bus_waveshaper':'none','fade_ms':0,
    'target_peak':0.8,'sample_rate':44100,'channels':2,'sample_count':frames,
    'pcm_quantizer':'signed16_round_nearest_ties_even','encoder':'canonical_pcm16_wav_44'}
  output=authorized_reconstruct_mix(self.fx.root,{'projectId':self.base['projectId'],
    'expectedCurrentRevisionId':parent['revisionId'],'mixRecipe':recipe},self.owner['principalId'])
  self.request={'projectId':self.base['projectId'],'revisionId':output['revisionId'],
    'artifactId':output['artifactId'],'mixRecipe':recipe}
  return output
 def test_unauthorized_and_master_without_dry_source_fail_closed(self):
  self.assertEqual(self.fx.api('/api/m045/export-daw-bundle',self.request)[0],403)
  self.assertEqual(self.request_bundle()[0],409)
 def test_bundle_revision_stems_midi_musicxml_and_checksum_identity(self):
  output=self.build_canonical_mix()
  status,headers,data=self.request_bundle()
  self.assertEqual(status,200,data[:200]);self.assertEqual(headers.get('Content-Type'),'application/zip')
  with zipfile.ZipFile(io.BytesIO(data)) as pkg:
   files=pkg.namelist();self.assertIn('daw_manifest.json',files)
   self.assertIn('master_44k1_16b.wav',files)
   self.assertIn('scorecore_arrangement.mid',files)
   self.assertIn('scorecore_arrangement.musicxml',files)
   manifest=json.loads(pkg.read('daw_manifest.json'))
   self.assertEqual(manifest['schema'],'sara.daw.bundle.v1')
   self.assertEqual(manifest['projectRevisionId'],output['revisionId'])
   self.assertEqual(manifest['masterArtifactId'],output['artifactId'])
   self.assertEqual(manifest['midiPpq'],480)
   self.assertEqual(manifest['noteCount'],1)
   self.assertTrue(manifest['reconstructionExact'])
   self.assertFalse(manifest['releaseCleared'])
   for path,sha in manifest['fileSha256'].items():
    self.assertEqual(hashlib.sha256(pkg.read(path)).hexdigest(),sha,path)
   self.assertEqual(hashlib.sha256(pkg.read('master_44k1_16b.wav')).hexdigest(),output['artifactId'])
   self.assertEqual(pkg.read('scorecore_arrangement.mid')[:4],b'MThd')
   self.assertEqual(pkg.read('scorecore_arrangement.mid')[12:14],(480).to_bytes(2,'big'))
   self.assertIn(b'<score-partwise',pkg.read('scorecore_arrangement.musicxml'))
  self.assertEqual(studio.project_operation(self.fx.root,{'projectId':self.base['projectId']},
       principal_id=self.owner['principalId'])['revision']['revisionId'],output['revisionId'])
  self.assertEqual(self.request_bundle()[2],data) # deterministic cold read, no current mutation
 def test_tampered_recipe_and_foreign_principal_are_denied(self):
  self.build_canonical_mix()
  bad={**self.request,'mixRecipe':{**self.request['mixRecipe'],'target_peak':0.5}}
  self.assertEqual(self.request_bundle(bad)[0],409)
  self.fx.signup('artist_b','another strong password!')
  cookie,_=self.fx.login('artist_b','another strong password!')
  self.assertEqual(self.request_bundle(cookie=cookie)[0],403)
 def test_tampered_durable_attempt_cannot_mint_reconstruction_certificate(self):
  result=self.build_canonical_mix()
  from pathlib import Path
  attempt_path=studio.project_owner_directory(self.fx.root,self.base['projectId'],
    self.owner['principalId'])/'render-attempts'/(result['operationId']+'.json')
  recorded=json.loads(attempt_path.read_text())
  recorded['masterProvenance']['transform_chain'][0]['recipeSha256']='0'*64
  attempt_path.write_text(json.dumps(recorded))
  self.assertEqual(self.request_bundle()[0],409)
 def test_recreated_archive_works_after_non_target_successor_revision(self):
  result=self.build_canonical_mix()
  code,headers,original=self.request_bundle();self.assertEqual(code,200)
  current=studio.project_operation(self.fx.root,{'projectId':self.base['projectId']},
    principal_id=self.owner['principalId'])
  successor=studio.project_operation(self.fx.root,{
    'projectId':self.base['projectId'],'expectedCurrentRevisionId':result['revisionId'],
    'songSpec':current['songSpec'],'sourceAssetDigests':current['revision']['sourceAssetDigests'],
    'outputArtifactIds':current['revision']['outputArtifactIds']},
    commit=True,principal_id=self.owner['principalId'])
  self.assertNotEqual(successor['revision']['revisionId'],result['revisionId'])
  code,headers,reopened=self.request_bundle();self.assertEqual(code,200)
  self.assertEqual(reopened,original)
 def test_revoked_session_cannot_export_immutable_history(self):
  self.build_canonical_mix()
  sessions=self.fx.api('/api/me/sessions',cookie=self.cookie)[2]['sessions']
  self.assertEqual(self.fx.api('/api/me/sessions/revoke',{'sessionId':sessions[0]['sessionId']},
                                cookie=self.cookie)[0],200)
  self.assertEqual(self.request_bundle()[0],403)
 def test_bogus_artifact_is_not_authorized_by_cas_presence(self):
  self.build_canonical_mix()
  orphan=hashlib.sha256(b'ORPHAN').hexdigest()
  studio._publish_cas_exact(self.fx.root,orphan,b'ORPHAN')
  self.assertEqual(self.request_bundle({**self.request,'artifactId':orphan})[0],403)

if __name__=='__main__':unittest.main()

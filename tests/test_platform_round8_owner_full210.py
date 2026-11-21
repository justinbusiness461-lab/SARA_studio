"""Physical 210s dry-f64 CAS stem -> canonical 37MB WAV Studio revision."""
import copy,hashlib,os,resource,struct,tempfile,unittest,wave
from pathlib import Path
import studio_server as studio
import test_m045_native_attempt as native
from m045_stem_reconstruction_owner import authorized_reconstruct_mix

class Owned210SecondAudio(unittest.TestCase):
 def setUp(self):
  self.fx=native.NativeAttemptTests()
  self.fx.setUp()
  self.addCleanup(self.fx.tearDown)
 def test_210s_full_wav_has_exact_source_membership_history_and_pcm_readback(self):
  base=self.fx.r1
  root=self.fx.root;pid=self.fx.pid
  frames=210*44100
  specimen=struct.pack('<dd',0.06,-0.06)
  sha=hashlib.sha256()
  with tempfile.TemporaryDirectory() as folder:
   source=Path(folder)/'source.f64'
   with source.open('wb') as f:
    for index in range((frames+16383)//16384):
     block=specimen*min(16384,frames-index*16384)
     f.write(block);sha.update(block)
   digest=sha.hexdigest()
   # Test fixture materialization; ownership is only established by exact
   # revision membership after digest-checked source readback.
   studio._publish_cas_exact(root,digest,source.read_bytes())
   from io import BytesIO
   seed=BytesIO()
   with wave.open(seed,'wb') as w:
    w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
    w.writeframes(struct.pack('<hh',100,-100)*44100)
   parent=seed.getvalue()
   parent_id=hashlib.sha256(parent).hexdigest()
   studio._publish_cas_exact(root,parent_id,parent)
   spec=copy.deepcopy(self.fx.fixture.spec)
   spec['timebase']['initial_bpm']=120
   spec['structure']['sections']=[{
      **spec['structure']['sections'][0],
      'start_tick':0,'end_tick':403200}]
   first=studio.project_operation(root,{'projectId':pid,
      'expectedCurrentRevisionId':base['revision']['revisionId'],
      'songSpec':spec,'sourceAssetDigests':[digest],
      'outputArtifactIds':[parent_id]},commit=True)
   rid=first['revision']['revisionId']
   recipe={'schema_version':'sara.mix.recipe.v1',
      'source_project_revision_id':rid,
      'production_timeline_digest':first['revision']['productionTimelineDigest'],
      'stem_artifact_ids':[digest],'bus_waveshaper':'none',
      'fade_ms':0,'target_peak':0.8,'sample_rate':44100,
      'channels':2,'sample_count':frames,
      'pcm_quantizer':'signed16_round_nearest_ties_even','encoder':'canonical_pcm16_wav_44'}
   result=authorized_reconstruct_mix(root,{'projectId':pid,
      'expectedCurrentRevisionId':rid,'mixRecipe':recipe},studio.LOCAL_PRINCIPAL_ID)
   self.assertEqual(result['state'],'RENDERED_BOUND')
   self.assertFalse(result['releaseCleared'])
   revision=studio.project_operation(root,{'projectId':pid})['revision']
   self.assertEqual(revision['revisionId'],result['revisionId'])
   self.assertEqual(revision['sourceAssetDigests'],[digest])
   master=studio.project_audio_bytes(root,{'projectId':pid,
      'revisionId':result['revisionId'],'artifactId':result['artifactId']})
   self.assertEqual(len(master),44+frames*4)
   self.assertEqual(hashlib.sha256(master).hexdigest(),result['artifactId'])
   with wave.open(__import__('io').BytesIO(master),'rb') as audio:
    self.assertEqual((audio.getnframes(),audio.getframerate(),audio.getnchannels()),
                     (frames,44100,2))
    initial=audio.readframes(128)
    audio.setpos(frames-128)
    final=audio.readframes(128)
    self.assertEqual(initial,final)
    self.assertNotEqual(initial,bytes(len(initial)))
   ancestor=studio.project_operation(root,{'projectId':pid,'revisionId':rid})
   self.assertEqual(ancestor['revision']['revisionId'],rid)
   self.assertNotIn(result['artifactId'],ancestor['revision']['outputArtifactIds'])
   self.assertLess(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,850*1024)

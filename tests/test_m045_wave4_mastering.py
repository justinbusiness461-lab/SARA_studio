"""Wave 004 RED tests: real DSP, lawful master publication and rights receipts."""
import hashlib, io, json, math, socketserver, struct, sys, tempfile, threading, unittest, urllib.error, urllib.request, wave, subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import studio_server as studio
import test_m044_operations as fixtures

def sine_audio(duration=1.1,peak=.13,rate=44100):
 out=io.BytesIO()
 with wave.open(out,'wb') as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate)
  frames=bytearray()
  for i in range(round(rate*duration)):
   x=int(32767*peak*math.sin(2*math.pi*997*i/rate))
   frames.extend(struct.pack('<hh',x,x))
  w.writeframes(bytes(frames))
 return out.getvalue()

class MasterProcessorTests(unittest.TestCase):
 def test_measured_accurate_ceiling_and_physical_output(self):
  from m045_wave4_mastering_provenance import master_wav_to_lufs_target
  data=sine_audio(1.3)
  mastered,receipt=master_wav_to_lufs_target(wav_bytes=data,target_lufs=-14.0,true_peak_ceiling_dbtp=-1.0)
  self.assertEqual(receipt["mastered_wav_sha256"],hashlib.sha256(mastered).hexdigest())
  self.assertLessEqual(receipt["measured_output_true_peak_dbtp"],-0.9,receipt)
  self.assertLess(abs(receipt["measured_output_lufs"]+14),0.65,receipt)
  self.assertTrue(receipt["true_peak_verified"])
  with wave.open(io.BytesIO(mastered)) as w:
   self.assertEqual((w.getframerate(),w.getsampwidth(),w.getnchannels()),(44100,2,2))
 def test_deterministic_gain_and_presets(self):
  from m045_wave4_mastering_provenance import master_wav_to_lufs_target
  data=sine_audio(.8,.06)
  a,one=master_wav_to_lufs_target(wav_bytes=data,target_lufs=-14.0)
  b,two=master_wav_to_lufs_target(wav_bytes=data,target_lufs=-14.0)
  self.assertEqual(a,b);self.assertEqual(one,two)
  club,receipt=master_wav_to_lufs_target(wav_bytes=data,target_lufs=-9.0)
  self.assertLessEqual(receipt['measured_output_true_peak_dbtp'],-0.9)
  self.assertNotEqual(a,club)
 def test_fails_closed_on_silent_or_invalid_presets(self):
  from m045_wave4_mastering_provenance import master_wav_to_lufs_target
  for value in (float('nan'),float('inf'),-50.0,3.0):
   with self.assertRaises(ValueError):master_wav_to_lufs_target(wav_bytes=sine_audio(.5),target_lufs=value)
  with self.assertRaises(ValueError):master_wav_to_lufs_target(wav_bytes=sine_audio(.5,peak=0.0))
 def test_rights_held_without_evidence(self):
  from m045_wave4_mastering_provenance import CanonicalProvenanceRecord
  d=hashlib.sha256(b'one').hexdigest()
  record=CanonicalProvenanceRecord(artifact_sha256=d,pcm_sha256=d,project_id='p',revision_id='r',
   origin_type='DSP_TRANSFORM',preservation_tier='P3',rights_status='UNVERIFIED_HELD',
   parent_artifact_sha256s=[d],transform_chain=[{'kind':'loudness-master'}])
  self.assertFalse(record.to_dict()['release_cleared'])
  with self.assertRaises(ValueError):
   CanonicalProvenanceRecord(artifact_sha256='z'*64,pcm_sha256=d,project_id='p',revision_id='r',
    origin_type='DSP_TRANSFORM',preservation_tier='P3',rights_status='ARTIST_ORIGINAL',
    parent_artifact_sha256s=[d],transform_chain=[]).validate()

class MasterHTTPTests(unittest.TestCase):
 def setUp(self):
  self.fixture=fixtures.OperationTests();self.fixture.setUp()
  self.root=self.fixture.root;self.pid=self.fixture.pid
  self.source=sine_audio(.65)
  self.digest=hashlib.sha256(self.source).hexdigest()
  studio._publish_cas_exact(self.root,self.digest,self.source)
  self.saved=studio.project_operation(self.root,{
   'projectId':self.pid,'expectedCurrentRevisionId':self.fixture.r1['revision']['revisionId'],
   'songSpec':self.fixture.spec,'sourceAssetDigests':[],'outputArtifactIds':[self.digest]},commit=True)
  self.rid=self.saved['revision']['revisionId']
  self.priorRoot,self.priorPort=studio.EXPORT_ROOT,studio.PORT
  self.httpd=socketserver.TCPServer(('127.0.0.1',0),studio.StudioHandler)
  studio.EXPORT_ROOT=self.root;studio.PORT=self.httpd.server_address[1]
  self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True);self.thread.start()
  self.session=studio.issue_studio_session(studio.LOCAL_PRINCIPAL_ID)
 def tearDown(self):
  self.httpd.shutdown();self.httpd.server_close();self.thread.join(timeout=3)
  studio.EXPORT_ROOT=self.priorRoot;studio.PORT=self.priorPort
  self.fixture.tearDown()
 def body(self):
  return {'projectId':self.pid,'revisionId':self.rid,'artifactId':self.digest,
    'expectedCurrentRevisionId':self.rid,'targetLufs':-14.0,'truePeakCeilingDbtp':-1.0}
 def call(self,body=None,session=None):
  h={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{studio.PORT}',
    'X-Studio-Capability':studio.CAPABILITY}
  if session is not None:h['X-Studio-Session']=session
  req=urllib.request.Request(f'http://127.0.0.1:{studio.PORT}/api/m045/master',
    data=json.dumps(body or self.body()).encode(),headers=h)
  try:
   with urllib.request.urlopen(req,timeout=30) as r:return r.status,json.loads(r.read())
  except urllib.error.HTTPError as e:
   return e.code,json.loads(e.read())
 def test_lawful_master_revision_historical_and_provenance_readback(self):
  status,receipt=self.call(session=self.session)
  self.assertEqual(status,200,receipt)
  self.assertNotEqual(receipt['revisionId'],self.rid)
  self.assertEqual(receipt['sourceArtifactId'],self.digest)
  self.assertEqual(receipt['rightsStatus'],'UNVERIFIED_HELD')
  self.assertFalse(receipt['releaseCleared'])
  output=studio.project_audio_bytes(self.root,{'projectId':self.pid,'revisionId':receipt['revisionId'],'artifactId':receipt['artifactId']})
  self.assertEqual(hashlib.sha256(output).hexdigest(),receipt['artifactId'])
  original=studio.project_audio_bytes(self.root,{'projectId':self.pid,'revisionId':self.rid,'artifactId':self.digest})
  self.assertEqual(original,self.source)
  live=studio.project_operation(self.root,{'projectId':self.pid})
  self.assertEqual(live['manifest']['currentRevisionId'],receipt['revisionId'])
  attempts=list((self.root/'projects'/self.pid/'render-attempts').glob('master-*.json'))
  self.assertEqual(len(attempts),1)
  attempt=json.loads(attempts[0].read_text())
  self.assertEqual(attempt['masterProvenance']['parent_artifact_sha256s'],[self.digest])
  self.assertEqual(attempt['masterProvenance']['artifact_sha256'],receipt['artifactId'])
  self.assertFalse(attempt['masterProvenance']['release_cleared'])
 def test_provenance_pcm_digest_matches_decoded_audio_not_fixed_header_offset(self):
  status,receipt=self.call(session=self.session)
  self.assertEqual(status,200,receipt)
  attempts=list((self.root/'projects'/self.pid/'render-attempts').glob('master-*.json'))
  provenance=json.loads(attempts[0].read_text())['masterProvenance']
  actual=studio.project_audio_bytes(self.root,{'projectId':self.pid,
   'revisionId':receipt['revisionId'],'artifactId':receipt['artifactId']})
  with wave.open(io.BytesIO(actual),'rb') as w:
   pcm=w.readframes(w.getnframes())
  self.assertEqual(provenance['pcm_sha256'],hashlib.sha256(pcm).hexdigest())
 def test_sonic_lock_blocks_global_master(self):
  spec={**self.fixture.spec,'tracks':[{**self.fixture.spec['tracks'][0],'sonic_lock':True}]}
  locked=studio.project_operation(self.root,{
   'projectId':self.pid,'expectedCurrentRevisionId':self.rid,
   'songSpec':spec,'sourceAssetDigests':[],'outputArtifactIds':[self.digest]},commit=True)
  rid=locked['revision']['revisionId']
  status,result=self.call(body={**self.body(),'revisionId':rid,
   'expectedCurrentRevisionId':rid},session=self.session)
  self.assertIn(status,(403,409),result)
 def test_master_survives_fresh_owner_process_and_historical_audio_remains_lawful(self):
  status,receipt=self.call(session=self.session)
  self.assertEqual(status,200,receipt)
  script="""
import hashlib,json,sys
import studio_server as s
root,pid,rid,aid,old_rid,old_aid=sys.argv[1:]
history=s.project_operation(root,{'projectId':pid,'revisionId':rid})
assert history['revision']['revisionId']==rid
assert history['manifest']['currentRevisionId']==rid
assert hashlib.sha256(s.project_audio_bytes(root,{'projectId':pid,'revisionId':rid,'artifactId':aid})).hexdigest()==aid
assert hashlib.sha256(s.project_audio_bytes(root,{'projectId':pid,'revisionId':old_rid,'artifactId':old_aid})).hexdigest()==old_aid
print('FRESH_PROCESS_HISTORY_AND_SOURCE_PASS')
"""
  import os
  cp=subprocess.run([sys.executable,'-c',script,str(self.root),self.pid,
    receipt['revisionId'],receipt['artifactId'],self.rid,self.digest],
    cwd=Path(__file__).resolve().parents[1],
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]/'tools')},
    capture_output=True,text=True,timeout=20)
  self.assertEqual(cp.returncode,0,cp.stderr)
  self.assertIn('FRESH_PROCESS_HISTORY_AND_SOURCE_PASS',cp.stdout)
 def test_denies_missing_session_foreign_and_unbound_CAS(self):
  self.assertEqual(self.call()[0],403)
  foreign=studio.issue_studio_session('another-principal')
  self.assertEqual(self.call(session=foreign)[0],403)
  orphan=hashlib.sha256(b'not-owned').hexdigest()
  studio._publish_cas_exact(self.root,orphan,b'not-owned')
  self.assertEqual(self.call(body={**self.body(),'artifactId':orphan},session=self.session)[0],403)
  self.assertEqual(self.call(body={**self.body(),'rightsStatus':'LICENSE_CLEARED'},session=self.session)[0],400)
 def test_stale_revision_and_no_false_p0(self):
  self.assertEqual(self.call(body={**self.body(),'expectedCurrentRevisionId':'stale'},session=self.session)[0],409)
  self.assertEqual(self.call(body={**self.body(),'promoteToP0':True},session=self.session)[0],400)

if __name__=='__main__':unittest.main()

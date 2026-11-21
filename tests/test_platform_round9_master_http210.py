"""R9-B physical 210-second authenticated HTTP POST master and immutable proof."""
import hashlib,io,json,subprocess,tempfile,unittest,urllib.request,urllib.error,wave
from pathlib import Path
import studio_server as studio
from test_platform_identity_and_catalog import PlatformHTTP,SPEC

class LongMasterHttp(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.owner=self.fx.signup();self.cookie,_=self.fx.login()
 def test_210s_stereo_http_master_dual_meter_receipt_and_stale_fencing(self):
  with tempfile.TemporaryDirectory() as tmp:
   source_path=Path(tmp)/'source.wav'
   subprocess.run(['ffmpeg','-nostdin','-y','-hide_banner','-loglevel','error',
       '-f','lavfi','-i','sine=frequency=997:sample_rate=44100:duration=210',
       '-ar','44100','-ac','2','-c:a','pcm_s16le',str(source_path)],
       check=True,timeout=35)
   source=source_path.read_bytes()
  principal=self.owner['principalId']
  first=studio.project_operation(self.fx.root,{
     'expectedCurrentRevisionId':None,'songSpec':SPEC},commit=True,principal_id=principal)
  aid=hashlib.sha256(source).hexdigest()
  studio._publish_cas_exact(self.fx.root,aid,source)
  bound=studio.project_operation(self.fx.root,{
      'projectId':first['manifest']['projectId'],
      'expectedCurrentRevisionId':first['revision']['revisionId'],
      'songSpec':SPEC,'outputArtifactIds':[aid]},commit=True,principal_id=principal)
  pid,rid=bound['manifest']['projectId'],bound['revision']['revisionId']
  payload={'projectId':pid,'revisionId':rid,'artifactId':aid,
      'expectedCurrentRevisionId':rid,'targetLufs':-14.,'truePeakCeilingDbtp':-1.}
  url=f'http://127.0.0.1:{studio.PORT}/api/m045/master'
  def call(cookie,payload):
   req=urllib.request.Request(url,method='POST',data=json.dumps(payload).encode(),
      headers={'Origin':f'http://127.0.0.1:{studio.PORT}',
       'X-Studio-Capability':studio.CAPABILITY,'Cookie':cookie,
       'Content-Type':'application/json'})
   try:
    with urllib.request.urlopen(req,timeout=120) as res:return res.status,json.loads(res.read())
   except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
  status,data=call(self.cookie,payload)
  self.assertEqual(status,200,data)
  receipt=data['telemetry']['reference_meter']
  self.assertEqual(receipt['samples_per_channel'],9261000)
  self.assertEqual(receipt['oversample_factor'],4)
  self.assertLess(abs(receipt['integrated_lufs']-data['telemetry']['measured_output_lufs']),.3)
  self.assertLess(abs(receipt['true_peak_dbtp']-data['telemetry']['measured_output_true_peak_dbtp']),.4)
  self.assertEqual(receipt['input_wav_sha256'],data['artifactId'])
  self.assertFalse(data['releaseCleared'])
  self.assertEqual(data['rightsStatus'],'UNVERIFIED_HELD')
  current=studio.project_operation(self.fx.root,{'projectId':pid},principal_id=principal)
  self.assertEqual(current['revision']['revisionId'],data['revisionId'])
  audio=studio.project_audio_bytes(self.fx.root,{'projectId':pid,
    'revisionId':data['revisionId'],'artifactId':data['artifactId']},principal_id=principal)
  self.assertEqual(hashlib.sha256(audio).hexdigest(),data['artifactId'])
  with wave.open(io.BytesIO(audio),'rb') as wav:
   self.assertEqual((wav.getnframes(),wav.getnchannels(),wav.getframerate()),(9261000,2,44100))
  self.assertEqual(call(self.cookie,payload)[0],409)
  self.fx.signup('artist_b','another strong password!')
  other,_=self.fx.login('artist_b','another strong password!')
  self.assertEqual(call(other,payload)[0],403)

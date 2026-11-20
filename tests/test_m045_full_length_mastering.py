"""Regression-first full-length CPU mastering: bounded 210s PCM, durable CAS, rights HELD."""
import hashlib, io, json, os, resource, subprocess, sys, tempfile, unittest, wave
from pathlib import Path
from m045_wave4_mastering_provenance import master_wav_to_lufs_target
import studio_server as studio
from m045_wave4_service import authorized_master

SPEC={'song_id':'long-master','timebase':{'initial_bpm':120,'ticks_per_quarter_note':960},
 'structure':{'sections':[{'id':'full_song','start_tick':0,'end_tick':403200}]},
 'tracks':[{'track_id':'bass','events':[]}]}

class FullLengthMasterBoundary(unittest.TestCase):
 def make_audio(self,seconds):
  # Deterministic PCM16 stereo synth directly to disk with FFmpeg; no large Python loops.
  path=self.root/f'original_{seconds}.wav'
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
      '-f','lavfi','-i',f'sine=frequency=997:sample_rate=44100:duration={seconds}',
      '-ac','2','-c:a','pcm_s16le',str(path)],capture_output=True,check=True,timeout=65)
  return path.read_bytes()

 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='sara-long-master-proof-')
  self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name)

 def test_210_second_pcm_stereo_master_is_physically_decodable_and_measured(self):
  source=self.make_audio(210)
  self.assertGreater(len(source),16*1024*1024)
  original_digest=hashlib.sha256(source).hexdigest()
  master,telemetry=master_wav_to_lufs_target(wav_bytes=source,target_lufs=-14.0,
                                             true_peak_ceiling_dbtp=-1.0)
  self.assertEqual(hashlib.sha256(source).hexdigest(),original_digest)
  self.assertEqual(hashlib.sha256(master).hexdigest(),telemetry['mastered_wav_sha256'])
  with wave.open(io.BytesIO(master),'rb') as decoded:
   self.assertEqual((decoded.getframerate(),decoded.getnchannels(),decoded.getsampwidth()),
     (44100,2,2))
   self.assertEqual(decoded.getnframes(),210*44100)
  self.assertLessEqual(telemetry['measured_output_true_peak_dbtp'],-.9,telemetry)
  self.assertLessEqual(abs(telemetry['measured_output_lufs']+14),.65,telemetry)
  self.assertEqual(telemetry['meterConformance'],'NOT_INDEPENDENTLY_CERTIFIED')
  self.assertLess(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,850*1024) # KiB on Linux

 def test_180_second_cas_revision_and_cold_restart_historical_source(self):
  source=self.make_audio(180)
  self.assertGreater(len(source),16*1024*1024)
  parent=self.root/'cas'
  original_sha=hashlib.sha256(source).hexdigest()
  studio._publish_cas_exact(parent,original_sha,source)
  first=studio.project_operation(parent,{'projectId':'a'*32,'expectedCurrentRevisionId':None,
    'songSpec':SPEC},commit=True)
  authorized=studio.project_operation(parent,{'projectId':'a'*32,
    'expectedCurrentRevisionId':first['revision']['revisionId'],'songSpec':SPEC,
    'outputArtifactIds':[original_sha]},commit=True)
  rid=authorized['revision']['revisionId']
  receipt=authorized_master(parent,{'projectId':'a'*32,'revisionId':rid,
    'expectedCurrentRevisionId':rid,'artifactId':original_sha,
    'targetLufs':-14.0,'truePeakCeilingDbtp':-1.0},studio.LOCAL_PRINCIPAL_ID)
  self.assertEqual(receipt['status'],'SUCCESS')
  self.assertEqual(receipt['rightsStatus'],'UNVERIFIED_HELD')
  self.assertFalse(receipt['releaseCleared'])
  self.assertNotEqual(receipt['revisionId'],rid)
  self.assertLessEqual(receipt['telemetry']['measured_output_true_peak_dbtp'],-.9)
  self.assertLess(abs(receipt['telemetry']['measured_output_lufs']+14),.65)
  new=studio.project_audio_bytes(parent,{'projectId':'a'*32,'revisionId':receipt['revisionId'],
      'artifactId':receipt['artifactId']})
  self.assertEqual(hashlib.sha256(new).hexdigest(),receipt['artifactId'])
  self.assertEqual(studio.project_audio_bytes(parent,{'projectId':'a'*32,'revisionId':rid,
      'artifactId':original_sha}),source)
  with wave.open(io.BytesIO(new),'rb') as decoded:self.assertEqual(decoded.getnframes(),180*44100)
  code=("import studio_server as s,sys,hashlib; r,p,rv,av,old,old_a=sys.argv[1:];"
      "x=s.project_operation(r,{'projectId':p});assert x['revision']['revisionId']==rv;"
      "assert hashlib.sha256(s.project_audio_bytes(r,{'projectId':p,'revisionId':rv,'artifactId':av})).hexdigest()==av;"
      "assert hashlib.sha256(s.project_audio_bytes(r,{'projectId':p,'revisionId':old,'artifactId':old_a})).hexdigest()==old_a;"
      "print('180S_COLD_REOPEN_PASS')")
  subprocess.run([sys.executable,'-c',code,str(parent),'a'*32,receipt['revisionId'],
    receipt['artifactId'],rid,original_sha],env={**os.environ,'PYTHONPATH':str(Path(studio.__file__).parent)},
    capture_output=True,text=True,check=True,timeout=40)
  self.assertLess(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,850*1024)

if __name__=='__main__':unittest.main()

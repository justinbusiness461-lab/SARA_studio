"""Physical CPU-only 210s mastering and immutable Studio authorization regression.

This checks a fully associated 210s source/master, NOT licensing, certified
BS.1770 metrology, streaming-platform conformance or human listening approval.
"""
import hashlib,io,subprocess,tempfile,unittest,wave
from pathlib import Path
import studio_server as studio
from m045_wave4_service import authorized_master

class FullSongMasterOwner(unittest.TestCase):
 def test_210_second_stereo_source_master_cas_and_fresh_process_readback(self):
  with tempfile.TemporaryDirectory(prefix="sara-master-210-") as tmp:
   root=Path(tmp)
   source_path=root/"synthetic-210.wav"
   subprocess.run(["ffmpeg","-y","-nostdin","-hide_banner","-loglevel","error",
     "-f","lavfi","-i","sine=frequency=220:sample_rate=44100:duration=210",
     "-ar","44100","-ac","2","-c:a","pcm_s16le",str(source_path)],check=True,timeout=35)
   source=source_path.read_bytes()
   with wave.open(io.BytesIO(source),"rb") as wav:
    self.assertEqual(wav.getnframes(),210*44100)
    self.assertEqual(wav.getnchannels(),2)
   self.assertGreater(len(source),16*1024*1024)
   self.assertLess(len(source),40*1024*1024)
   spec={"song_id":"fullsong-210","title":"Synth Fixture 210",
    "timebase":{"initial_bpm":120,"ticks_per_quarter_note":960},
    "structure":{"sections":[{"id":"long_intro","start_tick":0,"end_tick":420*960}]},
    "tracks":[{"track_id":"lead","events":[]}]}
   principal=studio.LOCAL_PRINCIPAL_ID
   created=studio.project_operation(root,
       {"expectedCurrentRevisionId":None,"songSpec":spec},commit=True,principal_id=principal)
   digest=hashlib.sha256(source).hexdigest()
   studio._publish_cas_exact(root,digest,source)
   bound=studio.project_operation(root,{"projectId":created["manifest"]["projectId"],
      "expectedCurrentRevisionId":created["revision"]["revisionId"],
      "songSpec":spec,"outputArtifactIds":[digest]},commit=True,principal_id=principal)
   pid,rid=bound["manifest"]["projectId"],bound["revision"]["revisionId"]
   result=authorized_master(root,{"projectId":pid,"revisionId":rid,
    "artifactId":digest,"expectedCurrentRevisionId":rid,"targetLufs":-14.0,
    "truePeakCeilingDbtp":-1.0},principal_id=principal)
   self.assertEqual(result["status"],"SUCCESS")
   self.assertFalse(result["releaseCleared"])
   self.assertEqual(result["rightsStatus"],"UNVERIFIED_HELD")
   out=studio.project_audio_bytes(root,{"projectId":pid,
       "revisionId":result["revisionId"],"artifactId":result["artifactId"]},
       principal_id=principal)
   self.assertEqual(hashlib.sha256(out).hexdigest(),result["artifactId"])
   with wave.open(io.BytesIO(out),"rb") as wav:
    self.assertEqual(wav.getnframes(),210*44100)
    self.assertEqual(wav.getnchannels(),2)
    self.assertEqual(wav.getframerate(),44100)
   self.assertEqual(hashlib.sha256(studio.project_audio_bytes(root,
      {"projectId":pid,"revisionId":rid,"artifactId":digest},
      principal_id=principal)).hexdigest(),digest)
   telemetry=result["telemetry"]
   self.assertLessEqual(telemetry["measured_output_true_peak_dbtp"],-0.95)
   self.assertEqual(telemetry["meterConformance"],"NOT_INDEPENDENTLY_CERTIFIED")
   self.assertEqual(telemetry["mastered_wav_sha256"],result["artifactId"])
   code='''import sys,hashlib
sys.path.insert(0,"tools")
from studio_server import project_audio_bytes
data=project_audio_bytes(sys.argv[1],{"projectId":sys.argv[2],
"revisionId":sys.argv[3],"artifactId":sys.argv[4]},principal_id=sys.argv[5])
print(hashlib.sha256(data).hexdigest())'''
   fresh=subprocess.run(["python3","-c",code,str(root),pid,
     result["revisionId"],result["artifactId"],principal],
     check=True,capture_output=True,text=True,timeout=30)
   self.assertEqual(fresh.stdout.strip(),result["artifactId"])

if __name__=="__main__":unittest.main()


"""R11-B physically verify true 210s canonical DAW ZIP from owner and cold re-open."""
import hashlib,json,resource,tempfile,unittest,zipfile,wave,subprocess
from pathlib import Path
from test_m045_daw_export import DawHttp
from m045_daw_export import export_authorized_daw_bundle,verify_authorized_daw_bundle
class LongDawRoundtrip(unittest.TestCase):
 def test_210_second_bundle_streaming_source_and_master_identity(self):
  fx=DawHttp('test_bundle_revision_stems_midi_musicxml_and_checksum_identity')
  fx.setUp();self.addCleanup(fx.doCleanups)
  output=fx.build_canonical_mix(frames=210*44100)
  with tempfile.TemporaryDirectory() as directory:
   bundle=Path(directory)/'original.zip'
   out=export_authorized_daw_bundle(fx.fx.root,fx.request,fx.owner['principalId'],bundle)
   self.assertEqual(out['state'],'DAW_BUNDLE_PREPARED_PRIVATE')
   receipt=verify_authorized_daw_bundle(fx.fx.root,fx.request,fx.owner['principalId'],bundle)
   self.assertEqual(receipt['state'],'VERIFIED_UNMODIFIED_BUNDLE')
   self.assertEqual(receipt['masterArtifactId'],output['artifactId'])
   with zipfile.ZipFile(bundle) as archive:
    info=archive.getinfo('master_44k1_16b.wav')
    self.assertEqual(info.file_size,44+210*44100*4)
    master=Path(directory)/'decoded-master.wav'
    with master.open('wb') as f,archive.open(info) as source:
     for chunk in iter(lambda:source.read(1024*1024),b''):f.write(chunk)
    self.assertEqual(hashlib.sha256(master.read_bytes()).hexdigest(),output['artifactId'])
    with wave.open(str(master),'rb') as w:
     self.assertEqual((w.getnframes(),w.getframerate(),w.getnchannels(),w.getsampwidth()),(9261000,44100,2,2))
    ff=subprocess.run(['/usr/local/bin/ffprobe','-v','error','-select_streams','a:0',
       '-show_entries','stream=sample_rate,channels,codec_name,duration','-of','json',str(master)],
       check=True,capture_output=True,text=True)
    stream=json.loads(ff.stdout)['streams'][0]
    self.assertEqual((stream['sample_rate'],stream['channels'],stream['codec_name']),('44100',2,'pcm_s16le'))
    print('DAW_R11_210_PHYSICAL',json.dumps({'archiveSha256':receipt['archiveSha256'],
      'masterSha256':output['artifactId'],'masterFrames':9261000,
      'zipBytes':bundle.stat().st_size,'peakRssKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
      'ffprobe':stream},sort_keys=True))
if __name__=='__main__':unittest.main()

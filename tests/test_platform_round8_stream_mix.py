"""R8-A RED: bounded deterministic f64 stem reader, 210s PCM16 output."""
import copy,hashlib,struct,tempfile,unittest,os,wave
from pathlib import Path
from m045_stem_reconstruction import reconstruct_master

class StreamMixTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.folder=Path(self.tmp.name)
  self.frames=2005
  self.stems=[
    b''.join(struct.pack('<dd',0.16 if i%4 else -0.26,0.04) for i in range(self.frames)),
    b''.join(struct.pack('<dd',-0.01,0.008 if i%3 else -0.08) for i in range(self.frames))]
  self.recipe={'schema_version':'sara.mix.recipe.v1',
   'source_project_revision_id':'a'*64,'production_timeline_digest':'b'*64,
   'stem_artifact_ids':[hashlib.sha256(d).hexdigest() for d in self.stems],
   'bus_waveshaper':'tanh','fade_ms':5.0,'target_peak':0.89,
   'sample_rate':44100,'channels':2,'sample_count':self.frames,
   'pcm_quantizer':'signed16_round_nearest_ties_even','encoder':'canonical_pcm16_wav_44'}
  self.paths=[]
  for i,data in enumerate(self.stems):
   p=self.folder/f'stem{i}.f64';p.write_bytes(data);self.paths.append(p)
 def test_small_exact_stream_is_byte_identical_to_existing_algorithm(self):
  from m045_stem_reconstruction import reconstruct_master_to_file
  dst=self.folder/'mix.wav'
  outcome=reconstruct_master_to_file(self.paths,self.recipe,dst,chunk_frames=128)
  assert dst.read_bytes()==reconstruct_master(self.stems,self.recipe)
  self.assertEqual(outcome['sha256'],hashlib.sha256(dst.read_bytes()).hexdigest())
 def test_forged_digest_symlink_misaligned_input_rejected(self):
  from m045_stem_reconstruction import reconstruct_master_to_file
  dst=self.folder/'mix.wav'
  wrong={**self.recipe,'stem_artifact_ids':['f'*64,self.recipe['stem_artifact_ids'][1]]}
  with self.assertRaises(ValueError):
   reconstruct_master_to_file(self.paths,wrong,dst)
  symlink=self.folder/'link.f64';symlink.symlink_to(self.paths[0])
  with self.assertRaises((ValueError,OSError)):
   reconstruct_master_to_file([symlink,self.paths[1]],self.recipe,dst)
  self.paths[0].write_bytes(self.stems[0][:-8])
  with self.assertRaises(ValueError):
   reconstruct_master_to_file(self.paths,self.recipe,dst)
 def test_210s_stream_exact_frame_count_under_memory_cap(self):
  from m045_stem_reconstruction import reconstruct_master_to_file
  frames=44100*210
  raw=struct.pack('<dd',0.04,-0.04)
  large=self.folder/'large.f64'
  sha=hashlib.sha256()
  with large.open('wb') as f:
   for i in range((frames+16383)//16384):
    block=raw*min(16384,frames-i*16384)
    f.write(block);sha.update(block)
  recipe={**self.recipe,'sample_count':frames,'stem_artifact_ids':[sha.hexdigest()],
          'bus_waveshaper':'none','fade_ms':0,'target_peak':0.88}
  dest=self.folder/'full.wav'
  out=reconstruct_master_to_file([large],recipe,dest,chunk_frames=16384)
  self.assertEqual(out['sample_count'],frames)
  self.assertEqual(out['byte_length'],44+frames*4)
  with wave.open(str(dest),'rb') as f:
   self.assertEqual((f.getnframes(),f.getframerate(),f.getnchannels(),f.getsampwidth()),(frames,44100,2,2))
  self.assertEqual(dest.stat().st_size,44+frames*4)

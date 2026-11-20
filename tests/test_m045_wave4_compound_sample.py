"""Wave004 source-only tests: no audio publication or cloned rights authority."""
import hashlib,io,math,struct,unittest,wave
from m045_edit_proposal import compile_compound_plan
from m045_sample_lab_dsp import slice_sample,resonant_lowpass,metallic_comb,rate_pitch_shift,apply_effect_graph

def pcm(frames=5000,rate=44100):
 b=io.BytesIO()
 with wave.open(b,'wb') as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate)
  w.writeframes(b''.join(struct.pack('<hh',*([int(8000*math.sin(2*math.pi*i*997/rate))]*2)) for i in range(frames)))
 return b.getvalue()

class CompoundSample(unittest.TestCase):
 def spec(self,lock_bass=False,lock_verse=False):
  return {'structure':{'sections':[{'id':'s0','name':'Verse','type':'verse','start_tick':0},
   {'id':'h1','name':'Chorus','type':'chorus','sonic_lock':True,'start_tick':3840},
   {'id':'s2','name':'Verse','type':'verse','sonic_lock':lock_verse,'start_tick':7680}]},
   'tracks':[{'track_id':'bass','sonic_lock':lock_bass},{'track_id':'percussion','sonic_lock':False}]}
 def test_natural_compound_scope_and_immutable_spec(self):
  spec=self.spec();before=repr(spec)
  p=compile_compound_plan('Keep the hook exactly the same, slow down the middle verse a little, make the bass darker, add a weird metallic sound.',spec)
  self.assertEqual([x['kind'] for x in p['operations']],['vocalPhrasing','filter','metallic'])
  self.assertEqual(p['operations'][0]['sectionId'],'s2')
  self.assertEqual(p['preservedSectionIds'],['h1']);self.assertEqual(repr(spec),before)
 def test_ambiguous_and_locked_fail_atomically(self):
  for prompt,spec in [('darken bass',self.spec(lock_bass=True)),('slow down verse 2',self.spec(lock_verse=True)),('make it awesome',self.spec()),('darken bass, darken bass',self.spec())]:
   with self.subTest(prompt=prompt),self.assertRaises(ValueError):compile_compound_plan(prompt,spec)
 def test_selected_frame_slice_does_not_expand_source(self):
  source=pcm(44100*15);digest=hashlib.sha256(source).hexdigest()
  cut=slice_sample(source,110,44110)
  with wave.open(io.BytesIO(cut),'rb') as w:self.assertEqual(w.getnframes(),44000)
  self.assertEqual(hashlib.sha256(source).hexdigest(),digest)
  with self.assertRaises(ValueError):slice_sample(source,-1,44)
 def test_filter_comb_varispeed_and_graph(self):
  source=pcm();digest=hashlib.sha256(source).hexdigest()
  for out in [resonant_lowpass(source,900,.707),metallic_comb(source,3,.55),apply_effect_graph(source,[{'id':'a','operation':'lowpass','input':'source','cutoffHz':900,'q':.707},{'id':'b','operation':'metallic_comb','input':'a','delayMs':3,'feedback':.55}],output_id='b')]:
   self.assertNotEqual(out,source)
   with wave.open(io.BytesIO(out),'rb') as w:self.assertEqual(w.getnframes(),5000)
  with wave.open(io.BytesIO(rate_pitch_shift(source,12)),'rb') as w:self.assertEqual(w.getnframes(),2500)
  self.assertEqual(hashlib.sha256(source).hexdigest(),digest)
 def test_fx_graph_rejects_cycles_and_duplicates(self):
  a={'id':'same','operation':'lowpass','input':'source','cutoffHz':900,'q':.707}
  with self.assertRaises(ValueError):apply_effect_graph(pcm(),[a,a],output_id='same')
  with self.assertRaises(ValueError):apply_effect_graph(pcm(),[{**a,'input':'same'}],output_id='same')

if __name__=='__main__':unittest.main()
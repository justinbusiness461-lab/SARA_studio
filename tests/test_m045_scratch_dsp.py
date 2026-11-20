import io,math,struct,sys,unittest,wave,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from m045_scratch_dsp import render_scratch_mix, waveform_pcm

def wav(samples,rate=44100):
 b=io.BytesIO()
 with wave.open(b,"wb") as f:
  f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate)
  f.writeframes(b"".join(struct.pack("<hh",*v) for v in samples))
 return b.getvalue()

class ScratchDSPTests(unittest.TestCase):
 def setUp(self):
  self.base=wav([(0,0)]*2200)
  self.scratch=wav([(10000,-9000)]*200)
 def marker(self,deck="A",start=600,technique="baby"):
  return {"type":"DJ_SCRATCH_MARKER","event_id":f"dj:test:{start}:{deck}",
   "tick":0,"duration_ticks":480,"deck":deck,"technique":technique,
   "sample_index":start,"audio_status":"UNRENDERED_SOURCE_ASSET_REQUIRED"}
 def test_samples_outside_scheduled_windows_are_bit_exact(self):
  mixed,proof=render_scratch_mix(self.base,
    [{"marker":self.marker(),"sample_asset_wav":self.scratch,"source_asset_digest":hashlib.sha256(self.scratch).hexdigest()}],
    window_frames=200)
  b,_=waveform_pcm(self.base);a,_=waveform_pcm(mixed)
  self.assertEqual(b[:600*4],a[:600*4]);self.assertEqual(b[800*4:],a[800*4:])
  self.assertEqual(proof["sample_rate"],44100)
  self.assertEqual(proof["sample_windows"],[[600,800]])
  self.assertEqual(proof["fade_samples"],50)  # 2ms capped to 1/4 event
  self.assertNotEqual(a[675*4:700*4],b[675*4:700*4])
 def test_simultaneous_decks_sum_before_clamp(self):
  a=self.marker("A");b=self.marker("B")
  source=wav([(22000,22000)]*200)
  digest=hashlib.sha256(source).hexdigest()
  output,proof=render_scratch_mix(self.base,[
   {"marker":a,"sample_asset_wav":source,"source_asset_digest":digest},
   {"marker":b,"sample_asset_wav":source,"source_asset_digest":digest}],window_frames=200)
  pcm,_=waveform_pcm(output)
  # Peak in the center exceeds PCM ceiling, but remains clipped only once
  self.assertEqual(struct.unpack_from("<h",pcm,700*4)[0],32767)
  self.assertEqual(proof["decks"],["A","B"])
 def test_rate_digest_and_missing_source_rejected(self):
  with self.assertRaises(ValueError):
   render_scratch_mix(self.base,[{"marker":self.marker(),"sample_asset_wav":None,
    "source_asset_digest":"0"*64}],window_frames=200)
  with self.assertRaises(ValueError):
   render_scratch_mix(self.base,[{"marker":self.marker(),"sample_asset_wav":wav([(1,1)]*200,48000),
    "source_asset_digest":"0"*64}],window_frames=200)
 def test_reverse_fractional_position_and_silent_source(self):
  source=wav([(i*50,i*50) for i in range(200)])
  output,proof=render_scratch_mix(self.base,[{"marker":self.marker(technique="chirp"),
    "sample_asset_wav":source,"source_asset_digest":hashlib.sha256(source).hexdigest()}],window_frames=200)
  self.assertEqual(proof["techniques"],["chirp"])
  self.assertNotEqual(output,self.base)

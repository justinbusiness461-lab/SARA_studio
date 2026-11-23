"""R9-B RED: deterministic K-weighting, 400ms gates, 4x truepeak vectors."""
import io,math,struct,tempfile,unittest,wave
from pathlib import Path
from m045_bs1770_reference import measure_reference_pcm16, k_weighting_biquads

def fixture(rate=48000,duration=2.0,frequency=997,amplitude=0.5,phase=0,silence_start=None):
 frames=int(rate*duration)
 buffer=io.BytesIO()
 with wave.open(buffer,'wb') as f:
  f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate)
  raw=bytearray()
  for i in range(frames):
   value=0 if silence_start is not None and i>=rate*silence_start else int(round(amplitude*32767*math.sin(2*math.pi*frequency*i/rate+phase)))
   raw.extend(struct.pack('<hh',value,value))
  f.writeframes(raw)
 return buffer.getvalue()

class ReferenceLoudness(unittest.TestCase):
 def test_48k_table_coefficients_and_44100_design_are_real_biquads(self):
  shelf,rlb=k_weighting_biquads(48000)
  self.assertAlmostEqual(shelf[0][0],1.53512485958697,places=10)
  self.assertAlmostEqual(shelf[1][1],-1.69065929318241,places=10)
  self.assertAlmostEqual(rlb[1][1],-1.99004745483398,places=10)
  for rate in (44100,48000):
   a,b=k_weighting_biquads(rate)
   self.assertEqual(len(a[0]),3)
   self.assertEqual(len(b[1]),3)
  with self.assertRaises(ValueError):k_weighting_biquads(32000)
 def test_997hz_stereo_calibration_tone_lufs_at_both_rates(self):
  for rate in (44100,48000):
   result=measure_reference_pcm16(fixture(rate))
   self.assertAlmostEqual(result['integrated_lufs'],-6.02,delta=0.3)
   self.assertAlmostEqual(result['true_peak_dbtp'],-6.02,delta=0.3)
   self.assertEqual(result['gating_block_ms'],400)
   self.assertEqual(result['hop_ms'],100)
   self.assertEqual(result['oversample_factor'],4)
   self.assertEqual(result['meterConformance'],'REFERENCE_VECTOR_TESTED_NOT_INDEPENDENTLY_CERTIFIED')
 def test_absolute_and_relative_gates_exclude_silence(self):
  full=measure_reference_pcm16(fixture(48000,duration=2.0))
  partial=measure_reference_pcm16(fixture(48000,duration=4.0,silence_start=2))
  # FFmpeg ebur128 independently observes -6.4 LUFS: boundary
  # 400ms windows straddling the 2s tone/silence transition retain energy.
  self.assertAlmostEqual(partial['integrated_lufs'],-6.36,delta=.2)
  self.assertGreater(partial['blocks_rejected'],0)
  with self.assertRaises(ValueError):measure_reference_pcm16(fixture(48000,duration=1.0,amplitude=0))
 def test_fs_over_four_inter_sample_peak_higher_than_sample_peak(self):
  data=fixture(48000,frequency=12000,amplitude=.98,phase=math.pi/4)
  result=measure_reference_pcm16(data)
  self.assertGreater(result['true_peak_dbtp']-result['sample_peak_dbfs'],1.9)
  # FFmpeg ebur128 measures +0.4 dBTP on this abrupt-start fs/4 tone.
  self.assertAlmostEqual(result['true_peak_dbtp'],.4,delta=.2)
 def test_wav_does_not_claim_reference_on_forged_header(self):
  data=bytearray(fixture())
  data[0:4]=b'BAD!'
  with self.assertRaises(ValueError):measure_reference_pcm16(bytes(data))

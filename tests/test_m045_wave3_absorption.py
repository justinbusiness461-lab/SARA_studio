"""Wave 003 native capability tests. W003 local RED preceded module creation."""
import io, math, struct, unittest, wave, xml.etree.ElementTree as ET, hashlib, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m045_wave3_rhythm_harmony import derive_subdivision_step_sample, build_subdivision_pattern_events, analyze_harmonic_and_tempo_compatibility, crossfade_pcm16_wavs
from m045_audio_to_midi import transcribe_wav_to_scorecore_notes, export_scorecore_notes_to_musicxml, export_scorecore_notes_to_smf
from m045_fm_preview_synth import render_fm_preview_wav

class Wave3Tests(unittest.TestCase):
 def test_triplet_and_swing_sample_clock(self):
  self.assertEqual(derive_subdivision_step_sample(bpm=120,bar=1,step_index=1,subdivision='8th_triplet'),7350)
  self.assertEqual(derive_subdivision_step_sample(bpm=120,bar=1,step_index=1,subdivision='8th',swing_ratio='2/3'),14700)
  self.assertEqual(derive_subdivision_step_sample(bpm=120,bar=2,step_index=0,subdivision='16th'),88200)
 def test_triplet_monotonic_and_invalid_bpm(self):
  samples=[derive_subdivision_step_sample(bpm=111,bar=3,step_index=i,subdivision='16th_triplet') for i in range(24)]
  self.assertEqual(len(set(samples)),24);self.assertEqual(samples,sorted(samples))
  for invalid in (float('nan'),float('inf'),0,-100):
   with self.assertRaises(ValueError):derive_subdivision_step_sample(bpm=invalid,bar=1,step_index=0,subdivision='8th')
 def test_velocity_tiers_and_duplicate_identity(self):
  rows=build_subdivision_pattern_events(bpm=120,bar=1,subdivision='16th',steps=[{'event_id':'a','step_index':0,'velocity_tier':'ghost','midi_note':36,'instrument_role':'kick'},{'event_id':'b','step_index':4,'velocity_tier':'accent','midi_note':38,'instrument_role':'snare'}])
  self.assertEqual([e.midi_velocity for e in rows],[45,127]);self.assertEqual([e.sample_position for e in rows],[0,22050])
  with self.assertRaises(ValueError):build_subdivision_pattern_events(bpm=120,bar=1,subdivision='16th',steps=[{'event_id':'a','step_index':0,'midi_note':36,'instrument_role':'kick'},{'event_id':'a','step_index':4,'midi_note':38,'instrument_role':'snare'}])
 def test_camelot_and_half_time(self):
  eq=analyze_harmonic_and_tempo_compatibility(source_key='A minor',target_key='A minor',source_bpm=100,target_bpm=100);self.assertEqual(eq.harmonic_relation,'EXACT_MATCH')
  rel=analyze_harmonic_and_tempo_compatibility(source_key='A minor',target_key='C major',source_bpm=100,target_bpm=50)
  self.assertEqual(rel.harmonic_relation,'RELATIVE_MAJOR_MINOR');self.assertEqual(rel.effective_target_bpm,100);self.assertTrue(rel.bpm_compatible)
  fifth=analyze_harmonic_and_tempo_compatibility(source_key='A minor',target_key='E minor',source_bpm=100,target_bpm=100);self.assertEqual(fifth.harmonic_relation,'ADJACENT_FIFTH')
  clash=analyze_harmonic_and_tempo_compatibility(source_key='A minor',target_key='C minor',source_bpm=100,target_bpm=200);self.assertLess(clash.harmonic_score,fifth.harmonic_score)
 def test_stereo_crossfade_determinism(self):
  def wav_for(v):
   f=io.BytesIO()
   with wave.open(f,'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100);w.writeframes(struct.pack('<hh',v,v)*100)
   return f.getvalue()
  a=wav_for(10000);b=wav_for(-10000);out=crossfade_pcm16_wavs(a,b,fade_samples=50)
  with wave.open(io.BytesIO(out),'rb') as w:self.assertEqual((w.getnframes(),w.getnchannels()),(150,2))
  self.assertEqual(out,crossfade_pcm16_wavs(a,b,fade_samples=50))
  with self.assertRaises(ValueError):crossfade_pcm16_wavs(a,b,fade_samples=101)
 def test_four_operator_fm_deterministic_decodable(self):
  args={'notes':[{'midi_note':36,'start_tick':0,'duration_ticks':480,'velocity':110}],'bpm':120,'total_bars':1}
  a=render_fm_preview_wav(**args);self.assertEqual(a,render_fm_preview_wav(**args))
  with wave.open(io.BytesIO(a),'rb') as w:
   self.assertEqual((w.getframerate(),w.getnchannels(),w.getsampwidth()),(44100,2,2))
   pcm=struct.unpack('<'+str(w.getnframes()*2)+'h',w.readframes(w.getnframes()))
   self.assertGreater(max(abs(x) for x in pcm),200)
 def test_transcription_not_false_p0(self):
  source=render_fm_preview_wav(notes=[{'midi_note':36,'start_tick':0,'duration_ticks':600,'velocity':120}],bpm=120,total_bars=1)
  r=transcribe_wav_to_scorecore_notes(wav_bytes=source,bpm=120)
  self.assertEqual(r.promoted_preservation_tier,'P3_RECONSTRUCTION')
  self.assertFalse(r.loss_report['independent_audio_p0_preservation'])
  self.assertEqual(r.source_artifact_sha256,hashlib.sha256(source).hexdigest())
  self.assertIn(36,{n.midi_note for n in r.notes});self.assertEqual(r.ppq,960)
 def test_transcribe_wrong_rate_rejected(self):
  f=io.BytesIO()
  with wave.open(f,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(22050);w.writeframes(b'\0\0'*3000)
  with self.assertRaises(ValueError):transcribe_wav_to_scorecore_notes(wav_bytes=f.getvalue(),bpm=110)
 def test_musicxml_valid_and_title_escaped(self):
  audio=render_fm_preview_wav(notes=[{'midi_note':40,'start_tick':480,'duration_ticks':480}],bpm=120,total_bars=1)
  r=transcribe_wav_to_scorecore_notes(wav_bytes=audio,bpm=120)
  xml=export_scorecore_notes_to_musicxml(r.notes,title='C & <Studio>')
  self.assertEqual(ET.fromstring(xml).tag,'score-partwise');self.assertIn('C &amp; &lt;Studio&gt;',xml)
 def test_smf_0_1_headers(self):
  audio=render_fm_preview_wav(notes=[{'midi_note':43,'start_tick':0,'duration_ticks':480}],bpm=120,total_bars=1)
  r=transcribe_wav_to_scorecore_notes(wav_bytes=audio,bpm=120)
  for fmt in (0,1):
   data=export_scorecore_notes_to_smf(r.notes,bpm=120,smf_type=fmt)
   self.assertEqual(data[:4],b'MThd');self.assertEqual(int.from_bytes(data[8:10],'big'),fmt)
   self.assertEqual(int.from_bytes(data[12:14],'big'),960);self.assertIn(b'MTrk',data)
 def test_invalid_synth_input(self):
  for pitch in (-1,128):
   with self.assertRaises(ValueError):render_fm_preview_wav(notes=[{'midi_note':pitch,'start_tick':0,'duration_ticks':100}],bpm=100,total_bars=1)
  with self.assertRaises(ValueError):render_fm_preview_wav(notes=[],bpm=float('nan'))

if __name__=='__main__':unittest.main()

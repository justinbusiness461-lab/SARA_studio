"""Studio R33: fail-closed one-occurrence real-source PCM crop; never an onset issuer."""
import hashlib, os, sys, tempfile, unittest, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from m045_denial_observation_window import WindowHeld, extract_denial_observation_window

class DenialWindowEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='studio-r33-')
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        self.mp3=self.dir/'source.mp3';self.mp3.write_bytes(b'UNQUALIFIED TEST SOURCE')
        self.pcm=self.dir/'decode.pcm'
        # Test-only synthetic media, not any authenticated music.
        n=96*48000
        self.pcm.write_bytes((b'\x00\x01\x02\x03')*n)
        self.out=self.dir/'window.wav'
        self.msha=hashlib.sha256(self.mp3.read_bytes()).hexdigest()
        self.psha=hashlib.sha256(self.pcm.read_bytes()).hexdigest()
        self.a=60*48000;self.b=94*48000
    def run_extract(self,**changes):
        kw=dict(source_mp3=self.mp3,full_decoded_pcm=self.pcm,output_wav=self.out,
                expected_source_mp3_sha256=self.msha,expected_decoded_pcm_sha256=self.psha,
                source_start_sample=self.a,source_end_sample_exclusive=self.b)
        kw.update(changes)
        return extract_denial_observation_window(**kw)
    def test_exact_full_decode_slice_verified_against_readback(self):
        record=self.run_extract()
        self.assertEqual(record['window']['sourceStartSample'],self.a)
        self.assertEqual(record['window']['sourceEndSampleExclusive'],self.b)
        self.assertEqual(record['window']['framesPerChannel'],self.b-self.a)
        with self.pcm.open('rb') as source:
            source.seek(self.a*4)
            expected=source.read((self.b-self.a)*4)
        with wave.open(str(self.out),'rb') as wav:
            self.assertEqual((wav.getframerate(),wav.getnchannels(),wav.getsampwidth()),(48000,2,2))
            self.assertEqual(wav.readframes(wav.getnframes()),expected)
        self.assertEqual(record['window']['pcmSha256'],hashlib.sha256(expected).hexdigest())
    def test_never_claim_onset_even_with_pre_roll(self):
        r=self.run_extract()
        self.assertEqual(r['verification'],'UNVERIFIED')
        self.assertEqual(r['onsetSample'],None)
        self.assertFalse(r['studioIssued'])
        self.assertFalse(r['fullyObserved'])
        self.assertEqual(r['boundaryStatus'],'UNVERIFIED')
    def test_original_68_second_boundary_rejected(self):
        with self.assertRaisesRegex(WindowHeld,'POSSIBLE_HEAD_TRUNCATION'):
            self.run_extract(source_start_sample=68*48000)
        self.assertFalse(self.out.exists())
    def test_window_start_after_68_rejected_even_with_later_marker(self):
        with self.assertRaisesRegex(WindowHeld,'POSSIBLE_HEAD_TRUNCATION'):
            self.run_extract(source_start_sample=69*48000)
    def test_forged_mp3_identity_is_rejected(self):
        with self.assertRaisesRegex(WindowHeld,'SOURCE_MP3_DIGEST_MISMATCH'):
            self.run_extract(expected_source_mp3_sha256='0'*64)
    def test_forged_full_decoded_identity_is_rejected(self):
        with self.assertRaisesRegex(WindowHeld,'FULL_PCM_DIGEST_MISMATCH'):
            self.run_extract(expected_decoded_pcm_sha256='a'*64)
    def test_missing_source_artifact_is_rejected(self):
        with self.assertRaisesRegex(WindowHeld,'SOURCE_MISSING'):
            self.run_extract(source_mp3=self.dir/'not-found.mp3')
    def test_invalid_window_position_and_booleans_rejected(self):
        for a,b in [(-1,self.b),(True,self.b),(self.b,self.a),(0,False),(0,99*48000)]:
            with self.subTest(a=a,b=b),self.assertRaises(WindowHeld):
                self.run_extract(source_start_sample=a,source_end_sample_exclusive=b)
    def test_wrong_sample_rate_is_not_silently_resampled(self):
        with self.assertRaisesRegex(WindowHeld,'CLOCK_MISMATCH'):
            self.run_extract(sample_rate=44100)
    def test_existing_output_is_preserved_exactly(self):
        self.out.write_bytes(b'DO NOT OVERWRITE')
        with self.assertRaisesRegex(WindowHeld,'OUTPUT_ALREADY_EXISTS'):
            self.run_extract()
        self.assertEqual(self.out.read_bytes(),b'DO NOT OVERWRITE')
    def test_no_caller_supplied_verified_status_or_onset_field(self):
        with self.assertRaises(TypeError):
            self.run_extract(onset_sample=60*48000+10)
        with self.assertRaises(TypeError):
            self.run_extract(verification='AUTHENTICATED')
    def test_bounded_context_only_one_word_no_inventory_expansion(self):
        x=self.run_extract()
        self.assertEqual(x['occurrenceId'],'DENIAL_01')
        self.assertEqual(x['lyricTokenRef'],'denial-chorus-w001')
        self.assertEqual(x['scope'],'SINGLE_OCCURRENCE_OBSERVATION_ONLY')
        self.assertEqual(x['coordinateSystem'],'LOCAL_FFMPEG_DECODED_PCM_START_UNBOUND')
if __name__=='__main__':unittest.main()

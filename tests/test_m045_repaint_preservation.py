import io,sys,pathlib,unittest,wave,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from m045_repaint import bar_sample_window,read_pcm16_wav,splice_exact_region

def wav(frames,block):
    b=io.BytesIO()
    with wave.open(b,"wb") as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(44100)
        f.writeframes(block*frames)
    return b.getvalue()

class RepaintPreservationTests(unittest.TestCase):
    def test_rational_bar_boundaries_and_exact_non_target_bytes(self):
        spec={"timebase":{"sample_rate":44100,"initial_bpm":96,"meter":"4/4","ticks_per_quarter_note":960},
              "tracks":[]}
        base=wav(44100*10,b"\x01\x00\x02\x00")
        candidate=wav(44100*10,b"\x09\x00\x08\x00")
        a,b=bar_sample_window(spec,2,3,441000)
        self.assertEqual((a,b),(110250,220500))
        merged,proof=splice_exact_region(base,candidate,a,b)
        bpcm,_=read_pcm16_wav(base)
        mpcm,_=read_pcm16_wav(merged)
        self.assertEqual(mpcm[:a*4],bpcm[:a*4])
        self.assertEqual(mpcm[b*4:],bpcm[b*4:])
        self.assertNotEqual(mpcm[a*4:b*4],bpcm[a*4:b*4])
        self.assertEqual(proof["preservation_tier"],"P1")
    def test_invalid_length_and_tempo_fail_closed(self):
        spec={"timebase":{"sample_rate":44100,"initial_bpm":96,"meter":"4/4","ticks_per_quarter_note":960},"tracks":[]}
        with self.assertRaisesRegex(ValueError,"LENGTH"):
            splice_exact_region(wav(441000,b"\x01\x00\x02\x00"),
                wav(44100,b"\x09\x00\x08\x00"),110250,220500)
        with self.assertRaisesRegex(ValueError,"TEMPO"):
            bar_sample_window({**spec,"timebase":{**spec["timebase"],"initial_bpm":0}},2,3,441000)
        with self.assertRaisesRegex(ValueError,"METER"):
            bar_sample_window({**spec,"timebase":{**spec["timebase"],"meter":"6/8"}},2,3,441000)

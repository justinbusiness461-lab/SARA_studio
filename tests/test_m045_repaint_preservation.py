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

class RepaintCrossfadeTests(unittest.TestCase):
    def test_five_ms_cosine_removes_dc_boundary_step_without_touching_outside(self):
        import struct
        start, end = 500, 1500
        base = wav(2000, struct.pack('<hh', 0, 0))
        candidate = wav(2000, struct.pack('<hh', 16000, 16000))
        output, proof = splice_exact_region(base, candidate, start, end)
        original, _ = read_pcm16_wav(base)
        result, _ = read_pcm16_wav(output)
        self.assertEqual(proof['fade_samples'], 220)
        self.assertEqual(result[:start*4], original[:start*4])
        self.assertEqual(result[end*4:], original[end*4:])
        channel = [struct.unpack_from('<h',result,i*4)[0] for i in range(2000)]
        self.assertLess(max(abs(channel[i]-channel[i-1]) for i in range(start-1,start+221)),120)
        self.assertLess(max(abs(channel[i]-channel[i-1]) for i in range(end-221,end+1)),120)
        self.assertEqual(channel[start+221], 16000)
        self.assertEqual(channel[end-221], 16000)

    def test_short_window_clamps_fades_without_overlapping_or_bleed(self):
        import struct
        base = wav(100,struct.pack('<hh',-1000,-1000))
        candidate = wav(100,struct.pack('<hh',1000,1000))
        for width in (1,2,3,4,5,8,9,16):
            start = 40
            end = start+width
            output, proof=splice_exact_region(base,candidate,start,end)
            a,_=read_pcm16_wav(base)
            b,_=read_pcm16_wav(output)
            self.assertEqual(proof['fade_samples'],width//4)
            self.assertEqual(b[:start*4],a[:start*4])
            self.assertEqual(b[end*4:],a[end*4:])
            self.assertEqual(len(b),len(a))

    def test_signed_pcm16_extremes_do_not_overflow(self):
        import struct
        base=wav(1000,struct.pack('<hh',-32768,32767))
        candidate=wav(1000,struct.pack('<hh',32767,-32768))
        out,proof=splice_exact_region(base,candidate,300,700)
        pcm,_=read_pcm16_wav(out)
        self.assertEqual(len(pcm),4000)
        self.assertEqual(proof['fade_samples'],100)

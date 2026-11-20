"""Independent Wave004 metering/shape adversarial: never silently extend 44.1 kHz authority."""
import io,math,struct,unittest,wave
from m045_wave4_mastering_provenance import master_wav_to_lufs_target

def intersample_audio(rate=44100,amplitude=.10):
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(b''.join(struct.pack('<hh',*([round(amplitude*32767*math.sin(math.pi*i/2+math.pi/4))]*2)) for i in range(rate*2)))
    return buffer.getvalue()

class Wave4Parity(unittest.TestCase):
    def test_quarter_rate_intersample_peak_output_is_bounded_and_physically_decoded(self):
        source=intersample_audio()
        output,metrics=master_wav_to_lufs_target(wav_bytes=source,target_lufs=-14,true_peak_ceiling_dbtp=-1)
        self.assertLessEqual(metrics['measured_output_true_peak_dbtp'],-.9)
        self.assertEqual(metrics['meterConformance'],'NOT_INDEPENDENTLY_CERTIFIED')
        with wave.open(io.BytesIO(output),'rb') as decoded:
            self.assertEqual(decoded.getframerate(),44100)
            self.assertEqual(decoded.getnframes(),88200)
    def test_48k_is_explicitly_unsupported_not_silently_certified(self):
        with self.assertRaisesRegex(ValueError,'44100'):
            master_wav_to_lufs_target(wav_bytes=intersample_audio(48000),target_lufs=-14,true_peak_ceiling_dbtp=-1)

if __name__=='__main__':unittest.main()
"""Independent qualification oracle; no issuer implementation or runtime claim."""
import unittest
from fractions import Fraction

def sample_at_frame(frame, rate, fps_num, fps_den=1):
    for value in (frame, rate, fps_num, fps_den):
        if type(value) is not int: raise ValueError('integer required; bool rejected')
    if frame < 0 or min(rate, fps_num, fps_den) <= 0: raise ValueError('invalid clock')
    return (frame * rate * fps_den) // fps_num

def window(frame_start, frame_end, rate, fps_num, fps_den, grant_start, grant_end):
    if frame_end <= frame_start: raise ValueError('empty/reversed frame window')
    a = sample_at_frame(frame_start, rate, fps_num, fps_den)
    b = sample_at_frame(frame_end, rate, fps_num, fps_den)
    if not grant_start <= a < b <= grant_end: raise ValueError('outside grant')
    return a, b

class ClockOracleTests(unittest.TestCase):
    def test_24fps_15_seconds(self):
        self.assertEqual(window(0,360,48000,24,1,0,720000),(0,720000))
    def test_fractional_fps_exact(self):
        self.assertEqual(sample_at_frame(450,48000,30000,1001),720720)
        self.assertEqual(Fraction(450*1001,30000),Fraction(15015,1000))
    def test_fractional_adjacent_windows_no_gap(self):
        for f in range(1000):
            a,b = window(f,f+1,48000,30000,1001,0,2000000)
            self.assertEqual(a, int(Fraction(f,1) / Fraction(30000,1001) * 48000))
            self.assertEqual(b, int(Fraction(f+1,1) / Fraction(30000,1001) * 48000))
            self.assertIn(b-a,(1601,1602))
    def test_wrong_15second_assumption_rejected(self):
        with self.assertRaises(ValueError): window(0,450,48000,30000,1001,0,720000)
    def test_nonzero_global_offset(self):
        self.assertEqual(window(240,600,48000,24,1,480000,1200000),(480000,1200000))
    def test_one_sample_short_denied(self):
        with self.assertRaises(ValueError): window(240,600,48000,24,1,480000,1199999)
    def test_boolean_and_float_frames_denied(self):
        for f in (True,False,1.0,'1'):
            with self.assertRaises(ValueError): sample_at_frame(f,48000,24)
    def test_invalid_and_reversed_denied(self):
        for args in ((-1,48000,24,1),(1,0,24,1),(1,48000,0,1),(1,48000,24,0)):
            with self.assertRaises(ValueError): sample_at_frame(*args)
        with self.assertRaises(ValueError): window(10,9,48000,24,1,0,100000)

if __name__ == '__main__': unittest.main(verbosity=2)

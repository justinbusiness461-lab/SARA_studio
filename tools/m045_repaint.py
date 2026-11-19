"""Bounded deterministic repaint planning and PCM16 splice. No provider ownership."""
from __future__ import annotations
from fractions import Fraction
import hashlib
import io
import wave

RATE=44100
CHANNELS=2
FRAME_BYTES=4

def bar_sample_window(song_spec, start_bar, end_bar, frame_count):
    if type(start_bar) is not int or type(end_bar) is not int or start_bar < 1 or end_bar <= start_bar:
        raise ValueError("INVALID_BAR_RANGE")
    if not isinstance(song_spec,dict):
        raise ValueError("SONGSPEC_REQUIRED")
    tb=song_spec.get("timebase") or {}
    if not isinstance(tb,dict) or tb.get("sample_rate") != RATE:
        raise ValueError("CANONICAL_SAMPLE_RATE_REQUIRED")
    if tb.get("meter") != "4/4":
        raise ValueError("REPAINT_METER_UNQUALIFIED")
    bpm=tb.get("initial_bpm")
    if type(bpm) not in (int,float,str):
        raise ValueError("REPAINT_TEMPO_UNQUALIFIED")
    tempo=Fraction(str(bpm))
    if not 30 <= tempo <= 300:
        raise ValueError("REPAINT_TEMPO_UNQUALIFIED")
    if any(e.get("type") in ("TEMPO","TEMPO_CHANGE","METER_CHANGE") for track in song_spec.get("tracks",[]) for e in track.get("events",[])):
        raise ValueError("REPAINT_VARIABLE_TEMPO_UNQUALIFIED")
    ticks=tb.get("ticks_per_quarter_note")
    if type(ticks) is not int or ticks <= 0:
        raise ValueError("REPAINT_TICK_GRID_UNQUALIFIED")
    span=Fraction(RATE*240,1)/tempo
    def nearest(x): return (x.numerator*2+x.denominator)//(x.denominator*2)
    start=nearest((start_bar-1)*span)
    end=nearest((end_bar-1)*span)
    if not 0 <= start < end <= frame_count:
        raise ValueError("REPAINT_WINDOW_OUTSIDE_AUDIO")
    return start,end

def read_pcm16_wav(data):
    if not isinstance(data,bytes) or len(data)>40*1024*1024:
        raise ValueError("REPAINT_AUDIO_SIZE_INVALID")
    try:
        with wave.open(io.BytesIO(data),"rb") as h:
            if (h.getnchannels(),h.getsampwidth(),h.getframerate(),h.getcomptype()) != (2,2,RATE,"NONE"):
                raise ValueError("REPAINT_CANONICAL_STEREO_PCM16_REQUIRED")
            n=h.getnframes()
            pcm=h.readframes(n)
            if n <= 0 or len(pcm)!=n*FRAME_BYTES:
                raise ValueError("REPAINT_AUDIO_TRUNCATED")
            return pcm,n
    except (EOFError,wave.Error) as exc:
        raise ValueError("REPAINT_INVALID_WAV") from exc

def splice_exact_region(base_wav,generated_wav,start_sample,end_sample):
    base,frames=read_pcm16_wav(base_wav)
    generated,new_frames=read_pcm16_wav(generated_wav)
    if frames!=new_frames or not 0<=start_sample<end_sample<=frames:
        raise ValueError("REPAINT_LENGTH_OR_WINDOW_CONFLICT")
    left=start_sample*FRAME_BYTES
    right=end_sample*FRAME_BYTES
    result=base[:left]+generated[left:right]+base[right:]
    if result[:left]!=base[:left] or result[right:]!=base[right:]:
        raise AssertionError("P1_OUTSIDE_REGION_CHANGED")
    b=io.BytesIO()
    with wave.open(b,"wb") as out:
        out.setnchannels(2);out.setsampwidth(2);out.setframerate(RATE);out.writeframes(result)
    return b.getvalue(),{
        "preservation_tier":"P1",
        "preservation_method":"EXACT_OUTSIDE_REGION_PCM_SPLICING",
        "outside_prefix_sha256":hashlib.sha256(base[:left]).hexdigest(),
        "outside_suffix_sha256":hashlib.sha256(base[right:]).hexdigest(),
        "start_sample":start_sample,"end_sample":end_sample,
        "source_audio_sha256":hashlib.sha256(base_wav).hexdigest()
    }

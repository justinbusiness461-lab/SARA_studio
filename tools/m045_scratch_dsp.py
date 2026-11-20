"""Deterministic local scratch DSP. CAS and revision authority remain in studio_server."""
from __future__ import annotations
import hashlib
import io
import math
import struct
import wave

RATE = 44100
FRAME = 4
TECHNIQUES = {"baby", "chirp", "2_click_flare", "two_deck_juggle"}


def waveform_pcm(data):
    if not isinstance(data,bytes) or not (44 <= len(data) <= 40*1024*1024):
        raise ValueError("SCRATCH_SOURCE_INVALID")
    try:
        with wave.open(io.BytesIO(data),"rb") as f:
            if (f.getnchannels(),f.getframerate(),f.getsampwidth(),f.getcomptype()) != (2,RATE,2,"NONE"):
                raise ValueError("SCRATCH_PCM16_44100_STEREO_REQUIRED")
            count=f.getnframes()
            pcm=f.readframes(count)
            if count<=0 or len(pcm)!=FRAME*count:
                raise ValueError("SCRATCH_AUDIO_TRUNCATED")
            return pcm,count
    except (wave.Error,EOFError) as exc:
        raise ValueError("SCRATCH_AUDIO_INVALID") from exc


def _velocity(technique, fraction):
    # Positive = forward; negative = reverse. All transport is bounded.
    if technique=="baby":
        return 1.2 if fraction<0.5 else -1.2
    if technique=="chirp":
        return 1.7 if fraction<0.5 else -1.35
    if technique=="2_click_flare":
        return 1.0 if fraction<0.5 else -1.0
    return 2.0 if fraction<0.25 or 0.5<=fraction<0.75 else -2.0


def _crossfader(technique,fraction):
    if technique=="chirp":
        return 1.0 if fraction<0.44 or fraction>0.56 else 0.0
    if technique=="2_click_flare":
        return 1.0 if int(fraction*8)%2==0 else 0.0
    if technique=="two_deck_juggle":
        return 1.0 if int(fraction*4)%2==0 else 0.0
    return 1.0


def _quantize(value):
    if not math.isfinite(value):
        raise ValueError("NONFINITE_DSP_SAMPLE")
    return min(32767,max(-32768,int(round(value))))


def render_scratch_mix(base_wav, performances, *, window_frames):
    """Return PCM16 WAV + scope proof; does NOT authorize or publish CAS.

    performances contain an exact marker and its previously authorized raw WAV.
    All source reads/ownership checks must be completed by the Studio caller.
    """
    base,frames=waveform_pcm(base_wav)
    if (type(window_frames) is not int or window_frames<=0 or
        window_frames>44100*8 or not isinstance(performances,list) or
        not 0<len(performances)<=128):
        raise ValueError("SCRATCH_WINDOW_INVALID")
    mix=[float(s) for s in struct.unpack("<"+"h"*(frames*2),base)]
    touched=set()
    deck_set=set()
    techniques=[]
    fade=min(88,window_frames//4)
    for performance in performances:
        if not isinstance(performance,dict):
            raise ValueError("SCRATCH_PERFORMANCE_INVALID")
        marker=performance.get("marker")
        source=performance.get("sample_asset_wav")
        sha=performance.get("source_asset_digest")
        if not isinstance(source,bytes) or not isinstance(sha,str) or hashlib.sha256(source).hexdigest()!=sha:
            raise ValueError("SCRATCH_SAMPLE_ASSET_DIGEST_INVALID")
        source_pcm,source_frames=waveform_pcm(source)
        if (not isinstance(marker,dict) or marker.get("type")!="DJ_SCRATCH_MARKER"
                or marker.get("audio_status")!="UNRENDERED_SOURCE_ASSET_REQUIRED"
                or marker.get("deck") not in ("A","B") or marker.get("technique") not in TECHNIQUES):
            raise ValueError("SCRATCH_MARKER_INVALID")
        start=marker.get("sample_index")
        if type(start) is not int or start<0 or start+window_frames>frames:
            raise ValueError("SCRATCH_EVENT_OUTSIDE_BASE_AUDIO")
        # Decode source exactly once and use float64 Python arithmetic.
        samples=struct.unpack("<"+"h"*(source_frames*2),source_pcm)
        position=0.0
        for j in range(window_frames):
            fraction=j/window_frames
            if j:
                position += _velocity(marker["technique"],(j-1)/window_frames)
            # Wrap for playable forward/reverse simulated platter traversal.
            p=position%source_frames
            left=int(math.floor(p))
            right=(left+1)%source_frames
            alpha=p-left
            envelope=1.0
            if fade:
                if j<fade:
                    envelope*=0.5*(1-math.cos(math.pi*(j+1)/(fade+1)))
                if j>=window_frames-fade:
                    k=window_frames-1-j
                    envelope*=0.5*(1-math.cos(math.pi*(k+1)/(fade+1)))
            g=envelope*_crossfader(marker["technique"],fraction)
            for channel in (0,1):
                sample=(1-alpha)*samples[left*2+channel]+alpha*samples[right*2+channel]
                mix[(start+j)*2+channel]+=g*sample
            touched.add(start+j)
        deck_set.add(marker["deck"])
        techniques.append(marker["technique"])
    data=bytearray(base)
    for i in touched:
        struct.pack_into("<hh",data,i*FRAME,_quantize(mix[i*2]),_quantize(mix[i*2+1]))
    ranges=[]
    for i in sorted(touched):
        if ranges and ranges[-1][1]==i:
            ranges[-1][1]+=1
        else:
            ranges.append([i,i+1])
    # Exact output invariance outside edit union.
    if any(data[i*FRAME:(i+1)*FRAME]!=base[i*FRAME:(i+1)*FRAME]
           for i in range(frames) if i not in touched):
        raise AssertionError("SCRATCH_OUTSIDE_REGION_CHANGED")
    out=io.BytesIO()
    with wave.open(out,"wb") as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(bytes(data))
    return out.getvalue(),{"schema_version":"sara.scratch.dsp.v1",
        "sample_rate":RATE,"channels":2,"fade_samples":fade,
        "sample_windows":ranges,"decks":sorted(deck_set),
        "techniques":techniques,
        "source_audio_sha256":hashlib.sha256(base_wav).hexdigest(),
        "output_pcm_sha256":hashlib.sha256(data).hexdigest()}

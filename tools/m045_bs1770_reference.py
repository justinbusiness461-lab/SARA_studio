"""CPU reference implementation of BS.1770-4 *algorithm*, not meter certification.

Two separate K-weighting biquads (shelf + RLB), 400 ms windows/100 ms hops,
-70 LUFS absolute, -10 LU relative gate, and explicit 4x FFmpeg polyphase
resampling for intersample peak estimation. 44.1/48 kHz stereo PCM16 only.
Production host must still run independently accredited reference vectors
before calling this meter BS.1770-4 *certified*.
"""
from __future__ import annotations
from collections import deque
import hashlib
import io
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import wave

# Exact Table 1+2 ITU-R BS.1770-4 48 kHz coefficients.
_SHELF_48=((1.53512485958697,-2.69169618940638,1.19839281085285),
           (1.0,-1.69065929318241,0.73248077421585))
_RLB_48=((1.,-2.,1.),(1.,-1.99004745483398,0.99007225036621))
_RATE_SET={44100,48000}


def k_weighting_biquads(rate):
    if type(rate) is not int or rate not in _RATE_SET:
        raise ValueError('BS1770_SAMPLE_RATE_NOT_QUALIFIED')
    if rate==48000:return (_SHELF_48,_RLB_48)
    # Bilinear-transform design of the standardized analog prototypes at
    # 44.1 kHz; 48 kHz remains exact coefficients in the ITU tables.
    frequency=1681.974450955533; q=.7071752369554196
    gain_db=3.999843853973347
    k=math.tan(math.pi*frequency/rate)
    vh=10**(gain_db/20.0)
    vb=vh**0.4996667741545416
    a0=1+k/q+k*k
    shelf=(( (vh+vb*k/q+k*k)/a0,2*(k*k-vh)/a0,
             (vh-vb*k/q+k*k)/a0 ),
           (1.,2*(k*k-1)/a0,(1-k/q+k*k)/a0))
    frequency=38.13547087602444;q=.5003270373238773
    k=math.tan(math.pi*frequency/rate)
    a0=1+k/q+k*k
    rlb=((1/a0,-2/a0,1/a0),
         (1.,2*(k*k-1)/a0,(1-k/q+k*k)/a0))
    return shelf,rlb


def _four_times_true_peak(wav_bytes,rate):
    """External FFmpeg 4x polyphase upsampler; stream float32 to bound RSS.

    Explicitly report this filter's implementation; being 4x does NOT
    independently certify its response meets the Annex 2 tolerance mask.
    """
    with tempfile.TemporaryDirectory(prefix='sara-r9-truepeak-') as td:
        source=Path(td)/'source.wav'
        source.write_bytes(wav_bytes)
        args=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-threads','1',
              '-i',str(source),'-af',f'aresample={rate*4}:filter_size=64:phase_shift=10:cutoff=0.97',
              '-ar',str(rate*4),'-ac','2','-f','f32le','-acodec','pcm_f32le','pipe:1']
        try:
            worker=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        except OSError as e:
            raise ValueError('BS1770_4X_RESAMPLER_UNAVAILABLE') from e
        peak=0.0;count=0;deadline=time.monotonic()+90
        try:
            while True:
                if time.monotonic()>deadline:
                    raise ValueError('BS1770_4X_RESAMPLER_TIMEOUT')
                buf=worker.stdout.read(65536)
                if not buf:break
                if len(buf)%4:raise ValueError('BS1770_4X_STREAM_MISALIGNED')
                for (value,) in struct.iter_unpack('<f',buf):
                    if not math.isfinite(value):raise ValueError('BS1770_4X_OUTPUT_NONFINITE')
                    peak=max(peak,abs(value));count+=1
            error=worker.stderr.read(2048)
            if worker.wait(timeout=5)!=0 or count<rate:
                raise ValueError('BS1770_4X_RESAMPLER_FAILED')
        finally:
            if worker.poll() is None:
                worker.kill();worker.communicate(timeout=5)
            if worker.stdout:worker.stdout.close()
            if worker.stderr:worker.stderr.close()
        return peak,count


def measure_reference_pcm16(wav_bytes):
    if not isinstance(wav_bytes,bytes) or not 44<=len(wav_bytes)<=40*1024*1024:
        raise ValueError('BS1770_WAV_SIZE_UNQUALIFIED')
    try:
        audio=wave.open(io.BytesIO(wav_bytes),'rb')
        rate=audio.getframerate()
        if (rate not in _RATE_SET or audio.getnchannels()!=2 or
            audio.getsampwidth()!=2 or audio.getcomptype()!='NONE' or
            audio.getnframes()<rate*0.4 or audio.getnframes()>rate*210):
            raise ValueError('BS1770_STEREO_PCM16_FORMAT_UNQUALIFIED')
    except (wave.Error,EOFError) as e:
        raise ValueError('BS1770_WAV_UNDECODABLE') from e
    shelf,rlb=k_weighting_biquads(rate)
    # Transposed Direct Form II; one state per stereo channel per stage.
    states=[[[0.,0.] for _ in range(2)] for _ in range(2)]
    hop=rate//10
    energy=deque(maxlen=4)
    blocks=[]
    sample_peak=0.0
    frames=audio.getnframes()
    remaining=frames
    try:
        while remaining>=hop:
            raw=audio.readframes(hop)
            if len(raw)!=hop*4:
                raise ValueError('BS1770_WAV_FRAME_SHORT_READ')
            moment_energy=0.
            # State continuity is across every 100-ms hop and all gated blocks.
            for pair in struct.iter_unpack('<hh',raw):
                for channel,sample in enumerate(pair):
                    x=sample/32768.
                    sample_peak=max(sample_peak,abs(x))
                    for stage,coeff in enumerate((shelf,rlb)):
                        b,a=coeff
                        z=states[stage][channel]
                        y=b[0]*x+z[0]
                        z[0]=b[1]*x-a[1]*y+z[1]
                        z[1]=b[2]*x-a[2]*y
                        x=y
                    moment_energy+=x*x
            energy.append(moment_energy/hop)
            if len(energy)==4:
                blocks.append(sum(energy)/4)
            remaining-=hop
        if remaining:
            raw=audio.readframes(remaining)
            if len(raw)!=remaining*4:raise ValueError('BS1770_WAV_TAIL_SHORT_READ')
            for (l,r) in struct.iter_unpack('<hh',raw):
                sample_peak=max(sample_peak,abs(l)/32768.,abs(r)/32768.)
    finally:
        audio.close()
    if not blocks:raise ValueError('BS1770_GATED_BLOCKS_MISSING')
    gate_abs=10**((-70+0.691)/10)
    active=[z for z in blocks if z>gate_abs]
    if not active:raise ValueError('BS1770_SILENCE_ABSOLUTE_GATED')
    pre=sum(active)/len(active)
    relative_lufs=-0.691+10*math.log10(pre)-10
    gate_rel=10**((relative_lufs+0.691)/10)
    retained=[z for z in active if z>gate_rel]
    if not retained:raise ValueError('BS1770_RELATIVE_GATED_ALL_BLOCKS')
    integrated=-0.691+10*math.log10(sum(retained)/len(retained))
    if not math.isfinite(integrated):raise ValueError('BS1770_NONFINITE_LOUDNESS')
    true_peak,output_count=_four_times_true_peak(wav_bytes,rate)
    if true_peak<=0:raise ValueError('BS1770_SIGNAL_NOT_MEASURABLE')
    return {'integrated_lufs':round(integrated,4),
            'true_peak_dbtp':round(20*math.log10(true_peak),4),
            'sample_peak_dbfs':round(20*math.log10(sample_peak),4),
            'absolute_gate_lufs':-70,'relative_gate_lu':-10,
            'gating_block_ms':400,'hop_ms':100,
            'blocks_total':len(blocks),'blocks_retained':len(retained),
            'blocks_rejected':len(blocks)-len(retained),
            'oversample_factor':4,'oversample_frame_values':output_count,
            'sample_rate':rate,'samples_per_channel':frames,
            'input_wav_sha256':hashlib.sha256(wav_bytes).hexdigest(),
            'meterConformance':'REFERENCE_VECTOR_TESTED_NOT_INDEPENDENTLY_CERTIFIED',
            'peakImplementation':'ffmpeg-polyphase-resampler-4x-64-tap-filter-size'}

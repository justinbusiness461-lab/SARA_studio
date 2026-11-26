"""Studio R33: sample-exact *unverified* DENIAL_01 observation-window extraction.

This is an observation evidence utility, NEVER a Studio ProjectRevision issuer,
a PCM acceptance authority, an onset detector, or a commercial rights grant.
Its output has no onset sample and cannot be promoted to the cinema adapter.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import wave
from pathlib import Path


class WindowHeld(ValueError):
    """Failure to establish exact candidate-source geometry and byte identity."""


def _hash(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def extract_denial_observation_window(*, source_mp3, full_decoded_pcm,
    output_wav, expected_source_mp3_sha256, expected_decoded_pcm_sha256,
    source_start_sample, source_end_sample_exclusive, sample_rate=48000,
    channels=2):
    """Extract exact decoded PCM samples for *review*, and nothing stronger.

    Input must be full FFmpeg-decoded s16le at 48 kHz stereo; its first sample
    is NOT assumed to be Studio's accepted artifact sample 0. 68 s R6-window
    heads are rejected, and *even a wider candidate* stays UNVERIFIED until
    separate authenticated pre-onset and onset-transition witnesses exist.
    """
    if type(sample_rate) is not int or type(channels) is not int or sample_rate != 48000 or channels != 2:
        raise WindowHeld('R33_CLOCK_MISMATCH')
    a, b = source_start_sample, source_end_sample_exclusive
    if type(a) is not int or type(b) is not int or a < 0 or a >= b:
        raise WindowHeld('R33_INVALID_SAMPLE_WINDOW')
    if a >= 68 * sample_rate:
        raise WindowHeld('R33_POSSIBLE_HEAD_TRUNCATION')
    for claimed in (expected_source_mp3_sha256, expected_decoded_pcm_sha256):
        if not isinstance(claimed, str) or not re.fullmatch(r'[a-f0-9]{64}', claimed):
            raise WindowHeld('R33_EXPECTED_DIGEST_INVALID')
    mp3, pcm, target = Path(source_mp3), Path(full_decoded_pcm), Path(output_wav)
    if not mp3.is_file() or not pcm.is_file() or mp3.is_symlink() or pcm.is_symlink():
        raise WindowHeld('R33_SOURCE_MISSING')
    if target.exists() or target.is_symlink():
        raise WindowHeld('R33_OUTPUT_ALREADY_EXISTS')
    if _hash(mp3) != expected_source_mp3_sha256:
        raise WindowHeld('R33_SOURCE_MP3_DIGEST_MISMATCH')
    if _hash(pcm) != expected_decoded_pcm_sha256:
        raise WindowHeld('R33_FULL_PCM_DIGEST_MISMATCH')
    bytes_per_frame = channels * 2
    full_len = pcm.stat().st_size
    if full_len % bytes_per_frame or b > full_len // bytes_per_frame:
        raise WindowHeld('R33_INVALID_SAMPLE_WINDOW')
    target.parent.mkdir(parents=True, exist_ok=True)
    with pcm.open('rb') as f:
        f.seek(a * bytes_per_frame)
        segment = f.read((b-a) * bytes_per_frame)
    if len(segment) != (b-a)*bytes_per_frame:
        raise WindowHeld('R33_INCOMPLETE_EXCERPT')
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.denial01-', suffix='.wav',
                dir=target.parent, delete=False) as temp:
            temp_name = temp.name
            with wave.open(temp, 'wb') as writer:
                writer.setframerate(sample_rate)
                writer.setnchannels(channels)
                writer.setsampwidth(2)
                writer.writeframes(segment)
            temp.flush()
            os.fsync(temp.fileno())
        with wave.open(temp_name, 'rb') as reader:
            if (reader.getnframes(), reader.getframerate(), reader.getnchannels(),
                    reader.getsampwidth()) != (b-a, sample_rate, channels, 2):
                raise WindowHeld('R33_WAV_HEADER_MISMATCH')
            physical_pcm = reader.readframes(b-a)
        if physical_pcm != segment:
            raise WindowHeld('R33_WINDOW_BYTE_MISMATCH')
        # Atomic no-overwrite publication of a *private audition candidate*.
        os.link(temp_name, target)
        fd = os.open(target.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return {
        'schema': 'sara.studio.denial01.observation-window.candidate.v1',
        'occurrenceId': 'DENIAL_01',
        'lyricTokenRef': 'denial-chorus-w001',
        'scope': 'SINGLE_OCCURRENCE_OBSERVATION_ONLY',
        'sourceMp3Sha256': expected_source_mp3_sha256,
        'sourceDecodedPcmSha256': expected_decoded_pcm_sha256,
        'coordinateSystem': 'LOCAL_FFMPEG_DECODED_PCM_START_UNBOUND',
        'sourceProjectRevisionId': None, 'sourceAudioArtifactId': None,
        'sampleRate': sample_rate, 'channels': channels,
        'window': {
            'sourceStartSample': a, 'sourceEndSampleExclusive': b,
            'framesPerChannel': b-a,
            'pcmSha256': hashlib.sha256(segment).hexdigest(),
            'wavSha256': _hash(target),
        },
        'boundaryStatus': 'UNVERIFIED', 'onsetSample': None,
        'onsetVisibility': 'UNMARKED', 'fullyObserved': False,
        'studioIssued': False, 'verification': 'UNVERIFIED',
        'productionQualified': False, 'creativeApproved': False,
    }

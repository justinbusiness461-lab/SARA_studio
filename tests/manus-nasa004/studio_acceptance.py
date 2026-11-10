#!/usr/bin/env python3
"""Independent QA-only Sound Forge WAV/edit/tenancy evidence inspector.
Does not mutate projects, call vendor APIs, or replace any Studio owner.
Not proof of deployed app behavior without externally captured inputs.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import wave


class ContractFailure(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise ContractFailure(reason)


def verify_wav(blob: bytes):
    _require(len(blob) >= 44, "too short for PCM WAV")
    _require(blob[:4] == b'RIFF' and blob[8:12] == b'WAVE', "RIFF/WAVE signature invalid")
    _require(struct.unpack_from('<I', blob, 4)[0] == len(blob) - 8, "RIFF byte count mismatch")
    pos, seen = 12, {}
    while pos < len(blob):
        _require(pos + 8 <= len(blob), "truncated chunk header")
        name, size = blob[pos:pos+4], struct.unpack_from('<I', blob, pos+4)[0]
        pos += 8
        _require(pos + size <= len(blob), "truncated chunk payload")
        if name in (b'fmt ', b'data'):
            _require(name not in seen, "duplicate required audio chunk")
            seen[name] = blob[pos:pos+size]
        pos += size + (size & 1)
        _require(pos <= len(blob), "invalid chunk padding")
    _require(pos == len(blob), "trailing partial chunk")
    _require(b'fmt ' in seen and b'data' in seen, "missing PCM format or audio data")
    fmt = seen[b'fmt ']
    _require(len(fmt) >= 16, "invalid PCM format chunk")
    codec, channels, rate, byte_rate, align, bits = struct.unpack('<HHIIHH', fmt[:16])
    _require(codec == 1 and bits == 16, "not supported PCM16 WAV")
    _require(channels in (1, 2), "invalid audio channel count")
    _require(8000 <= rate <= 192000, "sample rate outside validation profile")
    _require(align == 2 * channels and byte_rate == rate * align, "invalid format stride/rate")
    data = seen[b'data']
    _require(len(data) > 0 and len(data) % align == 0, "empty or partial audio frame")
    with wave.open(io.BytesIO(blob), 'rb') as reader:
        _require(reader.getcomptype() == 'NONE' and reader.getsampwidth() == 2, "PCM decoder rejects format")
        _require(reader.getnchannels() == channels and reader.getframerate() == rate, "PCM decoder metadata mismatch")
        samples = reader.readframes(reader.getnframes())
        _require(samples == data, "decoded PCM bytes disagree with data chunk")
    frames = len(data) // align
    sample_values = struct.unpack('<' + 'h' * (len(data)//2), data)
    peak = max(abs(x) for x in sample_values) / 32768.0
    dc = sum(sample_values) / len(sample_values) / 32768.0
    rms = (sum((x / 32768.0)**2 for x in sample_values))**0.5 / (len(sample_values)**0.5)
    stereo_corr = None
    if channels == 2 and frames >= 2:
        left, right = sample_values[0::2], sample_values[1::2]
        av_l, av_r = sum(left)/frames, sum(right)/frames
        sum_l = sum((v - av_l)**2 for v in left)
        sum_r = sum((v - av_r)**2 for v in right)
        if sum_l > 0 and sum_r > 0:
            stereo_corr = sum((l-av_l)*(r-av_r) for l,r in zip(left,right)) / (sum_l*sum_r)**0.5
    return {"sha256": hashlib.sha256(blob).hexdigest(), "pcm_sha256": hashlib.sha256(data).hexdigest(),
            "codec": "PCM16", "sample_rate": rate, "channels": channels,
            "frames": frames, "duration_seconds": frames / rate,
            "peak_normalized": round(peak, 8), "dc_normalized": round(dc, 8),
            "rms_normalized": round(rms, 8),
            "left_right_correlation": None if stereo_corr is None else round(stereo_corr, 6),
            "silent": peak == 0, "pcm_bytes": data}


def compare_revisions(blob_a: bytes, blob_b: bytes, start_frame: int, end_frame: int, tail_frames: int = 0):
    a, b = verify_wav(blob_a), verify_wav(blob_b)
    _require(a['channels'] == b['channels'] and a['sample_rate'] == b['sample_rate'] and a['frames'] == b['frames'],
             "R1/R2 waveform formats or durations differ; sample-locality comparison unavailable")
    _require(0 <= start_frame < end_frame <= a['frames'] and tail_frames >= 0, "invalid edit-frame envelope")
    stride = a['channels'] * 2
    x, y = a['pcm_bytes'], b['pcm_bytes']
    outside, inside, first, last = 0, 0, None, None
    for frame in range(a['frames']):
        k = frame*stride
        if x[k:k+stride] != y[k:k+stride]:
            if first is None: first = frame
            last = frame
            if start_frame <= frame < min(a['frames'], end_frame + tail_frames):
                inside += 1
            else:
                outside += 1
    _require(a['sha256'] != b['sha256'], "R1/R2 identical audio artifacts")
    _require(inside > 0, "no changed frames in target edit envelope")
    _require(outside == 0, "unrelated PCM frames changed outside edit plus permitted tail")
    return {"status": "PASS", "r1_sha256": a['sha256'], "r2_sha256": b['sha256'],
            "target_changed_frames": inside, "outside_changed_frames": outside,
            "first_changed_frame": first, "last_changed_frame": last,
            "sample_rate": a['sample_rate'], "channels": a['channels'], "frames": a['frames']}


def verify_tenant_observations(evidence):
    """Validate independent observed HTTP outcomes; do not generate or claim observations."""
    required = {
        'A_READ_OWN': {200}, 'B_READ_A': {404}, 'ANON_READ_A': {401,403},
        'B_MUTATE_A': {404}, 'ANON_MUTATE_A': {401,403},
        'B_ARTIFACT_A': {404}, 'B_HISTORY_A': {404},
        'B_FORGED_OWNER_A': {404},
    }
    _require(evidence.get('evidence_kind') == 'OBSERVED_HTTP', 'not observational HTTP evidence')
    _require(evidence.get('target_commit') and evidence.get('target_url_id'), 'missing target identity')
    values = evidence.get('observations')
    _require(isinstance(values, list), 'observations must be a list')
    results = {}
    for row in values:
        case, status, body = row.get('case'), row.get('status'), row.get('response_excerpt','')
        _require(case in required and case not in results, 'unknown or duplicate security case')
        _require(type(status) is int, 'invalid HTTP status observation')
        _require(isinstance(body, str) and len(body) <= 2048, 'invalid response excerpt')
        _require(status in required[case], f'{case}: HTTP {status} violates tenant-boundary contract')
        # Ensure negative responses never echo known protected project sentinel.
        _require(case == 'A_READ_OWN' or 'TENANT_A_SECRET_CANARY' not in body,
                 f'{case}: response leaked protected sentinel')
        results[case] = status
    _require(set(results) == set(required), 'incomplete tenant-boundary observations')
    return {"status": "PASS", "observed_case_count": len(results),
            "target_commit": evidence['target_commit'], "target_url_id": evidence['target_url_id']}


def main():
    parser = argparse.ArgumentParser(description='Independent Studio audio and tenancy acceptance; no server mutations')
    parser.add_argument('--r1', type=Path); parser.add_argument('--r2', type=Path)
    parser.add_argument('--start-frame', type=int); parser.add_argument('--end-frame', type=int)
    parser.add_argument('--tail-frames', type=int, default=0)
    parser.add_argument('--tenant-observations', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    receipt = {"schema":"sara-studio.independent-qa.v1", "status":"UNVERIFIED", "evaluations":{}}
    try:
        if args.r1 or args.r2:
            _require(args.r1 and args.r2 and args.start_frame is not None and args.end_frame is not None,
                     'both WAV paths and edit envelope are required')
            a, b = args.r1.read_bytes(), args.r2.read_bytes()
            receipt['evaluations']['r1_wav'] = {k:v for k,v in verify_wav(a).items() if k != 'pcm_bytes'}
            receipt['evaluations']['r2_wav'] = {k:v for k,v in verify_wav(b).items() if k != 'pcm_bytes'}
            receipt['evaluations']['edit_locality'] = compare_revisions(a,b,args.start_frame,args.end_frame,args.tail_frames)
        if args.tenant_observations:
            receipt['evaluations']['tenant_boundary'] = verify_tenant_observations(json.loads(args.tenant_observations.read_text()))
        _require(bool(receipt['evaluations']), 'nothing was evaluated; provide real WAVs or captured HTTP observations')
        receipt['status'] = 'PASS'
    except (ContractFailure, OSError, KeyError, ValueError, wave.Error, TypeError) as exc:
        receipt['status'] = 'FAIL'
        receipt['first_failed_boundary'] = str(exc)
    rendered = json.dumps(receipt, indent=2) + '\n'
    if args.output: args.output.write_text(rendered)
    print(rendered, end='')
    return 0 if receipt['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())

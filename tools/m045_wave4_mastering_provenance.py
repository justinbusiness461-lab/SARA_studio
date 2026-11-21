"""S.A.R.A. Studio Wave 004 CPU-only mastering and subordinate provenance evidence.

Uses FFmpeg's EBU R128 loudnorm filter and an independent output measurement.
This is NOT a claim of certified BS.1770-4 meter conformance. Source is immutable,
and publication/authorization belongs exclusively to studio_server.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, io, json, math, re, subprocess, tempfile, wave
from pathlib import Path

ALLOWED_RIGHTS_STATES=frozenset({"ARTIST_ORIGINAL","LICENSE_CLEARED","OPEN_WEIGHT_UNVERIFIED",
 "PROVIDER_TERMS_UNVERIFIED","UNVERIFIED_HELD"})
ALLOWED_ORIGIN_TYPES=frozenset({"ARTIST_UPLOAD","NATIVE_SCORECORE","FM_PREVIEW_SYNTH",
 "OPEN_WEIGHT_MODEL","COMMERCIAL_API","DSP_TRANSFORM"})
_SHA=re.compile(r"[0-9a-f]{64}\Z")
# Only Studio's host-side mastering accepts this larger, fixed PCM16 boundary.
# Generic exports, JSON uploads, previews and arbitrary render payloads stay 16 MiB.
MAX_MASTER_SECONDS=210
MAX_MASTER_BYTES=40*1024*1024
@dataclass(frozen=True)
class CanonicalProvenanceRecord:
 artifact_sha256:str
 pcm_sha256:str
 project_id:str
 revision_id:str
 origin_type:str
 preservation_tier:str
 rights_status:str
 parent_artifact_sha256s:list[str]
 transform_chain:list[dict]
 def validate(self):
  if not all(isinstance(d,str) and _SHA.fullmatch(d) for d in
             [self.artifact_sha256,self.pcm_sha256,*self.parent_artifact_sha256s]):
   raise ValueError("INVALID_PROVENANCE_DIGEST")
  if not self.project_id or not self.revision_id:
   raise ValueError("MISSING_AUTHORITY_ID")
  if self.origin_type not in ALLOWED_ORIGIN_TYPES:
   raise ValueError("INVALID_ORIGIN_TYPE")
  if self.preservation_tier not in {"P0","P1","P2","P3"}:
   raise ValueError("INVALID_PRESERVATION_TIER")
  if self.rights_status not in ALLOWED_RIGHTS_STATES:
   raise ValueError("INVALID_RIGHTS_STATUS")
  if not self.parent_artifact_sha256s or not all(isinstance(v,dict) for v in self.transform_chain):
   raise ValueError("INVALID_LINEAGE")
 def to_dict(self):
  self.validate()
  return {**asdict(self),"release_cleared":False} # No authorization without verified rights source.

def _filter_metrics(stderr:bytes):
 text=stderr.decode("utf-8","replace")
 matches=re.findall(r'\{\s*"input_i"\s*:\s*".*?"[\s\S]*?\}',text)
 if not matches:raise ValueError("LOUDNESS_METER_RECEIPT_MISSING")
 info=json.loads(matches[-1])
 try:
  result={k:float(info[k]) for k in
   ["input_i","input_tp","input_lra","input_thresh","output_i","output_tp","output_lra","target_offset"]}
 except (KeyError,ValueError,TypeError) as e:raise ValueError("LOUDNESS_METER_INVALID") from e
 if not all(math.isfinite(v) for v in result.values()):
  raise ValueError("LOUDNESS_UNMEASURABLE")
 return result

def _run(args,deadline):
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=deadline,check=False)
 except (OSError,subprocess.TimeoutExpired) as e:
  raise ValueError("LOUDNESS_ENGINE_UNAVAILABLE_OR_TIMEOUT") from e
 if p.returncode:raise ValueError("LOUDNESS_ENGINE_FAILED")
 return p

def _validate_audio(data):
 if not isinstance(data,bytes) or not 44<=len(data)<=MAX_MASTER_BYTES:
  raise ValueError("MASTER_INPUT_UNSUPPORTED_LENGTH")
 try:
  with wave.open(io.BytesIO(data),"rb") as w:
   if (w.getcomptype()!="NONE" or w.getframerate()!=44100 or w.getsampwidth()!=2
    or w.getnchannels() not in (1,2) or w.getnframes()<4410):
    raise ValueError("MASTER_INPUT_REQUIRES_44100_PCM16")
   if w.getnframes()>44100*MAX_MASTER_SECONDS:
    raise ValueError("MASTER_INPUT_DURATION_UNQUALIFIED")
   frames=w.getnframes()
   # Validate bounded blocks; a 210-second song is not decoded into an extra
   # 37 MiB temporary buffer merely to check completeness.
   remaining=frames
   while remaining:
    chunk=min(65536,remaining)
    raw=w.readframes(chunk)
    if len(raw)!=chunk*w.getnchannels()*2:
     raise ValueError("TRUNCATED_MASTER_SOURCE")
    remaining-=chunk
   return frames
 except (wave.Error, EOFError) as e:
  raise ValueError("MASTER_INPUT_PCM_INVALID") from e

def master_wav_to_lufs_target(*,wav_bytes:bytes,target_lufs=-14.0,true_peak_ceiling_dbtp=-1.0):
 """FFmpeg BS.1770-derived gating, true peak, two-pass normalization and readback.
 Reports actual independent output measurement; target cannot be faked by requested gain.
 """
 if (type(target_lufs) not in (int,float) or not math.isfinite(target_lufs)
  or target_lufs not in (-14.0,-9.0)):
  raise ValueError("MASTER_PRESET_NOT_QUALIFIED")
 if (type(true_peak_ceiling_dbtp) not in (int,float) or not math.isfinite(true_peak_ceiling_dbtp)
  or true_peak_ceiling_dbtp!=-1.0):
  raise ValueError("MASTER_CEILING_NOT_QUALIFIED")
 samples=_validate_audio(wav_bytes)
 # These are ephemeral DSP work files, not immutable artifact authority.
 with tempfile.TemporaryDirectory(prefix="sara-wave4-dsp-") as tmp:
  src=Path(tmp)/"source.wav";dst=Path(tmp)/"master.wav"
  src.write_bytes(wav_bytes)
  af=f"loudnorm=I={target_lufs}:TP={true_peak_ceiling_dbtp}:LRA=11:print_format=json"
  first=_run(["ffmpeg","-y","-nostdin","-hide_banner","-loglevel","info","-threads","1",
   "-i",str(src),"-af",af,"-f","null","-"],90)
  before=_filter_metrics(first.stderr)
  if before["input_i"] <= -69.9:raise ValueError("CANNOT_MASTER_SILENT_AUDIO")
  filter2=(f"loudnorm=I={target_lufs}:TP={true_peak_ceiling_dbtp}:LRA=11"
   f":measured_I={before['input_i']}:measured_TP={before['input_tp']}"
   f":measured_LRA={before['input_lra']}:measured_thresh={before['input_thresh']}"
   f":offset={before['target_offset']}:linear=true:print_format=json")
  _run(["ffmpeg","-y","-nostdin","-hide_banner","-loglevel","info","-threads","1",
   "-i",str(src),"-af",filter2,"-ar","44100","-ac","2",
   "-c:a","pcm_s16le",str(dst)],90)
  output=dst.read_bytes()
  _validate_audio(output)
  if len(output)>MAX_MASTER_BYTES:raise ValueError("MASTER_OUTPUT_TOO_LARGE")
  independent=_run(["ffmpeg","-nostdin","-hide_banner","-loglevel","info","-threads","1",
   "-i",str(dst),"-af",af,"-f","null","-"],90)
  measured=_filter_metrics(independent.stderr)
  # Independent implementation: explicit stereo K-shelf + RLB, two-stage
  # BS.1770 gating and bounded FFmpeg 4x polyphase intersample measurement.
  # Reference vectors are checked; accredited calibration is NOT claimed.
  from m045_bs1770_reference import measure_reference_pcm16
  reference=measure_reference_pcm16(output)
  if (abs(reference["integrated_lufs"]-measured["input_i"])>0.3 or
      abs(reference["true_peak_dbtp"]-measured["input_tp"])>0.4):
   raise ValueError("MASTER_REFERENCE_METER_DISAGREEMENT")
  if reference["true_peak_dbtp"]>true_peak_ceiling_dbtp+0.1:
   raise ValueError("MASTER_REFERENCE_TRUE_PEAK_CEILING_FAILED")
  if measured["input_tp"]>true_peak_ceiling_dbtp+0.05:
   raise ValueError("INDEPENDENT_TRUE_PEAK_CEILING_FAILED")
  status="TARGET_REACHED" if abs(measured["input_i"]-target_lufs)<=0.5 else "TARGET_UNREACHED_LIMITED"
  telemetry={
   "method":"ffmpeg-loudnorm-ebu-r128-bs1770-based","meterConformance":"NOT_INDEPENDENTLY_CERTIFIED",
   "target_lufs":target_lufs,"true_peak_ceiling_dbtp":true_peak_ceiling_dbtp,
   "input_lufs":round(before["input_i"],2),"input_true_peak_dbtp":round(before["input_tp"],2),
   "measured_output_lufs":round(measured["input_i"],2),
   "measured_output_true_peak_dbtp":round(measured["input_tp"],2),
   "true_peak_verified":True,"targetStatus":status,
   "reference_meter":reference,
   "mastered_wav_sha256":hashlib.sha256(output).hexdigest()
  }
  return output,telemetry

"""ACE-Step 1.5 official asynchronous REST client for native S.A.R.A. GenerationAttempt.

Upstream contract: POST /release_task -> POST /query_result -> GET /v1/audio.
This adapter owns no CAS, project revision, or playable-media authorization.
No synthetic audio or fake remote checkpoint attestation is permitted.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from m045_generation_attempt import M045_MAX_WAV_BYTES, _verify_wav, native_atomic_write_bytes

HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_DOWNLOAD_BYTES = 48 * 1024 * 1024
MODEL_NAME = "acestep-v15-turbo"

class ProviderUnavailable(RuntimeError):
    pass

class RemoteSubmissionUncertain(ProviderUnavailable):
    pass

class AceStepProvider:
    model_id = "ace-step-1.5"
    model_version = "ace-step-1.5"
    supports_remote_resume = True
    supports_repaint = True

    def __init__(self, *, endpoint_url=None, checkpoint_dir=None, checkpoint_sha256=None,
                 api_key=None, timeout=300, poll_interval=1, max_polls=180):
        self.endpoint = endpoint_url if endpoint_url is not None else os.getenv("SARA_ACESTEP_ENDPOINT_URL", "")
        self.checkpoint_dir = checkpoint_dir if checkpoint_dir is not None else os.getenv("ACESTEP_CHECKPOINT_DIR", "")
        self.checkpoint_sha256 = (checkpoint_sha256 if checkpoint_sha256 is not None
                                  else os.getenv("SARA_ACESTEP_CHECKPOINT_SHA256", ""))
        self.api_key = api_key if api_key is not None else os.getenv("SARA_ACESTEP_API_KEY", "")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_polls = max_polls

    def _url(self, endpoint):
        base = urllib.parse.urlsplit(self.endpoint)
        if (not base.hostname or base.username or base.password or base.query or base.fragment
                or base.path not in ("", "/")
                or not (base.scheme == "https" or (base.scheme == "http" and base.hostname in ("127.0.0.1", "localhost")))):
            raise ProviderUnavailable("ACE_STEP_ENDPOINT_UNTRUSTED")
        return self.endpoint.rstrip("/") + endpoint

    @staticmethod
    def _multipart(fields, source, *, field_name="src_audio", filename="source.wav"):
        # Multipart is required: ACE-Step does not accept client-local paths.
        if field_name not in ("src_audio","reference_audio"):
            raise ValueError("ACE_STEP_MULTIPART_FIELD_UNQUALIFIED")
        boundary = "sara" + hashlib.sha256(source + json.dumps(fields,sort_keys=True).encode()).hexdigest()[:32]
        chunks=[]
        for name, value in sorted(fields.items()):
            if isinstance(value, bool):
                value="true" if value else "false"
            chunks.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode())
        chunks.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field_name}\"; filename=\"{filename}\"\r\nContent-Type: audio/wav\r\n\r\n").encode())
        chunks.append(source)
        chunks.append((f"\r\n--{boundary}--\r\n").encode())
        return b"".join(chunks), "multipart/form-data; boundary="+boundary

    def _request(self, path, body=None, *, limit=1024*1024, src_audio=None, reference_audio=None):
        headers={"Accept": "application/json" if body is not None or path != "/v1/audio" else "audio/wav"}
        if self.api_key:
            headers["Authorization"]="Bearer "+self.api_key
        if src_audio is not None or reference_audio is not None:
            if (path != "/release_task" or not isinstance(body,dict)
                    or (src_audio is not None and reference_audio is not None)):
                raise ValueError("ACE_STEP_INVALID_AUDIO_MULTIPART")
            if reference_audio is not None:
                payload,mime=self._multipart(body,reference_audio,
                    field_name="reference_audio",filename="reference.wav")
            else:
                payload,mime=self._multipart(body,src_audio)
            headers["Content-Type"]=mime
        elif body is not None:
            payload=json.dumps(body,sort_keys=True).encode("utf-8")
            headers["Content-Type"]="application/json"
        else:
            payload=None
        request=urllib.request.Request(self._url(path),
            data=payload,
            headers=headers,method="POST" if body is not None else "GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if path.startswith("/v1/audio?"):
                    raw=response.read(limit+1)
                    if len(raw)>limit or not raw:
                        raise ValueError("ACE_STEP_AUDIO_OUT_OF_BOUNDS")
                    return raw
                raw=response.read(limit+1)
                if len(raw)>limit:
                    raise ValueError("ACE_STEP_RESPONSE_TOO_LARGE")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderUnavailable("ACE_STEP_REMOTE_UNAVAILABLE") from exc
        try:
            doc=json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise ValueError("ACE_STEP_INVALID_JSON") from exc
        if not isinstance(doc,dict) or doc.get("code")!=200 or doc.get("error"):
            raise ProviderUnavailable("ACE_STEP_UPSTREAM_REJECTED")
        return doc.get("data")

    @staticmethod
    def _music_attributes(spec):
        if not isinstance(spec,dict):
            raise ValueError("SONGSPEC_REQUIRED")
        tb=spec.get("timebase") or {}
        out={}
        bpm=tb.get("initial_bpm")
        if bpm is not None:
            if type(bpm) not in (int,float) or not 30<=bpm<=300:
                raise ValueError("ACE_STEP_INVALID_BPM")
            out["bpm"]=int(bpm)
        key=tb.get("key")
        if isinstance(key,str) and key.strip():
            out["key_scale"]=key.strip()
        meter=tb.get("meter")
        if isinstance(meter,str) and "/" in meter:
            out["time_signature"]=meter.split("/",1)[0]
        return out

    def __call__(self, stage_dir, song_spec, prompt, lyrics, seed, params):
        if not self.endpoint:
            raise ProviderUnavailable("ACE_STEP_RUNTIME_UNQUALIFIED" if self.checkpoint_dir else "ACE_STEP_NOT_CONFIGURED")
        self._url("/health")
        if not isinstance(self.checkpoint_sha256,str) or not HEX64.fullmatch(self.checkpoint_sha256):
            raise ProviderUnavailable("ACE_STEP_CHECKPOINT_IDENTITY_UNVERIFIED")
        if not shutil.which("ffmpeg"):
            raise ProviderUnavailable("FFMPEG_NOT_INSTALLED")
        if not isinstance(prompt,str) or not prompt.strip():
            raise ValueError("GENERATION_PROMPT_REQUIRED")
        if lyrics is not None and not isinstance(lyrics,str):
            raise ValueError("INVALID_LYRICS")
        if not isinstance(params,dict):
            raise ValueError("ACE_STEP_UNSUPPORTED_PARAMETERS")
        repaint=params.get("_m045_repaint")
        reference=params.get("_m045_reference")
        allowed={"music_length_ms"}
        if reference is not None:
            allowed.add("_m045_reference")
            if (not isinstance(reference,dict)
                    or set(reference)!={"reference_sha256","audio_cover_strength"}):
                raise ValueError("ACE_STEP_REFERENCE_AUTHORITY_REQUIRED")
            if repaint is not None:
                raise ValueError("ACE_STEP_REFERENCE_REPAINT_UNQUALIFIED")
        if repaint is not None:
            allowed.update({"edit_mode","start_bar","end_bar","target_track_id","_m045_repaint"})
            if params.get("edit_mode")!="repaint":
                raise ValueError("ACE_STEP_REPAINT_MODE_REQUIRED")
            if (not isinstance(repaint,dict) or
                    set(repaint)!={"start_sample","end_sample","source_sha256"}):
                raise ValueError("ACE_STEP_REPAINT_AUTHORITY_REQUIRED")
        if set(params)-allowed:
            raise ValueError("ACE_STEP_UNSUPPORTED_PARAMETERS")
        duration=params.get("music_length_ms",15000)
        if type(duration) is not int or not 10000 <= duration <= 210000:
            raise ValueError("ACE_STEP_DURATION_OUT_OF_RANGE")
        if type(seed) is not int:
            raise ValueError("INVALID_SEED")
        body={"prompt":prompt,"lyrics":lyrics or "","audio_duration":duration/1000,
              "audio_format":"wav","model":MODEL_NAME,"task_type":"text2music",
              "batch_size":1,"use_random_seed":False,"seed":seed,
              "thinking":False, **self._music_attributes(song_spec)}
        stage=pathlib.Path(stage_dir)
        source_bytes=None
        reference_bytes=None
        if reference is not None:
            ref_path=stage/"reference-source.wav"
            if not ref_path.is_file() or ref_path.is_symlink():
                raise ValueError("ACE_STEP_REFERENCE_SOURCE_MISSING")
            reference_bytes=ref_path.read_bytes()
            strength=reference["audio_cover_strength"]
            if (not isinstance(reference["reference_sha256"],str)
                    or not HEX64.fullmatch(reference["reference_sha256"])
                    or type(strength) not in (float,int) or not 0<=strength<=1
                    or hashlib.sha256(reference_bytes).hexdigest()!=reference["reference_sha256"]):
                raise ValueError("ACE_STEP_REFERENCE_SOURCE_MISMATCH")
            from m045_repaint import read_pcm16_wav
            read_pcm16_wav(reference_bytes)
            body["audio_cover_strength"]=strength
        if repaint is not None:
            source_file=stage/"repaint-source.wav"
            if not source_file.is_file() or source_file.is_symlink():
                raise ValueError("ACE_STEP_REPAINT_SOURCE_MISSING")
            source_bytes=source_file.read_bytes()
            from m045_repaint import read_pcm16_wav
            _, source_frames=read_pcm16_wav(source_bytes)
            start,end=repaint["start_sample"],repaint["end_sample"]
            if (type(start) is not int or type(end) is not int
                    or not 0<=start<end<=source_frames
                    or hashlib.sha256(source_bytes).hexdigest()!=repaint["source_sha256"]):
                raise ValueError("ACE_STEP_REPAINT_SOURCE_MISMATCH")
            body.update({"task_type":"repaint","chunk_mask_mode":"explicit",
                "repainting_start":start/44100, "repainting_end":end/44100,
                "audio_duration":source_frames/44100})
        started=time.monotonic()
        identity = {
            "endpoint_url": self.endpoint.rstrip("/"),
            "checkpoint_sha256": self.checkpoint_sha256,
            "request_sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
            "provider": "ace_step_native",
            "source_sha256": hashlib.sha256(source_bytes).hexdigest() if source_bytes is not None else None,
            "reference_sha256": hashlib.sha256(reference_bytes).hexdigest() if reference_bytes is not None else None,
        }
        task_path = stage / "upstream-task.json"
        if task_path.is_file():
            saved = json.loads(task_path.read_text(encoding="utf-8"))
            if (not isinstance(saved, dict)
                    or any(saved.get(k) != v for k, v in identity.items())
                    or not isinstance(saved.get("task_id"), str)
                    or not saved["task_id"]):
                raise ValueError("ACE_STEP_REMOTE_TASK_IDENTITY_CONFLICT")
            task_id = saved["task_id"]
        else:
            try:
                released = self._request("/release_task", body, src_audio=source_bytes,
                                         reference_audio=reference_bytes)
            except ProviderUnavailable as exc:
                # Upstream might have accepted the task before our connection failed.
                # No task ID means no lawful way to resume; do not blindly retry.
                raise RemoteSubmissionUncertain("ACE_STEP_SUBMISSION_OUTCOME_UNKNOWN") from exc
            if not isinstance(released, dict) or not isinstance(released.get("task_id"), str) or not released["task_id"]:
                raise RemoteSubmissionUncertain("ACE_STEP_SUBMISSION_MISSING_TASK_ID")
            task_id = released["task_id"]
            try:
                native_atomic_write_bytes(task_path, json.dumps({
                    **identity, "task_id": task_id
                }, sort_keys=True).encode("utf-8"))
            except OSError as exc:
                raise RemoteSubmissionUncertain("ACE_STEP_ACCEPTED_BUT_TASK_ID_NOT_DURABLE") from exc
        result=None
        for _ in range(self.max_polls):
            rows=self._request("/query_result",{"task_id_list":[task_id]})
            if not isinstance(rows,list) or len(rows)!=1 or rows[0].get("task_id")!=task_id:
                raise ValueError("ACE_STEP_INVALID_TASK_STATUS")
            row=rows[0]
            if row.get("status")==2:
                raise ProviderUnavailable("ACE_STEP_GENERATION_FAILED")
            if row.get("status")==1:
                result=row.get("result")
                break
            if row.get("status")!=0:
                raise ValueError("ACE_STEP_UNKNOWN_TASK_STATUS")
            if time.monotonic()-started > self.timeout:
                raise ProviderUnavailable("ACE_STEP_POLL_TIMEOUT")
            time.sleep(self.poll_interval)
        if result is None:
            raise ProviderUnavailable("ACE_STEP_POLL_EXHAUSTED")
        try:
            files=json.loads(result) if isinstance(result,str) else result
        except ValueError as exc:
            raise ValueError("ACE_STEP_INVALID_RESULT") from exc
        if not isinstance(files,list) or len(files)!=1 or not isinstance(files[0],dict):
            raise ValueError("ACE_STEP_INVALID_RESULT")
        file_url=files[0].get("file")
        if not isinstance(file_url,str) or not file_url.startswith("/v1/audio?path="):
            raise ValueError("ACE_STEP_FOREIGN_AUDIO_URL")
        parts=urllib.parse.urlsplit(file_url)
        if parts.fragment or parts.netloc or parts.scheme or parts.path!="/v1/audio":
            raise ValueError("ACE_STEP_FOREIGN_AUDIO_URL")
        remote_audio=self._request(file_url,limit=MAX_DOWNLOAD_BYTES)
        source_path=stage/"native-provider-download"
        native_atomic_write_bytes(source_path,remote_audio)
        decoded=stage/"ace-step-decoded.wav"
        try:
            proc=subprocess.run(["ffmpeg","-nostdin","-y","-v","error",
                "-i",str(source_path),"-vn","-ac","2","-ar","44100",
                "-c:a","pcm_s16le","-t","210","-f","wav",str(decoded)],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90,check=False)
        except subprocess.TimeoutExpired as exc:
            raise ProviderUnavailable("ACE_STEP_DECODE_TIMEOUT") from exc
        if proc.returncode!=0 or not decoded.is_file() or not 44 < decoded.stat().st_size <= M045_MAX_WAV_BYTES:
            raise ValueError("ACE_STEP_DECODE_INVALID")
        output=stage/"output.wav"
        native_atomic_write_bytes(output,decoded.read_bytes())
        media=_verify_wav(output)
        if media["channels"]!=2 or media["sample_rate"]!=44100:
            raise ValueError("ACE_STEP_CANONICAL_PCM_REQUIRED")
        receipt={
            "source_type":"OPEN_WEIGHT_REMOTE_PROVIDER",
            "rights_status":"OPEN_WEIGHT_UNVERIFIED_TRAINING_DATA",
            "license_class":"UNVERIFIED",
            "preservation_tier":"P2" if repaint is not None else "P3",
            "provider_id":"ace_step_native_api",
            "model_id":self.model_id,"model_version":self.model_version,
            "dit_model":str(files[0].get("dit_model",""))[:128],
            "checkpoint_sha256":self.checkpoint_sha256,
            "checkpoint_identity_source":"OPERATOR_CONFIGURED_UNVERIFIED",
            "provider_request_id":task_id[:128],
            "seed":seed,
            "reference_artifact_digest":reference["reference_sha256"] if reference is not None else None,
            "reference_strength":reference["audio_cover_strength"] if reference is not None else None,
            "audio_sha256":media["sha256"],
            "latency_ms":int((time.monotonic()-started)*1000),
            "output_format":"wav_pcm16_stereo_44100"}
        native_atomic_write_bytes(stage/"provider-receipt.json",json.dumps(receipt,sort_keys=True).encode())
        return output

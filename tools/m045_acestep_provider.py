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

    def _request(self, path, body=None, *, limit=1024*1024):
        headers={"Accept": "application/json" if body is not None or path != "/v1/audio" else "audio/wav"}
        if self.api_key:
            headers["Authorization"]="Bearer "+self.api_key
        if body is not None:
            headers["Content-Type"]="application/json"
        request=urllib.request.Request(self._url(path),
            data=(json.dumps(body,sort_keys=True).encode("utf-8") if body is not None else None),
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
        if not isinstance(params,dict) or set(params)-{"music_length_ms"}:
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
        started=time.monotonic()
        identity = {
            "endpoint_url": self.endpoint.rstrip("/"),
            "checkpoint_sha256": self.checkpoint_sha256,
            "request_sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
            "provider": "ace_step_native",
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
                released = self._request("/release_task", body)
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
            "preservation_tier":"P3",
            "provider_id":"ace_step_native_api",
            "model_id":self.model_id,"model_version":self.model_version,
            "dit_model":str(files[0].get("dit_model",""))[:128],
            "checkpoint_sha256":self.checkpoint_sha256,
            "checkpoint_identity_source":"OPERATOR_CONFIGURED_UNVERIFIED",
            "provider_request_id":task_id[:128],
            "seed":seed,
            "audio_sha256":media["sha256"],
            "latency_ms":int((time.monotonic()-started)*1000),
            "output_format":"wav_pcm16_stereo_44100"}
        native_atomic_write_bytes(stage/"provider-receipt.json",json.dumps(receipt,sort_keys=True).encode())
        return output

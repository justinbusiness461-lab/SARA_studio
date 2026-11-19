"""ACE-Step remote inference adapter. No embedded GPU inference or synthetic fallback.

Remote service must be separately qualified and return full canonical PCM16 WAV
with an immutable checkpoint SHA-256. Local checkpoints alone are not executable.
"""
from __future__ import annotations
import hashlib
import json
import os
import pathlib
import urllib.parse
import urllib.request
import urllib.error
from m045_generation_attempt import _verify_wav, native_atomic_write_bytes, M045_MAX_WAV_BYTES

class ProviderUnavailable(RuntimeError):
    pass

class AceStepProvider:
    model_id = "ace-step-1.5"
    model_version = "ace-step-1.5"

    def __init__(self, *, endpoint_url=None, checkpoint_dir=None, timeout=300):
        self.endpoint = endpoint_url if endpoint_url is not None else os.getenv("SARA_ACESTEP_ENDPOINT_URL", "")
        self.checkpoint_dir = checkpoint_dir if checkpoint_dir is not None else os.getenv("ACESTEP_CHECKPOINT_DIR", "")
        self.timeout = timeout

    def __call__(self, stage_dir, song_spec, prompt, lyrics, seed, params):
        if not self.endpoint:
            raise ProviderUnavailable("ACE_STEP_RUNTIME_UNQUALIFIED" if self.checkpoint_dir else "ACE_STEP_NOT_CONFIGURED")
        uri = urllib.parse.urlsplit(self.endpoint)
        if (not uri.hostname or uri.username or uri.password or uri.fragment
                or not (uri.scheme == "https" or (uri.scheme == "http" and uri.hostname in ("localhost", "127.0.0.1")))):
            raise ProviderUnavailable("ACE_STEP_ENDPOINT_UNTRUSTED")
        if not isinstance(prompt,str) or not prompt.strip():
            raise ValueError("GENERATION_PROMPT_REQUIRED")
        if not isinstance(params,dict) or set(params) - {"music_length_ms"}:
            raise ValueError("ACE_STEP_UNSUPPORTED_PARAMETERS")
        duration = params.get("music_length_ms", 15000)
        if type(duration) is not int or not 3000 <= duration <= 210000:
            raise ValueError("ACE_STEP_DURATION_OUT_OF_RANGE")
        request_body={"model_id":self.model_id,"prompt":prompt,"lyrics":lyrics or "",
                      "duration_ms":duration,"seed":int(seed),"song_spec":song_spec}
        request = urllib.request.Request(self.endpoint, method="POST",
            data=json.dumps(request_body,sort_keys=True).encode("utf-8"),
            headers={"Content-Type":"application/json","Accept":"audio/wav"})
        try:
            with urllib.request.urlopen(request,timeout=self.timeout) as response:
                mime=response.headers.get("Content-Type","").split(";",1)[0].lower()
                if mime not in ("audio/wav","audio/x-wav"):
                    raise ValueError("ACE_STEP_INVALID_MEDIA_TYPE")
                checkpoint_digest=response.headers.get("X-Checkpoint-SHA256","")
                model=response.headers.get("X-Model-Id","")
                request_id=response.headers.get("X-Request-Id","")
                data=response.read(M045_MAX_WAV_BYTES+1)
        except (urllib.error.URLError,TimeoutError) as exc:
            raise ProviderUnavailable("ACE_STEP_REMOTE_UNAVAILABLE") from exc
        if (len(checkpoint_digest)!=64 or any(c not in "0123456789abcdef" for c in checkpoint_digest)
                or model!=self.model_id):
            raise ValueError("ACE_STEP_CHECKPOINT_ATTESTATION_MISSING")
        if not (44 < len(data) <= M045_MAX_WAV_BYTES):
            raise ValueError("ACE_STEP_AUDIO_OUT_OF_BOUNDS")
        output=pathlib.Path(stage_dir)/"output.wav"
        native_atomic_write_bytes(output,data)
        media=_verify_wav(output)
        if media["sample_rate"]!=44100 or media["channels"]!=2:
            raise ValueError("ACE_STEP_CANONICAL_PCM16_REQUIRED")
        receipt={"source_type":"OPEN_WEIGHT_REMOTE_PROVIDER",
                 "rights_status":"OPEN_WEIGHT_UNVERIFIED_TRAINING_DATA",
                 "license_class":"UNVERIFIED",
                 "preservation_tier":"P3",
                 "provider_id":"ace_step_remote",
                 "model_id":self.model_id,
                 "model_version":self.model_version,
                 "checkpoint_sha256":checkpoint_digest,
                 "provider_request_id":str(request_id)[:128],
                 "seed":int(seed),
                 "audio_sha256":media["sha256"],
                 "output_format":"wav_pcm16_stereo_44100"}
        native_atomic_write_bytes(pathlib.Path(stage_dir)/"provider-receipt.json",json.dumps(receipt,sort_keys=True).encode("utf-8"))
        return output

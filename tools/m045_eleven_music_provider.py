"""Host-registered Eleven Music transport for Studio's native GenerationAttempt.

No project/revision/CAS authority lives here. No fixture or silent fallback.
The current 16 MiB Studio artifact ceiling limits this adapter to <= 90 s.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from m045_generation_attempt import native_atomic_write_bytes

ENDPOINT = "https://api.elevenlabs.io/v1/music"
MODEL_ID = "music_v2_5"
MODEL_VERSION = "elevenlabs-music-v2.5"
MAX_UPSTREAM_BYTES = 20 * 1024 * 1024
MAX_WAV_BYTES = 16 * 1024 * 1024

class ProviderUnavailable(RuntimeError):
    pass

class ElevenMusicProvider:
    """Production API adapter; registered explicitly by a trusted host."""

    model_id = MODEL_ID
    model_version = MODEL_VERSION

    def __init__(self, api_key=None, *, timeout_seconds=120):
        self._api_key = api_key if api_key is not None else os.environ.get("ELEVENLABS_API_KEY", "")
        self.timeout_seconds = timeout_seconds

    def __call__(self, stage_dir, song_spec, prompt, lyrics, seed, params):
        if not self._api_key or not self._api_key.strip():
            raise ProviderUnavailable("ELEVENLABS_API_KEY_UNCONFIGURED")
        if not shutil.which("ffmpeg"):
            raise ProviderUnavailable("FFMPEG_NOT_INSTALLED")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("GENERATION_PROMPT_REQUIRED")
        if lyrics is not None and not isinstance(lyrics, str):
            raise ValueError("INVALID_LYRICS")
        if not isinstance(params, dict) or set(params) - {"music_length_ms", "force_instrumental"}:
            raise ValueError("UNSUPPORTED_PROVIDER_PARAMETERS")
        duration_ms = params.get("music_length_ms", 15000)
        if type(duration_ms) is not int or not 3000 <= duration_ms <= 90000:
            raise ValueError("DURATION_OUTSIDE_NATIVE_ARTIFACT_LIMIT")
        if type(params.get("force_instrumental", False)) is not bool:
            raise ValueError("INVALID_INSTRUMENTAL_PARAMETER")
        if lyrics and params.get("force_instrumental"):
            raise ValueError("LYRICS_CONFLICT_WITH_INSTRUMENTAL")
        # Prompt mode does not accept the API's seed parameter. The request's
        # Studio seed is recorded but NOT asserted to control provider randomness.
        full_prompt = prompt if not lyrics else prompt + "\nLyrics:\n" + lyrics
        if len(full_prompt) > 4100:
            raise ValueError("ELEVEN_MUSIC_PROMPT_TOO_LONG")
        body = {
            "prompt": full_prompt,
            "music_length_ms": duration_ms,
            "model_id": MODEL_ID,
            "force_instrumental": bool(params.get("force_instrumental", False)),
        }
        request = urllib.request.Request(
            ENDPOINT + "?output_format=mp3_44100_128",
            data=json.dumps(body, sort_keys=True).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
                "xi-api-key": self._api_key,
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                mime = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if mime not in {"audio/mpeg", "audio/mp3", "application/octet-stream"}:
                    raise ValueError("PROVIDER_RETURNED_NON_AUDIO_CONTENT")
                upstream_id = response.headers.get("song-id", "")
                raw = response.read(MAX_UPSTREAM_BYTES + 1)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderUnavailable("ELEVEN_MUSIC_UPSTREAM_UNAVAILABLE") from exc
        if not raw or len(raw) > MAX_UPSTREAM_BYTES or not raw.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
            raise ValueError("INVALID_OR_OVERSIZED_PROVIDER_AUDIO")
        # Decode real upstream audio; never replace it with generated tones.
        stage = pathlib.Path(stage_dir)
        output = stage / "output.wav"
        decoded_path = stage / "provider-decoded.wav"
        try:
            converted = subprocess.run(
                ["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                 "-f", "mp3", "-i", "pipe:0", "-vn",
                 "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le",
                 "-t", "90", "-f", "wav", str(decoded_path)],
                input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=False, timeout=45,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderUnavailable("PROVIDER_AUDIO_DECODE_TIMEOUT") from exc
        if converted.returncode != 0 or not decoded_path.is_file() or not (44 < decoded_path.stat().st_size <= MAX_WAV_BYTES):
            raise ValueError("PROVIDER_AUDIO_DECODE_OR_SIZE_FAILED")
        audio_bytes = decoded_path.read_bytes()
        native_atomic_write_bytes(output, audio_bytes)
        decoded_path.unlink()
        receipt = {
            "source_type": "EXTERNAL_COMMERCIAL_PROVIDER",
            "rights_status": "PROVIDER_TERMS_UNVERIFIED",
            "preservation_tier": "P3",
            "provider_id": "elevenlabs_music",
            "model_id": MODEL_ID,
            "model_version": MODEL_VERSION,
            "provider_song_id": str(upstream_id)[:128],
            "upstream_sha256": hashlib.sha256(raw).hexdigest(),
            "audio_sha256": hashlib.sha256(audio_bytes).hexdigest(),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "seed_applied_by_provider": False,
            "output_format": "wav_pcm16_stereo_44100",
        }
        native_atomic_write_bytes(stage / "provider-receipt.json",
                                  json.dumps(receipt, sort_keys=True).encode("utf-8"))
        return output

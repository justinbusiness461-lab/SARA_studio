"""Opt-in ACE-Step 1.5 Modal GPU server; DOES NOT deploy on import.

The 120-second Function input timeout and 30-second idle window are safety
limits, NOT a hard account-spend cap. Startup may fail if it exceeds 95s.
Web-server HTTP timeout alone cannot identify a cancellable FunctionCall;
only a separately host-bound Modal spawn ID can be safely cancelled.


Deployment requires operator approval, Modal credentials, and a named secret.
Do not advertise readiness until a real inference and Studio playback pass.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

import modal

UPSTREAM_REPO = "https://github.com/ace-step/ACE-Step-1.5.git"
# Verified upstream source identity at authoring; refresh deliberately.
UPSTREAM_COMMIT = "ca1e85fe9430179831e6bc6be790c332190a3866"
MODEL_VOLUME_PATH = "/models/checkpoints"
MODEL_VOLUME_NAME = "sara-acestep-15-weights"
MODEL_SECRET_NAME = "sara-acestep-secret"

weights_volume = modal.Volume.from_name(MODEL_VOLUME_NAME, create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libsndfile1", "curl")
    .run_commands(
        "python -m pip install uv",
        f"git clone {UPSTREAM_REPO} /opt/ACE-Step-1.5",
        f"git -C /opt/ACE-Step-1.5 checkout --detach {UPSTREAM_COMMIT}",
        "cd /opt/ACE-Step-1.5 && uv sync --frozen",
    )
)
app = modal.App("sara-studio-acestep-15")


def _checkpoint_manifest(root: Path) -> dict[str, str]:
    """Hash all supported model files; never treat an empty set as qualified."""
    values = {}
    if not root.is_dir():
        return values
    for entry in sorted(root.rglob("*")):
        if entry.is_symlink():
            raise RuntimeError("checkpoint symlink prohibited")
        if entry.is_file() and entry.suffix in {".safetensors", ".bin", ".pt"}:
            digest = hashlib.sha256()
            with entry.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            values[str(entry.relative_to(root))] = digest.hexdigest()
    return values


def _manifest_sha256(entries: dict[str, str]) -> str:
    if not entries:
        raise RuntimeError("no weights available: checkpoint identity not verified")
    return hashlib.sha256(json.dumps(entries, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


@app.function(
    image=image,
    gpu="L40S",
    volumes={MODEL_VOLUME_PATH: weights_volume},
    secrets=[modal.Secret.from_name(MODEL_SECRET_NAME)],
    timeout=120,
    startup_timeout=110,
    scaledown_window=30,
    min_containers=0,
    retries=0,
    max_containers=1,
)
@modal.concurrent(max_inputs=1)
@modal.web_server(port=8001, startup_timeout=100)
def serve_acestep_api():
    api_key = os.environ.get("ACESTEP_API_KEY", "")
    if len(api_key) < 32 or api_key.strip() != api_key:
        raise RuntimeError("secure ACESTEP_API_KEY secret is required")
    model_root = Path(MODEL_VOLUME_PATH)
    model_root.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "ACESTEP_CHECKPOINTS_DIR": MODEL_VOLUME_PATH,
        "ACESTEP_API_KEY": api_key,
        "ACESTEP_CONFIG_PATH": "acestep-v15-turbo",
        "ACESTEP_LM_MODEL_PATH": "acestep-5Hz-lm-1.7B",
        "ACESTEP_BATCH_SIZE": "1",
        "ACESTEP_NO_INIT": "false",
    })
    proc = subprocess.Popen(
        ["uv", "run", "acestep-api", "--host", "0.0.0.0", "--port", "8001"],
        cwd="/opt/ACE-Step-1.5",
        env=env,
    )
    deadline = time.monotonic() + 95
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"ACE-Step terminated during startup: {proc.returncode}")
        try:
            with urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=3) as response:
                if response.status == 200:
                    weights_volume.commit()
                    entries = _checkpoint_manifest(model_root)
                    digest = _manifest_sha256(entries)
                    print("ACESTEP_CHECKPOINT_MANIFEST_SHA256=" + digest, flush=True)
                    print("ACESTEP_UPSTREAM_COMMIT=" + UPSTREAM_COMMIT, flush=True)
                    return
        except (OSError, TimeoutError, ValueError):
            time.sleep(2)
    raise TimeoutError("ACE-Step startup not qualified; /health or weights unavailable")

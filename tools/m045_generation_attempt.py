#!/usr/bin/env python3
"""Native Mission 045 GenerationAttempt durability boundary.

This module owns attempt lifecycle records only. Project revisions, CAS objects,
authentication, authorization, and revision association remain supplied by the
canonical studio_server.py callbacks.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
import time
import uuid
import wave
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional


HEX64 = re.compile(r"^[a-f0-9]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class AttemptSecurityError(PermissionError):
    pass


class AttemptLifecycleState(str, Enum):
    PREPARING = "PREPARING"
    FAILED_PRE_COMMIT = "FAILED_PRE_COMMIT"
    ARTIFACT_DURABLE = "ARTIFACT_DURABLE"
    COMMITTED = "COMMITTED"
    ASSOCIATED_HISTORICAL = "ASSOCIATED_HISTORICAL"
    COMMIT_UNCERTAIN = "COMMIT_UNCERTAIN"


def _conflict(message: str) -> Exception:
    """Use the canonical conflict type when studio_server is already loaded."""
    try:
        from studio_server import ProjectConflict  # type: ignore
        return ProjectConflict(message)
    except (ImportError, ModuleNotFoundError):
        return ValueError(message)


def native_atomic_write_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".m045-write-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _safe(value: str, label: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def _request_digest(kwargs: Dict[str, Any]) -> str:
    stable = {
        "project_id": kwargs["project_id"],
        "base_revision_id": kwargs["base_revision_id"],
        "expected_current_revision_id": kwargs["expected_current_revision_id"],
        "idempotency_key": kwargs["idempotency_key"],
        "model_id": kwargs["model_id"],
        "model_version": kwargs["model_version"],
        "seed": kwargs["seed"],
        "song_spec": kwargs["song_spec"],
        "prompt": kwargs["prompt"],
        "lyrics": kwargs.get("lyrics"),
        "params": kwargs.get("params") or {},
    }
    return hashlib.sha256(_json_bytes(stable)).hexdigest()


def _verify_wav(path: Path) -> Dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            width = audio.getsampwidth()
            rate = audio.getframerate()
            frames = audio.getnframes()
            if audio.getcomptype() != "NONE" or channels not in (1, 2) or width != 2 or rate <= 0 or frames <= 0:
                raise ValueError("unsupported physical WAV")
            raw = audio.readframes(frames)
            if len(raw) != frames * channels * width:
                raise ValueError("truncated physical WAV")
    except (wave.Error, EOFError, OSError) as exc:
        raise ValueError("invalid physical WAV") from exc
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "sample_rate": rate,
        "channels": channels,
        "sample_width": width,
        "frames": frames,
        "byte_length": len(raw) + 44,
    }


class GenerationAttemptOwner:
    """Durable attempt protocol around canonical Studio authorities."""

    def __init__(
        self,
        *,
        data_root: Path,
        resolve_session_principal: Callable[[str], str],
        authorize_project: Callable[[str, str, str], bool],
        read_revision: Callable[[str, str], Optional[Dict[str, Any]]],
        list_project_revisions: Callable[[str], Dict[str, Dict[str, Any]]],
        publish_cas_object: Callable[[bytes], str],
        associate_and_commit_revision: Callable[..., Dict[str, Any]],
        atomic_write_fn: Callable[[Path, bytes], None] = native_atomic_write_bytes,
    ) -> None:
        self.data_root = Path(data_root).resolve()
        self.resolve_session_principal = resolve_session_principal
        self.authorize_project = authorize_project
        self.read_revision = read_revision
        self.list_project_revisions = list_project_revisions
        self.publish_cas_object = publish_cas_object
        self.associate_and_commit_revision = associate_and_commit_revision
        self.atomic_write_fn = atomic_write_fn
        self._thread_locks: Dict[str, threading.Lock] = {}
        self._thread_locks_guard = threading.Lock()

    def authenticate_bearer(self, headers: Dict[str, str]) -> str:
        value = headers.get("Authorization", "")
        if not isinstance(value, str) or not value.startswith("Bearer ") or not value[7:]:
            raise AttemptSecurityError("authentication required")
        try:
            principal = self.resolve_session_principal(value[7:])
        except Exception as exc:
            raise AttemptSecurityError("authentication denied") from exc
        if not isinstance(principal, str) or not principal:
            raise AttemptSecurityError("authentication denied")
        return principal

    def _authorize(self, headers: Dict[str, str], project_id: str, capability: str) -> str:
        principal = self.authenticate_bearer(headers)
        try:
            allowed = self.authorize_project(principal, project_id, capability)
        except Exception as exc:
            raise AttemptSecurityError("project authorization denied") from exc
        if allowed is False:
            raise AttemptSecurityError("project authorization denied")
        return principal

    def _project_dir(self, project_id: str) -> Path:
        return self.data_root / "projects" / project_id

    def _attempt_dir(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "generation-attempts"

    def _attempt_path(self, project_id: str, idempotency_key: str) -> Path:
        return self._attempt_dir(project_id) / (hashlib.sha256(idempotency_key.encode()).hexdigest() + ".json")

    def _load_attempt(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_attempt(self, path: Path, record: Dict[str, Any]) -> None:
        record["updated_at"] = time.time()
        self.atomic_write_fn(path, _json_bytes(record))

    def _lock(self, project_id: str):
        directory = self._project_dir(project_id)
        directory.mkdir(parents=True, exist_ok=True)
        with self._thread_locks_guard:
            thread_lock = self._thread_locks.setdefault(project_id, threading.Lock())
        thread_lock.acquire()
        handle = os.open(directory / ".m045-generation.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX)
        except Exception:
            os.close(handle)
            thread_lock.release()
            raise
        return handle, thread_lock

    def _unlock(self, locked) -> None:
        handle, thread_lock = locked
        fcntl.flock(handle, fcntl.LOCK_UN)
        os.close(handle)
        thread_lock.release()

    def _find_revision(self, project_id: str, attempt_id: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
        for revision in self.list_project_revisions(project_id).values():
            operation = revision.get("operation") or {}
            if (revision.get("attemptId") == attempt_id
                    or revision.get("idempotencyKey") == idempotency_key
                    or operation.get("id") == "m045:" + attempt_id):
                return revision
        return None

    def reconcile_attempt(self, *, headers: Dict[str, str], project_id: str, idempotency_key: str) -> Dict[str, Any]:
        project_id = _safe(project_id, "project_id")
        idempotency_key = _safe(idempotency_key, "idempotency_key")
        self._authorize(headers, project_id, "generate")
        handle = self._lock(project_id)
        try:
            path = self._attempt_path(project_id, idempotency_key)
            if not path.is_file():
                raise ValueError("generation attempt not found")
            attempt = self._load_attempt(path)
            revision = self._find_revision(project_id, attempt["attempt_id"], idempotency_key)
            if revision is not None:
                current = self.read_revision(project_id, "CURRENT")
                current_id = current.get("revisionId") if current else None
                state = (AttemptLifecycleState.COMMITTED.value
                         if current_id == revision.get("revisionId")
                         else AttemptLifecycleState.ASSOCIATED_HISTORICAL.value)
                attempt["state"] = state
                attempt["committed_revision_id"] = revision.get("revisionId")
                self._save_attempt(path, attempt)
                return {"state": state, "attempt": attempt, "revision": revision, "reconciled": True}
            return {"state": attempt["state"], "attempt": attempt, "revision": None, "reconciled": False}
        finally:
            self._unlock(handle)

    def execute_attempt(self, **kwargs: Any) -> Dict[str, Any]:
        headers = kwargs.get("headers") or {}
        project_id = _safe(kwargs.get("project_id"), "project_id")
        base_revision_id = _safe(kwargs.get("base_revision_id"), "base_revision_id")
        expected_revision_id = _safe(kwargs.get("expected_current_revision_id"), "expected_current_revision_id")
        idempotency_key = _safe(kwargs.get("idempotency_key"), "idempotency_key")
        model_id = _safe(kwargs.get("model_id"), "model_id")
        model_version = _safe(kwargs.get("model_version"), "model_version")
        synthesize = kwargs.get("synthesize_to_stage_fn")
        if not callable(synthesize):
            raise ValueError("synthesis function required")
        if base_revision_id != expected_revision_id:
            raise _conflict("base and expected revisions differ")
        self._authorize(headers, project_id, "generate")
        request_digest = _request_digest(kwargs)
        handle = self._lock(project_id)
        path = self._attempt_path(project_id, idempotency_key)
        try:
            existing = self._load_attempt(path) if path.is_file() else None
            if existing is not None:
                if existing.get("request_digest") != request_digest:
                    raise _conflict("idempotency key payload conflict")
                revision = self._find_revision(project_id, existing["attempt_id"], idempotency_key)
                if revision is not None:
                    current = self.read_revision(project_id, "CURRENT")
                    state = (AttemptLifecycleState.COMMITTED.value
                             if current and current.get("revisionId") == revision.get("revisionId")
                             else AttemptLifecycleState.ASSOCIATED_HISTORICAL.value)
                    existing["state"] = state
                    existing["committed_revision_id"] = revision.get("revisionId")
                    self._save_attempt(path, existing)
                    return {"state": state, "attempt": existing, "revision": revision, "replayed": True}
                if existing.get("state") == AttemptLifecycleState.FAILED_PRE_COMMIT.value:
                    raise RuntimeError(existing.get("error_code", "previous synthesis failed"))
                if existing.get("state") == AttemptLifecycleState.COMMIT_UNCERTAIN.value:
                    raise _conflict("commit outcome remains uncertain; reconcile first")
                raise _conflict("generation attempt is already in progress")

            current = self.read_revision(project_id, "CURRENT")
            if not current or current.get("revisionId") != expected_revision_id:
                raise _conflict("stale expected revision")
            attempt = {
                "attempt_id": "att_" + uuid.uuid4().hex,
                "project_id": project_id,
                "base_revision_id": base_revision_id,
                "expected_current_revision_id": expected_revision_id,
                "idempotency_key": idempotency_key,
                "request_digest": request_digest,
                "model_id": model_id,
                "model_version": model_version,
                "seed": int(kwargs.get("seed", 0)),
                "state": AttemptLifecycleState.PREPARING.value,
                "created_at": time.time(),
                "updated_at": time.time(),
                "error_code": None,
                "artifact_digest": None,
                "committed_revision_id": None,
            }
            self._save_attempt(path, attempt)
            stage_dir = self._attempt_dir(project_id) / (attempt["attempt_id"] + ".stage")
            stage_dir.mkdir(parents=True, exist_ok=True)
            stage_path = stage_dir / "output.wav"
            try:
                result = synthesize(stage_dir, kwargs.get("song_spec"), kwargs.get("prompt"), kwargs.get("lyrics"), int(kwargs.get("seed", 0)), kwargs.get("params") or {})
                result_path = Path(result)
                if result_path != stage_path:
                    if not result_path.is_file():
                        raise ValueError("synthesizer did not produce a file")
                    self.atomic_write_fn(stage_path, result_path.read_bytes())
                if not stage_path.is_file():
                    raise ValueError("synthesizer did not produce a WAV")
                media = _verify_wav(stage_path)
                artifact_digest = self.publish_cas_object(stage_path.read_bytes())
                if artifact_digest != media["sha256"] or not HEX64.fullmatch(artifact_digest):
                    raise ValueError("CAS digest mismatch")
                attempt["artifact_digest"] = artifact_digest
                attempt["media"] = media
                attempt["state"] = AttemptLifecycleState.ARTIFACT_DURABLE.value
                self._save_attempt(path, attempt)
            except Exception as exc:
                attempt["state"] = AttemptLifecycleState.FAILED_PRE_COMMIT.value
                attempt["error_code"] = str(exc)
                self._save_attempt(path, attempt)
                raise

            reconciled = False
            try:
                committed = self.associate_and_commit_revision(
                    project_id=project_id,
                    expected_current_revision_id=expected_revision_id,
                    base_revision_id=base_revision_id,
                    attempt_id=attempt["attempt_id"],
                    idempotency_key=idempotency_key,
                    artifact_digest=artifact_digest,
                    song_spec=kwargs.get("song_spec"),
                    source_asset_digests=kwargs.get("source_asset_digests") or [],
                )
            except Exception as exc:
                revision = self._find_revision(project_id, attempt["attempt_id"], idempotency_key)
                if revision is None:
                    attempt["state"] = AttemptLifecycleState.COMMIT_UNCERTAIN.value
                    attempt["error_code"] = str(exc)
                    self._save_attempt(path, attempt)
                    return {"state": attempt["state"], "attempt": attempt, "revision": None, "reconciled": False}
                committed = revision
                reconciled = True
            revision = (committed.get("revision")
                        if isinstance(committed, dict) and isinstance(committed.get("revision"), dict)
                        else committed)
            if not isinstance(revision, dict) or not revision.get("revisionId"):
                raise ValueError("canonical commit returned no revision")
            current = self.read_revision(project_id, "CURRENT")
            state = (AttemptLifecycleState.COMMITTED.value
                     if current and current.get("revisionId") == revision.get("revisionId")
                     else AttemptLifecycleState.ASSOCIATED_HISTORICAL.value)
            attempt["state"] = state
            attempt["committed_revision_id"] = revision.get("revisionId")
            self._save_attempt(path, attempt)
            return {"state": state, "attempt": attempt, "revision": revision, "replayed": False, "reconciled": reconciled}
        finally:
            self._unlock(handle)

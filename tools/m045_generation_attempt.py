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


M045_MAX_SECONDS = 210
M045_MAX_WAV_BYTES = 40 * 1024 * 1024

HEX64 = re.compile(r"^[a-f0-9]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class AttemptSecurityError(PermissionError):
    pass


class AttemptLifecycleState(str, Enum):
    PREPARING = "PREPARING"
    POLL_INTERRUPTED = "POLL_INTERRUPTED"
    SUBMISSION_UNCERTAIN = "SUBMISSION_UNCERTAIN"
    AWAITING_TAKE_SELECTION = "AWAITING_TAKE_SELECTION"
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
    # Preserve exact historical fingerprint for unconditioned single-take
    # attempts, including ones persisted before these optional fields existed.
    if kwargs.get("reference_artifact_digest") is not None:
        stable["reference_artifact_digest"] = kwargs["reference_artifact_digest"]
        stable["audio_cover_strength"] = kwargs.get("audio_cover_strength", 1.0)
    if kwargs.get("batch_count", 1) not in (None, 1):
        stable["batch_count"] = kwargs["batch_count"]
    if kwargs.get("typed_edit_proposal") is not None:
        stable["typed_edit_proposal"] = kwargs["typed_edit_proposal"]
    return hashlib.sha256(_json_bytes(stable)).hexdigest()


def _verify_wav(path: Path) -> Dict[str, Any]:
    if path.stat().st_size > M045_MAX_WAV_BYTES:
        raise ValueError("M045 artifact too large")
    try:
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            width = audio.getsampwidth()
            rate = audio.getframerate()
            frames = audio.getnframes()
            if audio.getcomptype() != "NONE" or channels not in (1, 2) or width != 2 or rate <= 0 or frames <= 0:
                raise ValueError("unsupported physical WAV")
            if frames > rate * M045_MAX_SECONDS:
                raise ValueError("M045 duration boundary exceeded")
            if frames * channels * width > M045_MAX_WAV_BYTES:
                raise ValueError("M045 artifact too large")
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
        # HTTP field names are case insensitive. The transport may preserve
        # lowercase names when forwarding headers into the owner dictionary.
        values = [v for k,v in headers.items() if isinstance(k,str) and k.lower()=="authorization"]
        if len(values) != 1:
            raise AttemptSecurityError("authentication required")
        value = values[0]
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
            if (attempt_id in revision.get("historicalGenerationAttempts", [])
                    or revision.get("attemptId") == attempt_id
                    or revision.get("idempotencyKey") == idempotency_key
                    or operation.get("id") == "m045:" + attempt_id):
                return revision
        return None

    def reconcile_attempt(self, *, headers: Dict[str, str], project_id: str, idempotency_key: str,
                          synthesize_to_stage_fn=None) -> Dict[str, Any]:
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
            provider = synthesize_to_stage_fn
            if isinstance(provider, dict):
                provider = provider.get(attempt.get("model_id"))
            if (attempt["state"] in {AttemptLifecycleState.POLL_INTERRUPTED.value,
                                      AttemptLifecycleState.PREPARING.value}
                    and (self._attempt_dir(project_id) / (attempt["attempt_id"] + ".stage") / "upstream-task.json").is_file()
                    and callable(provider)
                    and getattr(provider, "supports_remote_resume", False)
                    and getattr(provider, "model_id", None) == attempt.get("model_id")
                    and getattr(provider, "model_version", None) == attempt.get("model_version")):
                stored = attempt.get("resume_request")
                if not isinstance(stored, dict):
                    raise _conflict("missing durable resume request")
                retry_fields = dict(stored)
                # Optional fields omitted by legacy attempts remain omitted.
                # Do not replay a serialized null as an invalid explicit batch.
                for field in ("reference_artifact_digest", "audio_cover_strength", "batch_count"):
                    if retry_fields.get(field) is None:
                        retry_fields.pop(field, None)
                retry_fields["headers"] = headers
                retry_fields["synthesize_to_stage_fn"] = provider
            else:
                return {"state": attempt["state"], "attempt": attempt, "revision": None, "reconciled": False}
        finally:
            self._unlock(handle)
        # Re-enter canonical execution under the same project lock and idempotency
        # key. Never submit a second task: the provider verifies its saved task ID.
        return self.execute_attempt(**retry_fields)

    def read_take_audio(self, *, headers, project_id, idempotency_key, take_index):
        project_id = _safe(project_id, "project_id")
        idempotency_key = _safe(idempotency_key, "idempotency_key")
        self._authorize(headers, project_id, "generate")
        if type(take_index) is not int:
            raise ValueError("invalid take index")
        handle = self._lock(project_id)
        try:
            record_path = self._attempt_path(project_id, idempotency_key)
            attempt = self._load_attempt(record_path)
            if attempt.get("project_id") != project_id or attempt.get("batch_count",1) <= 1:
                raise _conflict("multi-take association missing")
            takes = attempt.get("takes") or []
            if len(takes) != attempt["batch_count"] or not 0 <= take_index < len(takes):
                raise _conflict("take unavailable")
            selected = takes[take_index]
            if selected.get("take_index") != take_index:
                raise _conflict("take identity mismatch")
            digest = selected["artifact_digest"]
            if not isinstance(digest,str) or not HEX64.fullmatch(digest):
                raise _conflict("take digest invalid")
            from studio_server import artifact_bytes, validate_render_audio
            validate_render_audio(self.data_root, digest)
            data = artifact_bytes(self.data_root, digest)
            if hashlib.sha256(data).hexdigest() != digest:
                raise _conflict("take integrity mismatch")
            return data
        finally:
            self._unlock(handle)

    def select_take(self, *, headers, project_id, idempotency_key,
                    take_index, expected_current_revision_id):
        project_id = _safe(project_id, "project_id")
        idempotency_key = _safe(idempotency_key, "idempotency_key")
        expected_current_revision_id = _safe(expected_current_revision_id,"expected_current_revision_id")
        self._authorize(headers, project_id, "generate")
        if type(take_index) is not int:
            raise ValueError("invalid take_index")
        handle = self._lock(project_id)
        try:
            path = self._attempt_path(project_id, idempotency_key)
            attempt = self._load_attempt(path)
            if attempt.get("project_id") != project_id or attempt.get("batch_count",1) <= 1:
                raise _conflict("multi-take attempt missing")
            takes = attempt.get("takes",[])
            if (len(takes) != attempt["batch_count"]
                    or not 0 <= take_index < len(takes)
                    or takes[take_index].get("take_index") != take_index
                    or attempt.get("state") not in ("AWAITING_TAKE_SELECTION","TAKE_SELECTED","SELECTION_UNCERTAIN")):
                raise _conflict("take selection not available")
            existing = (attempt.get("selections") or {}).get(str(take_index))
            operation_attempt = attempt["attempt_id"] + "-take-" + str(take_index)
            recovered = self._find_revision(project_id, operation_attempt, idempotency_key+":take:"+str(take_index))
            if existing or recovered:
                revision = recovered or self.read_revision(project_id, existing["revision_id"])
                if revision is None or revision.get("outputArtifactIds") != [takes[take_index]["artifact_digest"]]:
                    raise _conflict("selected take revision identity mismatch")
                return {"state":"TAKE_SELECTED","revision":revision,"attempt":attempt,"reconciled":True}
            current = self.read_revision(project_id, "CURRENT")
            if not current or current.get("revisionId") != expected_current_revision_id:
                raise _conflict("stale expected revision")
            # A take belongs to the SongSpec captured at generation. Only its
            # original base or a previously selected sibling can be its parent.
            # Unrelated revisions require a separate explicit rebase operation.
            lawful_heads={attempt["base_revision_id"]}
            lawful_heads.update(binding["revision_id"] for binding in
                               attempt.get("selections",{}).values())
            if expected_current_revision_id not in lawful_heads:
                raise _conflict("take selection requires explicit rebase from unrelated revision")
            from studio_server import project_operation,validate_render_audio
            principal=self.authenticate_bearer(headers)
            snapshot=project_operation(self.data_root, {"projectId":project_id},principal_id=principal)
            if snapshot["revision"]["revisionId"] != expected_current_revision_id:
                raise _conflict("stale expected revision")
            digest=takes[take_index]["artifact_digest"]
            validate_render_audio(self.data_root,digest)
            attempt["selection_intent"]={"take_index":take_index,
                "expected_revision_id":expected_current_revision_id}
            self._save_attempt(path,attempt)
            try:
                committed=self.associate_and_commit_revision(
                    project_id=project_id,expected_current_revision_id=expected_current_revision_id,
                    base_revision_id=expected_current_revision_id,attempt_id=operation_attempt,
                    idempotency_key=idempotency_key+":take:"+str(take_index),
                    artifact_digest=digest,song_spec=snapshot["songSpec"],
                    source_asset_digests=snapshot["revision"].get("sourceAssetDigests",[]))
            except Exception as exc:
                found=self._find_revision(project_id,operation_attempt,idempotency_key+":take:"+str(take_index))
                if found is None:
                    attempt["state"]="SELECTION_UNCERTAIN"
                    self._save_attempt(path,attempt)
                    raise _conflict("take commit uncertain; reread canonical revision") from exc
                committed=found
            revision = committed.get("revision") if isinstance(committed,dict) and "revision" in committed else committed
            if revision.get("outputArtifactIds") != [digest]:
                raise _conflict("take commit returned conflicting artifact")
            attempt.setdefault("selections",{})[str(take_index)]={"revision_id":revision["revisionId"],
                "artifact_digest":digest}
            attempt.pop("selection_intent",None)
            attempt["state"]="TAKE_SELECTED"
            self._save_attempt(path,attempt)
            return {"state":"TAKE_SELECTED","revision":revision,"attempt":attempt,"reconciled":False}
        finally:
            self._unlock(handle)

    def _execute_multi(self, kwargs, *, project_id, base_revision_id,
                       expected_revision_id, idempotency_key, model_id, model_version,
                       synthesize, requested, reference_audio, reference_digest, reference_strength):
        if not getattr(synthesize,"supports_multitake",False):
            raise _conflict("multi-take provider not qualified")
        count=kwargs["batch_count"]
        digest=_request_digest(kwargs)
        handle=self._lock(project_id)
        try:
            path=self._attempt_path(project_id,idempotency_key)
            resume=False
            if path.is_file():
                attempt=self._load_attempt(path)
                if attempt.get("request_digest") != digest:
                    raise _conflict("idempotency key payload conflict")
                if attempt.get("state") in ("AWAITING_TAKE_SELECTION","TAKE_SELECTED"):
                    return {"state":attempt["state"],"attempt":attempt,"revision":None,"replayed":True}
                stage=self._attempt_dir(project_id)/(attempt["attempt_id"]+".stage")
                saved_task=stage/"upstream-task.json"
                if (not getattr(synthesize,"supports_remote_resume",False)
                        or not saved_task.is_file() or saved_task.is_symlink()):
                    raise _conflict("multi-take completion unknown; no blind retry")
                resume=True
            else:
                current=self.read_revision(project_id,"CURRENT")
                if not current or current.get("revisionId")!=expected_revision_id:
                    raise _conflict("stale expected revision")
                attempt={"attempt_id":"att_"+uuid.uuid4().hex,"project_id":project_id,
                   "base_revision_id":base_revision_id,"expected_current_revision_id":expected_revision_id,
                   "idempotency_key":idempotency_key,"request_digest":digest,
                   "model_id":model_id,"model_version":model_version,"batch_count":count,
                   "resume_request":{k:kwargs.get(k) for k in (
                       "project_id","base_revision_id","expected_current_revision_id",
                       "idempotency_key","model_id","model_version","seed",
                       "song_spec","prompt","lyrics","params","batch_count",
                       "reference_artifact_digest","audio_cover_strength",
                       "typed_edit_proposal")},
                   "state":"PREPARING","takes":[],"selections":{}}
                self._save_attempt(path,attempt)
            stage=self._attempt_dir(project_id)/(attempt["attempt_id"]+".stage")
            stage.mkdir(parents=True,exist_ok=True)
            if getattr(synthesize,"supports_remote_resume",False):
                for directory in (stage.parent,stage):
                    fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                    try: os.fsync(fd)
                    finally: os.close(fd)
            params={**requested,"_m045_batch_count":count}
            if reference_audio is not None:
                source=stage/"reference-source.wav"
                if source.exists() and source.read_bytes()!=reference_audio:
                    raise _conflict("reference identity drift")
                if not source.exists(): self.atomic_write_fn(source,reference_audio)
                params["_m045_reference"]={"reference_sha256":reference_digest,
                                           "audio_cover_strength":float(reference_strength)}
            try:
                paths=synthesize(stage,kwargs.get("song_spec"),kwargs.get("prompt"),
                                 kwargs.get("lyrics"),int(kwargs.get("seed",0)),params)
                if not isinstance(paths,(tuple,list)) or len(paths)!=count:
                    raise ValueError("multi-take provider returned wrong take count")
                takes=[]
                digests=set()
                expected_frames=None
                requires_proof=getattr(synthesize,"requires_batch_provenance",False)
                batch_proof=None
                if requires_proof:
                    proof_path=stage/"provider-takes.json"
                    if not proof_path.is_file() or proof_path.is_symlink():
                        raise ValueError("multi-take provider provenance missing")
                    batch_proof=json.loads(proof_path.read_text(encoding="utf-8"))
                    if not isinstance(batch_proof,list) or len(batch_proof)!=count:
                        raise ValueError("multi-take provenance cardinality mismatch")
                for i,source in enumerate(paths):
                    path_i=Path(source)
                    if path_i.parent.resolve()!=stage.resolve() or not path_i.is_file() or path_i.is_symlink():
                        raise ValueError("multi-take staged output invalid")
                    media=_verify_wav(path_i)
                    if media["channels"]!=2 or media["sample_rate"]!=44100 or media["sample_width"]!=2:
                        raise ValueError("multi-take canonical PCM16 required")
                    raw=path_i.read_bytes()
                    if expected_frames is None:
                        expected_frames=media["frames"]
                    elif media["frames"]!=expected_frames:
                        raise ValueError("multi-take sample length mismatch")
                    if batch_proof is not None:
                        receipt=batch_proof[i]
                        if (not isinstance(receipt,dict) or receipt.get("take_index")!=i
                                or receipt.get("artifact_digest")!=media["sha256"]
                                or receipt.get("model_id")!=model_id
                                or receipt.get("model_version")!=model_version
                                or receipt.get("preservation_tier")!="P3"
                                or receipt.get("rights_status")!="OPEN_WEIGHT_UNVERIFIED_TRAINING_DATA"
                                or not HEX64.fullmatch(str(receipt.get("checkpoint_sha256","")))):
                            raise ValueError("multi-take provider proof mismatch")
                    # Durable ownership precedes CAS publication, so an abrupt
                    # crash after write cannot create ownerless content.
                    intents=attempt.setdefault("publication_intents",[])
                    intent={"take_index":i,"artifact_digest":media["sha256"],
                            "state":"PUBLICATION_REQUESTED"}
                    previous=next((v for v in intents if v.get("take_index")==i),None)
                    if previous is not None and previous.get("artifact_digest")!=media["sha256"]:
                        raise _conflict("take publication identity drift")
                    if previous is None:
                        intents.append(intent)
                    self._save_attempt(path,attempt)
                    sha=self.publish_cas_object(raw)
                    if sha!=media["sha256"] or sha in digests:
                        raise ValueError("multi-take digest collision or alias")
                    digests.add(sha)
                    from m045_repaint import read_pcm16_wav
                    pcm,frames=read_pcm16_wav(raw)
                    takes.append({"take_index":i,"artifact_digest":sha,
                        "pcm_sha256":hashlib.sha256(pcm).hexdigest(),
                        "duration_sec":frames/44100,
                        "provenance":batch_proof[i] if batch_proof is not None else
                                     {"source_type":"TEST_PROVIDER_UNVERIFIED","preservation_tier":"P3"}})
                    attempt["takes"]=list(takes)
                    self._save_attempt(path,attempt)
                attempt["state"]="AWAITING_TAKE_SELECTION"
                self._save_attempt(path,attempt)
                return {"state":attempt["state"],"attempt":attempt,"revision":None,"replayed":False}
            except Exception as exc:
                remote=stage/"upstream-task.json"
                if remote.is_file():
                    attempt["state"]="POLL_INTERRUPTED"
                elif exc.__class__.__name__=="RemoteSubmissionUncertain":
                    attempt["state"]="SUBMISSION_UNCERTAIN"
                else:
                    attempt["state"]="FAILED_PRE_COMMIT"
                attempt["error_code"]=str(exc)
                self._save_attempt(path,attempt)
                raise
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
        # A full-mix provider edit cannot isolate a locked stem. Both
        # generation and scoped repaint fail closed while any track is locked.
        from studio_server import project_operation, project_audio_bytes
        from m045_repaint import bar_sample_window, read_pcm16_wav
        principal = self.authenticate_bearer(headers)
        saved = project_operation(self.data_root, {"projectId": project_id,
            "revisionId": base_revision_id}, principal_id=principal)
        current_spec = saved["songSpec"]
        if any(track.get("sonic_lock") is True for track in current_spec.get("tracks", [])):
            raise _conflict("Sonic Lock prevents full-mix reconstruction")
        requested = kwargs.get("params") or {}
        if not isinstance(requested, dict):
            raise ValueError("invalid generation params")
        batch_count=kwargs.get("batch_count",1)
        if type(batch_count) is not int or not 1 <= batch_count <= 4:
            raise ValueError("batch_count must be an integer from 1 to 4")

        reference_digest=kwargs.get("reference_artifact_digest")
        reference_audio=None
        reference_strength=kwargs.get("audio_cover_strength",1.0)
        if reference_digest is not None:
            if not isinstance(reference_digest,str) or not HEX64.fullmatch(reference_digest):
                raise ValueError("invalid reference_artifact_digest")
            if (type(reference_strength) not in (float,int) or
                    not 0.0 <= reference_strength <= 1.0):
                raise ValueError("invalid audio_cover_strength")
            # The caller's principal and source revision were already verified
            # by project_operation. Reference authority must be a member of
            # this exact revision, never CAS existence or client-provided paths.
            from studio_server import artifact_bytes, validate_render_audio
            revision=saved["revision"]
            member=set(revision.get("sourceAssetDigests",[]))
            member.update(revision.get("outputArtifactIds",[]))
            member.update(b["artifactId"] for b in saved.get("historicalOutputBindings",[]))
            if reference_digest not in member:
                raise _conflict("reference audio is not bound to authorized source revision")
            validate_render_audio(self.data_root,reference_digest)
            reference_audio=artifact_bytes(self.data_root,reference_digest)
        elif kwargs.get("audio_cover_strength") is not None:
            raise ValueError("audio_cover_strength requires reference_artifact_digest")
        selective = requested.get("edit_mode") == "repaint"
        if selective and reference_digest is not None:
            raise _conflict("repaint and style reference cannot be combined before qualification")
        source_pcm = None
        region = None
        if selective:
            if not getattr(synthesize, "supports_repaint", False):
                raise _conflict("Change ONLY This requires a qualified selective renderer")
            if (set(requested) - {"edit_mode", "start_bar", "end_bar",
                                  "target_track_id", "music_length_ms"}):
                raise ValueError("unsupported scoped edit parameters")
            target = requested.get("target_track_id")
            if not isinstance(target, str) or target not in {
                track.get("track_id") for track in current_spec.get("tracks", [])}:
                raise ValueError("repaint target track not found")
            if kwargs.get("song_spec") != current_spec:
                raise _conflict("repaint source SongSpec mismatch")
            source_revision = saved["revision"]
            artifacts = source_revision.get("outputArtifactIds") or []
            if len(artifacts) != 1:
                raise _conflict("repaint requires a single lawful base audio artifact")
            source_pcm = project_audio_bytes(self.data_root, {
                "projectId": project_id, "revisionId": base_revision_id,
                "artifactId": artifacts[0]}, principal_id=principal)
            _, source_frames = read_pcm16_wav(source_pcm)
            region = bar_sample_window(current_spec, requested.get("start_bar"),
                                       requested.get("end_bar"), source_frames)
            if kwargs.get("typed_edit_proposal") is not None:
                from m045_typed_edit_proposal import validate_typed_repaint_proposal
                validated = validate_typed_repaint_proposal(
                    kwargs["typed_edit_proposal"], current_spec, source_frames,
                    region, target)
                if (kwargs["typed_edit_proposal"]["target_scope"]["start_bar"] != requested["start_bar"]
                        or kwargs["typed_edit_proposal"]["target_scope"]["end_bar"] != requested["end_bar"]):
                    raise ValueError("TYPED_EDIT_TARGET_SCOPE_MISMATCH")
            # Section protection is evaluated on canonical integer ticks.
            quarter_ticks = current_spec["timebase"]["ticks_per_quarter_note"]
            first_tick = (requested["start_bar"] - 1) * 4 * quarter_ticks
            final_tick = (requested["end_bar"] - 1) * 4 * quarter_ticks
            for section in current_spec.get("structure", {}).get("sections", []):
                if section.get("sonic_lock") is not True:
                    continue
                a, b = section.get("start_tick"), section.get("end_tick")
                if type(a) is not int or type(b) is not int or b <= a:
                    raise _conflict("locked section has invalid timing")
                if first_tick < b and a < final_tick:
                    raise _conflict("Sonic Lock protects the selected section")
        elif ("target_bar_range" in requested or "target_sample_range" in requested
              or requested.get("edit_mode") is not None):
            raise _conflict("Change ONLY This requires a qualified selective renderer")
        elif kwargs.get("typed_edit_proposal") is not None:
            raise _conflict("typed edit requires qualified scoped repaint")
        if batch_count > 1:
            if selective:
                raise _conflict("multi-take repaint unqualified")
            return self._execute_multi(kwargs,project_id=project_id,
                base_revision_id=base_revision_id,expected_revision_id=expected_revision_id,
                idempotency_key=idempotency_key,model_id=model_id,model_version=model_version,
                synthesize=synthesize,requested=requested,reference_audio=reference_audio,
                reference_digest=reference_digest,reference_strength=reference_strength)
        request_digest = _request_digest(kwargs)
        handle = self._lock(project_id)
        path = self._attempt_path(project_id, idempotency_key)
        try:
            existing = self._load_attempt(path) if path.is_file() else None
            resume = False
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
                if existing.get("state") == AttemptLifecycleState.SUBMISSION_UNCERTAIN.value:
                    raise _conflict("remote submission outcome uncertain; no safe task ID")
                if (existing.get("state") in {AttemptLifecycleState.POLL_INTERRUPTED.value,
                                               AttemptLifecycleState.PREPARING.value}
                        and getattr(synthesize, "supports_remote_resume", False)):
                    stage_resume = self._attempt_dir(project_id) / (existing["attempt_id"] + ".stage")
                    task_file = stage_resume / "upstream-task.json"
                    if not task_file.is_file() or task_file.is_symlink():
                        raise _conflict("durable upstream task identity missing")
                    # When Studio observed the submission, its native attempt also
                    # binds the task identity. Divergence is not a retry signal.
                    anchored_task = existing.get("remote_task")
                    if anchored_task is not None:
                        actual_task = json.loads(task_file.read_text(encoding="utf-8"))
                        if actual_task != anchored_task:
                            raise _conflict("remote task identity tampered")
                    attempt = existing
                    resume = True
                else:
                    raise _conflict("generation attempt is already in progress")

            if not resume:
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
                    "resume_request": {k: kwargs.get(k) for k in (
                        "project_id", "base_revision_id", "expected_current_revision_id",
                        "idempotency_key", "model_id", "model_version", "seed",
                        "song_spec", "prompt", "lyrics", "params",
                        "reference_artifact_digest", "audio_cover_strength",
                        "batch_count", "typed_edit_proposal")},
                    "created_at": time.time(),
                    "updated_at": time.time(),
                    "error_code": None,
                    "artifact_digest": None,
                    "committed_revision_id": None,
                }
                self._save_attempt(path, attempt)
            stage_dir = self._attempt_dir(project_id) / (attempt["attempt_id"] + ".stage")
            stage_dir.mkdir(parents=True, exist_ok=True)
            if getattr(synthesize, "supports_remote_resume", False):
                # Cross the directory durability boundary BEFORE remote submission.
                # Otherwise a durable task file may disappear with its unflushed parent.
                for directory in (stage_dir.parent, stage_dir):
                    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                    try:
                        os.fsync(fd)
                    finally:
                        os.close(fd)
            stage_path = stage_dir / "output.wav"
            synth_params = dict(requested)
            if reference_audio is not None:
                reference_path=stage_dir/"reference-source.wav"
                if reference_path.exists() and reference_path.read_bytes()!=reference_audio:
                    raise _conflict("reference staging identity mismatch")
                if not reference_path.exists():
                    self.atomic_write_fn(reference_path,reference_audio)
                synth_params["_m045_reference"]={
                    "reference_sha256":reference_digest,
                    "audio_cover_strength":float(reference_strength)}
            if region is not None:
                source_path = stage_dir / "repaint-source.wav"
                if source_path.exists() and source_path.read_bytes() != source_pcm:
                    raise _conflict("repaint source staging identity mismatch")
                if not source_path.exists():
                    self.atomic_write_fn(source_path, source_pcm)
                synth_params["_m045_repaint"] = {
                    "start_sample": region[0], "end_sample": region[1],
                    "source_sha256": hashlib.sha256(source_pcm).hexdigest()}
            try:
                result = synthesize(stage_dir, kwargs.get("song_spec"), kwargs.get("prompt"), kwargs.get("lyrics"), int(kwargs.get("seed", 0)), synth_params)
                result_path = Path(result)
                if result_path != stage_path:
                    if not result_path.is_file():
                        raise ValueError("synthesizer did not produce a file")
                    self.atomic_write_fn(stage_path, result_path.read_bytes())
                if not stage_path.is_file():
                    raise ValueError("synthesizer did not produce a WAV")
                if region is not None:
                    from m045_repaint import splice_exact_region
                    merged, preservation = splice_exact_region(
                        source_pcm, stage_path.read_bytes(), region[0], region[1])
                    self.atomic_write_fn(stage_path, merged)
                    receipt_path = stage_dir / "provider-receipt.json"
                    if not receipt_path.is_file():
                        raise ValueError("missing repaint provider provenance")
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                    if receipt.get("preservation_tier") != "P2":
                        raise ValueError("repaint provider must declare P2")
                    receipt.update(preservation)
                    receipt["audio_sha256"] = hashlib.sha256(merged).hexdigest()
                    self.atomic_write_fn(receipt_path, _json_bytes(receipt))
                media = _verify_wav(stage_path)
                receipt_path = stage_dir / "provider-receipt.json"
                if receipt_path.is_file():
                    provenance = json.loads(receipt_path.read_text(encoding="utf-8"))
                    expected_rights = {
                        "EXTERNAL_COMMERCIAL_PROVIDER": "PROVIDER_TERMS_UNVERIFIED",
                        "OPEN_WEIGHT_REMOTE_PROVIDER": "OPEN_WEIGHT_UNVERIFIED_TRAINING_DATA",
                    }
                    origin = provenance.get("source_type")
                    if (origin not in expected_rights
                            or provenance.get("rights_status") != expected_rights[origin]
                            or provenance.get("preservation_tier") != ("P1" if region else "P3")
                            or (region and (provenance.get("preservation_method") !=
                                "EXACT_OUTSIDE_REGION_PCM_SPLICING"
                                or provenance.get("start_sample") != region[0]
                                or provenance.get("end_sample") != region[1]
                                or provenance.get("source_audio_sha256") != hashlib.sha256(source_pcm).hexdigest()))
                            or provenance.get("model_id") != model_id
                            or provenance.get("model_version") != model_version
                            or provenance.get("audio_sha256") != media["sha256"]):
                        raise ValueError("provider provenance mismatch")
                    if origin == "OPEN_WEIGHT_REMOTE_PROVIDER":
                        checkpoint = provenance.get("checkpoint_sha256", "")
                        if (not isinstance(checkpoint, str)
                                or not HEX64.fullmatch(checkpoint)
                                or provenance.get("seed") != int(kwargs.get("seed", 0))):
                            raise ValueError("checkpoint provenance mismatch")
                    if reference_audio is not None:
                        if (provenance.get("reference_artifact_digest")!=reference_digest
                                or provenance.get("reference_strength")!=float(reference_strength)):
                            raise ValueError("reference provenance mismatch")
                    attempt["provenance"] = provenance
                artifact_digest = self.publish_cas_object(stage_path.read_bytes())
                if artifact_digest != media["sha256"] or not HEX64.fullmatch(artifact_digest):
                    raise ValueError("CAS digest mismatch")
                attempt["artifact_digest"] = artifact_digest
                attempt["media"] = media
                attempt["state"] = AttemptLifecycleState.ARTIFACT_DURABLE.value
                self._save_attempt(path, attempt)
            except Exception as exc:
                upstream_path = stage_dir / "upstream-task.json"
                if (getattr(synthesize, "supports_remote_resume", False)
                        and exc.__class__.__name__ == "RemoteSubmissionUncertain"):
                    attempt["state"] = AttemptLifecycleState.SUBMISSION_UNCERTAIN.value
                elif (getattr(synthesize, "supports_remote_resume", False)
                        and upstream_path.is_file() and not upstream_path.is_symlink()
                        and "GENERATION_FAILED" not in str(exc)
                        and "IDENTITY_CONFLICT" not in str(exc)):
                    task_record = json.loads(upstream_path.read_text(encoding="utf-8"))
                    if not isinstance(task_record, dict) or not task_record.get("task_id"):
                        raise _conflict("invalid durable remote task")
                    attempt["remote_task"] = task_record
                    attempt["state"] = AttemptLifecycleState.POLL_INTERRUPTED.value
                else:
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

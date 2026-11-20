#!/usr/bin/env python3
"""S.A.R.A. Sound Forge local studio server — PWA + disk writes + hybrid + vocal lab."""
from __future__ import annotations

import lyric_timeline as lyrics
import io
import wave
import http.server
import json
import math
import os
import socketserver
import struct
import sys
from pathlib import Path
from urllib.parse import unquote

PORT = int(os.environ.get("STUDIO_PORT", "8765"))
ROOT = Path(__file__).resolve().parent.parent
EXPORT_ROOT = ROOT / "workspace" / "studio_exports"

import hashlib
import subprocess
from datetime import datetime, timezone

MANIFEST_LOG_PATH = EXPORT_ROOT / "manifest_registry.json"


# M040: exact-origin admission, per-process capability, immutable export objects.
import secrets
import fcntl
import tempfile
import re
from urllib.parse import urlsplit

try:
    from m045_generation_attempt import AttemptSecurityError, GenerationAttemptOwner
except ImportError:  # pragma: no cover - keeps unrelated tooling importable
    AttemptSecurityError = None
    GenerationAttemptOwner = None

CAPABILITY = secrets.token_urlsafe(32)
LOCAL_PRINCIPAL_ID = "local-studio-user"
SESSION_PRINCIPALS = {}
M045_ATTEMPT_OWNER = None
M045_SYNTHESIZE_TO_STAGE = None
# HVC-003 signing and rights must be configured by the server host, not HTTP.
M045_GRANT_SIGNING_RING = None
M045_GRANT_RIGHTS_POLICY = None
MAX_REQUEST = 64 * 1024 * 1024
MAX_ARTIFACT = 16 * 1024 * 1024

def _principal_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        raise ValueError("invalid principal")
    return value

def issue_studio_session(principal_id=LOCAL_PRINCIPAL_ID):
    principal_id = _principal_id(principal_id)
    token = secrets.token_urlsafe(32)
    SESSION_PRINCIPALS[token] = principal_id
    return token

def resolve_studio_session(token):
    if not isinstance(token, str) or not token:
        raise ProjectConflict("session denied")
    principal_id = SESSION_PRINCIPALS.get(token)
    if principal_id is None:
        raise ProjectConflict("session denied")
    return principal_id


def configure_m045_generation(owner, synthesize_to_stage_fn):
    """Install a host-owned M045 owner and synthesizer; no client fallback exists."""
    global M045_ATTEMPT_OWNER, M045_SYNTHESIZE_TO_STAGE
    M045_ATTEMPT_OWNER = owner
    M045_SYNTHESIZE_TO_STAGE = synthesize_to_stage_fn

def configure_m045_soundtrack_grant(signing_ring, rights_policy):
    """Opt in to lawful Studio→PulseForge issuance using host-owned policy.

    The caller may select an already-accepted revision/artifact but cannot mint
    music rights, trusted signer keys, or ownerless CAS authorization.
    """
    from m045_soundtrack_grant import HostSigningKeyRing
    if not isinstance(signing_ring, HostSigningKeyRing) or not callable(rights_policy):
        raise ValueError("HVC003_HOST_SIGNING_AND_RIGHTS_POLICY_REQUIRED")
    signing_ring.require_active_key()
    global M045_GRANT_SIGNING_RING, M045_GRANT_RIGHTS_POLICY
    M045_GRANT_SIGNING_RING = signing_ring
    M045_GRANT_RIGHTS_POLICY = rights_policy


def make_m045_native_owner(root):
    """Bind M045 to the existing project, session, revision and CAS authorities."""
    if GenerationAttemptOwner is None:
        raise RuntimeError("M045_GENERATION_OWNER_UNAVAILABLE")
    root = Path(root).resolve()

    def authorize(principal_id, pid, capability):
        if capability != "generate":
            return False
        project_owner_directory(root, project_id(pid), principal_id, allow_create=False)
        # The current owner callback contract can only commit for the local
        # principal. Other principals fail closed until principal-bound commits.
        return principal_id == LOCAL_PRINCIPAL_ID

    def read_revision(pid, rid):
        request = {"projectId": project_id(pid)}
        if rid != "CURRENT":
            request["revisionId"] = rid
        try:
            return project_operation(root, request, principal_id=LOCAL_PRINCIPAL_ID)["revision"]
        except (ValueError, FileNotFoundError):
            return None

    def list_revisions(pid):
        pid = project_id(pid)
        directory = project_owner_directory(root, pid, LOCAL_PRINCIPAL_ID, allow_create=False)
        manifest = project_operation(root, {"projectId": pid}, principal_id=LOCAL_PRINCIPAL_ID)["manifest"]
        found = {}
        for path in sorted((directory / "revisions").glob("*.json")):
            revision, _, _ = project_revision(root, directory, pid, path.stem)
            revision = dict(revision)
            revision["is_current"] = (revision["revisionId"] == manifest["currentRevisionId"])
            found[revision["revisionId"]] = revision
        # Consume Studio's lawful historical-render association authority.
        # These receipts are not an alternative CAS owner or current pointer.
        history = directory / "historical-renders"
        if history.is_dir():
            for receipt_file in sorted(history.glob("m045:*.json")):
                receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
                operation_id = (receipt.get("operation") or {}).get("id")
                rid = receipt.get("revisionId")
                if (not isinstance(operation_id, str) or not operation_id.startswith("m045:att_")
                        or receipt_file.name != operation_id + ".json"
                        or receipt.get("projectId") != pid or rid not in found
                        or receipt.get("songSpecDigest") != found[rid]["songSpecDigest"]
                        or receipt.get("productionTimelineDigest") != found[rid]["productionTimelineDigest"]):
                    raise ProjectConflict("M045 historical identity mismatch")
                authorized = project_operation(root, {"projectId": pid, "revisionId": rid},
                                               principal_id=LOCAL_PRINCIPAL_ID)
                authorized_digests = {binding["artifactId"] for binding in
                                      authorized.get("historicalOutputBindings", [])}
                if (not isinstance(receipt.get("artifactIds"), list)
                        or len(receipt["artifactIds"]) != 1
                        or receipt["artifactIds"][0] not in authorized_digests):
                    raise ProjectConflict("M045 historical binding invalid")
                found[rid].setdefault("historicalGenerationAttempts", []).append(operation_id[5:])
        return found

    def publish(data):
        digest = hashlib.sha256(data).hexdigest()
        _publish_cas_exact(root, digest, data)
        return digest

    def commit(**kwargs):
        request = {
            "projectId": kwargs["project_id"],
            "expectedCurrentRevisionId": kwargs["expected_current_revision_id"],
            "songSpec": kwargs["song_spec"],
            "sourceAssetDigests": kwargs.get("source_asset_digests") or [],
            "outputArtifactIds": [kwargs["artifact_digest"]],
            "operationId": "m045:" + kwargs["attempt_id"],
            "operationContext": {"kind": "m045_generation", "attemptId": kwargs["attempt_id"]},
        }
        current = project_operation(root, {"projectId": kwargs["project_id"]},
                                    principal_id=LOCAL_PRINCIPAL_ID)["manifest"]["currentRevisionId"]
        if current != kwargs["expected_current_revision_id"]:
            # Historical renders may bind to an ancestor but never promote it.
            # project_operation verifies ancestry, exact source SongSpec, digest
            # identity, media validity and durable historical association.
            request["operationContext"] = {
                "kind": "render",
                "sourceRevisionId": kwargs["expected_current_revision_id"],
                "attemptId": kwargs["attempt_id"],
            }
        return project_operation(root, request, commit=True, principal_id=LOCAL_PRINCIPAL_ID)

    return GenerationAttemptOwner(
        data_root=root,
        resolve_session_principal=resolve_studio_session,
        authorize_project=authorize,
        read_revision=read_revision,
        list_project_revisions=list_revisions,
        publish_cas_object=publish,
        associate_and_commit_revision=commit,
        atomic_write_fn=atomic_write_bytes,
    )


def configure_m045_from_environment(root):
    """Opt-in authorized providers. Missing credentials never enable generation."""
    providers = {}
    if os.environ.get("ELEVENLABS_API_KEY"):
        from m045_eleven_music_provider import ElevenMusicProvider
        provider = ElevenMusicProvider()
        providers[provider.model_id] = provider
    if os.environ.get("SARA_ACESTEP_ENDPOINT_URL"):
        from m045_acestep_provider import AceStepProvider
        provider = AceStepProvider()
        providers[provider.model_id] = provider
    if not providers:
        return False
    configure_m045_generation(make_m045_native_owner(root), providers)
    return True


def authorized_origin(origin, host):
    if host not in {f"localhost:{PORT}", f"127.0.0.1:{PORT}"} or not origin:
        return False
    try:
        u = urlsplit(origin)
        return (u.scheme == "http" and u.netloc == host and u.hostname in {"localhost", "127.0.0.1"}
                and u.port == PORT and not u.username and not u.password
                and not u.path and not u.query and not u.fragment)
    except (ValueError, TypeError):
        return False

def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def durable_mkdir(path):
    if path.exists():
        if path.is_symlink() or not path.is_dir(): raise ValueError("unsafe directory")
        return
    durable_mkdir(path.parent)
    path.mkdir(mode=0o700)
    sync_dir(path.parent)

def atomic_write_bytes(path, data):
    durable_mkdir(path.parent)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path); sync_dir(path.parent)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def persist_export(root, filename, subdirectory, data):
    root=Path(root).resolve(); durable_mkdir(root)
    fd=os.open(root/".export.lock",os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX)
        return _persist_export_locked(root,filename,subdirectory,data)
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)

def _persist_export_locked(root, filename, subdirectory, data):
    # Friendly names never designate authority and never accept path syntax.
    for value in (filename, subdirectory):
        if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}",value) or value in {".",".."}:
            raise ValueError("invalid export name")
    if len(data)>MAX_ARTIFACT: raise ValueError("artifact too large")
    root=Path(root).resolve(); durable_mkdir(root)
    digest=hashlib.sha256(data).hexdigest()
    directory=root/"objects"/digest[:2]; durable_mkdir(directory)
    obj=directory/digest
    if obj.exists():
        if obj.is_symlink() or obj.read_bytes()!=data: raise ValueError("immutable object corruption")
    else:
        atomic_write_bytes(obj,data)
    ledger_path=root/"manifest_registry.json"
    registry=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    if not isinstance(registry,list): raise ValueError("invalid existing ledger")
    row={"timestamp":datetime.now(timezone.utc).isoformat(),"filename":filename,"subdirectory":subdirectory,
         "absolute_path":str(obj),"sha256_checksum":"sha256:"+digest,"bytes_written":len(data)}
    registry.append(row)
    atomic_write_bytes(ledger_path,json.dumps(registry,indent=2).encode())
    # Pointer changes only after object and ledger have crossed durability barriers.
    alias_dir=root/"aliases"/subdirectory; durable_mkdir(alias_dir)
    alias=alias_dir/(filename+".json")
    atomic_write_bytes(alias,json.dumps({"sha256":digest,"object_path":str(obj)}).encode())
    return {"status":"SUCCESS","saved_at":str(obj),"alias_at":str(alias),"sha256":digest,"bytes":len(data)}


# M042: one durable project pointer, immutable revision history and fenced saves.
class ProjectConflict(ValueError):
    pass


def project_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def project_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ValueError("invalid projectId")
    return value


def authorize_project_owner(directory, pid, principal_id, create=False):
    principal_id = _principal_id(principal_id)
    owner_path = directory / "ProjectOwner.json"
    if owner_path.is_symlink():
        raise ValueError("unsafe project owner path")
    if owner_path.exists():
        owner = json.loads(owner_path.read_text())
        if owner != {"projectId": pid, "principalId": principal_id, "formatVersion": 1}:
            raise ProjectConflict("project principal denied")
        return principal_id
    # Existing pre-auth projects may be adopted only by the historical local
    # Studio principal. Named/multi-user principals cannot claim unowned state.
    if not create and principal_id != LOCAL_PRINCIPAL_ID:
        raise ProjectConflict("project principal denied")
    atomic_write_bytes(owner_path, project_json({
        "projectId": pid, "principalId": principal_id, "formatVersion": 1
    }))
    return principal_id


def project_owner_directory(root, pid, principal_id, allow_create=False):
    """Serialize and recover immutable first-owner establishment.

    .owner-claims contains recovery intent only. It never selects revisions,
    artifacts, currentness, or project content.
    """
    principal_id = _principal_id(principal_id)
    projects = root / "projects"
    durable_mkdir(projects)
    fd = os.open(projects / ".owner-create.lock",
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        claims = projects / ".owner-claims"
        durable_mkdir(claims)
        claim_path = claims / (pid + ".json")
        if claim_path.is_symlink():
            raise ValueError("unsafe owner claim path")
        directory = projects / pid
        existed = directory.is_dir()
        owner_path = directory / "ProjectOwner.json"

        claim = None
        if claim_path.exists():
            claim = json.loads(claim_path.read_text())
            expected_claim = {"projectId": pid, "principalId": principal_id, "formatVersion": 1}
            if claim != expected_claim:
                raise ProjectConflict("project owner claim denied")

        if not existed:
            if not allow_create:
                raise ValueError("unknown project")
            if claim is None:
                claim = {"projectId": pid, "principalId": principal_id, "formatVersion": 1}
                atomic_write_bytes(claim_path, project_json(claim))
            durable_mkdir(directory)
            authorize_project_owner(directory, pid, principal_id, create=True)
        elif owner_path.exists():
            authorize_project_owner(directory, pid, principal_id, create=False)
        elif claim is not None:
            # Same principal resumes an interrupted first-owner transaction.
            authorize_project_owner(directory, pid, principal_id, create=True)
        else:
            # Preserve fail-closed legacy policy: only LOCAL_PRINCIPAL_ID may
            # adopt an existing ownerless pre-auth project.
            authorize_project_owner(directory, pid, principal_id, create=False)

        owner = json.loads(owner_path.read_text())
        expected_owner = {"projectId": pid, "principalId": principal_id, "formatVersion": 1}
        if owner != expected_owner:
            raise ProjectConflict("project principal denied")

        if claim_path.exists():
            stored_claim = json.loads(claim_path.read_text())
            if stored_claim != expected_owner:
                raise ProjectConflict("project owner claim mismatch")
            claim_path.unlink()
            sync_dir(claims)
        return directory
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def artifact_bytes(root, digest):
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("invalid artifact digest")
    path = root / "objects" / digest[:2] / digest
    if path.is_symlink() or not path.is_file():
        raise ValueError("referenced artifact unavailable")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("referenced artifact corruption")
    return data


def project_boundary(name):
    """Internal fault-injection seam; not controllable by HTTP callers."""
    pass


def project_namespace_fence(path, boundary):
    # Existing-but-unflushed directories from a killed earlier process also count.
    while True:
        sync_dir(path)
        if path == boundary: break
        if path == path.parent: raise ValueError("namespace boundary escaped")
        path = path.parent


def project_artifact_fence(root, digest):
    artifact_bytes(root, digest)
    path = root / "objects" / digest[:2] / digest
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)
    project_namespace_fence(path.parent, root.parent)


def lyric_read(root, digest):
    """Authenticate the full immutable lyric/evidence/audio chain on every reopen."""
    doc = json.loads(artifact_bytes(root, digest))
    current = doc; refs = [digest]; seen = set()
    for _ in range(128):
        ident = current['revisionId']
        if ident in seen: raise ValueError("cyclic lyric ancestry")
        seen.add(ident)
        source = current['sourceArtifactId']; evidence = current['evidenceArtifactId']
        lyrics.validate(current, artifact_bytes(root, source), json.loads(artifact_bytes(root, evidence)))
        refs += [source, evidence]
        parent = current['parentArtifactId']
        if parent is None:
            if current['parentRevisionId'] is not None or current['correctionHistory']:
                raise ValueError("invalid initial lyric ancestry")
            return doc, list(set(refs))
        old = json.loads(artifact_bytes(root, parent)); refs.append(parent)
        if old['revisionId'] != current['parentRevisionId']: raise ValueError("lyric parent mismatch")
        delta = current['correctionHistory'][-1]
        expected = lyrics.correction(old, parent,
                    [{'wordId': c['wordId'], 'text': c['after']} for c in delta['changes']],
                    delta['actor'], delta['reason'])
        if expected != current: raise ValueError("invalid correction lineage")
        current = old
    raise ValueError("lyric history limit reached")


def project_result(root, manifest, revision, spec, timeline):
    result = {"status": "SUCCESS", "manifest": manifest, "revision": revision,
              "songSpec": spec, "productionTimeline": timeline}
    if revision.get('lyricTimelineDigest'):
        result['lyricTimeline'] = lyric_read(root, revision['lyricTimelineDigest'])[0]
    return result


def project_revision(root, directory, pid, rid):
    if not isinstance(rid, str) or not re.fullmatch(r"[a-f0-9]{64}", rid):
        raise ValueError("invalid revisionId")
    path = directory / "revisions" / (rid + ".json")
    if path.is_symlink(): raise ValueError("unsafe revision path")
    revision = json.loads(path.read_text())
    core = {k: v for k, v in revision.items() if k != "revisionId"}
    if revision.get("projectId") != pid or revision.get("revisionId") != rid or hashlib.sha256(project_json(core)).hexdigest() != rid:
        raise ValueError("revision identity mismatch")
    spec = json.loads(artifact_bytes(root, revision["songSpecDigest"]))
    timeline = json.loads(artifact_bytes(root, revision["productionTimelineDigest"]))
    if timeline["songSpecDigest"] != revision["songSpecDigest"]:
        raise ValueError("timeline source mismatch")
    for aid in revision["sourceAssetDigests"] + revision["outputArtifactIds"]:
        artifact_bytes(root, aid)
    if revision.get("lyricTimelineDigest"):
        doc, _ = lyric_read(root, revision["lyricTimelineDigest"])
        if doc["sourceArtifactId"] not in revision["sourceAssetDigests"]:
            raise ValueError("lyric audio not bound to project")
    return revision, spec, timeline


def validate_render_audio_bytes(data):
    if (len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE"
            or struct.unpack_from("<I", data, 4)[0] + 8 != len(data)):
        raise ValueError("invalid render WAV container")
    offset = 12
    format_seen = False
    data_seen = False
    block_align = None
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("truncated WAV chunk header")
        kind = data[offset:offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        start = offset + 8
        end = start + size
        if end > len(data):
            raise ValueError("truncated WAV chunk")
        if kind == b"fmt ":
            if format_seen or size < 16:
                raise ValueError("invalid WAV format chunk")
            encoding, channels, rate, byte_rate, block_align, bits = struct.unpack_from("<HHIIHH", data, start)
            if (encoding != 1 or channels not in (1, 2) or bits != 16
                    or not 8000 <= rate <= 192000 or block_align != channels * 2
                    or byte_rate != rate * block_align):
                raise ValueError("invalid WAV PCM metadata")
            format_seen = True
        elif kind == b"data":
            if not format_seen or data_seen or not size or size % block_align:
                raise ValueError("invalid WAV PCM frame alignment")
            data_seen = True
        offset = end + (size & 1)
    if offset != len(data) or not data_seen:
        raise ValueError("invalid WAV chunk layout")
    try:
        with wave.open(io.BytesIO(data), "rb") as audio:
            channels, width, rate, frames = (audio.getnchannels(), audio.getsampwidth(),
                                             audio.getframerate(), audio.getnframes())
            if (audio.getcomptype() != "NONE" or channels not in (1, 2)
                    or width != 2 or rate <= 0 or frames <= 0):
                raise ValueError("unsupported render PCM format")
            if len(audio.readframes(frames)) != frames * channels * width:
                raise ValueError("truncated render PCM")
    except (wave.Error, EOFError) as error:
        raise ValueError("invalid render WAV") from error



def validate_render_audio(root, digest):
    data = artifact_bytes(root, digest)
    validate_render_audio_bytes(data)


def _render_operation_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        raise ValueError("invalid render operationId")
    return value


def _render_data_bytes(raw):
    if type(raw) is bytes:
        return raw  # Trusted server-internal media only; JSON cannot supply bytes.
    if isinstance(raw, list) and all(type(v) is int and 0 <= v <= 255 for v in raw):
        return bytes(raw)
    raise ValueError("render data_bytes must be byte list or trusted bytes")


def render_authoritative_revision_bytes(spec):
    completed = subprocess.run(
        ["node", str(ROOT / "tools" / "render_revision.cjs")],
        input=project_json(spec),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        timeout=90,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout:
        raise ValueError("authoritative revision render failed")
    if len(completed.stdout) > MAX_ARTIFACT:
        raise ValueError("artifact too large")
    validate_render_audio_bytes(completed.stdout)
    return completed.stdout


def _assert_revision_in_history(root, directory, pid, manifest, rid):
    ancestor = manifest["currentRevisionId"]
    seen = set()
    while ancestor != rid:
        if ancestor is None or ancestor in seen:
            raise ProjectConflict("render source is outside committed history")
        seen.add(ancestor)
        prior, _, _ = project_revision(root, directory, pid, ancestor)
        ancestor = prior["parentRevisionId"]
    return project_revision(root, directory, pid, rid)


def _render_commit_request(root, directory, pid, attempt):
    revision, spec, _ = project_revision(root, directory, pid, attempt["sourceRevisionId"])
    request = {
        "projectId": pid,
        "expectedCurrentRevisionId": attempt["sourceRevisionId"],
        "songSpec": spec,
        "sourceAssetDigests": revision["sourceAssetDigests"],
        "outputArtifactIds": [attempt["artifactDigest"]],
        "operationId": attempt["operationId"],
        "operationContext": {"kind": "render", "sourceRevisionId": attempt["sourceRevisionId"]},
    }
    if attempt.get("masterProvenance") is not None:
        request["operationContext"]["masterProvenance"] = attempt["masterProvenance"]
    meaning = {k: v for k, v in request.items() if k != "operationId"}
    if hashlib.sha256(project_json(meaning)).hexdigest() != attempt["operationMeaningDigest"]:
        raise ValueError("render attempt meaning mismatch")
    return request


def _historical_receipt_from_attempt(root, directory, pid, attempt):
    revision, _, _ = project_revision(root, directory, pid, attempt["sourceRevisionId"])
    return {
        "operation": {"id": attempt["operationId"], "meaningDigest": attempt["operationMeaningDigest"]},
        "projectId": pid,
        "revisionId": attempt["sourceRevisionId"],
        "artifactIds": [attempt["artifactDigest"]],
        "songSpecDigest": revision["songSpecDigest"],
        "productionTimelineDigest": revision["productionTimelineDigest"],
    }


def _write_render_attempt(path, attempt):
    atomic_write_bytes(path, project_json(attempt))
    project_namespace_fence(path.parent, path.parents[3])


def _publish_cas_exact(root, digest, data):
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("render digest mismatch")
    directory = root / "objects" / digest[:2]
    durable_mkdir(directory)
    obj = directory / digest
    if obj.exists():
        if obj.is_symlink() or obj.read_bytes() != data:
            raise ValueError("immutable object corruption")
    else:
        atomic_write_bytes(obj, data)
    project_artifact_fence(root, digest)
    return obj


def reconcile_render_attempts(root, directory, pid, manifest):
    attempts = directory / "render-attempts"
    if not attempts.is_dir():
        return
    history = directory / "historical-renders"
    for path in sorted(attempts.glob("*.json")):
        attempt = json.loads(path.read_text())
        required = {
            "operationId", "projectId", "sourceRevisionId", "artifactDigest",
            "intendedCas", "byteLength", "songSpecDigest",
            "productionTimelineDigest", "operationMeaningDigest", "state"
        }
        if not required <= set(attempt):
            raise ValueError("incomplete render attempt")
        if (attempt["projectId"] != pid
                or path.name != attempt["operationId"] + ".json"
                or attempt["intendedCas"] != f"objects/{attempt['artifactDigest'][:2]}/{attempt['artifactDigest']}"):
            raise ValueError("render attempt identity mismatch")
        revision, _, _ = _assert_revision_in_history(
            root, directory, pid, manifest, attempt["sourceRevisionId"])
        if (revision["songSpecDigest"] != attempt["songSpecDigest"]
                or revision["productionTimelineDigest"] != attempt["productionTimelineDigest"]):
            raise ValueError("render attempt source mismatch")
        state = attempt["state"]
        cas = root / attempt["intendedCas"]
        if state == "VALIDATED_NOT_PUBLISHED":
            # Crash after atomic CAS publication but before state advancement is
            # recoverable only because exact CAS identity was already durable.
            if not cas.exists():
                continue
            data = artifact_bytes(root, attempt["artifactDigest"])
            if len(data) != attempt["byteLength"]:
                raise ValueError("render attempt byte length mismatch")
            validate_render_audio_bytes(data)
            project_artifact_fence(root, attempt["artifactDigest"])
            attempt["state"] = "ARTIFACT_DURABLE"
            _write_render_attempt(path, attempt)
            state = "ARTIFACT_DURABLE"
        if state == "ARTIFACT_DURABLE":
            data = artifact_bytes(root, attempt["artifactDigest"])
            if len(data) != attempt["byteLength"]:
                raise ValueError("render attempt byte length mismatch")
            validate_render_audio_bytes(data)
            project_artifact_fence(root, attempt["artifactDigest"])
            # Do not invent a successor for a render whose source is still current.
            # The exact caller may replay that operation; open-time recovery is only
            # for historical source revisions.
            if attempt["sourceRevisionId"] == manifest["currentRevisionId"]:
                continue
            receipt = _historical_receipt_from_attempt(root, directory, pid, attempt)
            durable_mkdir(history)
            destination = history / (attempt["operationId"] + ".json")
            encoded = project_json(receipt)
            if destination.exists() and destination.read_bytes() != encoded:
                raise ProjectConflict("historical render recovery conflict")
            if not destination.exists():
                atomic_write_bytes(destination, encoded)
            attempt["state"] = "HISTORICALLY_BOUND"
            _write_render_attempt(path, attempt)
            state = "HISTORICALLY_BOUND"
        if state == "HISTORICALLY_BOUND":
            receipt = _historical_receipt_from_attempt(root, directory, pid, attempt)
            destination = history / (attempt["operationId"] + ".json")
            if not destination.is_file() or destination.read_bytes() != project_json(receipt):
                raise ValueError("historical render binding missing")
        elif state not in {"VALIDATED_NOT_PUBLISHED", "ARTIFACT_DURABLE", "REVISION_BOUND"}:
            raise ValueError("unknown render attempt state")


def render_publish_operation(root, request, principal_id=LOCAL_PRINCIPAL_ID, master_provenance=None):
    root = Path(root).resolve()
    pid = project_id(request.get("projectId"))
    operation_id = _render_operation_id(request.get("operationId"))
    source_revision = request.get("sourceRevisionId")
    filename = request.get("filename", "m044.wav")
    subdirectory = request.get("subdirectory", "m044")
    for value in (filename, subdirectory):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
            raise ValueError("invalid export name")
    directory = project_owner_directory(
        root, pid, principal_id, allow_create=False)
    lock = os.open(directory / ".render.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        manifest_path = directory / "ProjectManifest.json"
        if not manifest_path.is_file():
            raise ValueError("project has no committed revision")
        manifest = json.loads(manifest_path.read_text())
        revision, spec, _ = _assert_revision_in_history(
            root, directory, pid, manifest, source_revision)
        raw_data = request.get("data_bytes")
        data = (render_authoritative_revision_bytes(spec)
                if raw_data is None else _render_data_bytes(raw_data))
        if len(data) > MAX_ARTIFACT:
            raise ValueError("artifact too large")
        validate_render_audio_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        if master_provenance is not None:
            from m045_wave4_mastering_provenance import CanonicalProvenanceRecord
            if not isinstance(master_provenance, CanonicalProvenanceRecord):
                raise ValueError("MASTER_PROVENANCE_TYPE_DENIED")
            master_provenance.validate()
            # Physical PCM identity and lawful source binding must match the
            # claimed provenance, not a client/path/digest-only assertion.
            with wave.open(io.BytesIO(data), "rb") as verified_pcm:
                true_pcm_hash = hashlib.sha256(
                    verified_pcm.readframes(verified_pcm.getnframes())).hexdigest()
            if true_pcm_hash != master_provenance.pcm_sha256:
                raise ValueError("MASTER_PCM_PROVENANCE_MISMATCH")
            project_audio_bytes(root, {"projectId":pid,
                "revisionId":source_revision,
                "artifactId":master_provenance.parent_artifact_sha256s[0]},
                principal_id=principal_id)
            if (master_provenance.artifact_sha256 != digest
                    or master_provenance.project_id != pid
                    or master_provenance.revision_id != source_revision
                    or master_provenance.rights_status != "UNVERIFIED_HELD"
                    or master_provenance.origin_type != "DSP_TRANSFORM"
                    or master_provenance.parent_artifact_sha256s[0] == digest):
                raise ValueError("MASTER_PROVENANCE_MISMATCH")
            provenanced = master_provenance.to_dict()
        else:
            provenanced = None
        commit_request = {
            "projectId": pid,
            "expectedCurrentRevisionId": source_revision,
            "songSpec": spec,
            "sourceAssetDigests": revision["sourceAssetDigests"],
            "outputArtifactIds": [digest],
            "operationId": operation_id,
            "operationContext": {"kind": "render", "sourceRevisionId": source_revision},
        }
        if provenanced is not None:
            commit_request["operationContext"]["masterProvenance"] = provenanced
        meaning = {k: v for k, v in commit_request.items() if k != "operationId"}
        meaning_digest = hashlib.sha256(project_json(meaning)).hexdigest()
        attempts = directory / "render-attempts"
        staging = directory / "render-staging"
        durable_mkdir(attempts)
        durable_mkdir(staging)
        attempt_path = attempts / (operation_id + ".json")
        staging_path = staging / (operation_id + ".wav")
        identity = {
            "operationId": operation_id,
            "projectId": pid,
            "sourceRevisionId": source_revision,
            "artifactDigest": digest,
            "intendedCas": f"objects/{digest[:2]}/{digest}",
            "byteLength": len(data),
            "songSpecDigest": revision["songSpecDigest"],
            "productionTimelineDigest": revision["productionTimelineDigest"],
            "operationMeaningDigest": meaning_digest,
            "filename": filename,
            "subdirectory": subdirectory,
        }
        if provenanced is not None:
            identity["masterProvenance"] = provenanced
        if attempt_path.exists():
            attempt = json.loads(attempt_path.read_text())
            for key, value in identity.items():
                if attempt.get(key) != value:
                    raise ProjectConflict("render attempt identity conflict")
            if not staging_path.is_file() or staging_path.read_bytes() != data:
                raise ProjectConflict("render staging identity conflict")
        else:
            atomic_write_bytes(staging_path, data)
            attempt = {**identity, "state": "VALIDATED_NOT_PUBLISHED"}
            _write_render_attempt(attempt_path, attempt)
        if attempt["state"] == "VALIDATED_NOT_PUBLISHED":
            project_boundary("render_attempt_validated_not_published")
            staged = staging_path.read_bytes()
            if hashlib.sha256(staged).hexdigest() != digest:
                raise ValueError("render staging corruption")
            _publish_cas_exact(root, digest, staged)
            project_boundary("render_attempt_cas_published_before_state")
            attempt["state"] = "ARTIFACT_DURABLE"
            _write_render_attempt(attempt_path, attempt)
        if attempt["state"] == "ARTIFACT_DURABLE":
            project_boundary("render_attempt_artifact_durable")
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        os.close(lock)

    result = project_operation(root, _render_commit_request(root, directory, pid, attempt), commit=True, principal_id=principal_id)

    lock = os.open(directory / ".render.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        attempt = json.loads(attempt_path.read_text())
        if result["revision"]["revisionId"] == source_revision and result["manifest"]["currentRevisionId"] != source_revision:
            if attempt["state"] != "HISTORICALLY_BOUND":
                # project_operation/open-time reconciliation owns historical binding.
                reconcile_render_attempts(root, directory, pid, result["manifest"])
                attempt = json.loads(attempt_path.read_text())
            if attempt["state"] != "HISTORICALLY_BOUND":
                raise ValueError("historical render did not bind")
            project_boundary("render_attempt_historically_bound")
        else:
            attempt["state"] = "REVISION_BOUND"
            _write_render_attempt(attempt_path, attempt)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        os.close(lock)
    return result


def render_authorized_scratch_operation(root, request, principal_id=LOCAL_PRINCIPAL_ID):
    """Studio-owned scratch render using only lawful revision/CAS association."""
    from m045_scratch_dsp import render_scratch_mix, waveform_pcm
    if not isinstance(request,dict):
        raise ValueError("scratch request required")
    pid=project_id(request.get("projectId"))
    rid=request.get("revisionId")
    base_id=request.get("baseArtifactId")
    refs=request.get("sampleAssetDigests")
    selected=project_operation(root,{"projectId":pid,"revisionId":rid},principal_id=principal_id)
    revision=selected["revision"]
    spec=selected["songSpec"]
    if not isinstance(refs,dict) or not isinstance(base_id,str):
        raise ValueError("invalid scratch artifact references")
    base=project_audio_bytes(root,{"projectId":pid,"revisionId":rid,"artifactId":base_id},principal_id=principal_id)
    waveform_pcm(base)
    tracks=[t for t in spec["tracks"] if t.get("track_id")=="dj_scratch"]
    if len(tracks)!=1 or tracks[0].get("muted") is True:
        raise ProjectConflict("no active scratch track")
    events=tracks[0]["events"]
    if not events or len(events)>128:
        raise ValueError("scratch marker count unavailable")
    validate_dj_scratch_authority(spec)
    if set(refs)!={event["event_id"] for event in events}:
        raise ProjectConflict("scratch source map does not match source revision")
    bpm=spec["timebase"]["initial_bpm"]
    window=(2*480*60*44100+bpm*960)//(2*bpm*960)
    if not 0<window<=44100*8:
        raise ValueError("scratch window unsupported")
    performances=[]
    for marker in events:
        digest=refs[marker["event_id"]]
        if not isinstance(digest,str) or not re.fullmatch("[a-f0-9]{64}",digest):
            raise ValueError("invalid scratch source digest")
        if digest not in revision["sourceAssetDigests"]:
            raise ProjectConflict("scratch source not attached to authorized revision")
        data=artifact_bytes(Path(root).resolve(),digest)
        waveform_pcm(data)
        performances.append({"marker":marker,"sample_asset_wav":data,
                             "source_asset_digest":digest})
    output,proof=render_scratch_mix(base,performances,window_frames=window)
    identity={"schema":"sara.scratch.render.v1","sourceRevisionId":rid,
        "baseArtifactId":base_id,
        "sourceAssetDigests":{k:refs[k] for k in sorted(refs)}}
    op="scratch:"+hashlib.sha256(project_json(identity)).hexdigest()[:48]
    published=render_publish_operation(root,{"projectId":pid,"sourceRevisionId":rid,
        "operationId":op,"filename":"scratch-render.wav","subdirectory":"scratch",
        "data_bytes":list(output)},principal_id=principal_id)
    selected_revision=published["revision"]["revisionId"]
    digest=hashlib.sha256(output).hexdigest()
    readback=project_audio_bytes(root,{"projectId":pid,"revisionId":selected_revision,
                                      "artifactId":digest},principal_id=principal_id)
    if readback!=output:
        raise ValueError("scratch render readback mismatch")
    return {"projectId":pid,"sourceRevisionId":rid,"revisionId":selected_revision,
            "artifactId":digest,"proof":proof,"operationId":op}


def project_audio_bytes(root, request, principal_id=LOCAL_PRINCIPAL_ID):
    root = Path(root).resolve()
    pid = project_id(request.get("projectId"))
    rid = request.get("revisionId")
    digest = request.get("artifactId")
    directory = project_owner_directory(
        root, pid, principal_id, allow_create=False)
    manifest_path = directory / "ProjectManifest.json"
    if not manifest_path.is_file():
        raise ValueError("unknown project")
    manifest = json.loads(manifest_path.read_text())
    revision, _, _ = _assert_revision_in_history(root, directory, pid, manifest, rid)
    allowed = set(revision.get("outputArtifactIds", []))
    history = directory / "historical-renders"
    if history.is_dir():
        for path in sorted(history.glob("*.json")):
            receipt = json.loads(path.read_text())
            if receipt.get("projectId") == pid and receipt.get("revisionId") == rid:
                allowed.update(receipt.get("artifactIds", []))
    if digest not in allowed:
        raise ProjectConflict("artifact is not lawfully bound to requested revision")
    validate_render_audio(root, digest)
    return artifact_bytes(root, digest)

def reconcile_historical_renders(root, directory, pid, manifest):
    # Pending records carry ownership. Never infer it from unassociated CAS bytes.
    pending = directory / "pending-renders"
    for path in sorted(pending.glob("*.json")):
        receipt = json.loads(path.read_text())
        rid = receipt["revisionId"]
        ancestor = manifest["currentRevisionId"]
        seen = set()
        while ancestor != rid:
            if ancestor is None or ancestor in seen:
                raise ValueError("pending render source outside committed history")
            seen.add(ancestor)
            prior, _, _ = project_revision(root, directory, pid, ancestor)
            ancestor = prior["parentRevisionId"]
        revision, _, _ = project_revision(root, directory, pid, rid)
        if (receipt["projectId"] != pid
                or receipt["songSpecDigest"] != revision["songSpecDigest"]
                or receipt["productionTimelineDigest"] != revision["productionTimelineDigest"]
                or path.name != receipt["operation"]["id"] + ".json"):
            raise ValueError("pending render identity mismatch")
        for digest in receipt["artifactIds"]:
            validate_render_audio(root, digest)
            project_artifact_fence(root, digest)
        history = directory / "historical-renders"
        durable_mkdir(history)
        destination = history / path.name
        encoded = project_json(receipt)
        if destination.exists() and destination.read_bytes() != encoded:
            raise ProjectConflict("historical render recovery conflict")
        if not destination.exists():
            atomic_write_bytes(destination, encoded)
        path.unlink()
        sync_dir(pending)


def historical_result(root, directory, manifest, revision, spec, timeline):
    result = project_result(root, manifest, revision, spec, timeline)
    bindings = []
    for path in sorted((directory / "historical-renders").glob("*.json")):
        receipt = json.loads(path.read_text())
        if receipt["revisionId"] == revision["revisionId"]:
            for aid in receipt["artifactIds"]:
                validate_render_audio(root, aid)
                bindings.append({"artifactId": aid, "revisionId": revision["revisionId"],
                                 "songSpecDigest": revision["songSpecDigest"],
                                 "productionTimelineDigest": revision["productionTimelineDigest"]})
    if bindings:
        result["historicalOutputBindings"] = bindings
    return result


def validate_dj_scratch_authority(spec, prior=None):
    """Validate editable DJ markers against canonical ScoreCore clock and locks."""
    tracks=spec.get("tracks", [])
    dj=[t for t in tracks if t.get("track_id")=="dj_scratch"]
    if len(dj)>1 or (dj and dj[0].get("type")!="DJ"):
        raise ValueError("invalid DJ track identity")
    for track in tracks:
        if track.get("track_id")!="dj_scratch" and any(
                e.get("type")=="DJ_SCRATCH_MARKER" for e in track.get("events",[])):
            raise ValueError("DJ marker outside canonical track")
    if dj:
        tb=spec.get("timebase",{})
        bpm=tb.get("initial_bpm")
        if (tb.get("meter")!="4/4" or tb.get("sample_rate")!=44100
                or tb.get("ticks_per_quarter_note")!=960
                or type(bpm) is not int or not 60<=bpm<=180):
            raise ValueError("DJ source clock unsupported")
        sections=spec["structure"]["sections"]
        if len(dj[0].get("events",[]))>4096:
            raise ValueError("DJ marker count exceeds capacity")
        identities=set()
        for e in dj[0].get("events",[]):
            if (not isinstance(e,dict)
                    or set(e)!={"type","event_id","tick","duration_ticks","deck",
                                "technique","sample_index","audio_status"}
                    or e["type"]!="DJ_SCRATCH_MARKER"
                    or type(e["tick"]) is not int or e["tick"]<0
                    or e["duration_ticks"]!=480
                    or e["technique"] not in ("baby","chirp","2_click_flare","two_deck_juggle")
                    or e["deck"] not in ("A","B")
                    or e["audio_status"]!="UNRENDERED_SOURCE_ASSET_REQUIRED"):
                raise ValueError("invalid DJ marker")
            members=[sec for sec in sections if
                 type(sec.get("start_tick")) is int and type(sec.get("end_tick")) is int
                 and sec["start_tick"]<=e["tick"]<sec["end_tick"]
                 and (e["tick"]-sec["start_tick"])%480==0
                 and e["tick"]<sec["start_tick"]+16*480]
            if len(members)!=1:
                raise ValueError("DJ marker off section beat grid")
            expected_id=f'dj:{members[0]["id"]}:{e["tick"]}:{e["deck"]}'
            samples=(2*e["tick"]*60*44100+bpm*960)//(2*bpm*960)
            if (e["event_id"]!=expected_id or e["sample_index"]!=samples
                    or type(e["sample_index"]) is not int or expected_id in identities):
                raise ValueError("DJ marker identity or sample clock mismatch")
            identities.add(expected_id)
    if prior is not None:
        old_tracks={t.get("track_id"):t for t in prior.get("tracks",[])}
        new_tracks={t.get("track_id"):t for t in tracks}
        for track_id,old in old_tracks.items():
            if old.get("sonic_lock") is True:
                current=new_tracks.get(track_id)
                if current is None or current.get("events")!=old.get("events"):
                    raise ProjectConflict("Sonic Lock protects symbolic events")
        before=(old_tracks.get("dj_scratch") or {}).get("events",[])
        after=(new_tracks.get("dj_scratch") or {}).get("events",[])
        before_ids={x.get("event_id"):x for x in before}
        after_ids={x.get("event_id"):x for x in after}
        locked=[sec for sec in prior.get("structure",{}).get("sections",[])
                if sec.get("sonic_lock") is True]
        for sec in locked:
            first,last=sec.get("start_tick"),sec.get("end_tick")
            if type(first) is not int or type(last) is not int or first>=last:
                raise ProjectConflict("invalid Sonic Lock section clock")
            old_region={k:v for k,v in before_ids.items() if first<=v["tick"]<last}
            new_region={k:v for k,v in after_ids.items() if first<=v["tick"]<last}
            if old_region!=new_region:
                raise ProjectConflict("Sonic Lock protects DJ region")


def project_operation(root, request, commit=False, lyric=False, principal_id=LOCAL_PRINCIPAL_ID):
    import uuid
    root = Path(root).resolve()
    pid = request.get("projectId")
    if pid is None:
        if not commit or request.get("expectedCurrentRevisionId") is not None:
            raise ValueError("projectId required")
        pid = uuid.uuid4().hex
    pid = project_id(pid)
    directory = project_owner_directory(
        root, pid, principal_id, allow_create=commit)
    fd = os.open(directory / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        path = directory / "ProjectManifest.json"
        if path.is_symlink(): raise ValueError("unsafe manifest path")
        manifest = json.loads(path.read_text()) if path.exists() else None
        current = manifest["currentRevisionId"] if manifest else None
        if manifest and (manifest.get("projectId") != pid or manifest.get("formatVersion") != 1):
            raise ValueError("invalid project manifest")
        if manifest:
            reconcile_render_attempts(root, directory, pid, manifest)
            reconcile_historical_renders(root, directory, pid, manifest)
        if not commit:
            if not manifest: raise ValueError("project has no committed revision")
            rid = request.get("revisionId") or current
            ancestor, seen = current, set()
            while ancestor != rid:
                if ancestor is None or ancestor in seen:
                    raise ValueError("revision is not in committed project history")
                seen.add(ancestor)
                previous, _, _ = project_revision(root, directory, pid, ancestor)
                ancestor = previous["parentRevisionId"]
            revision, spec, timeline = project_revision(root, directory, pid, rid)
            return historical_result(root, directory, manifest, revision, spec, timeline)
        operation = None
        if request.get('operationId') is not None:
            if lyric or not isinstance(request['operationId'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', request['operationId']):
                raise ValueError('invalid operationId')
            if not pid or request.get('expectedCurrentRevisionId') is None:
                raise ValueError('operation requires an existing revision')
            meaning = {k: v for k, v in request.items() if k != 'operationId'}
            operation = {'id': request['operationId'], 'meaningDigest': hashlib.sha256(project_json(meaning)).hexdigest()}
            # The receipt lives in the existing immutable revision chain. No
            # side ledger or second pointer can independently select an outcome.
            history = directory / "historical-renders"
            receipt_path = history / (operation["id"] + ".json")
            if receipt_path.exists():
                receipt = json.loads(receipt_path.read_text())
                if receipt["operation"] != operation:
                    raise ProjectConflict("operation identity payload conflict")
                prior, prior_spec, prior_timeline = project_revision(root, directory, pid, receipt["revisionId"])
                return historical_result(root, directory, manifest, prior, prior_spec, prior_timeline)
            context = request.get("operationContext")
            render = isinstance(context, dict) and context.get("kind") == "render"
            captured = request["expectedCurrentRevisionId"]
            if render and context.get("sourceRevisionId") != captured:
                raise ProjectConflict("render revision identity mismatch")
            source = None
            ancestor, seen = current, set()
            while ancestor:
                if ancestor in seen: raise ValueError('cyclic project history')
                seen.add(ancestor)
                prior, prior_spec, prior_timeline = project_revision(root, directory, pid, ancestor)
                receipt = prior.get('operation')
                if receipt and receipt['id'] == operation['id']:
                    if receipt != operation: raise ProjectConflict('operation identity payload conflict')
                    return project_result(root, manifest, prior, prior_spec, prior_timeline)
                if render and ancestor == captured:
                    source = prior, prior_spec, prior_timeline
                ancestor = prior['parentRevisionId']
            if render:
                if source is None:
                    raise ProjectConflict("render source is outside committed history")
                prior, prior_spec, prior_timeline = source
                outputs = request.get("outputArtifactIds")
                if (request.get("songSpec") != prior_spec
                        or request.get("sourceAssetDigests", []) != prior["sourceAssetDigests"]
                        or request.get("lyricTimelineDigest") is not None
                        or not isinstance(outputs, list) or len(outputs) != 1):
                    raise ProjectConflict("render payload does not match captured revision")
                validate_render_audio(root, outputs[0])
                if captured != current:
                    project_artifact_fence(root, outputs[0])
                    pending = directory / "pending-renders"
                    durable_mkdir(pending)
                    receipt = {
                        "operation": operation, "projectId": pid,
                        "revisionId": captured, "artifactIds": outputs,
                        "songSpecDigest": prior["songSpecDigest"],
                        "productionTimelineDigest": prior["productionTimelineDigest"],
                    }
                    atomic_write_bytes(pending / (operation["id"] + ".json"), project_json(receipt))
                    project_boundary("artifact_durable_before_historical_binding")
                    reconcile_historical_renders(root, directory, pid, manifest)
                    return historical_result(root, directory, manifest, prior, prior_spec, prior_timeline)
        if "expectedCurrentRevisionId" not in request or request["expectedCurrentRevisionId"] != current:
            raise ProjectConflict("stale project revision; reopen before saving")
        previous = None
        if current:
            # Fail closed if existing authority is corrupt; never overwrite it as a repair.
            previous, old_spec, _ = project_revision(root, directory, pid, current)
        if lyric and not previous: raise ValueError("save project before lyrics")
        spec = old_spec if lyric else request.get("songSpec")
        if not isinstance(spec, dict) or not isinstance(spec.get("tracks"), list) or (not isinstance(spec.get("structure"), dict) or not isinstance(spec["structure"].get("sections"), list)) or not isinstance(spec.get("timebase"), dict):
            raise ValueError("SongSpec required")
        validate_dj_scratch_authority(spec, old_spec if previous else None)
        if request.get("lyricTimelineDigest") is not None:
            raise ValueError("lyric digest cannot bypass the lyric transaction")
        sources = previous['sourceAssetDigests'][:] if lyric else request.get("sourceAssetDigests", [])
        outputs = previous['outputArtifactIds'][:] if lyric else request.get("outputArtifactIds", [])
        lyric_digest = previous.get('lyricTimelineDigest') if previous else None
        lyric_refs = []
        if lyric:
            action = request.get('action')
            if action == 'candidate':
                if lyric_digest: raise ValueError('existing lyric truth requires correction, not replacement')
                source = request['sourceArtifactId']; audio = artifact_bytes(root, source)
                info, _ = lyrics.pcm_info(audio)
                transcript = request.get('knownTranscript', '')
                evidence = {**info, 'method': 'known-text-energy-islands-v1',
                            'claim': 'provided transcript alignment; NOT ASR; NOT voice detection',
                            'knownTranscript': transcript}
                evidence_id = persist_export(root, 'LyricEvidence.json', 'lyric-metadata', project_json(evidence))['sha256']
                doc = lyrics.candidate(audio, source, evidence_id, transcript, request.get('language', 'en'))
                if source not in sources: sources.append(source)
            elif action == 'correct':
                if not lyric_digest: raise ValueError('no lyric revision to correct')
                old, _ = lyric_read(root, lyric_digest)
                if request.get('expectedLyricRevisionId') != old['revisionId']:
                    raise ProjectConflict('stale lyric revision; reopen before correcting')
                doc = lyrics.correction(old, lyric_digest, request.get('changes'), request.get('actor'), request.get('reason', ''))
            else: raise ValueError('unknown lyric action')
            lyrics.validate(doc, artifact_bytes(root, doc['sourceArtifactId']), json.loads(artifact_bytes(root, doc['evidenceArtifactId'])))
            lyric_digest = persist_export(root, 'LyricTimeline.json', 'lyric-metadata', project_json(doc))['sha256']
            project_boundary('lyric_durable_before_project_revision')
        if lyric_digest:
            doc, lyric_refs = lyric_read(root, lyric_digest)
            if doc['sourceArtifactId'] not in sources: raise ValueError('cannot drop lyric audio source')
        if not isinstance(sources, list) or not isinstance(outputs, list) or len(sources) + len(outputs) > 128:
            raise ValueError("invalid artifact bindings")
        for aid in sources + outputs: artifact_bytes(root, aid)
        spec_bytes = project_json(spec)
        song_digest = persist_export(root, "SongSpec.json", "project-metadata", spec_bytes)["sha256"]
        timeline = {"formatVersion": 1, "songSpecDigest": song_digest, "timebase": spec["timebase"], "sections": spec["structure"]["sections"], "tracks": spec["tracks"]}
        timeline_digest = persist_export(root, "ProductionTimeline.json", "project-metadata", project_json(timeline))["sha256"]
        core = {"projectId": pid, "formatVersion": 1, "parentRevisionId": current,
                "songSpecDigest": song_digest, "productionTimelineDigest": timeline_digest,
                "lyricTimelineDigest": lyric_digest, "sourceAssetDigests": sorted(set(sources)),
                "outputArtifactIds": sorted(set(outputs)), "createdAt": datetime.now(timezone.utc).isoformat(),
                "outputBindings": [{"artifactId": aid, "songSpecDigest": song_digest, "productionTimelineDigest": timeline_digest} for aid in sorted(set(outputs))]}
        if operation is not None: core['operation'] = operation
        rid = hashlib.sha256(project_json(core)).hexdigest()
        revision = {"revisionId": rid, **core}
        revisions = directory / "revisions"
        durable_mkdir(revisions)
        revision_path = revisions / (rid + ".json")
        if revision_path.exists(): raise ValueError("revision already exists")
        atomic_write_bytes(revision_path, project_json(revision))
        project_boundary("revision_durable_before_reread")
        # Verify exact references from disk, not from in-memory objects.
        project_revision(root, directory, pid, rid)
        for aid in [song_digest, timeline_digest] + sources + outputs + lyric_refs:
            project_artifact_fence(root, aid)
        project_namespace_fence(revisions, root.parent)
        project_boundary("before_manifest_promotion")
        new_manifest = {"projectId": pid, "currentRevisionId": rid, "formatVersion": 1}
        atomic_write_bytes(path, project_json(new_manifest))
        project_boundary("after_manifest_promotion")
        if json.loads(path.read_text()) != new_manifest:
            raise ValueError("project manifest reread mismatch")
        return project_result(root, new_manifest, revision, spec, timeline)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def write_stereo_wav(path: Path, duration_sec: float = 8.0, bpm: float = 102.0) -> int:
    sample_rate = 44100
    n = int(sample_rate * duration_sec)
    frames = bytearray()
    beat = 60.0 / max(40.0, bpm)
    for s in range(n):
        t = s / sample_rate
        env = min(1.0, t * 4) * max(0.0, 1.0 - (t / duration_sec) * 0.85)
        phase = (t % beat) / beat
        kick = math.sin(2 * math.pi * (80 - 40 * phase) * t) * math.exp(-phase * 8) * 0.35
        bass = math.sin(2 * math.pi * 55 * t) * 0.2 * env
        hat = (1 if (s % max(1, int(sample_rate * beat / 4))) < 80 else 0) * 0.08
        mid = math.sin(2 * math.pi * 220 * t) * 0.06 * env
        l = kick + bass + hat + mid
        r = kick * 0.9 + bass * 1.05 + hat * 0.85 + mid * 1.1
        frames += struct.pack(
            "<hh",
            max(-32767, min(32767, int(l * 32767))),
            max(-32767, min(32767, int(r * 32767))),
        )
    data_size = len(frames)
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, 2, sample_rate, sample_rate * 4, 4, 16)
    header += b"data" + struct.pack("<I", data_size)
    atomic_write_bytes(path, header + frames)
    return data_size


class StudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print(f"[Studio-Server] {fmt % args}")

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        if authorized_origin(self.headers.get("Origin"), self.headers.get("Host")):
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Vary", "Origin")
        super().end_headers()

    def _host_allowed(self):
        return self.headers.get("Host") in {f"localhost:{PORT}", f"127.0.0.1:{PORT}"}

    def do_GET(self):
        if not self._host_allowed(): return self._json(403,{"status":"ERROR","error":"host denied"})
        if self.headers.get("Origin") and not authorized_origin(self.headers["Origin"], self.headers["Host"]):
            return self._json(403,{"status":"ERROR","error":"origin denied"})
        path=unquote(self.path.split("?",1)[0])
        if path.startswith("/workspace") or path.startswith("/.git"):
            return self._json(403,{"status":"ERROR","error":"private storage"})
        if path in {"/","/index.html"}:
            # Fresh same-origin capability, never cached by the service worker.
            session = issue_studio_session(LOCAL_PRINCIPAL_ID)
            body=(ROOT/"index.html").read_text().replace(
                "<head>",
                "<head><script>window.__STUDIO_CAPABILITY__="+json.dumps(CAPABILITY)+";window.__STUDIO_SESSION__="+json.dumps(session)+";</script>"
            ).encode()
            self.send_response(200);self.send_header("Content-Type","text/html");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body);return
        public={"/studio-shell.css","/app-core.js","/scorecore.js","/app-ui.js","/app-cinema.js","/service-worker.js","/manifest.json","/icons/icon.svg","/icons/icon-192.png","/icons/icon-512.png"}
        if path not in public: return self._json(404,{"status":"ERROR","error":"not a public asset"})
        return super().do_GET()

    def do_OPTIONS(self):
        if not authorized_origin(self.headers.get("Origin"), self.headers.get("Host")):
            return self._json(403,{"status":"ERROR","error":"origin denied"})
        if self.headers.get("Access-Control-Request-Method") not in {"GET","POST"}:
            return self._json(403,{"status":"ERROR","error":"method denied"})
        requested={v.strip().lower() for v in self.headers.get("Access-Control-Request-Headers","").split(",") if v.strip()}
        if not requested <= {"authorization","content-type","x-studio-capability","x-studio-session"}:
            return self._json(403,{"status":"ERROR","error":"headers denied"})
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods","GET, POST")
        self.send_header("Access-Control-Allow-Headers","Authorization, Content-Type, X-Studio-Capability, X-Studio-Session")
        self.end_headers()

    def _json(self, code: int, obj: dict):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        if authorized_origin(self.headers.get("Origin"), self.headers.get("Host")):
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Vary", "Origin")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not authorized_origin(self.headers.get("Origin"),self.headers.get("Host")):
            return self._json(403,{"status":"ERROR","error":"origin denied"})
        supplied=self.headers.get("X-Studio-Capability","")
        if not secrets.compare_digest(supplied,CAPABILITY):
            return self._json(403,{"status":"ERROR","error":"capability denied"})
        path = unquote(self.path.split("?",1)[0])
        principal_id = None
        if path.startswith("/api/projects/") or path in {"/api/m045/transcribe-midi", "/api/m045/preview-synth", "/api/m045/master", "/api/m045/compound-plan", "/api/m045/sample-preview", "/api/m045/soundtrack-grant"}:
            try:
                principal_id = resolve_studio_session(self.headers.get("X-Studio-Session", ""))
            except ProjectConflict as e:
                return self._json(403, {"status": "DENY", "error": str(e)})
        try:
            if self.headers.get("Transfer-Encoding"): raise ValueError("transfer encoding unsupported")
            length=int(self.headers.get("Content-Length","-1"))
            if length<0 or length>MAX_REQUEST:
                return self._json(413,{"status":"ERROR","error":"request too large or missing length"})
            payload=json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload,dict): raise ValueError("object required")
        except (ValueError,UnicodeError):
            return self._json(400,{"status":"ERROR","error":"invalid request"})

        if path in {"/api/m045/compound-plan", "/api/m045/sample-preview"}:
            try:
                from m045_wave4_service import authorized_compound_plan,authorized_sample_transform
                operation = (authorized_compound_plan if path.endswith("compound-plan")
                             else authorized_sample_transform)
                return self._json(200,operation(EXPORT_ROOT,payload,principal_id))
            except (ProjectConflict,PermissionError) as exc:
                return self._json(403,{"status":"DENY","error":str(exc)})
            except (ValueError,KeyError,TypeError,OSError,wave.Error,EOFError) as exc:
                return self._json(400,{"status":"ERROR","error":str(exc)})

        if path == "/api/m045/soundtrack-grant":
            if M045_GRANT_SIGNING_RING is None or M045_GRANT_RIGHTS_POLICY is None:
                return self._json(503, {"status": "BLOCKED",
                    "error": "HVC003 host signing/rights authority unconfigured"})
            try:
                from m045_soundtrack_grant import issue_authorized_grant, GrantIssuerDenied
                grant = issue_authorized_grant(
                    root=EXPORT_ROOT, request=payload, principal_id=principal_id,
                    ring=M045_GRANT_SIGNING_RING, read_project=project_operation,
                    read_audio=project_audio_bytes, rights_policy=M045_GRANT_RIGHTS_POLICY)
                return self._json(200, grant)
            except ProjectConflict as error:
                return self._json(403, {"status": "DENY", "error": str(error)})
            except GrantIssuerDenied as error:
                return self._json(403, {"status": "DENY", "error": str(error)})
            except (ValueError, KeyError, TypeError, OSError, wave.Error, EOFError):
                return self._json(400, {"status": "ERROR",
                    "error": "historical soundtrack grant source unqualified"})

        if path == "/api/m045/master":
            try:
                from m045_wave4_service import authorized_master
                return self._json(200, authorized_master(EXPORT_ROOT, payload, principal_id))
            except (ProjectConflict, PermissionError) as exc:
                status = 409 if isinstance(exc, ProjectConflict) and "stale" in str(exc) else 403
                return self._json(status, {"status":"DENY","error":str(exc)})
            except (ValueError, KeyError, TypeError, OSError, wave.Error, EOFError) as exc:
                return self._json(400, {"status":"ERROR","error":str(exc)})

        if path in {"/api/m045/transcribe-midi", "/api/m045/preview-synth"}:
            # No client-provided PCM, CAS path, note list or revision publication.
            # Resolve studio principal and source graph before interpreting a note.
            try:
                from m045_wave3_service import authorized_transcribe, authorized_preview
                operation = authorized_transcribe if path.endswith("transcribe-midi") else authorized_preview
                return self._json(200, operation(EXPORT_ROOT, payload, principal_id))
            except ProjectConflict as exc:
                return self._json(403, {"status":"DENY","error":str(exc)})
            except PermissionError as exc:
                return self._json(403, {"status":"DENY","error":str(exc)})
            except (ValueError, KeyError, TypeError, OSError, wave.Error, EOFError) as exc:
                return self._json(400, {"status":"ERROR","error":str(exc)})

        if path == "/api/m045/attempts/take-audio":
            if M045_ATTEMPT_OWNER is None:
                return self._json(503, {"status":"BLOCKED","error":"M045 owner unavailable"})
            try:
                audio=M045_ATTEMPT_OWNER.read_take_audio(
                    headers=dict(self.headers),project_id=payload["project_id"],
                    idempotency_key=payload["idempotency_key"],
                    take_index=payload["take_index"])
                self.send_response(200)
                self.send_header("Content-Type","audio/wav")
                self.send_header("Cache-Control","no-store")
                self.send_header("Content-Length",str(len(audio)))
                self.end_headers()
                self.wfile.write(audio)
                return
            except AttemptSecurityError as exc:
                return self._json(403, {"status":"DENY","error":str(exc)})
            except ProjectConflict as exc:
                return self._json(409, {"status":"CONFLICT","error":str(exc)})
            except (ValueError,KeyError,TypeError,OSError) as exc:
                return self._json(400, {"status":"ERROR","error":str(exc)})

        if path == "/api/m045/attempts/select-take":
            if M045_ATTEMPT_OWNER is None:
                return self._json(503, {"status":"BLOCKED","error":"M045 owner unavailable"})
            try:
                result=M045_ATTEMPT_OWNER.select_take(
                    headers=dict(self.headers),project_id=payload["project_id"],
                    idempotency_key=payload["idempotency_key"],
                    take_index=payload["take_index"],
                    expected_current_revision_id=payload["expected_current_revision_id"])
                return self._json(200,result)
            except AttemptSecurityError as exc:
                return self._json(403, {"status":"DENY","error":str(exc)})
            except ProjectConflict as exc:
                return self._json(409, {"status":"CONFLICT","error":str(exc)})
            except (ValueError,KeyError,TypeError,OSError) as exc:
                return self._json(400, {"status":"ERROR","error":str(exc)})

        if path == "/api/m045/attempts/reconcile":
            if M045_ATTEMPT_OWNER is None:
                return self._json(503, {"status": "BLOCKED", "error": "M045 attempt owner unavailable"})
            try:
                result = M045_ATTEMPT_OWNER.reconcile_attempt(
                    headers=dict(self.headers),
                    project_id=payload["project_id"],
                    idempotency_key=payload["idempotency_key"],
                    synthesize_to_stage_fn=M045_SYNTHESIZE_TO_STAGE)
                return self._json(200, result)
            except AttemptSecurityError as exc:
                return self._json(403, {"status": "DENY", "error": str(exc)})
            except ProjectConflict as exc:
                return self._json(409, {"status": "CONFLICT", "error": str(exc)})
            except RuntimeError as exc:
                return self._json(422, {"status": "ERROR", "error": str(exc)})
            except (ValueError, KeyError, TypeError, OSError) as exc:
                return self._json(400, {"status": "ERROR", "error": str(exc)})

        if path == "/api/m045/attempts":
            if M045_ATTEMPT_OWNER is None:
                return self._json(503, {"status": "BLOCKED", "error": "M045 generation authority unavailable"})
            try:
                fields = dict(payload)
                provider = M045_SYNTHESIZE_TO_STAGE
                if isinstance(provider, dict):
                    provider = provider.get(fields.get("model_id"))
                if not callable(provider):
                    return self._json(503, {"status": "BLOCKED", "error": "M045 selected provider unavailable"})
                configured_model = getattr(provider, "model_id", None)
                configured_version = getattr(provider, "model_version", None)
                if configured_model and (fields.get("model_id") != configured_model
                                         or fields.get("model_version") != configured_version):
                    return self._json(400, {"status": "DENY", "error": "host provider model mismatch"})
                fields["headers"] = dict(self.headers)
                fields["synthesize_to_stage_fn"] = provider
                result = M045_ATTEMPT_OWNER.execute_attempt(**fields)
                return self._json(200, result)
            except AttemptSecurityError as e:
                return self._json(403, {"status": "DENY", "error": str(e)})
            except ProjectConflict as e:
                return self._json(409, {"status": "CONFLICT", "error": str(e)})
            except RuntimeError as e:
                return self._json(422, {"status": "ERROR", "error": str(e)})
            except (ValueError, KeyError, TypeError, OSError, wave.Error, EOFError, IndexError) as e:
                return self._json(400, {"status": "ERROR", "error": str(e)})

        if path == "/api/m045/scratch/render":
            try:
                return self._json(200, render_authorized_scratch_operation(
                    EXPORT_ROOT, payload, principal_id=principal_id))
            except ProjectConflict as e:
                return self._json(409, {"status":"CONFLICT","error":str(e)})
            except (ValueError, KeyError, TypeError, OSError, wave.Error, EOFError):
                return self._json(400, {"status":"ERROR",
                    "error":"scratch source or revision authority unqualified"})
        if path == "/api/projects/render":
            try:
                return self._json(200, render_publish_operation(EXPORT_ROOT, payload, principal_id=principal_id))
            except ProjectConflict as e:
                return self._json(409, {"status": "CONFLICT", "error": str(e)})
            except (ValueError, KeyError, TypeError, OSError, wave.Error, EOFError, IndexError):
                return self._json(400, {"status": "ERROR", "error": "invalid or unavailable render authority"})
        if path == "/api/projects/audio":
            try:
                data = project_audio_bytes(EXPORT_ROOT, payload, principal_id=principal_id)
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(data)))
                if authorized_origin(self.headers.get("Origin"), self.headers.get("Host")):
                    self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
                    self.send_header("Vary", "Origin")
                self.end_headers()
                self.wfile.write(data)
                return
            except ProjectConflict as e:
                return self._json(403, {"status": "DENY", "error": str(e)})
            except (ValueError, KeyError, TypeError, OSError, wave.Error, EOFError, IndexError):
                return self._json(400, {"status": "ERROR", "error": "invalid or unavailable audio authority"})
        if path in {"/api/projects/commit", "/api/projects/open", "/api/projects/lyrics"}:
            try:
                return self._json(200, project_operation(EXPORT_ROOT, payload, commit=not path.endswith("/open"), lyric=path.endswith("/lyrics"), principal_id=principal_id))
            except ProjectConflict as e:
                return self._json(409, {"status": "CONFLICT", "error": str(e)})
            except (ValueError, KeyError, TypeError, OSError, wave.Error, EOFError, IndexError):
                return self._json(400, {"status": "ERROR", "error": "invalid or unavailable project authority"})
        if path == "/api/write_production_file":
            self._handle_write(payload)
            return
        if path == "/api/dispatch_neural_compilation":
            self._handle_neural(payload)
            return
        if path == "/api/local_neural_vocal_synthesis":
            self._handle_vocal_lab(payload)
            return
        self.send_error(404, "Not found")

    def _handle_write(self, payload: dict):
        try:
            raw=payload.get("data_bytes")
            if isinstance(raw,str): data=raw.encode()
            elif isinstance(raw,list) and all(type(v) is int and 0<=v<=255 for v in raw): data=bytes(raw)
            else: raise ValueError("invalid data_bytes")
            receipt=persist_export(EXPORT_ROOT,payload.get("filename","export.bin"),payload.get("subdirectory","exports"),data)
            self._json(200,receipt)
        except ValueError as e: self._json(400,{"status":"ERROR","error":str(e)})
        except OSError: self._json(500,{"status":"ERROR","error":"storage failure"})

    def _handle_neural(self, request_data: dict):
        try:
            title = str(request_data.get("title") or "SARA_RELEASE_TRACK")
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:80]
            cfg = request_data.get("configuration") or {}
            bpm = float(cfg.get("target_bpm") or 102)
            scale = str(cfg.get("target_scale") or "F# minor")
            lyrics = str(request_data.get("lyrics") or "")
            prompt = str(request_data.get("prompt_directive") or "")
            masters = EXPORT_ROOT / "production_masters"
            otio_dir = EXPORT_ROOT / "otio_packages"
            masters.mkdir(parents=True, exist_ok=True)
            otio_dir.mkdir(parents=True, exist_ok=True)
            wav_path = masters / f"{safe}_broadcast_master.wav"
            otio_path = otio_dir / f"{safe}_broadcast_interchange.otio.json"
            duration = 8.0
            nbytes = write_stereo_wav(wav_path, duration_sec=duration, bpm=bpm)
            otio = {
                "OTIO_SCHEMA": "Timeline.1",
                "name": f"{title} Broadcast Master Timeline",
                "metadata": {
                    "neural_provider_attribution": "SARA_LOCAL_HYBRID_PROXY",
                    "model_version_pin": "local_deterministic_wav_proxy_v1",
                    "target_bpm": bpm,
                    "target_scale": scale,
                    "prompt_directive": prompt[:500],
                    "lyrics_character_count": len(lyrics),
                },
                "tracks": {
                    "OTIO_SCHEMA": "Stack.1",
                    "name": "Tracks Stack",
                    "children": [
                        {
                            "OTIO_SCHEMA": "Track.1",
                            "name": "Vocal Broadcast Channel",
                            "kind": "Video",
                            "children": [
                                {
                                    "OTIO_SCHEMA": "Clip.1",
                                    "name": "Hybrid_Performance_Block",
                                    "source_range": {
                                        "OTIO_SCHEMA": "TimeRange.1",
                                        "start_time": {
                                            "OTIO_SCHEMA": "RationalTime.1",
                                            "rate": 30,
                                            "value": 0,
                                        },
                                        "duration": {
                                            "OTIO_SCHEMA": "RationalTime.1",
                                            "rate": 30,
                                            "value": int(duration * 30),
                                        },
                                    },
                                }
                            ],
                        }
                    ],
                },
            }
            atomic_write_bytes(otio_path, json.dumps(otio, indent=2).encode("utf-8"))
            print(f"[Studio-Server] hybrid master {wav_path} ({nbytes} PCM bytes)")
            wav_receipt=persist_export(EXPORT_ROOT,wav_path.name,"production_masters",wav_path.read_bytes())
            otio_receipt=persist_export(EXPORT_ROOT,otio_path.name,"otio_packages",otio_path.read_bytes())
            self._json(
                200,
                {
                    "status": "SUCCESS",
                    "saved_master_path": wav_receipt["saved_at"],
                    "saved_otio_path": otio_receipt["saved_at"],
                    "provider": "local_hybrid_proxy",
                },
            )
        except Exception as e:
            print(f"[Studio-Server] neural fault: {e}")
            self._json(500, {"status": "ERROR", "error": str(e)})

    def _handle_vocal_lab(self, request_data: dict):
        try:
            tools = str(Path(__file__).resolve().parent)
            if tools not in sys.path:
                sys.path.insert(0, tools)
            from vocal_lab import render_vocal_job

            result = render_vocal_job(request_data, EXPORT_ROOT)
            print(f"[Vocal-Lab] {result.get('engine')} → {result.get('saved_master_path')}")
            vocal_path=Path(result["saved_master_path"])
            receipt=persist_export(EXPORT_ROOT,vocal_path.name,"vocal_stems",vocal_path.read_bytes())
            result["saved_master_path"]=receipt["saved_at"]
            result["file_sha256"]=receipt["sha256"]
            self._json(200,result)
        except Exception as e:
            print(f"[Vocal-Lab] fault: {e}")
            self._json(500, {"status": "ERROR", "error": str(e)})


def main():
    durable_mkdir(EXPORT_ROOT)
    configure_m045_from_environment(EXPORT_ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), StudioHandler) as httpd:
        print("=" * 72)
        print(f"[Studio-Server] http://localhost:{PORT}")
        print(f"[Studio-Server] root {ROOT}")
        print(f"[Studio-Server] exports {EXPORT_ROOT}")
        print("[Studio-Server] POST /api/write_production_file")
        print("[Studio-Server] POST /api/dispatch_neural_compilation")
        print("[Studio-Server] POST /api/local_neural_vocal_synthesis")
        print("=" * 72)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Studio-Server] shutdown")
            sys.exit(0)


if __name__ == "__main__":
    main()
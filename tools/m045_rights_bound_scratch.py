"""Studio-host rights gate around canonical physical Scratch Surgeon renderer.

CAS presence never confers source use permission; this adapter requires both
exact revision membership AND host-attested rights for each editable event.
The existing Studio render attempt/ProjectRevision owner publishes the WAV.
"""
from __future__ import annotations
import hashlib

_CLEARED=frozenset({"ARTIST_ORIGINAL","LICENSE_CLEARED"})

def authorized_render_rights_bound_scratch(root,request,principal_id,rights_policy):
    from studio_server import (ProjectConflict,project_operation,project_audio_bytes,
                               project_owner_directory,render_authorized_scratch_operation)
    from m045_scratch_dsp import waveform_pcm
    if not callable(rights_policy):
        raise PermissionError("SCRATCH_HOST_RIGHTS_UNCONFIGURED")
    required={"projectId","revisionId","baseArtifactId","sampleAssetDigests"}
    if not isinstance(request,dict) or set(request)!=required:
        raise ValueError("SCRATCH_APPROVED_FIELDS_INVALID")
    pid,rid=request["projectId"],request["revisionId"]
    # Check the exact per-principal project namespace *before* revision reads.
    # Foreign project IDs must not become distinguishable from missing IDs.
    try:project_owner_directory(root,pid,principal_id,allow_create=False)
    except ProjectConflict as exc:
        raise PermissionError("SCRATCH_PROJECT_OWNERSHIP_DENIED") from exc
    selected=project_operation(root,{"projectId":pid,"revisionId":rid},principal_id=principal_id)
    current=project_operation(root,{"projectId":pid},principal_id=principal_id)
    if current["revision"]["revisionId"]!=rid:
        raise ProjectConflict("STALE_SCRATCH_CURRENT_REVISION")
    if request["baseArtifactId"] not in selected["revision"]["outputArtifactIds"]:
        raise ProjectConflict("SCRATCH_BASE_AUDIO_NOT_IN_REVISION")
    refs=request["sampleAssetDigests"]
    if not isinstance(refs,dict) or not refs or len(refs)>128:
        raise ValueError("SCRATCH_SAMPLE_REFERENCE_SET_INVALID")
    dj=[track for track in selected["songSpec"]["tracks"]
        if track.get("track_id")=="dj_scratch"]
    if len(dj)!=1 or dj[0].get("sonic_lock") is True:
        raise ProjectConflict("SCRATCH_TRACK_MISSING_OR_LOCKED")
    if any(s.get("sonic_lock") is True for s in selected["songSpec"]["structure"]["sections"]):
        raise ProjectConflict("SCRATCH_LOCKED_SECTION_REQUIRES_EXACT_SCOPE_REVIEW")
    events=dj[0].get("events",[])
    if len(events)!=len(refs) or {e.get("event_id") for e in events}!=set(refs):
        raise ProjectConflict("SCRATCH_EVENT_SAMPLE_BINDINGS_UNQUALIFIED")
    rights=[]
    for event in events:
        digest=refs[event["event_id"]]
        if digest not in selected["revision"]["sourceAssetDigests"]:
            raise ProjectConflict("SCRATCH_SOURCE_NOT_ATTACHED_TO_REVISION")
        # Independently verify host policy for this precise event, not a
        # reusable blanket provider permission, client assertion or CAS digest.
        grant=rights_policy(principal_id,pid,rid,event["event_id"],digest)
        if grant not in _CLEARED:
            raise PermissionError("SCRATCH_SAMPLE_RIGHTS_NOT_CLEARED")
        rights.append(grant)
    # Prior owner handles actual immutable render and publication.
    published=render_authorized_scratch_operation(root,request,principal_id=principal_id)
    bound=project_audio_bytes(root,{"projectId":pid,
        "revisionId":published["revisionId"],"artifactId":published["artifactId"]},
        principal_id=principal_id)
    base=project_audio_bytes(root,{"projectId":pid,"revisionId":rid,
        "artifactId":request["baseArtifactId"]},principal_id=principal_id)
    raw,frames=waveform_pcm(bound)
    original,n=waveform_pcm(base)
    if frames!=n or hashlib.sha256(bound).hexdigest()!=published["artifactId"]:
        raise ProjectConflict("SCRATCH_PHYSICAL_READBACK_FAILED")
    windows=published["proof"]["sample_windows"]
    mask=bytearray(frames)
    for a,b in windows:
        if not (type(a) is int and type(b) is int and 0<=a<b<=frames):
            raise ProjectConflict("SCRATCH_P1_SCOPE_INVALID")
        mask[a:b]=b"\x01"*(b-a)
    for i in range(frames):
        if mask[i]==0 and raw[i*4:i*4+4]!=original[i*4:i*4+4]:
            raise ProjectConflict("SCRATCH_P1_OUTSIDE_WINDOW_DRIFT")
    return {**published,"sampleRightsStatus":
        "ARTIST_ORIGINAL" if all(x=="ARTIST_ORIGINAL" for x in rights) else "LICENSE_CLEARED",
        "sampleRightsSource":"HOST_ATTESTED_EXACT_EVENT_AND_SOURCE",
        "preservationTier":"P1","creativeApproved":False,
        "audioStatus":"RENDERED_BOUND_NOT_CREATIVELY_APPROVED"}
"""Owner-adapter for exact single-track Sonic Lock revision mutations.

Approval tokens and action interpretations are custody only. This adapter
delegates all ProjectRevision creation and conflict arbitration to Studio.
"""
from __future__ import annotations

import copy
import hashlib
import json

def authorized_toggle_lock(root,request,principal_id):
    from studio_server import project_operation,ProjectConflict,project_json
    if not isinstance(request,dict) or set(request)!={
            "projectId","revisionId","targetTrackId","expectedLocked","setLocked"}:
        raise ValueError("INVALID_LOCK_OPERATION_FIELDS")
    if type(request["expectedLocked"]) is not bool or type(request["setLocked"]) is not bool:
        raise ValueError("INVALID_LOCK_TRANSITION")
    if request["expectedLocked"]==request["setLocked"]:
        raise ValueError("LOCK_TRANSITION_MUST_CHANGE_STATE")
    current=project_operation(root,{"projectId":request["projectId"]},principal_id=principal_id)
    rid=request["revisionId"]
    if current["manifest"]["currentRevisionId"]!=rid:
        raise ProjectConflict("stale Sonic Lock source revision")
    tracks=current["songSpec"]["tracks"]
    matched=[t for t in tracks if t.get("track_id")==request["targetTrackId"]]
    if len(matched)!=1:
        raise ProjectConflict("TARGET_TRACK_NOT_IN_CURRENT_SONGSPEC")
    was=matched[0].get("sonic_lock") is True
    if was!=request["expectedLocked"]:
        raise ProjectConflict("SONIC_LOCK_EXPECTED_STATE_MISMATCH")
    spec=copy.deepcopy(current["songSpec"])
    next(t for t in spec["tracks"] if t["track_id"]==request["targetTrackId"])["sonic_lock"]=request["setLocked"]
    meaning={"kind":"chat.sonic_lock.v1","sourceRevisionId":rid,
             "targetTrackId":request["targetTrackId"],"setLocked":request["setLocked"]}
    operation_id="chatlock:"+hashlib.sha256(project_json(meaning)).hexdigest()[:48]
    result=project_operation(root,{
      "projectId":request["projectId"],
      "expectedCurrentRevisionId":rid,
      "operationId":operation_id,
      "songSpec":spec,
      "sourceAssetDigests":current["revision"]["sourceAssetDigests"],
      "outputArtifactIds":current["revision"]["outputArtifactIds"]},
      commit=True,principal_id=principal_id)
    if result["manifest"]["currentRevisionId"]!=result["revision"]["revisionId"]:
        raise ProjectConflict("LOCK_REVISION_NOT_CURRENT")
    observed=project_operation(root,{"projectId":request["projectId"]},principal_id=principal_id)
    expected_locked=request["setLocked"]
    observed_track=[t for t in observed["songSpec"]["tracks"] if t.get("track_id")==request["targetTrackId"]]
    if (observed["revision"]["revisionId"]!=result["revision"]["revisionId"]
            or len(observed_track)!=1
            or (observed_track[0].get("sonic_lock") is True)!=expected_locked):
        raise ProjectConflict("SONIC_LOCK_REVISION_READBACK_FAILED")
    return {"projectId":request["projectId"],"sourceRevisionId":rid,
            "revisionId":result["revision"]["revisionId"],
            "targetTrackId":request["targetTrackId"],"locked":expected_locked,
            "operationId":operation_id}


def authorized_add_scratch(root,request,principal_id):
    """Commit one editable DJ event, never substitute synthetic scratch audio.

    The original audio binding and every non-target musical event remain
    exact. Playback is UNRENDERED until sample rights and source association
    qualify the separate Studio Scratch Surgeon render owner.
    """
    from studio_server import (project_operation,ProjectConflict,project_json,
                               validate_dj_scratch_authority)
    required={"projectId","revisionId","targetTrackId","selectedBar",
              "sectionId","stepIndex","technique","deck"}
    if not isinstance(request,dict) or set(request)!=required:
        raise ValueError("INVALID_ADD_SCRATCH_FIELDS")
    if request["targetTrackId"]!="dj_scratch":
        raise ProjectConflict("SCRATCH_REQUIRES_CANONICAL_DJ_TRACK")
    step=request["stepIndex"]
    if type(step) is not int or not 0<=step<16:
        raise ValueError("INVALID_SCRATCH_STEP")
    if request["technique"] not in ("baby","chirp","2_click_flare","two_deck_juggle"):
        raise ValueError("INVALID_SCRATCH_TECHNIQUE")
    if request["deck"] not in ("A","B") or type(request["selectedBar"]) is not int:
        raise ValueError("INVALID_SCRATCH_TARGET")
    current=project_operation(root,{"projectId":request["projectId"]},principal_id=principal_id)
    rid=request["revisionId"]
    if current["manifest"]["currentRevisionId"]!=rid:
        raise ProjectConflict("STALE_SCRATCH_SOURCE_REVISION")
    spec=current["songSpec"]
    tb=spec.get("timebase",{})
    bpm=tb.get("initial_bpm")
    if (tb.get("meter")!="4/4" or tb.get("sample_rate")!=44100 or
            tb.get("ticks_per_quarter_note")!=960 or type(bpm) is not int or
            not 60<=bpm<=180):
        raise ValueError("SCRATCH_CANONICAL_CLOCK_REQUIRED")
    sections=[sec for sec in spec["structure"]["sections"]
              if sec.get("id")==request["sectionId"]]
    if len(sections)!=1:
        raise ProjectConflict("DJ_SECTION_UNAVAILABLE")
    section=sections[0]
    tick=section["start_tick"]+step*480
    if tick>=section["end_tick"] or request["selectedBar"]!=tick//3840+1:
        raise ProjectConflict("DJ_BAR_STEP_TARGET_MISMATCH")
    if section.get("sonic_lock") is True:
        raise ProjectConflict("SONIC_LOCK_PROTECTS_DJ_SECTION")
    existing=[tr for tr in spec["tracks"] if tr.get("track_id")=="dj_scratch"]
    if len(existing)>1 or (existing and existing[0].get("type")!="DJ"):
        raise ProjectConflict("DJ_TRACK_IDENTITY_CONFLICT")
    if existing and existing[0].get("sonic_lock") is True:
        raise ProjectConflict("SONIC_LOCK_PROTECTS_DJ_TRACK")
    event_id=f'dj:{section["id"]}:{tick}:{request["deck"]}'
    if existing and any(e.get("event_id")==event_id for e in existing[0].get("events",[])):
        raise ProjectConflict("SCRATCH_EVENT_ALREADY_PRESENT_NO_DESTRUCTIVE_TOGGLE")
    if existing and len(existing[0].get("events",[]))>=4096:
        raise ProjectConflict("SCRATCH_EVENT_CAPACITY")
    new=copy.deepcopy(spec)
    dj=next((tr for tr in new["tracks"] if tr.get("track_id")=="dj_scratch"),None)
    if dj is None:
        dj={"track_id":"dj_scratch","name":"Scratch Surgeon","type":"DJ",
            "muted":False,"sonic_lock":False,"volume_db":0,"pan":0,"events":[]}
        new["tracks"].append(dj)
    event={"type":"DJ_SCRATCH_MARKER","event_id":event_id,"tick":tick,
           "duration_ticks":480,"deck":request["deck"],
           "technique":request["technique"],
           "sample_index":(2*tick*60*44100+bpm*960)//(2*bpm*960),
           "audio_status":"UNRENDERED_SOURCE_ASSET_REQUIRED"}
    dj["events"].append(event)
    dj["events"].sort(key=lambda e:(e["tick"],e["event_id"]))
    validate_dj_scratch_authority(new,prior=spec)
    meaning={"kind":"chat.dj_scratch_marker.v1","sourceRevisionId":rid,"marker":event}
    operation_id="chatdj:"+hashlib.sha256(project_json(meaning)).hexdigest()[:48]
    committed=project_operation(root,{
      "projectId":request["projectId"],
      "expectedCurrentRevisionId":rid,
      "operationId":operation_id,"songSpec":new,
      "sourceAssetDigests":current["revision"]["sourceAssetDigests"],
      "outputArtifactIds":current["revision"]["outputArtifactIds"]},
      commit=True,principal_id=principal_id)
    observed=project_operation(root,{"projectId":request["projectId"]},principal_id=principal_id)
    if (committed["revision"]["revisionId"]!=observed["revision"]["revisionId"]
        or observed["revision"]["outputArtifactIds"]!=current["revision"]["outputArtifactIds"]
        or observed["revision"]["sourceAssetDigests"]!=current["revision"]["sourceAssetDigests"]):
        raise ProjectConflict("DJ_EVENT_PRESERVATION_READBACK_FAILED")
    other_old=[t for t in spec["tracks"] if t.get("track_id")!="dj_scratch"]
    other_now=[t for t in observed["songSpec"]["tracks"] if t.get("track_id")!="dj_scratch"]
    if other_old!=other_now or not any(e==event for t in observed["songSpec"]["tracks"]
                                         if t.get("track_id")=="dj_scratch" for e in t["events"]):
        raise ProjectConflict("DJ_EVENT_READBACK_MISMATCH")
    return {"projectId":request["projectId"],"sourceRevisionId":rid,
        "revisionId":committed["revision"]["revisionId"],
        "operationId":operation_id,"event":event,
        "audioStatus":"UNRENDERED_SOURCE_ASSET_REQUIRED",
        "preservationTier":"P0_EXACT_NON_TARGET_EVENTS_AND_ARTIFACT_BINDINGS",
        "audioPlayable":False}
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

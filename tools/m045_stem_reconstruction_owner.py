"""Studio-authorized dry-f64 stem reconstruction; NO alternate revision/CAS owner.

Existing reconstruct_master supplies deterministic DSP. The canonical Studio render
attempt controls durable WAV publication and historical revision association.
"""
from __future__ import annotations
import hashlib

MAX_STEM_TOTAL_BYTES=32*1024*1024

def authorized_reconstruct_mix(root,request,principal_id):
    from studio_server import (ProjectConflict,project_operation,artifact_bytes,
        project_audio_bytes,render_publish_operation,project_json)
    from m045_stem_reconstruction import reconstruct_master,HEX
    if not isinstance(request,dict) or set(request)!={
            "projectId","expectedCurrentRevisionId","mixRecipe"}:
        raise ValueError("MIX_OWNER_FIELDS_INVALID")
    pid,rid,recipe=request["projectId"],request["expectedCurrentRevisionId"],request["mixRecipe"]
    current=project_operation(root,{"projectId":pid},principal_id=principal_id)
    if current["revision"]["revisionId"]!=rid:
        raise ProjectConflict("MIX_CURRENT_REVISION_STALE")
    if not isinstance(recipe,dict):
        raise ValueError("MIX_RECIPE_REQUIRED")
    if (recipe.get("source_project_revision_id")!=rid or
            recipe.get("production_timeline_digest")!=
                current["revision"]["productionTimelineDigest"]):
        raise ProjectConflict("MIX_RECIPE_REVISION_OR_TIMELINE_MISMATCH")
    if any(track.get("sonic_lock") is True for track in current["songSpec"]["tracks"]) or any(
            section.get("sonic_lock") is True for section in current["songSpec"]["structure"]["sections"]):
        raise ProjectConflict("MIX_SONIC_LOCK_NO_REINTERPRETATION")
    ids=recipe.get("stem_artifact_ids")
    if (not isinstance(ids,list) or not ids or len(ids)>32
            or any(not isinstance(x,str) or not HEX.fullmatch(x) for x in ids)
            or len(set(ids))!=len(ids) or ids!=sorted(ids)):
        raise ValueError("MIX_CANONICAL_STEM_ORDER_REQUIRED")
    if not set(ids)<=set(current["revision"]["sourceAssetDigests"]):
        raise ProjectConflict("MIX_STEM_NOT_ATTACHED_TO_SOURCE_REVISION")
    # CAS objects are not authorization: source membership and project
    # principal have been independently checked before every CAS read.
    source=[artifact_bytes(root,id_) for id_ in ids]
    if sum(map(len,source))>MAX_STEM_TOTAL_BYTES:
        raise ValueError("MIX_STEM_MEMORY_BOUND_EXCEEDED")
    master=reconstruct_master(source,recipe)
    sha=hashlib.sha256(master).hexdigest()
    recipe_digest=hashlib.sha256(project_json(recipe)).hexdigest()
    operation_id="mix:"+hashlib.sha256(project_json({
        "projectId":pid,"sourceRevisionId":rid,
        "recipeSha256":recipe_digest,"masterSha256":sha})).hexdigest()[:48]
    result=render_publish_operation(root,{"projectId":pid,
      "sourceRevisionId":rid,"operationId":operation_id,
      "filename":"dry-stem-mix.wav","subdirectory":"reconstruction",
      "data_bytes":master},principal_id=principal_id)
    published_revision=result["revision"]["revisionId"]
    reread=project_audio_bytes(root,{"projectId":pid,"revisionId":published_revision,
      "artifactId":sha},principal_id=principal_id)
    if reread!=master:
        raise ProjectConflict("MIX_PHYSICAL_WAV_READBACK_MISMATCH")
    return {"state":"RENDERED_BOUND","projectId":pid,
        "sourceRevisionId":rid,"revisionId":published_revision,
        "artifactId":sha,"operationId":operation_id,
        "recipeSchema":"sara.mix.recipe.v1","recipeSha256":recipe_digest,
        "stemArtifactIds":ids,"reconstructionExact":True,
        "creativeStemsExact":False,"releaseCleared":False,
        "rightsStatus":"UNVERIFIED_HELD","creativeApproved":False}
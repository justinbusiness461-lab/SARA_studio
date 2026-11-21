"""Studio-authorized dry-f64 stem reconstruction; NO alternate revision/CAS owner.

Existing reconstruct_master supplies deterministic DSP. The canonical Studio render
attempt controls durable WAV publication and historical revision association.
"""
from __future__ import annotations
import hashlib
import tempfile
from pathlib import Path

MAX_STEM_TOTAL_BYTES=2*1024*1024*1024

def authorized_reconstruct_mix(root,request,principal_id):
    from studio_server import (ProjectConflict,project_operation,artifact_bytes,
        project_audio_bytes,render_publish_operation,project_json,project_owner_directory,
        artifact_digest_verified,MAX_ARTIFACT)
    from m045_stem_reconstruction import reconstruct_master,HEX,reconstruct_master_to_file
    from m045_wave4_mastering_provenance import CanonicalProvenanceRecord
    import wave,io
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
    # CAS existence is never authorization. Exact principal/current-revision
    # association has been checked first. Recheck digest and on-disk length.
    root=Path(root).resolve()
    paths=[root/"objects"/digest[:2]/digest for digest in ids]
    for item in paths:artifact_digest_verified(root,item.name)
    if sum(x.stat().st_size for x in paths)>MAX_STEM_TOTAL_BYTES:
        raise ValueError("MIX_STEM_DISK_BOUND_EXCEEDED")
    recipe_digest=hashlib.sha256(project_json(recipe)).hexdigest()
    parent=current["revision"]["outputArtifactIds"]
    if not parent or len(parent)!=1:
        raise ProjectConflict("MIX_REQUIRES_EXACT_SOURCE_MASTER")
    project_audio_bytes(root,{"projectId":pid,"revisionId":rid,"artifactId":parent[0]},
                        principal_id=principal_id)
    owner_dir=project_owner_directory(root,pid,principal_id,allow_create=False)
    # Private scratch output does NOT become an artifact or authority until the
    # existing render publisher's durable attempt/namespace CAS transaction.
    with tempfile.TemporaryDirectory(prefix=".mix-r8-",dir=owner_dir) as folder:
        path=Path(folder)/"mix.wav"
        physical=reconstruct_master_to_file(paths,recipe,path)
        master=path.read_bytes()  # PCM16 <= ~37 MiB at 210s; not float64 stems.
        sha=hashlib.sha256(master).hexdigest()
        if sha!=physical["sha256"]:
            raise ProjectConflict("MIX_STAGE_DIGEST_READBACK_MISMATCH")
        operation_id="mix:"+hashlib.sha256(project_json({
            "projectId":pid,"sourceRevisionId":rid,
            "recipeSha256":recipe_digest,"masterSha256":sha})).hexdigest()[:48]
        provenance=None
        if len(master)>MAX_ARTIFACT:
            with wave.open(io.BytesIO(master),"rb") as wav:
                pcm_hash=hashlib.sha256(wav.readframes(wav.getnframes())).hexdigest()
            provenance=CanonicalProvenanceRecord(
                artifact_sha256=sha,pcm_sha256=pcm_hash,
                project_id=pid,revision_id=rid,origin_type="DSP_TRANSFORM",
                preservation_tier="P3",rights_status="UNVERIFIED_HELD",
                parent_artifact_sha256s=[parent[0]],
                transform_chain=[{"operation":"sara.mix.recipe.v1",
                  "recipeSha256":recipe_digest,
                  "stemArtifactIds":ids,
                  "sampleCount":recipe["sample_count"]}])
        result=render_publish_operation(root,{"projectId":pid,
          "sourceRevisionId":rid,"operationId":operation_id,
          "filename":"dry-stem-mix.wav","subdirectory":"reconstruction",
          "data_bytes":master},principal_id=principal_id,
          master_provenance=provenance)
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

"""Host-only Chat approval adapter into canonical GenerationAttemptOwner.

No duplicated render/CAS authority. A repaint is successful ONLY after
GenerationAttemptOwner durably stages, validates provider P2 provenance,
physically splices P1 PCM outside the selected window, commits a lawful Studio
ProjectRevision, and passes independent exact audio readback.
"""
from __future__ import annotations
import hashlib
import secrets

def authorized_repaint(root,request,principal_id,instruction,challenge):
    from studio_server import (project_operation,project_audio_bytes,
        make_m045_native_owner,ProjectConflict,M045_SYNTHESIZE_TO_STAGE)
    from platform_chat_approval import PlatformServiceUnavailable
    from m045_repaint import bar_sample_window,read_pcm16_wav
    expected={"projectId","revisionId","artifactId","targetTrackId","selectedBars"}
    if not isinstance(request,dict) or set(request)!=expected:
        raise ValueError("REPAINT_APPROVED_FIELDS_INVALID")
    if not isinstance(instruction,str) or not instruction.strip():
        raise ValueError("REPAINT_INSTRUCTION_REQUIRED")
    bars=request["selectedBars"]
    if (not isinstance(bars,list) or not bars
        or any(type(x) is not int for x in bars)
        or bars!=list(range(min(bars),max(bars)+1))):
        raise ValueError("REPAINT_CONTIGUOUS_BARS_REQUIRED")
    pid,rid=request["projectId"],request["revisionId"]
    live=project_operation(root,{"projectId":pid},principal_id=principal_id)
    if live["revision"]["revisionId"]!=rid:
        raise ProjectConflict("STALE_REPAINT_SOURCE_REVISION")
    spec=live["songSpec"]
    if request["targetTrackId"] not in {t.get("track_id") for t in spec["tracks"]}:
        raise ProjectConflict("REPAINT_TARGET_TRACK_MISSING")
    if any(t.get("sonic_lock") is True for t in spec["tracks"]):
        raise ProjectConflict("SONIC_LOCK_BLOCKS_FULL_MIX_REPAINT")
    attached=live["revision"]["outputArtifactIds"]
    if attached != [request["artifactId"]]:
        raise ProjectConflict("REPAINT_REQUIRES_EXACT_SINGLE_OUTPUT_BINDING")
    for section in spec.get("structure",{}).get("sections",[]):
        if section.get("sonic_lock") is True and (
            (bars[0]-1)*4*960<section.get("end_tick",0) and
            section.get("start_tick",0)<bars[-1]*4*960):
            raise ProjectConflict("SONIC_LOCK_PROTECTS_REPAINT_SECTION")
    providers=M045_SYNTHESIZE_TO_STAGE
    qualified=([p for p in providers.values() if getattr(p,"supports_repaint",False)]
               if isinstance(providers,dict) else
               [providers] if callable(providers) and getattr(providers,"supports_repaint",False) else [])
    if len(qualified)!=1:
        raise PlatformServiceUnavailable("HOST_REPAINT_PROVIDER_UNQUALIFIED_OR_AMBIGUOUS")
    provider=qualified[0]
    model_id=getattr(provider,"model_id",None)
    model_version=getattr(provider,"model_version",None)
    if not isinstance(model_id,str) or not model_id or not isinstance(model_version,str) or not model_version:
        raise PlatformServiceUnavailable("HOST_REPAINT_MODEL_IDENTITY_UNQUALIFIED")
    base=project_audio_bytes(root,{"projectId":pid,"revisionId":rid,
        "artifactId":request["artifactId"]},principal_id=principal_id)
    base_pcm,frames=read_pcm16_wav(base)
    start,end=bar_sample_window(spec,bars[0],bars[-1]+1,frames)
    # This token exists ONLY in the host stack and never reaches a Chat
    # approval body or browser. The owner still enforces exact scoped project
    # authorization, immutable revision and media identities.
    delegated=secrets.token_urlsafe(48)
    owner=make_m045_native_owner(root,scoped_principal=principal_id,
                                  host_delegation_token=delegated)
    params={"edit_mode":"repaint","start_bar":bars[0],"end_bar":bars[-1]+1,
            "target_track_id":request["targetTrackId"],
            "music_length_ms":round(frames*1000/44100)}
    result=owner.execute_attempt(
       headers={"Authorization":"Bearer "+delegated},
       project_id=pid,base_revision_id=rid,
       expected_current_revision_id=rid,
       idempotency_key="chat-repaint-"+hashlib.sha256(challenge.encode()).hexdigest()[:32],
       model_id=model_id,model_version=model_version,
       song_spec=spec,source_asset_digests=live["revision"]["sourceAssetDigests"],
       prompt=instruction,lyrics=None,seed=0,
       params=params,synthesize_to_stage_fn=provider)
    if result.get("state")!="COMMITTED" or not isinstance(result.get("revision"),dict):
        # COMMIT_UNCERTAIN cannot be announced as success, nor blindly retried.
        raise ProjectConflict("REPAINT_COMMIT_REQUIRES_CANONICAL_RECONCILIATION")
    revision=result["revision"]["revisionId"]
    digest=result["attempt"]["artifact_digest"]
    raw=project_audio_bytes(root,{"projectId":pid,"revisionId":revision,
        "artifactId":digest},principal_id=principal_id)
    output,n=read_pcm16_wav(raw)
    if (n!=frames or output[:start*4]!=base_pcm[:start*4]
            or output[end*4:]!=base_pcm[end*4:]):
        raise ProjectConflict("REPAINT_P1_PHYSICAL_READBACK_FAILED")
    proof=result["attempt"].get("provenance",{})
    if proof.get("preservation_tier")!="P1":
        raise ProjectConflict("REPAINT_PROVENANCE_NOT_P1")
    return {"projectId":pid,"sourceRevisionId":rid,"revisionId":revision,
        "artifactId":digest,"preservationTier":"P1",
        "preservationMethod":"EXACT_OUTSIDE_REGION_PCM_SPLICING",
        "prefixSha256":hashlib.sha256(base_pcm[:start*4]).hexdigest(),
        "suffixSha256":hashlib.sha256(base_pcm[end*4:]).hexdigest(),
        "startSample":start,"endSample":end,
        "audioStatus":"RENDERED_NOT_CREATIVELY_APPROVED",
        "rightsStatus":proof.get("rights_status","UNVERIFIED_HELD"),
        "attemptId":result["attempt"]["attempt_id"]}
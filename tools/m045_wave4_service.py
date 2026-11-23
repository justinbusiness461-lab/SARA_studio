"""Studio-owned Wave 004 mastering operation; no second CAS or rights authority."""
from __future__ import annotations
import hashlib
from m045_wave4_mastering_provenance import CanonicalProvenanceRecord,master_wav_to_lufs_target
def authorized_master(root,payload,principal_id):
 from studio_server import (ProjectConflict,project_operation,project_audio_bytes,
    render_publish_operation,project_json)
 required={'projectId','revisionId','artifactId','expectedCurrentRevisionId',
           'targetLufs','truePeakCeilingDbtp'}
 if not isinstance(payload,dict) or set(payload)!=required:
  raise ValueError("MASTER_REQUEST_FIELDS_NOT_QUALIFIED")
 if not principal_id:raise PermissionError("SESSION_REQUIRED")
 if payload["revisionId"]!=payload["expectedCurrentRevisionId"]:
  raise ProjectConflict("stale expected current revision")
 selected=project_operation(root,{"projectId":payload["projectId"],
   "revisionId":payload["revisionId"]},principal_id=principal_id)
 if any(track.get("sonic_lock") is True for track in selected["songSpec"]["tracks"]):
  raise ProjectConflict("sonic lock blocks global mastering")
 current=project_operation(root,{"projectId":payload["projectId"]},principal_id=principal_id)
 if current["manifest"]["currentRevisionId"]!=payload["expectedCurrentRevisionId"]:
  raise ProjectConflict("stale expected current revision")
 source=project_audio_bytes(root,{"projectId":payload["projectId"],
    "revisionId":payload["revisionId"],"artifactId":payload["artifactId"]},
    principal_id=principal_id)
 mastered,telemetry=master_wav_to_lufs_target(wav_bytes=source,
    target_lufs=payload["targetLufs"],
    true_peak_ceiling_dbtp=payload["truePeakCeilingDbtp"])
 source_id=hashlib.sha256(source).hexdigest()
 out_id=hashlib.sha256(mastered).hexdigest()
 # Rights clearance is never created by mastering. Existing SampleAsset/rights
 # authority must prove it separately. We cannot infer rights from CAS bytes.
 import io,wave
 with wave.open(io.BytesIO(mastered),"rb") as decoded:
  pcm_digest=hashlib.sha256(decoded.readframes(decoded.getnframes())).hexdigest()
 provenance=CanonicalProvenanceRecord(
   artifact_sha256=out_id,pcm_sha256=pcm_digest,
   project_id=payload["projectId"],revision_id=payload["revisionId"],
   origin_type="DSP_TRANSFORM",preservation_tier="P3",
   rights_status="UNVERIFIED_HELD",parent_artifact_sha256s=[source_id],
   transform_chain=[{"kind":"loudness-master","processor":"ffmpeg-loudnorm",
        "sourceRevisionId":payload["revisionId"],
        "targetLufs":payload["targetLufs"],"truePeakCeilingDbtp":payload["truePeakCeilingDbtp"],
        "measuredOutputLufs":telemetry["measured_output_lufs"],
        "measuredOutputTruePeakDbtp":telemetry["measured_output_true_peak_dbtp"],
        "meterConformance":telemetry["meterConformance"],
        "referenceIntegratedLufs":telemetry["reference_meter"]["integrated_lufs"],
        "referenceTruePeakDbtp":telemetry["reference_meter"]["true_peak_dbtp"],
        "referenceMeterInputWavSha256":telemetry["reference_meter"]["input_wav_sha256"]}])
 provenance.validate()
 # Same intended request has a stable operation identifier; NO blind retry from
 # the UI after an ambiguous server response—authoritative readback first.
 op_payload={"projectId":payload["projectId"],"sourceRevisionId":payload["revisionId"],
   "sourceArtifactId":source_id,"outputArtifactId":out_id,
   "targetLufs":payload["targetLufs"],"truePeakCeilingDbtp":payload["truePeakCeilingDbtp"]}
 operation_id="master-"+hashlib.sha256(project_json(op_payload)).hexdigest()[:40]
 published=render_publish_operation(root,{"projectId":payload["projectId"],
    "sourceRevisionId":payload["revisionId"],"operationId":operation_id,
    "filename":"master.wav","subdirectory":"masters","data_bytes":mastered},
    principal_id=principal_id,master_provenance=provenance)
 bound_rid=published["revision"]["revisionId"]
 readback=project_audio_bytes(root,{"projectId":payload["projectId"],
   "revisionId":bound_rid,"artifactId":out_id},principal_id=principal_id)
 if readback!=mastered:raise ValueError("MASTER_READBACK_INTEGRITY_FAILED")
 return {"status":"SUCCESS","projectId":payload["projectId"],
   "sourceRevisionId":payload["revisionId"],"sourceArtifactId":source_id,
   "revisionId":bound_rid,"artifactId":out_id,"operationId":operation_id,
   "rightsStatus":"UNVERIFIED_HELD","releaseCleared":False,
   "preservationTier":"P3","audioStatus":"RENDERED_BOUND_NOT_CREATIVELY_APPROVED",
   "telemetry":telemetry}

# Wave004 owner-disjoint extensions: proposal and preview consumers only.
# Master's existing render/CAS publication owner above is NOT modified.

def authorized_compound_plan(root,payload,principal_id):
 if not principal_id:raise PermissionError('SESSION_REQUIRED')
 if not isinstance(payload,dict) or set(payload)!={'projectId','revisionId','instruction'}:
  raise ValueError('COMPOUND_REQUEST_FIELDS_INVALID')
 from studio_server import project_operation
 from m045_edit_proposal import compile_compound_plan
 selected=project_operation(root,{'projectId':payload['projectId'],
    'revisionId':payload['revisionId']},principal_id=principal_id)
 if selected['manifest']['projectId']!=payload['projectId'] or selected['revision']['revisionId']!=payload['revisionId']:
  raise ValueError('COMPOUND_SOURCE_REVISION_MISMATCH')
 plan=compile_compound_plan(payload['instruction'],selected['songSpec'])
 return {'status':'SUCCESS','kind':'NON_AUTHORITATIVE_COMPOUND_PLAN',
   'projectId':payload['projectId'],'sourceRevisionId':payload['revisionId'],**plan}


def authorized_sample_transform(root,payload,principal_id):
 if not principal_id:raise PermissionError('SESSION_REQUIRED')
 if not isinstance(payload,dict) or set(payload)!={'projectId','revisionId','artifactId','transform','parameters'}:
  raise ValueError('SAMPLE_PREVIEW_REQUEST_FIELDS_INVALID')
 from studio_server import project_operation,project_audio_bytes
 from m045_sample_lab_dsp import slice_sample,resonant_lowpass,metallic_comb,rate_pitch_shift,apply_effect_graph
 import io,wave,base64
 selected=project_operation(root,{'projectId':payload['projectId'],'revisionId':payload['revisionId']},principal_id=principal_id)
 if selected['manifest']['projectId']!=payload['projectId'] or selected['revision']['revisionId']!=payload['revisionId']:
  raise ValueError('SAMPLE_SOURCE_REVISION_MISMATCH')
 source=project_audio_bytes(root,{'projectId':payload['projectId'],
  'revisionId':payload['revisionId'],'artifactId':payload['artifactId']},principal_id=principal_id)
 if hashlib.sha256(source).hexdigest()!=payload['artifactId']:
  raise ValueError('SAMPLE_SOURCE_HASH_MISMATCH')
 operation=payload['transform'];params=payload['parameters']
 if not isinstance(params,dict):raise ValueError('SAMPLE_TRANSFORM_PARAMETERS_INVALID')
 if operation=='slice' and set(params)=={'startFrame','endFrame'}:
  result=slice_sample(source,params['startFrame'],params['endFrame'])
 elif operation=='lowpass' and set(params)=={'startFrame','endFrame','cutoffHz','q'}:
  result=resonant_lowpass(slice_sample(source,params['startFrame'],params['endFrame']),params['cutoffHz'],params['q'])
 elif operation=='metallic_comb' and set(params)=={'startFrame','endFrame','delayMs','feedback'}:
  result=metallic_comb(slice_sample(source,params['startFrame'],params['endFrame']),params['delayMs'],params['feedback'])
 elif operation=='rate_pitch' and set(params)=={'startFrame','endFrame','semitones'}:
  result=rate_pitch_shift(slice_sample(source,params['startFrame'],params['endFrame']),params['semitones'])
 elif operation=='modular_graph' and set(params)=={'nodes','outputId'}:
  result=apply_effect_graph(source,params['nodes'],params['outputId'])
 else:raise ValueError('SAMPLE_TRANSFORM_OPERATION_UNSUPPORTED')
 if len(result)>4*1024*1024:raise ValueError('SAMPLE_PREVIEW_EXCEEDS_SIZE_BOUND')
 with wave.open(io.BytesIO(result),'rb') as decoded:
  pcm=decoded.readframes(decoded.getnframes())
 output_sha=hashlib.sha256(result).hexdigest()
 chain=params['nodes'] if operation=='modular_graph' else [{'operation':operation,**params}]
 provenance=CanonicalProvenanceRecord(
  artifact_sha256=output_sha,pcm_sha256=hashlib.sha256(pcm).hexdigest(),
  project_id=payload['projectId'],revision_id=payload['revisionId'],
  origin_type='DSP_TRANSFORM',preservation_tier='P3',rights_status='UNVERIFIED_HELD',
  parent_artifact_sha256s=[payload['artifactId']],transform_chain=chain).to_dict()
 return {'status':'SUCCESS','kind':'NON_AUTHORITATIVE_SAMPLE_PREVIEW',
  'projectId':payload['projectId'],'sourceRevisionId':payload['revisionId'],
  'sourceArtifactId':payload['artifactId'],'previewArtifactSha256':output_sha,
  'wavBase64':base64.b64encode(result).decode('ascii'),
  'provenance':provenance,'sourceMutation':False,'projectRevisionCommitted':False,
  'audioPublication':'NONE','requiresCreativeApproval':True}
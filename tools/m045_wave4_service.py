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
        "meterConformance":telemetry["meterConformance"]}])
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

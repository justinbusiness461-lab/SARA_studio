"""Wave 003 authorized, non-publishing ScoreCore projections.
Only Studio's existing ProjectRevision, principal, and lawful revision→artifact
association may authorize reads. Candidates are not audio-preservation proofs.
"""
from __future__ import annotations
import base64
import hashlib
from dataclasses import asdict
from fractions import Fraction
from m045_audio_to_midi import (transcribe_wav_to_scorecore_notes,
    export_scorecore_notes_to_musicxml,export_scorecore_notes_to_smf)
from m045_fm_preview_synth import render_fm_preview_wav

def _require_fields(payload,expected):
    if not isinstance(payload,dict) or set(payload)!=set(expected):
        raise ValueError("UNSUPPORTED_WAVE3_REQUEST_FIELDS")

def authorized_transcribe(root,payload,principal_id):
    _require_fields(payload,{"projectId","revisionId","artifactId"})
    if not principal_id:raise PermissionError("SESSION_REQUIRED")
    # Import is runtime-only to avoid introducing any competing Studio authority.
    from studio_server import project_operation,project_audio_bytes
    selected=project_operation(root,{"projectId":payload["projectId"],
        "revisionId":payload["revisionId"]},principal_id=principal_id)
    if selected["revision"]["revisionId"]!=payload["revisionId"]:
        raise ValueError("SOURCE_REVISION_MISMATCH")
    spec=selected["songSpec"]
    bpm=spec["timebase"]["initial_bpm"]
    source=project_audio_bytes(root,{"projectId":payload["projectId"],
        "revisionId":payload["revisionId"],"artifactId":payload["artifactId"]},
        principal_id=principal_id)
    candidate=transcribe_wav_to_scorecore_notes(wav_bytes=source,bpm=bpm)
    if candidate.source_artifact_sha256!=payload["artifactId"]:
        raise ValueError("SOURCE_DIGEST_MISMATCH")
    midi0=export_scorecore_notes_to_smf(candidate.notes,bpm=bpm,smf_type=0)
    midi1=export_scorecore_notes_to_smf(candidate.notes,bpm=bpm,smf_type=1)
    return {"status":"SUCCESS","kind":"NON_AUTHORITATIVE_TRANSCRIPTION_CANDIDATE",
        "projectId":payload["projectId"],"sourceRevisionId":payload["revisionId"],
        "sourceArtifactId":payload["artifactId"],"preservationTier":"P3_RECONSTRUCTION",
        "ppq":candidate.ppq,"notesDetected":candidate.notes_detected,
        "lossReport":candidate.loss_report,"estimatedNotes":[asdict(n) for n in candidate.notes],
        "musicXml":export_scorecore_notes_to_musicxml(candidate.notes),
        "midiType0Base64":base64.b64encode(midi0).decode("ascii"),
        "midiType1Base64":base64.b64encode(midi1).decode("ascii"),
        "projectRevisionCommitted":False,"audioPublication":"NONE","requiresHumanReview":True}

def authorized_preview(root,payload,principal_id):
    allowed={"projectId","revisionId","sectionId","trackId"}
    if not isinstance(payload,dict) or set(payload) not in (allowed,allowed|{"patch"}):
        raise ValueError("UNSUPPORTED_WAVE3_REQUEST_FIELDS")
    if not principal_id:raise PermissionError("SESSION_REQUIRED")
    from studio_server import project_operation
    selected=project_operation(root,{"projectId":payload["projectId"],
        "revisionId":payload["revisionId"]},principal_id=principal_id)
    spec=selected["songSpec"];tb=spec["timebase"]
    if tb.get("meter")!="4/4" or tb.get("ticks_per_quarter_note")!=960:
        raise ValueError("UNSUPPORTED_PREVIEW_TIMEBASE")
    sections=[s for s in spec["structure"]["sections"] if s["id"]==payload["sectionId"]]
    tracks=[t for t in spec["tracks"] if t["track_id"]==payload["trackId"]]
    if len(sections)!=1 or len(tracks)!=1:
        raise ValueError("AMBIGUOUS_OR_MISSING_TRACK_SECTION")
    sec,track=sections[0],tracks[0]
    start,end=sec["start_tick"],sec["end_tick"]
    if any(type(x)!=int for x in (start,end)) or start<0 or end<=start:
        raise ValueError("INVALID_PREVIEW_SECTION")
    for other in spec["structure"]["sections"]:
        if other is not sec and other["start_tick"]<end and start<other["end_tick"]:
            raise ValueError("AMBIGUOUS_OVERLAPPING_SECTIONS")
    length=end-start;ppq=960;bar_ticks=4*ppq
    if length%bar_ticks:raise ValueError("PREVIEW_REQUIRES_COMPLETE_BARS")
    bars=length//bar_ticks
    if not 1<=bars<=4:raise ValueError("PREVIEW_SECTION_DURATION_UNQUALIFIED")
    notes=[]
    for ev in track["events"]:
        if ev.get("type")!="NOTE_ON":continue
        tick,duration=ev["tick"],ev["duration_ticks"]
        if type(tick)!=int or type(duration)!=int or tick<0 or duration<=0:
            raise ValueError("INVALID_CANONICAL_NOTE")
        if tick<end and tick+duration>start:
            if tick<start or tick+duration>end:raise ValueError("PREVIEW_NOTE_CROSSES_SECTION")
            notes.append({"midi_note":ev["note_number"],"start_tick":tick-start,
                "duration_ticks":duration,"velocity":ev.get("velocity",100)})
    if not notes:raise ValueError("PREVIEW_HAS_NO_NOTES")
    audio=render_fm_preview_wav(notes=notes,bpm=tb["initial_bpm"],
        ppq=ppq,total_bars=bars,patch=payload.get("patch","fm_bass"))
    return {"status":"SUCCESS","kind":"NON_AUTHORITATIVE_FM_PREVIEW",
       "projectId":payload["projectId"],"sourceRevisionId":payload["revisionId"],
       "sectionId":sec["id"],"trackId":track["track_id"],
       "audioStatus":"PREVIEW_NOT_PUBLISHED","sampleRate":44100,
       "channels":2,"previewSha256":hashlib.sha256(audio).hexdigest(),
       "wavBase64":base64.b64encode(audio).decode("ascii"),
       "projectRevisionCommitted":False,"audioPreservationProof":"NOT_CLAIMED"}

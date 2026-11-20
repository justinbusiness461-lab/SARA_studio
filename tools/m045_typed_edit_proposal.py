"""Strict optional typed edit intent validation; source audio authority stays in Studio."""
from __future__ import annotations

from fractions import Fraction

_FIELDS = {"schema_version","target_scope","preserved_scopes","declared_tier","operation","rational_window"}


def _exact_keys(value, fields, label):
    if not isinstance(value,dict) or set(value)!=fields:
        raise ValueError(f"TYPED_EDIT_{label}_INVALID")


def _integer(v):
    return type(v) is int


def _rational(v):
    _exact_keys(v,{"numerator","denominator"},"RATIONAL_WINDOW")
    n,d=v["numerator"],v["denominator"]
    if not _integer(n) or not _integer(d) or d<=0 or abs(n)>2**53 or d>2**53:
        raise ValueError("TYPED_EDIT_RATIONAL_WINDOW_INVALID")
    return Fraction(n,d)


def validate_typed_repaint_proposal(proposal,song_spec,frame_count,sample_window,target_track):
    """Validate a P1 PCM region edit, not track-level isolation or note-level P0."""
    _exact_keys(proposal,_FIELDS,"PROPOSAL")
    if proposal["schema_version"]!="sara.typed-edit.v1":
        raise ValueError("TYPED_EDIT_VERSION_UNQUALIFIED")
    if proposal["operation"]!="repaint":
        raise ValueError("TYPED_EDIT_OPERATION_UNQUALIFIED")
    if proposal["declared_tier"]!="P1":
        raise ValueError("TYPED_EDIT_TIER_UNQUALIFIED")
    scope=proposal["target_scope"]
    _exact_keys(scope,{"kind","track_id","start_bar","end_bar"},"TARGET_SCOPE")
    if (scope["kind"]!="track_region" or scope["track_id"]!=target_track
            or type(scope["start_bar"]) is not int or type(scope["end_bar"]) is not int
            or scope["start_bar"] < 1 or scope["end_bar"]<=scope["start_bar"]):
        raise ValueError("TYPED_EDIT_TARGET_SCOPE_INVALID")
    from m045_repaint import bar_sample_window
    canonical=bar_sample_window(song_spec,scope["start_bar"],scope["end_bar"],frame_count)
    if tuple(sample_window)!=canonical:
        raise ValueError("TYPED_EDIT_RATIONAL_WINDOW_CONFLICT")
    a,b=canonical
    _exact_keys(proposal["rational_window"],{"start","end"},"RATIONAL_WINDOW")
    from m045_repaint import RATE
    start=_rational(proposal["rational_window"]["start"])
    end=_rational(proposal["rational_window"]["end"])
    if start!=Fraction(a,RATE) or end!=Fraction(b,RATE):
        raise ValueError("TYPED_EDIT_RATIONAL_WINDOW_CONFLICT")
    if not isinstance(song_spec,dict):
        raise ValueError("TYPED_EDIT_SONGSPEC_INVALID")
    if any(track.get("sonic_lock") is True for track in song_spec.get("tracks",[])):
        raise ValueError("TYPED_EDIT_SONIC_LOCK_TRACK")
    tpq=song_spec["timebase"]["ticks_per_quarter_note"]
    first=(scope["start_bar"]-1)*4*tpq
    last=(scope["end_bar"]-1)*4*tpq
    for section in song_spec.get("structure",{}).get("sections",[]):
        if section.get("sonic_lock") is True:
            low,high=section.get("start_tick"),section.get("end_tick")
            if not _integer(low) or not _integer(high) or high<=low:
                raise ValueError("TYPED_EDIT_SONIC_LOCK_SECTION_INVALID")
            if first<high and low<last:
                raise ValueError("TYPED_EDIT_SONIC_LOCK_SECTION")
    regions=proposal["preserved_scopes"]
    if not isinstance(regions,list):
        raise ValueError("TYPED_EDIT_PRESERVATION_SCOPE_INVALID")
    expected=[{"kind":"audio_region","start_sample":0,"end_sample":a},
              {"kind":"audio_region","start_sample":b,"end_sample":frame_count}]
    expected=[v for v in expected if v["start_sample"]<v["end_sample"]]
    if regions!=expected:
        raise ValueError("TYPED_EDIT_PRESERVATION_SCOPE_MUST_BE_EXACT_OUTSIDE_PCM")
    return {"schema_version":proposal["schema_version"],
            "declared_tier":"P1","validated_sample_window":[a,b],
            "preserved_scopes":expected}

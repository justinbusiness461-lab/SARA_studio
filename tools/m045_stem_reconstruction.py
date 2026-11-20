"""Portable deterministic DSP reconstruction mechanism; Studio owns publishing and revision truth."""
from __future__ import annotations
import hashlib
import io
import json
import math
import re
import struct
import wave

HEX=re.compile(r"^[a-f0-9]{64}$")
RECIPE_FIELDS={"schema_version","source_project_revision_id","production_timeline_digest",
 "stem_artifact_ids","bus_waveshaper","fade_ms","target_peak","sample_rate","channels",
 "sample_count","pcm_quantizer","encoder"}

def _verify(stems,recipe):
    if not isinstance(recipe,dict) or set(recipe)!=RECIPE_FIELDS:
        raise ValueError("MIX_RECIPE_SCHEMA_INVALID")
    if (recipe["schema_version"]!="sara.mix.recipe.v1" or
            recipe["bus_waveshaper"] not in ("none","tanh") or
            recipe["sample_rate"]!=44100 or recipe["channels"]!=2 or
            recipe["pcm_quantizer"]!="signed16_round_nearest_ties_even" or
            recipe["encoder"]!="canonical_pcm16_wav_44" or
            type(recipe["sample_count"]) is not int or not 0<recipe["sample_count"]<=44100*180):
        raise ValueError("MIX_RECIPE_UNQUALIFIED")
    if (not isinstance(recipe["source_project_revision_id"],str) or
            not HEX.fullmatch(recipe["source_project_revision_id"]) or
            not isinstance(recipe["production_timeline_digest"],str) or
            not HEX.fullmatch(recipe["production_timeline_digest"])):
        raise ValueError("MIX_REVISION_IDENTITY_INVALID")
    fade,target=recipe["fade_ms"],recipe["target_peak"]
    if (type(fade) not in (int,float) or not 0<=fade<=1000 or
            type(target) not in (int,float) or not 0<target<=1 or
            not math.isfinite(fade) or not math.isfinite(target)):
        raise ValueError("MIX_BUS_PARAMETERS_INVALID")
    if (not isinstance(stems,list) or not 0<len(stems)<=32 or
            not isinstance(recipe["stem_artifact_ids"],list) or
            len(stems)!=len(recipe["stem_artifact_ids"])):
        raise ValueError("MIX_STEM_COUNT_INVALID")
    for data,digest in zip(stems,recipe["stem_artifact_ids"]):
        if (not isinstance(data,bytes) or len(data)!=recipe["sample_count"]*16
                or not isinstance(digest,str) or not HEX.fullmatch(digest) or
                hashlib.sha256(data).hexdigest()!=digest):
            raise ValueError("MIX_STEM_IDENTITY_OR_ALIGNMENT_INVALID")
    return fade,target

def reconstruct_master(stems,recipe):
    """Decode exactly aligned little-endian interleaved f64, sum in recipe order, then bus."""
    fade,target=_verify(stems,recipe)
    size=recipe["sample_count"]
    channels=size*2
    values=[0.0]*channels
    for data in stems:
        for i,(value,) in enumerate(struct.iter_unpack("<d",data)):
            if not math.isfinite(value):
                raise ValueError("MIX_NONFINITE_STEM")
            values[i]+=value
            if not math.isfinite(values[i]):
                raise ValueError("MIX_NONFINITE_BUS")
    if recipe["bus_waveshaper"]=="tanh":
        values=[math.tanh(v) for v in values]
    fade_frames=min(size//2,int(round(fade*44.1)))
    if fade_frames:
        for i in range(fade_frames):
            # Sample zero and final sample exactly zero.
            envelope=0.5*(1-math.cos(math.pi*i/fade_frames))
            other=0.5*(1-math.cos(math.pi*(fade_frames-1-i)/fade_frames))
            for ch in (0,1):
                values[i*2+ch]*=envelope
                values[(size-fade_frames+i)*2+ch]*=other
    peak=max(map(abs,values))
    scale=target/peak if peak>0 else 1.0
    pcm=bytearray()
    for value in values:
        quantized=max(-32768,min(32767,int(round(value*scale*(32768 if value<0 else 32767)))))
        pcm.extend(struct.pack("<h",quantized))
    result=io.BytesIO()
    with wave.open(result,"wb") as out:
        out.setnchannels(2);out.setsampwidth(2);out.setframerate(44100)
        out.writeframes(pcm)
    return result.getvalue()

def export_two_tier_stems(stems,recipe):
    """Synthetic engine contract only, NOT an authorized Studio multitrack export."""
    master=reconstruct_master(stems,recipe)
    frozen=json.loads(json.dumps(recipe,sort_keys=True,allow_nan=False))
    recipe_bytes=json.dumps(frozen,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    return {
        "reconstruction_stems":{"exact_reconstruction_certified":True,
            "class":"reconstruction_stems","source_identity":frozen["source_project_revision_id"],
            "artifact_digests":frozen["stem_artifact_ids"]},
        "creative_stems":{"exact_reconstruction_certified":False,"class":"creative_stems"},
        "mix_recipe":frozen,
        "mix_recipe_sha256":hashlib.sha256(recipe_bytes).hexdigest(),
        "production_master":{"wav":master,"sha256":hashlib.sha256(master).hexdigest(),
            "sample_rate":44100,"channels":2}}

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
            type(recipe["sample_count"]) is not int or not 0<recipe["sample_count"]<=44100*210):
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

# Round 8: the transport is *on-disk interleaved float64*, not a PCM16 stem.
# A 210 s stereo source is 148,176,000 bytes per source; only the output
# PCM16 WAV is 37,044,044 bytes. This is an internal deterministic DSP layer,
# not a sample asset importer or an alternate project publisher.
def reconstruct_master_to_file(stem_paths, recipe, output_path, *, chunk_frames=16384):
    """Stream a deterministic canonical mix to a durably published PRIVATE WAV.

    Two identical passes avoid retaining whole float64 stems or the float64 bus:
    pass 1 hashes sources and calculates the post-envelope peak, pass 2
    quantizes with the exact global scale. Studio owns any subsequent revision
    publication. No user-supplied files or rights are authorized by this DSP.
    """
    import os
    import stat
    import tempfile
    from contextlib import ExitStack
    from pathlib import Path
    if (not isinstance(recipe, dict) or set(recipe)!=RECIPE_FIELDS or
        recipe.get("schema_version")!="sara.mix.recipe.v1" or
        recipe.get("bus_waveshaper") not in ("none","tanh") or
        recipe.get("sample_rate")!=44100 or recipe.get("channels")!=2 or
        recipe.get("pcm_quantizer")!="signed16_round_nearest_ties_even" or
        recipe.get("encoder")!="canonical_pcm16_wav_44" or
        type(recipe.get("sample_count")) is not int or
        not 0<recipe["sample_count"]<=44100*210 or
        not all(isinstance(recipe.get(k),str) and HEX.fullmatch(recipe[k])
                for k in ("source_project_revision_id","production_timeline_digest"))):
        raise ValueError("MIX_STREAM_RECIPE_UNQUALIFIED")
    if (type(chunk_frames) is not int or not 128<=chunk_frames<=65536 or
        not isinstance(stem_paths,(list,tuple)) or not 0<len(stem_paths)<=32 or
        not isinstance(recipe.get("stem_artifact_ids"),list) or
        len(stem_paths)!=len(recipe["stem_artifact_ids"])):
        raise ValueError("MIX_STREAM_INPUT_LIMITS")
    count=recipe["sample_count"]
    for digest in recipe["stem_artifact_ids"]:
        if not isinstance(digest,str) or not HEX.fullmatch(digest):
            raise ValueError("MIX_STREAM_STEM_DIGEST_INVALID")
    fade,target=recipe.get("fade_ms"),recipe.get("target_peak")
    if (type(fade) not in (float,int) or type(target) not in (float,int) or
        not math.isfinite(fade) or not math.isfinite(target) or
        not 0<=fade<=1000 or not 0<target<=1):
        raise ValueError("MIX_STREAM_BUS_PARAMETERS_INVALID")
    fade_frames=min(count//2,int(round(fade*44.1)))
    expected_bytes=count*16

    def envelope(index):
        factor=1.0
        if fade_frames:
            if index<fade_frames:
                factor=0.5*(1-math.cos(math.pi*index/fade_frames))
            if index>=count-fade_frames:
                i=index-(count-fade_frames)
                factor=0.5*(1-math.cos(math.pi*(fade_frames-1-i)/fade_frames))
        return factor

    def stream_bus(pass_index):
        with ExitStack() as stack:
            sources=[]
            digests=[]
            for path in stem_paths:
                try:
                    fd=os.open(os.fspath(path),os.O_RDONLY|os.O_NOFOLLOW)
                    f=stack.enter_context(os.fdopen(fd,"rb",buffering=0))
                    meta=os.fstat(f.fileno())
                except (OSError,TypeError,ValueError) as exc:
                    raise ValueError("MIX_STREAM_SOURCE_UNSAFE") from exc
                if not stat.S_ISREG(meta.st_mode) or meta.st_size!=expected_bytes:
                    raise ValueError("MIX_STREAM_SOURCE_LENGTH_INVALID")
                sources.append(f);digests.append(hashlib.sha256())
            for start in range(0,count,chunk_frames):
                frames=min(chunk_frames,count-start)
                channel_count=frames*2
                values=[0.0]*channel_count
                for f,h in zip(sources,digests):
                    raw=f.read(frames*16)
                    if len(raw)!=frames*16:
                        raise ValueError("MIX_STREAM_SOURCE_SHORT_READ")
                    h.update(raw)
                    for i,(value,) in enumerate(struct.iter_unpack("<d",raw)):
                        if not math.isfinite(value):
                            raise ValueError("MIX_NONFINITE_STEM")
                        values[i]+=value
                        if not math.isfinite(values[i]):
                            raise ValueError("MIX_NONFINITE_BUS")
                if recipe["bus_waveshaper"]=="tanh":
                    values=[math.tanh(v) for v in values]
                for i in range(frames):
                    e=envelope(start+i)
                    yield (values[2*i]*e, values[2*i+1]*e)
            for f,h,expected in zip(sources,digests,recipe["stem_artifact_ids"]):
                if f.read(1) or h.hexdigest()!=expected:
                    raise ValueError("MIX_STREAM_SOURCE_INTEGRITY_INVALID")
    # Source mismatch must never yield an authority transition; on mismatch
    # any private stage is discarded and no Studio revision is published.
    peak=0.0
    for l,r in stream_bus(1):
        peak=max(peak,abs(l),abs(r))
    scale=target/peak if peak>0 else 1.0
    destination=Path(output_path)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.is_symlink():
        raise ValueError("MIX_STREAM_DESTINATION_SYMLINK")
    fd,tmp=tempfile.mkstemp(prefix=".mix-stage-",suffix=".wav",dir=str(destination.parent))
    try:
        with os.fdopen(fd,"w+b") as staged:
            with wave.open(staged,"wb") as out:
                out.setnchannels(2);out.setsampwidth(2);out.setframerate(44100)
                packed=bytearray()
                for l,r in stream_bus(2):
                    for v in (l,r):
                        q=max(-32768,min(32767,int(round(v*scale*(32768 if v<0 else 32767)))))
                        packed.extend(struct.pack("<h",q))
                    if len(packed)>=chunk_frames*4:
                        out.writeframesraw(packed);packed.clear()
                if packed:out.writeframesraw(packed)
            staged.flush()
            os.fsync(staged.fileno())
        # Independently check size and complete SHA-256 of staged physical WAV.
        sha=hashlib.sha256()
        with open(tmp,"rb") as f:
            for part in iter(lambda:f.read(1024*1024),b""):sha.update(part)
        byte_length=os.stat(tmp).st_size
        if byte_length != 44+count*4:
            raise ValueError("MIX_STREAM_WAV_FRAME_LENGTH_MISMATCH")
        os.replace(tmp,destination)
        parent_fd=os.open(str(destination.parent),os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(parent_fd)
        finally:os.close(parent_fd)
        return {"sha256":sha.hexdigest(),"sample_count":count,
                "byte_length":byte_length,"sample_rate":44100,"channels":2,
                "peak_after_bus":peak}
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

"""R10-B canonical read-only, revision-bound DAW archive.

No new music authority: read the selected immutable Studio project/revision,
source/CAS membership and exact durable render attempt. Caller-supplied recipe
is not trusted: require a prior Studio render attempt with the SAME digest and
independently reconstruct the exact selected WAV before packaging dry stems.
"""
from __future__ import annotations
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import tempfile
import wave
import xml.etree.ElementTree as ET
import zipfile
from m045_audio_to_midi import _track
from m045_stem_reconstruction import reconstruct_master_to_file

PPQ=480
MAX_DAW_SOURCE_BYTES=512*1024*1024

class DawExportHold(ValueError):
    """No complete attributable dry reconstruction, never pretend stems exist."""

class DawSourceDenied(PermissionError):
    """An authenticated principal tried to select unbound artifact/source."""


def _serial(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def _zip_file(name):
    info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
    info.compress_type=zipfile.ZIP_STORED
    info.external_attr=0o600<<16
    return info


def _write_bytes(archive,name,data,hashes):
    archive.writestr(_zip_file(name),data)
    hashes[name]=hashlib.sha256(data).hexdigest()


def _write_source_stream(archive,name,source,hashes,expected_sha):
    sha=hashlib.sha256()
    with source.open('rb') as handle,archive.open(_zip_file(name),'w',force_zip64=True) as entry:
        for chunk in iter(lambda:handle.read(1024*1024),b''):
            sha.update(chunk);entry.write(chunk)
    if sha.hexdigest()!=expected_sha:
        raise DawExportHold('DAW_SOURCE_CHANGED_DURING_EXPORT')
    hashes[name]=sha.hexdigest()


def _preview_wav_from_float64(source,destination,sample_count):
    """DAW-friendly audition stem only; signed16 conversion is NOT exact mix."""
    with source.open('rb') as inp,wave.open(str(destination),'wb') as out:
        out.setnchannels(2);out.setsampwidth(2);out.setframerate(44100)
        for start in range(0,sample_count,32768):
            count=min(32768,sample_count-start)
            chunk=inp.read(count*16)
            if len(chunk)!=count*16:raise DawExportHold('DAW_STEM_FRAME_SHORT_READ')
            buf=bytearray()
            for (value,) in struct.iter_unpack('<d',chunk):
                if not math.isfinite(value):raise DawExportHold('DAW_NONFINITE_STEM')
                buf.extend(struct.pack('<h',max(-32768,min(32767,round(value*32767)))))
            out.writeframesraw(buf)
        if inp.read(1):raise DawExportHold('DAW_STEM_ALIGNMENT_INVALID')


def _extract_notes(spec,max_frames):
    tb=spec['timebase'];bpm=tb.get('initial_bpm',120);source_ppq=tb.get('ticks_per_quarter_note',960)
    if (tb.get('meter')!='4/4' or
            type(bpm) not in (int,float) or not math.isfinite(bpm) or not 40<=bpm<=240
            or type(source_ppq) is not int or not 1<=source_ppq<=9600
            or any(key in tb for key in ('tempoMap','tempo_map','tempoEvents'))):
        raise DawExportHold('DAW_TEMPO_MAP_UNQUALIFIED')
    tracks=[];n=0
    for t in spec.get('tracks',[]):
        selected=[]
        for e in t.get('events',[]):
            if e.get('type') not in ('NOTE','MIDI_NOTE'):
                if e.get('type') in ('NOTE_ON','NOTE_OFF','PITCHED_NOTE'):
                    raise DawExportHold('DAW_PITCHED_EVENT_SCHEMA_UNQUALIFIED')
                continue
            if any(type(e.get(k)) is not int for k in ('tick','duration_ticks','midi_note','velocity')):
                raise DawExportHold('DAW_NOTE_FIELDS_INVALID')
            start,duration,pitch,velocity=(e[k] for k in ('tick','duration_ticks','midi_note','velocity'))
            if (start<0 or duration<=0 or not 0<=pitch<=127 or not 1<=velocity<=127
                    or start*PPQ%source_ppq or duration*PPQ%source_ppq):
                raise DawExportHold('DAW_NOTE_TIMEBASE_UNREPRESENTABLE_AT_480_PPQ')
            a=start*PPQ//source_ppq;length=duration*PPQ//source_ppq
            if (a+length)*60*44100/(float(bpm)*PPQ)>max_frames+1:
                raise DawExportHold('DAW_NOTE_OUTSIDE_MASTER_TIMELINE')
            selected.append((a,a+length,pitch,velocity))
        selected.sort()
        if any(selected[i][0]<selected[i-1][1] for i in range(1,len(selected))):
            raise DawExportHold('DAW_OVERLAPPING_PITCH_EVENTS_UNSUPPORTED')
        tracks.append((str(t.get('name') or t.get('track_id') or 'track')[:100],selected))
        n+=len(selected)
    return bpm,tracks,n


def _midi_xml(spec,max_frames):
    bpm,tracks,count=_extract_notes(spec,max_frames)
    micro=round(60000000/bpm)
    if not 1<=micro<=0xFFFFFF:raise DawExportHold('DAW_TEMPO_INVALID')
    midi_tracks=[_track([(0,0,b'\xff\x51\x03'+micro.to_bytes(3,'big'))])]
    if not tracks:tracks=[('Empty SongSpec',[])]
    for title,notes in tracks:
        events=[]
        for start,end,pitch,velocity in notes:
            events.append((start,2,bytes((0x90,pitch,velocity))))
            events.append((end,1,bytes((0x80,pitch,0))))
        midi_tracks.append(_track(events))
    midi=b'MThd'+struct.pack('>IHHH',6,1,len(midi_tracks),PPQ)+b''.join(midi_tracks)
    root=ET.Element('score-partwise',{'version':'3.1'})
    ET.SubElement(ET.SubElement(root,'work'),'work-title').text=str(spec.get('title') or 'S.A.R.A. Studio')[:200]
    plist=ET.SubElement(root,'part-list')
    pitches=['C','C','D','D','E','F','F','G','G','A','A','B']
    for track_index,(title,notes) in enumerate(tracks):
        ident='P'+str(track_index+1)
        ET.SubElement(ET.SubElement(plist,'score-part',{'id':ident}),'part-name').text=title
        part=ET.SubElement(root,'part',{'id':ident})
        end=max((q[1] for q in notes),default=PPQ*4)
        bars=(end+PPQ*4-1)//(PPQ*4)
        if bars>3000:raise DawExportHold('DAW_SCORE_TOO_LONG')
        measures=[ET.SubElement(part,'measure',{'number':str(i+1)}) for i in range(bars)]
        att=ET.SubElement(measures[0],'attributes')
        ET.SubElement(att,'divisions').text=str(PPQ)
        tm=ET.SubElement(att,'time');ET.SubElement(tm,'beats').text='4';ET.SubElement(tm,'beat-type').text='4'
        def add_span(start,end,pitch=None):
            cursor=start
            while cursor<end:
                nxt=min(end,((cursor//(PPQ*4))+1)*(PPQ*4))
                note=ET.SubElement(measures[cursor//(PPQ*4)],'note')
                if pitch is None:ET.SubElement(note,'rest')
                else:
                    pn=ET.SubElement(note,'pitch');pc=pitch%12
                    ET.SubElement(pn,'step').text=pitches[pc]
                    if pc in (1,3,6,8,10):ET.SubElement(pn,'alter').text='1'
                    ET.SubElement(pn,'octave').text=str(pitch//12-1)
                    if nxt<end:ET.SubElement(note,'tie',{'type':'start'})
                    if cursor>start:ET.SubElement(note,'tie',{'type':'stop'})
                ET.SubElement(note,'duration').text=str(nxt-cursor)
                cursor=nxt
        cursor=0
        for start,end,pitch,velocity in notes:
            if start>cursor:add_span(cursor,start)
            add_span(start,end,pitch)
            cursor=end
        if cursor<bars*PPQ*4:add_span(cursor,bars*PPQ*4)
    xml=b'<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(root,encoding='utf-8')+b'\n'
    return midi,xml,bpm,count


def export_authorized_daw_bundle(root,request,principal_id,destination):
    """Write deterministic private archive to ephemeral file; no revision mutation."""
    from studio_server import (project_operation,project_audio_bytes,project_owner_directory,
        artifact_bytes,artifact_digest_verified,ProjectConflict,project_json)
    if not isinstance(request,dict) or set(request)!={'projectId','revisionId','artifactId','mixRecipe'}:
        raise DawExportHold('DAW_EXACT_RECIPE_REQUIRED')
    root=Path(root).resolve()
    pid,rid,master_sha,recipe=(request[k] for k in ('projectId','revisionId','artifactId','mixRecipe'))
    selected=project_operation(root,{'projectId':pid,'revisionId':rid},principal_id=principal_id)
    if master_sha not in selected['revision']['outputArtifactIds']:
        raise DawSourceDenied('DAW_SELECTED_ARTIFACT_NOT_REVISION_BOUND')
    master=project_audio_bytes(root,{'projectId':pid,'revisionId':rid,'artifactId':master_sha},principal_id=principal_id)
    if len(master)>40*1024*1024:raise DawExportHold('DAW_MASTER_BOUND_EXCEEDED')
    try:
        with wave.open(io.BytesIO(master),'rb') as audio:
            sample_count=audio.getnframes()
            if (audio.getframerate()!=44100 or audio.getnchannels()!=2 or
                  audio.getsampwidth()!=2 or audio.getcomptype()!='NONE'):
                raise DawExportHold('DAW_MASTER_PCM16_44K1_REQUIRED')
    except (wave.Error,EOFError) as e:raise DawExportHold('DAW_MASTER_UNDECODABLE') from e
    parent_id=selected['revision'].get('parentRevisionId')
    if not parent_id:raise DawExportHold('DAW_PARENT_SOURCE_REQUIRED')
    source=project_operation(root,{'projectId':pid,'revisionId':parent_id},principal_id=principal_id)
    if (not isinstance(recipe,dict) or recipe.get('source_project_revision_id')!=parent_id
            or recipe.get('production_timeline_digest')!=source['revision']['productionTimelineDigest']
            or recipe.get('sample_count')!=sample_count):
        raise DawExportHold('DAW_MIX_RECIPE_TIMELINE_OR_REVISION_MISMATCH')
    stem_ids=recipe.get('stem_artifact_ids')
    if not isinstance(stem_ids,list) or not stem_ids or len(stem_ids)>32 or stem_ids!=sorted(stem_ids):
        raise DawExportHold('DAW_STEM_ORDER_INVALID')
    if not set(stem_ids)<=set(source['revision']['sourceAssetDigests']):
        raise DawSourceDenied('DAW_STEM_NOT_REVISION_BOUND')
    directory=project_owner_directory(root,pid,principal_id,allow_create=False)
    operation=selected['revision'].get('operation')
    if not isinstance(operation,dict):raise DawExportHold('DAW_RENDER_ATTEMPT_UNPROVEN')
    path=directory/'render-attempts'/(str(operation.get('id',''))+'.json')
    if path.is_symlink() or not path.is_file():raise DawExportHold('DAW_DURABLE_RENDER_ATTEMPT_MISSING')
    attempt=json.loads(path.read_text())
    provenance=attempt.get('masterProvenance')
    recipe_sha=hashlib.sha256(project_json(recipe)).hexdigest()
    if (attempt.get('operationId')!=operation['id'] or
            attempt.get('operationMeaningDigest')!=operation['meaningDigest'] or
            attempt.get('artifactDigest')!=master_sha or
            attempt.get('sourceRevisionId')!=parent_id or
            not isinstance(provenance,dict) or
            provenance.get('artifact_sha256')!=master_sha or
            provenance.get('revision_id')!=parent_id or
            provenance.get('project_id')!=pid or
            provenance.get('preservation_tier')!='P3' or
            provenance.get('rights_status')!='UNVERIFIED_HELD' or
            provenance.get('parent_artifact_sha256s')!=source['revision']['outputArtifactIds'] or
            attempt.get('state') not in ('REVISION_BOUND','HISTORICALLY_BOUND') or
            attempt.get('intendedCas')!=f'objects/{master_sha[:2]}/{master_sha}' or
            provenance.get('transform_chain')!=[{'operation':'sara.mix.recipe.v1',
                'recipeSha256':recipe_sha,'stemArtifactIds':stem_ids,
                'sampleCount':sample_count}]):
        raise DawExportHold('DAW_ORIGINAL_RECIPE_PROVENANCE_NOT_ATTESTED')
    original_meaning={'projectId':pid,'expectedCurrentRevisionId':parent_id,
        'songSpec':source['songSpec'],
        'sourceAssetDigests':source['revision']['sourceAssetDigests'],
        'outputArtifactIds':[master_sha],
        'operationContext':{'kind':'render','sourceRevisionId':parent_id,
            'masterProvenance':provenance}}
    if hashlib.sha256(project_json(original_meaning)).hexdigest()!=operation['meaningDigest']:
        raise DawExportHold('DAW_RENDER_ATTEMPT_MEANING_TAMPERED')
    source_paths=[];total=0
    for digest in stem_ids:
        artifact_digest_verified(root,digest)
        path=root/'objects'/digest[:2]/digest
        total+=path.stat().st_size
        source_paths.append(path)
    if total>MAX_DAW_SOURCE_BYTES:
        raise DawExportHold('DAW_STEM_BUNDLE_DISK_LIMIT')
    midi,musicxml,bpm,note_count=_midi_xml(selected['songSpec'],sample_count)
    with tempfile.TemporaryDirectory(prefix='.sara-daw-proof-',dir=directory) as temp:
        temp=Path(temp);rebuild=temp/'reconstructed.wav'
        measured=reconstruct_master_to_file(source_paths,recipe,rebuild)
        if measured['sha256']!=master_sha or rebuild.read_bytes()!=master:
            raise DawExportHold('DAW_RECONSTRUCTED_MASTER_NOT_EXACT')
        hashes={}
        with zipfile.ZipFile(destination,'w',allowZip64=True) as bundle:
            _write_bytes(bundle,'master_44k1_16b.wav',master,hashes)
            _write_bytes(bundle,'SongSpec.json',artifact_bytes(root,selected['revision']['songSpecDigest']),hashes)
            _write_bytes(bundle,'ProductionTimeline.json',artifact_bytes(root,selected['revision']['productionTimelineDigest']),hashes)
            _write_bytes(bundle,'sara.mix.recipe.v1.json',project_json(recipe),hashes)
            _write_bytes(bundle,'scorecore_arrangement.mid',midi,hashes)
            _write_bytes(bundle,'scorecore_arrangement.musicxml',musicxml,hashes)
            _write_bytes(bundle,'tempo_map.json',_serial({'schema':'sara.tempo.map.v1',
                'ticksPerQuarter':PPQ,'events':[{'tick':0,'bpm':bpm}]}),hashes)
            for index,(stem,stem_id) in enumerate(zip(source_paths,stem_ids),1):
                # Raw f64 is exact mix source; audition WAV is an explicitly
                # non-reconstructive creative stem after quantization.
                _write_source_stream(bundle,f'stems/reconstruction_{index:02d}.f64le',stem,hashes,stem_id)
                creative=temp/f'creative_{index:02d}.wav'
                _preview_wav_from_float64(stem,creative,sample_count)
                creative_sha=hashlib.sha256(creative.read_bytes()).hexdigest()
                _write_source_stream(bundle,f'stems/creative_{index:02d}.wav',creative,hashes,creative_sha)
            manifest={'schema':'sara.daw.bundle.v1','projectId':pid,'projectRevisionId':rid,
                'sourceProjectRevisionId':parent_id,'masterArtifactId':master_sha,
                'songSpecDigest':selected['revision']['songSpecDigest'],
                'productionTimelineDigest':selected['revision']['productionTimelineDigest'],
                'originalRenderOperationId':attempt['operationId'],
                'mixRecipeSha256':recipe_sha,'stemArtifactIds':stem_ids,
                'sampleRateHz':44100,'channels':2,'sampleCount':sample_count,
                'midiPpq':PPQ,'tempoBpm':bpm,'noteCount':note_count,
                'reconstructionExact':True,'creativeStemsExact':False,
                'reconstructionSourceFormat':'interleaved_le_float64_stereo',
                'reconstructionRequiresRecipe':True,
                'musicXmlPolyphonySupported':False,'pitchedNotesInvented':False,
                'preservationTier':'P3','rightsStatus':'UNVERIFIED_HELD',
                'releaseCleared':False,'creativeApproved':False,
                'fileSha256':hashes}
            _write_bytes(bundle,'daw_manifest.json',_serial(manifest),{})
        # The canonical SongSpec, source mix and master remain immutable.
        for digest in stem_ids:artifact_digest_verified(root,digest)
    return {'state':'DAW_BUNDLE_PREPARED_PRIVATE','projectRevisionId':rid,
        'masterArtifactId':master_sha,'fileCount':len(hashes)+1,
        'reconstructionExact':True,'releaseCleared':False,'creativeApproved':False}


def verify_authorized_daw_bundle(root,request,principal_id,submitted):
    """R11-B: untrusted ZIP gets comparison only; no imported source authority.

    Re-export the selected historical Studio revision from its durable attempt
    and compare canonical ZIP bytes in streaming chunks. Never unpack, trust
    filenames, source code, or purported signatures from the uploaded archive.
    A match independently proves every source stem was reconstructed and all
    canonical per-entry checksums match; no revision or CAS object is created.
    """
    from pathlib import Path
    from contextlib import nullcontext
    if not isinstance(request,dict) or set(request)!={'projectId','revisionId','artifactId','mixRecipe'}:
        raise DawExportHold('DAW_VERIFY_EXACT_SOURCE_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='sara-verify-daw-') as scratch:
        canonical_path=Path(scratch)/'owner.zip'
        export_authorized_daw_bundle(root,request,principal_id,canonical_path)
        if isinstance(submitted,(bytes,bytearray)):
            source=io.BytesIO(submitted)
        elif isinstance(submitted,Path):
            if submitted.is_symlink() or not submitted.is_file():
                raise DawExportHold('DAW_SUBMITTED_UNSAFE_PATH')
            source=submitted.open('rb')
        else:raise DawExportHold('DAW_SUBMITTED_UNSUPPORTED')
        digest=hashlib.sha256()
        with source as incoming,canonical_path.open('rb') as original:
            while True:
                target=original.read(1024*1024)
                part=incoming.read(1024*1024)
                if part!=target:raise DawExportHold('DAW_ARCHIVE_NOT_CANONICAL_OR_TAMPERED')
                if not part:break
                digest.update(part)
        with zipfile.ZipFile(canonical_path) as package:
            manifest=json.loads(package.read('daw_manifest.json'))
            hashes=manifest['fileSha256']
            if set(hashes)|{'daw_manifest.json'}!=set(package.namelist()):
                raise DawExportHold('DAW_MANIFEST_FILE_SET_UNQUALIFIED')
            for name,sha in hashes.items():
                with package.open(name) as item:
                    h=hashlib.sha256()
                    for block in iter(lambda:item.read(1024*1024),b''):h.update(block)
                    if h.hexdigest()!=sha:raise DawExportHold('DAW_ARCHIVE_ENTRY_INTEGRITY_FAILED')
        return {'schema':'sara.daw.bundle.verify.receipt.v1',
                'state':'VERIFIED_UNMODIFIED_BUNDLE','projectRevisionId':request['revisionId'],
                'masterArtifactId':request['artifactId'],'archiveSha256':digest.hexdigest(),
                'verifiedEntries':len(hashes)+1,'reconstructionExact':True,
                'importCommitted':False,'newRevisionCommitted':False,
                'releaseCleared':False,'creativeApproved':False}

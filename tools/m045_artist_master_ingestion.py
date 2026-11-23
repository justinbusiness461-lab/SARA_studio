"""Studio-owned real artist-master admission: offline, host attested, revision bound.

No local path, digest, browser claim, imported master or trusted-title label
creates artist ownership. Only an explicitly installed host catalog authority
may attest rights and stable project identity. Musical timing, commercial
publication and creative approval are independent later gates.

The source container (MP3/Opus/M4A/WAV) and the 48k stereo PCM16 playback WAV
are immutable CAS assets. A separately decoded 44.1kHz PCM identity is observed
and reported; it is not silently promoted to the selected audio artifact.

All projects, revisions, currentness, and playable media are managed by
studio_server's existing canonical ProjectManifest/ProjectRevision/CAS graph.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import tempfile
import wave

from studio_server import (
    _publish_cas_exact, atomic_write_bytes, durable_mkdir,
    project_audio_bytes, project_namespace_fence,
    project_operation, project_owner_directory,
    validate_render_audio_bytes, ProjectConflict,
)

TITLES = ('Turn The Noise Back On', 'If This Is All I Get', 'Outlaws and Echoes')
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_DECODED_BYTES = 70 * 1024 * 1024
MAX_DURATION_SEC = 330
_HEX = re.compile(r'[0-9a-f]{64}\Z')
_PROJECT = re.compile(r'[0-9a-f]{32}\Z')


class ArtistMasterDenied(PermissionError):
    """No media or rights publication is authorized by this outcome."""


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _source_bytes(source_path):
    path = Path(source_path)
    if not path.is_file() or path.is_symlink():
        raise ArtistMasterDenied('EXACT_LOCAL_ARTIST_MASTER_FILE_REQUIRED')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 44 <= info.st_size <= MAX_SOURCE_BYTES:
            raise ArtistMasterDenied('ARTIST_MASTER_SIZE_NOT_QUALIFIED')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
        if len(raw) != info.st_size:
            raise ArtistMasterDenied('ARTIST_MASTER_CHANGED_DURING_READ')
        return path.resolve(), raw
    finally:
        os.close(fd)


def _call_host_catalog(principal_id, title, source_sha, host_catalog_lookup):
    if title not in TITLES or not callable(host_catalog_lookup):
        raise ArtistMasterDenied('ARTIST_MASTER_HOST_CATALOG_REQUIRED')
    entry = host_catalog_lookup(principal_id, title, source_sha)
    if not isinstance(entry, dict):
        raise ArtistMasterDenied('ARTIST_MASTER_CATALOG_MISSING')
    required = {'title':title,'principalId':principal_id,
                'sourceSha256':source_sha}
    if any(entry.get(k)!=v for k,v in required.items()):
        raise ArtistMasterDenied('ARTIST_MASTER_RIGHTS_NOT_HOST_VERIFIED')
    rights=entry.get('rightsStatus')
    if rights=='UNVERIFIED_HELD':
        # Host attestation permits bounded private review, never a release.
        # A browser flag, raw digest or Drive possession is not this policy.
        if (entry.get('privatePilotAuthorized') is not True
            or entry.get('commercialReleaseAuthorized') is not False):
            raise ArtistMasterDenied('HELD_MASTER_HOST_PRIVATE_RIGHTS_REQUIRED')
    elif rights!='ARTIST_OWNED':
        raise ArtistMasterDenied('ARTIST_MASTER_RIGHTS_NOT_HOST_VERIFIED')
    if (not isinstance(entry.get('projectId'),str)
        or not _PROJECT.fullmatch(entry['projectId'])
        or not isinstance(entry.get('rightsEvidenceSha256'),str)
        or not _HEX.fullmatch(entry['rightsEvidenceSha256'])):
        raise ArtistMasterDenied('ARTIST_MASTER_RIGHTS_EVIDENCE_MISSING')
    # Only the host callback is trusted, never a browser-supplied attestation.
    return entry


def _decode_rates(verified_source_bytes):
    if (not isinstance(verified_source_bytes, bytes)
        or not 44<=len(verified_source_bytes)<=MAX_SOURCE_BYTES):
        raise ArtistMasterDenied('ARTIST_MASTER_EXACT_VERIFIED_BYTES_REQUIRED')
    # Never let ffprobe/ffmpeg reopen the untrusted original pathname after
    # its SHA was checked. Immutable admission is derived from this exact
    # byte snapshot only, written into a private unique temp directory.
    try:
        with tempfile.TemporaryDirectory(prefix='sara-master-physical-') as work:
            local_source=Path(work)/'source-verified.media'
            with open(local_source,'xb') as stream:
                stream.write(verified_source_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            cmd=['ffprobe','-v','error','-select_streams','a:0',
                 '-show_entries','stream=codec_name,sample_rate,channels:format=duration',
                 '-of','json',str(local_source)]
            scan=subprocess.run(cmd,capture_output=True,timeout=22,check=True)
            observed=json.loads(scan.stdout)
            streams=observed.get('streams') or []
            seconds=float(observed['format']['duration'])
            if (len(streams)!=1 or not 0<seconds<=MAX_DURATION_SEC
                or streams[0].get('codec_name') not in
                   ('mp3','opus','aac','flac','pcm_s16le','alac')):
                raise ArtistMasterDenied('ARTIST_MASTER_CODEC_OR_DURATION_UNQUALIFIED')
            rates={}
            for rate in (44100,48000):
                output=Path(work)/(str(rate)+'.wav')
                subprocess.run(['ffmpeg','-hide_banner','-nostdin','-v','error','-i',
                    str(local_source),'-map','0:a:0','-vn','-sn','-dn','-ac','2',
                    '-ar',str(rate),'-c:a','pcm_s16le','-y',str(output)],
                    capture_output=True,timeout=120,check=True)
                if not output.is_file() or not 44<=output.stat().st_size<=MAX_DECODED_BYTES:
                    raise ArtistMasterDenied('ARTIST_MASTER_PCM_SIZE_UNQUALIFIED')
                data=output.read_bytes()
                validate_render_audio_bytes(data)
                with wave.open(io.BytesIO(data),'rb') as w:
                    frames=w.getnframes()
                    pcm=w.readframes(frames)
                    if (w.getframerate()!=rate or w.getnchannels()!=2
                        or w.getsampwidth()!=2 or len(pcm)!=frames*4):
                        raise ArtistMasterDenied('ARTIST_MASTER_PCM_IDENTITY_INVALID')
                if abs(frames/rate-seconds)>1.5:
                    raise ArtistMasterDenied('ARTIST_MASTER_DECODE_DURATION_DRIFT')
                rates[rate]={'bytes':data,'frames':frames,'pcmSha256':_digest(pcm),
                             'wavSha256':_digest(data)}
            return {'sourceCodec':streams[0]['codec_name'],
                'inputSampleRate':int(streams[0]['sample_rate']),
                'inputChannels':int(streams[0]['channels']),
                'reportedDurationSec':seconds,'byRate':rates}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            ValueError,KeyError,TypeError,OverflowError) as exc:
        raise ArtistMasterDenied('ARTIST_MASTER_PHYSICAL_DECODE_FAILED') from exc


def inspect_host_attested_master(*, principal_id, title, source_path,
                                 host_catalog_lookup):
    source,raw=_source_bytes(source_path)
    sha=_digest(raw)
    entry=_call_host_catalog(principal_id,title,sha,host_catalog_lookup)
    physical=_decode_rates(raw)
    pilot=None
    pilot_sections=[]
    if entry['rightsStatus']=='UNVERIFIED_HELD':
        # Only host catalog policy determines musical sample coordinates.
        # The legacy pilotSection remains valid; new multi-window authority
        # supports one 19s S15 and additional distinct 20s private pilots.
        proposed_many=entry.get('pilotSections')
        if proposed_many is not None:
            if ('pilotSection' in entry or not isinstance(proposed_many,list)
                or not 1<=len(proposed_many)<=4):
                raise ArtistMasterDenied('HELD_MASTER_HOST_SECTION_LIST_INVALID')
        else:
            proposed_many=[entry.get('pilotSection')]
        frames=physical['byRate'][44100]['frames']
        previous_end=0
        used=set()
        for proposed in proposed_many:
            if (not isinstance(proposed,dict)
                or set(proposed)!={'id','sampleRate','startSample','endSampleExclusive'}
                or not isinstance(proposed['id'],str)
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}',proposed['id'])
                or proposed['id'] in used
                or type(proposed['sampleRate']) is not int or proposed['sampleRate']!=44100
                or type(proposed['startSample']) is not int
                or type(proposed['endSampleExclusive']) is not int
                or not previous_end<=proposed['startSample']<proposed['endSampleExclusive']<=frames
                or proposed['endSampleExclusive']-proposed['startSample'] not in (19*44100,20*44100)):
                raise ArtistMasterDenied('HELD_MASTER_HOST_SAMPLE_WINDOW_NOT_QUALIFIED')
            pilot_sections.append({'id':proposed['id'],'sample_rate':44100,
                 'start_sample':proposed['startSample'],
                 'end_sample_exclusive':proposed['endSampleExclusive']})
            used.add(proposed['id']);previous_end=proposed['endSampleExclusive']
        pilot=pilot_sections[0]
    return {'entry':entry,'source':source,'raw':raw,'sha':sha,
            'physical':physical,'pilotSection':pilot,'pilotSections':pilot_sections}


def _unqualified_import_spec(title,source_sha,codec,rights_status='ARTIST_OWNED',pilot_section=None,pilot_sections=None):
    # This neutral scaffold intentionally provides NO sections or events.
    # It is *not* a guessed BPM or accepted musical timing interpretation.
    # The 120 BPM internal coordinate placeholder must never support a grant.
    spec={'song_id':'artist-master-'+source_sha[:16], 'title':title,
          'artistMasterImport':{
             'sourceSha256':source_sha,'sourceCodec':codec,
             'musicalTimingQualified':False,
             'timebaseIsUnqualifiedPlaceholder':True,
             'creativeApproved':False,'productionQualified':False},
          'timebase':{'initial_bpm':120,'ticks_per_quarter_note':960},
          'structure':{'sections':[]},'tracks':[]}
    if rights_status=='UNVERIFIED_HELD':
        spec['artistMasterImport'].update({
            'rightsStatus':'UNVERIFIED_HELD',
            'privatePilotAuthorized':True,
            'commercialReleaseAuthorized':False,
            'playbackSampleRate':44100,
            'preservationTier':'P0_SOURCE_BYTES'})
        # Studio's canonical project_operation derives immutable
        # ProductionTimeline.sections from SongSpec.structure.sections.
        # These are exact sample coordinates; the internal 120 BPM
        # timebase remains explicitly unqualified for musical inference.
        spec['structure']['sections']=list(pilot_sections or [pilot_section])
    return spec


def _stage_record(directory, filename, document):
    staged=directory/filename
    durable_mkdir(directory)
    if staged.is_symlink():
        raise ArtistMasterDenied('ARTIST_MASTER_INGEST_STAGE_UNSAFE')
    encoded=json.dumps(document,sort_keys=True,separators=(',',':')).encode()
    if staged.exists():
        prior=json.loads(staged.read_bytes())
        for k,v in document.items():
            if k!='state' and prior.get(k)!=v:
                raise ArtistMasterDenied('ARTIST_MASTER_INGEST_IDENTITY_CONFLICT')
        return staged,prior
    atomic_write_bytes(staged,encoded)
    project_namespace_fence(directory,directory.parents[2])
    if staged.read_bytes()!=encoded:
        raise ArtistMasterDenied('ARTIST_MASTER_DURABILITY_READBACK_FAILED')
    return staged,document


def ingest_original_master(*,root,principal_id,title,source_path,host_catalog_lookup):
    """Host-entrypoint. Never install as an unauthenticated HTTP ingestion API."""
    detail=inspect_host_attested_master(principal_id=principal_id,title=title,
           source_path=source_path,host_catalog_lookup=host_catalog_lookup)
    return _commit_preflight(root,principal_id,title,detail)


def _commit_preflight(root,principal_id,title,detail):
    """Write only after source, rights and both decodes cross admission gates."""
    root=Path(root).resolve()
    catalog,physical=detail['entry'],detail['physical']
    pid=catalog['projectId']
    source_sha=detail['sha']
    held=catalog['rightsStatus']=='UNVERIFIED_HELD'
    rate=44100 if held else 48000
    playback=physical['byRate'][rate]
    artifact=playback['wavSha256']
    spec=_unqualified_import_spec(title,source_sha,physical['sourceCodec'],
           catalog['rightsStatus'],detail.get('pilotSection'),detail.get('pilotSections'))

    # PREPARING is durable *before* any canonical project transition.
    # On reentry, ALWAYS reread the real project graph first; stage alone
    # cannot confer artifact authority, revision selection or creator rights.
    directory=project_owner_directory(root,pid,principal_id,allow_create=True)
    stage=directory/('artist-master-held-intakes' if held else 'artist-master-intakes')
    identity={'schemaVersion':'sara.master.ingest.host.v1','state':'PREPARING',
        'projectId':pid,'principalId':principal_id,'title':title,
        'rightsStatus':'UNVERIFIED_HELD' if held else 'ARTIST_ORIGINAL',
        'rightsEvidenceSha256':catalog['rightsEvidenceSha256'],
        'sourceSha256':source_sha,'playbackWavSha256':artifact,
        'decoded48000PcmSha256':physical['byRate'][48000]['pcmSha256'],
        'decoded44100PcmSha256':physical['byRate'][44100]['pcmSha256']}
    if held:
        identity.update({'privatePilotAuthorized':True,
                         'commercialReleaseAuthorized':False,
                         'pilotSection':detail['pilotSection']})
        if len(detail.get('pilotSections',[]))>1:
            identity['pilotSections']=detail['pilotSections']
    stage_file,prior=_stage_record(stage,source_sha+'.json',identity)
    try:
        selected=project_operation(root,{'projectId':pid},principal_id=principal_id)
    except (ValueError,FileNotFoundError):
        selected=None

    if prior['state']=='COMMITTED':
        rid=prior.get('committedRevisionId')
        if not isinstance(rid,str) or not _HEX.fullmatch(rid):
            raise ArtistMasterDenied('ARTIST_MASTER_COMMIT_RECEIPT_INVALID')
        historical=project_operation(root,{'projectId':pid,'revisionId':rid},
                                     principal_id=principal_id)
        if (historical['songSpec']!=spec
            or source_sha not in historical['revision']['sourceAssetDigests']
            or artifact not in historical['revision']['outputArtifactIds']):
            raise ArtistMasterDenied('ARTIST_MASTER_HISTORY_DRIFT')
        lawful=project_audio_bytes(root,{'projectId':pid,
              'revisionId':rid,'artifactId':artifact},principal_id=principal_id)
        if _digest(lawful)!=artifact:
            raise ArtistMasterDenied('ARTIST_MASTER_HISTORICAL_PLAYBACK_DRIFT')
        return {'status':'ALREADY_IMPORTED','projectId':pid,
                'revisionId':rid,'artifactId':artifact}

    if prior['state']!='PREPARING':
        raise ArtistMasterDenied('ARTIST_MASTER_AMBIGUOUS_STAGE_STATE')
    if selected is None:
        initial=project_operation(root,{'projectId':pid,
                      'expectedCurrentRevisionId':None,'songSpec':spec},
                      commit=True,principal_id=principal_id)
        r0=initial['revision']['revisionId']
    else:
        rev=selected['revision']
        if (selected['songSpec']==spec and
            source_sha in rev['sourceAssetDigests'] and
            artifact in rev['outputArtifactIds']):
            rid=rev['revisionId']
            lawful=project_audio_bytes(root,{'projectId':pid,
                     'revisionId':rid,'artifactId':artifact},
                     principal_id=principal_id)
            if _digest(lawful)!=artifact:
                raise ArtistMasterDenied('ARTIST_MASTER_EXISTING_READBACK_FAILED')
            atomic_write_bytes(stage_file,json.dumps({
                **identity,'state':'COMMITTED','committedRevisionId':rid
            },sort_keys=True,separators=(',',':')).encode())
            return {'status':'ALREADY_IMPORTED','projectId':pid,
                    'revisionId':rid,'artifactId':artifact}
        if (selected['songSpec']!=spec or rev['sourceAssetDigests']
            or rev['outputArtifactIds'] or rev['parentRevisionId'] is not None):
            raise ArtistMasterDenied('ARTIST_MASTER_PROJECT_ALREADY_HAS_DIFFERENT_CURRENT')
        # R0 was durably committed; CAS/media step may have faulted before R1.
        r0=rev['revisionId']
    # Durable PREPARING identity precedes both immutable CAS objects.
    _publish_cas_exact(root,source_sha,detail['raw'])
    _publish_cas_exact(root,artifact,playback['bytes'])
    r1=project_operation(root,{'projectId':pid,
        'expectedCurrentRevisionId':r0,'songSpec':spec,
        'sourceAssetDigests':[source_sha],
        'outputArtifactIds':[artifact]},commit=True,principal_id=principal_id)
    rid=r1['revision']['revisionId']
    lawful=project_audio_bytes(root,{'projectId':pid,'revisionId':rid,
        'artifactId':artifact},principal_id=principal_id)
    if _digest(lawful)!=artifact:
        raise ArtistMasterDenied('ARTIST_MASTER_LAWFUL_READBACK_MISMATCH')
    atomic_write_bytes(stage_file,json.dumps({
        **identity,'state':'COMMITTED','committedRevisionId':rid
    },sort_keys=True,separators=(',',':')).encode())
    return {'status':'IMPORTED_UNAPPROVED','title':title,'projectId':pid,
        'revisionId':rid,'artifactId':artifact,'sourceSha256':source_sha,
        'rightsStatus':'UNVERIFIED_HELD' if held else 'ARTIST_ORIGINAL',
        'privatePilotAuthorized':held,'commercialReleaseAuthorized':False,
        'rightsEvidenceSha256':catalog['rightsEvidenceSha256'],
        'sourceCodec':physical['sourceCodec'],
        'audioSampleRate':rate,'audioChannels':2,
        'decoded48000Frames':physical['byRate'][48000]['frames'],
        'decoded48000PcmSha256':physical['byRate'][48000]['pcmSha256'],
        'decoded44100Frames':physical['byRate'][44100]['frames'],
        'decoded44100PcmSha256':physical['byRate'][44100]['pcmSha256'],
        'musicalTimingQualified':False,'creativeApproved':False,
        'productionQualified':False,'externalSpendUsd':0.0}


def commit_verified_edit(*,root,principal_id,project_id,
                         expected_r1_revision_id,edited_wav_path,host_edit_verifier):
    """R2 is a REAL host-verified edited WAV, never a duplicated/rebranded R1."""
    if not callable(host_edit_verifier):
        raise ArtistMasterDenied('MASTER_EDIT_HOST_VERIFIER_REQUIRED')
    root=Path(root).resolve()
    current=project_operation(root,{'projectId':project_id},principal_id=principal_id)
    if current['manifest']['currentRevisionId']!=expected_r1_revision_id:
        raise ArtistMasterDenied('MASTER_EDIT_SOURCE_REVISION_STALE')
    source= current['revision']['outputArtifactIds']
    if len(source)!=1:raise ArtistMasterDenied('MASTER_EDIT_EXACT_SOURCE_REQUIRED')
    r1_audio=project_audio_bytes(root,{'projectId':project_id,
        'revisionId':expected_r1_revision_id,'artifactId':source[0]},
        principal_id=principal_id)
    path,output=_source_bytes(edited_wav_path)
    validate_render_audio_bytes(output)
    with wave.open(io.BytesIO(output),'rb') as w:
        if (w.getframerate() not in (44100,48000)
            or w.getnchannels()!=2 or w.getsampwidth()!=2):
            raise ArtistMasterDenied('MASTER_EDIT_OUTPUT_PCM_INVALID')
    edited_sha=_digest(output)
    if edited_sha==source[0]:
        raise ArtistMasterDenied('MASTER_EDIT_UNCHANGED_AUDIO_NOT_R2')
    evidence={'principalId':principal_id,'projectId':project_id,
              'sourceRevisionId':expected_r1_revision_id,
              'sourceAudioSha256':_digest(r1_audio),'editedAudioSha256':edited_sha}
    if host_edit_verifier(evidence) is not True:
        raise ArtistMasterDenied('MASTER_EDIT_PROVENANCE_NOT_HOST_VERIFIED')
    directory=project_owner_directory(root,project_id,principal_id,allow_create=False)
    edit_stage=directory/'artist-master-edits'/ (edited_sha+'.json')
    already_existed=edit_stage.exists()
    _stage_record(directory/'artist-master-edits',edited_sha+'.json',
                  {'schemaVersion':'sara.master.edit.host.v1','state':'PREPARING',
                   **evidence})
    if already_existed:
        raise ArtistMasterDenied('MASTER_EDIT_RECONCILIATION_REQUIRED')
    _publish_cas_exact(root,edited_sha,output)
    r2=project_operation(root,{'projectId':project_id,
       'expectedCurrentRevisionId':expected_r1_revision_id,
       'songSpec':current['songSpec'],
       'sourceAssetDigests':current['revision']['sourceAssetDigests'],
       'outputArtifactIds':[edited_sha]},commit=True,principal_id=principal_id)
    exact=project_audio_bytes(root,{'projectId':project_id,
       'revisionId':r2['revision']['revisionId'],'artifactId':edited_sha},
       principal_id=principal_id)
    if exact!=output:
        raise ArtistMasterDenied('MASTER_EDIT_LAWFUL_AUDIO_READBACK_MISMATCH')
    return {'state':'EDITED_UNAPPROVED','projectId':project_id,
            'sourceRevisionId':expected_r1_revision_id,
            'revisionId':r2['revision']['revisionId'],
            'artifactId':edited_sha,'preservationTier':'P3',
            'creativeApproved':False,'productionQualified':False}


def issue_accepted_master_grant(*,root,principal_id,project_id,revision_id,
          artifact_id,cinema_project_id,section_id,host_signing_ring,
          host_rights_policy,now=None):
    """Reuse exact Studio issuer; reject unqualified audio/tempo/rights."""
    from m045_soundtrack_grant import HostSigningKeyRing, issue_authorized_grant
    if not isinstance(host_signing_ring,HostSigningKeyRing):
        raise ArtistMasterDenied('MASTER_GRANT_HOST_SIGNER_REQUIRED')
    observed=project_operation(root,{'projectId':project_id,'revisionId':revision_id},
                               principal_id=principal_id)
    meta=observed['songSpec'].get('artistMasterImport') or {}
    held=meta.get('rightsStatus')=='UNVERIFIED_HELD'
    if not held and (meta.get('timebaseIsUnqualifiedPlaceholder') is not False
        or meta.get('musicalTimingQualified') is not True
        or not observed['productionTimeline'].get('sections')):
        raise ArtistMasterDenied('MASTER_GRANT_MUSICAL_TIMELINE_NOT_VERIFIED')
    if held and (meta.get('privatePilotAuthorized') is not True
                 or meta.get('commercialReleaseAuthorized') is not False
                 or not observed['productionTimeline'].get('sections')):
        raise ArtistMasterDenied('MASTER_GRANT_PRIVATE_SAMPLE_WINDOW_UNQUALIFIED')
    if not callable(host_rights_policy):
        raise ArtistMasterDenied('MASTER_GRANT_HOST_RIGHTS_REQUIRED')
    request={'projectId':project_id,'revisionId':revision_id,
             'artifactId':artifact_id,'cinemaProjectId':cinema_project_id,
             'sectionId':section_id,'fps':'24/1'}
    if held:
        request['scope']='private_cinema_pilot'
    return issue_authorized_grant(root=root,principal_id=principal_id,
         ring=host_signing_ring,rights_policy=host_rights_policy,
         read_project=project_operation,read_audio=project_audio_bytes,
         request=request,now=now)


def ingest_three_song_batch(*,root,principal_id,sources_by_title,host_catalog_lookup):
    """Host-only three-source preflight before ANY Studio project is created.

    A preflight failure produces no partial song revisions or false grants.
    A mid-commit fault leaves exact per-project durable identities, never
    an automatically retried remote effect or an arbitrary CAS owner.
    """
    if (not isinstance(sources_by_title,dict)
        or set(sources_by_title)!=set(TITLES)
        or not callable(host_catalog_lookup)):
        raise ArtistMasterDenied('THREE_SONG_EXACT_HOST_INTAKE_REQUIRED')
    paths=[str(Path(sources_by_title[t]).resolve()) for t in TITLES]
    if len(set(paths))!=3:
        raise ArtistMasterDenied('THREE_SONG_INDEPENDENT_FILES_REQUIRED')
    inspected=[inspect_host_attested_master(principal_id=principal_id,
        title=title,source_path=sources_by_title[title],
        host_catalog_lookup=host_catalog_lookup) for title in TITLES]
    if (len({e['sha'] for e in inspected})!=3
        or len({e['entry']['projectId'] for e in inspected})!=3):
        raise ArtistMasterDenied('THREE_SONG_DISTINCT_SOURCE_OR_PROJECT_REQUIRED')
    songs=[_commit_preflight(root,principal_id,title,e)
           for title,e in zip(TITLES,inspected)]
    return {'schemaVersion':'sara.studio.three_song_import.v1',
            'status':'THREE_MASTERS_IMPORTED_UNAPPROVED',
            'songs':songs,'issuedGrantCount':0,'grants':[],
            'productionQualified':False,'creativeApproved':False,
            'externalSpendUsd':0.0}


def make_unavailable_three_song_manifest(source_vantage):
    if not isinstance(source_vantage,str) or not source_vantage:
        raise ValueError('EVIDENCE_VANTAGE_REQUIRED')
    return {'schemaVersion':'sara.studio.three_song_grants.v1',
            'state':'BLOCKED_NO_EXECUTOR_SOURCE_BYTES',
            'sourceVantage':source_vantage,
            'productionQualified':False,'creativeApproved':False,
            'issuedGrantCount':0,'grants':[],
            'songs':[{'title':title,'sourceFileBytesAvailable':False,
                      'acceptedStudioProjectRevisionId':None,
                      'acceptedAudioArtifactId':None,'grantStatus':'NOT_ISSUED',
                      'rightsStatus':'UNVERIFIED_IN_THIS_EXECUTOR'}
                     for title in TITLES]}
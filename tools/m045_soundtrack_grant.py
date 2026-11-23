"""Studio-owned HVC-003 AcceptedSoundtrackGrant issuer (review candidate).

This module ONLY runs inside an authenticated Studio host and receives the
existing project/revision/audio authorities as function dependencies. Client
claims, raw CAS digests and request-supplied sample coordinates confer zero
music rights or currentness. A production host MUST pin keys + rights policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Mapping
import hashlib
import hmac
import io
import json
import math
import re
import secrets
import struct
import time
import wave


class GrantIssuerDenied(PermissionError):
    pass


@dataclass(frozen=True)
class HostSigningKeyRing:
    active_key_id: str
    keys_by_id: Mapping[str, bytes]
    revoked_key_ids: frozenset[str]

    def require_active_key(self):
        key=self.keys_by_id.get(self.active_key_id)
        if (not isinstance(self.active_key_id,str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,128}',self.active_key_id)
                or self.active_key_id in self.revoked_key_ids or not isinstance(key,bytes) or len(key)<32):
            raise GrantIssuerDenied('HOST_SIGNING_KEY_UNAVAILABLE')
        return key


def _canonical(fields):
    return json.dumps(fields,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def verify_issued_grant_signature(grant: Mapping, ring: HostSigningKeyRing) -> bool:
    try:
        if grant.get('signer_key_id')!=ring.active_key_id:return False
        key=ring.require_active_key()
        sig=grant['signature']
        if not isinstance(sig,str) or not re.fullmatch(r'[0-9a-f]{64}',sig):return False
        expected=hmac.new(key,_canonical({k:v for k,v in grant.items() if k!='signature'}),hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected,sig)
    except (ValueError,TypeError,KeyError,GrantIssuerDenied):
        return False


def _wav_identity(data: bytes):
    try:
        with wave.open(io.BytesIO(data),'rb') as wf:
            channels=wf.getnchannels();width=wf.getsampwidth();rate=wf.getframerate();samples=wf.getnframes()
            if (wf.getcomptype()!='NONE' or channels not in (1,2) or width!=2 or rate not in (44100,48000)
                    or samples<=0):
                raise GrantIssuerDenied('AUDIO_PCM_FORMAT_NOT_ADMITTED')
            pcm=wf.readframes(samples)
            if len(pcm)!=samples*channels*width:
                raise GrantIssuerDenied('TRUNCATED_ACCEPTED_AUDIO')
        return rate,channels,samples,hashlib.sha256(pcm).hexdigest()
    except (EOFError, wave.Error) as e:
        raise GrantIssuerDenied('ACCEPTED_AUDIO_NOT_DECODABLE') from e


def _section_bounds(timeline, section_id,rate,total_samples):
    tb=timeline.get('timebase',{})
    bpm=tb.get('initial_bpm');tpqn=tb.get('ticks_per_quarter_note')
    if type(bpm) is not int or not 30<=bpm<=300 or type(tpqn) is not int or not 1<=tpqn<=100000:
        raise GrantIssuerDenied('CANONICAL_TEMPO_CLOCK_UNAVAILABLE')
    sections=timeline.get('sections',[])
    if not isinstance(sections,list):raise GrantIssuerDenied('CANONICAL_SECTIONS_UNAVAILABLE')
    hits=[s for s in sections if isinstance(s,dict) and s.get('id')==section_id]
    if len(hits)!=1:raise GrantIssuerDenied('UNKNOWN_OR_AMBIGUOUS_CANONICAL_SECTION')
    sec=hits[0]
    first,last=sec.get('start_tick'),sec.get('end_tick')
    if type(first) is not int or type(last) is not int or not 0<=first<last:
        raise GrantIssuerDenied('INVALID_SECTION_TIMELINE')
    # Exact floor integer arithmetic. Only canonical ProductionTimeline ticks may
    # determine song offset; the request cannot provide sample bounds.
    start=(first*60*rate)//(bpm*tpqn)
    section_end=(last*60*rate)//(bpm*tpqn)
    end=min(total_samples,section_end,start+15*rate)
    if not 0<=start<end<=total_samples:raise GrantIssuerDenied('SOURCE_SECTION_OUTSIDE_ACCEPTED_AUDIO')
    return start,end


def _frame_covering_window(start,end,rate,num,den):
    # A video cover may contain sub-frame lead/tail; source audio [start,end)
    # MUST stay exact and must not be silently repositioned to video frames.
    return start*num//(rate*den),(end*num+rate*den-1)//(rate*den)


def issue_authorized_grant(*,root,request: Mapping,principal_id:str,ring:HostSigningKeyRing,
        read_project:Callable,read_audio:Callable,rights_policy:Callable,now=None):
    if not isinstance(request,Mapping):raise GrantIssuerDenied('OBJECT_REQUIRED')
    if any(k in request for k in ('resolved_start_sample','resolved_end_sample_exclusive',
                                   'resolved_start_frame','resolved_end_frame_exclusive','source_pcm_frames',
                                   'sample_rate','channels','rights_status','signature','signer_key_id',
                                   'private_pilot_authorized','approved_start_sample',
                                   'approved_end_sample_exclusive','commercial_release_authorized')):
        raise GrantIssuerDenied('CLIENT_SAMPLE_COORDINATES_DENIED')
    pid=request.get('projectId');rid=request.get('revisionId');aid=request.get('artifactId')
    cinema=request.get('cinemaProjectId');section_id=request.get('sectionId')
    for name,txt,pattern in [('STUDIO_PROJECT',pid,r'[a-f0-9]{32}'),
                            ('STUDIO_REVISION',rid,r'[a-f0-9]{64}'),
                            ('ACCEPTED_ARTIFACT',aid,r'[a-f0-9]{64}'),
                            ('CINEMA_PROJECT',cinema,r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}'),
                            ('SECTION_ID',section_id,r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}')]:
        if not isinstance(txt,str) or not re.fullmatch(pattern,txt):
            raise GrantIssuerDenied('INVALID_'+name)
    scope=request.get('scope')
    if scope not in (None,'private_cinema_pilot'):
        raise GrantIssuerDenied('UNSUPPORTED_SOUNDTRACK_GRANT_SCOPE')
    fps=request.get('fps','24/1')
    if fps not in ('24/1','30000/1001'):raise GrantIssuerDenied('UNSUPPORTED_VIDEO_FPS')
    fps_num,fps_den=map(int,fps.split('/'))
    ring.require_active_key()
    if not callable(read_project) or not callable(read_audio) or not callable(rights_policy):
        raise GrantIssuerDenied('HOST_AUTHORITIES_REQUIRED')
    # Read the actual Studio graph and lawful revision→artifact membership before
    # touching CAS bytes; arbitrary artifact discovery is never authorization.
    observed=read_project(root,{'projectId':pid,'revisionId':rid},principal_id=principal_id)
    if (not isinstance(observed,Mapping) or observed.get('revision',{}).get('revisionId')!=rid
            or observed.get('manifest',{}).get('projectId')!=pid
            or observed.get('revision',{}).get('projectId')!=pid):
        raise GrantIssuerDenied('PROJECT_REVISION_READBACK_MISMATCH')
    audio=read_audio(root,{'projectId':pid,'revisionId':rid,'artifactId':aid},principal_id=principal_id)
    if not isinstance(audio,bytes) or hashlib.sha256(audio).hexdigest()!=aid:
        raise GrantIssuerDenied('ACCEPTED_AUDIO_ARTIFACT_MISMATCH')
    rate,channels,count,pcm_digest=_wav_identity(audio)
    rights=rights_policy(pid,rid,aid,principal_id)
    if scope=='private_cinema_pilot':
        # Only the host-owned rights callback may permit unverified audio for
        # a bounded, non-commercial private preview. Client flags do nothing.
        if (not isinstance(rights,Mapping)
            or rights.get('rights_status')!='UNVERIFIED_HELD'
            or rights.get('private_pilot_authorized') is not True
            or rights.get('principal_id')!=principal_id
            or rights.get('revision_id')!=rid
            or rights.get('artifact_id')!=aid
            or rights.get('cinema_project_id')!=cinema):
            raise GrantIssuerDenied('PRIVATE_PILOT_HOST_RIGHTS_NOT_ATTESTED')
        # Reuse Studio's revision-backed timeline; do not infer exact samples
        # from the unqualified 120 BPM coordinate scaffold. Host must also
        # independently attest the *same* source window, by exact integers.
        sections=observed.get('productionTimeline',{}).get('sections',[])
        if not isinstance(sections,list):
            raise GrantIssuerDenied('CANONICAL_SAMPLE_SECTIONS_UNAVAILABLE')
        matches=[sec for sec in sections if isinstance(sec,Mapping)
                 and sec.get('id')==section_id]
        if len(matches)!=1:
            raise GrantIssuerDenied('UNKNOWN_OR_AMBIGUOUS_CANONICAL_SECTION')
        sec=matches[0]
        start,end=sec.get('start_sample'),sec.get('end_sample_exclusive')
        # Host-owned multi-window policy: each requested section is independently
        # matched to its immutable timeline coordinates. Legacy flat one-window
        # policies remain supported; client-supplied coordinates never are.
        approved=rights
        if 'approved_sections' in rights:
            window_map=rights['approved_sections']
            if not isinstance(window_map,Mapping):
                raise GrantIssuerDenied('PRIVATE_PILOT_APPROVED_SECTION_MAP_INVALID')
            approved=window_map.get(section_id)
            if not isinstance(approved,Mapping):
                raise GrantIssuerDenied('PRIVATE_PILOT_SECTION_NOT_HOST_ATTESTED')
            approved_start=approved.get('start_sample')
            approved_end=approved.get('end_sample_exclusive')
        else:
            approved_start=approved.get('approved_start_sample')
            approved_end=approved.get('approved_end_sample_exclusive')
        if (type(start) is not int or type(end) is not int
            or type(sec.get('sample_rate')) is not int
            or sec['sample_rate']!=rate or not 0<=start<end<=count
            or end-start not in (19*rate,20*rate)
            or type(approved_start) is not int
            or type(approved_end) is not int
            or approved_start!=start or approved_end!=end):
            raise GrantIssuerDenied('PRIVATE_PILOT_EXACT_WINDOW_NOT_HOST_APPROVED')
        rights_status='UNVERIFIED_HELD'
    else:
        # Existing commercially cleared / licensed issuer path unchanged.
        if rights not in ('ARTIST_OWNED','LICENSED_FOR_CINEMA'):
            raise GrantIssuerDenied('RIGHTS_NOT_HOST_ATTESTED')
        rights_status=rights
        start,end=_section_bounds(observed['productionTimeline'],section_id,rate,count)
    frame0,frame1=_frame_covering_window(start,end,rate,fps_num,fps_den)
    now=float(time.time() if now is None else now)
    if not math.isfinite(now) or now<0:raise GrantIssuerDenied('INVALID_HOST_TIME')
    grant={'schema_version':'sara.soundtrack.grant.v1','issuer':'sara_studio',
           'audience':'pulseforge_cinema','signer_key_id':ring.active_key_id,
           'grant_id':'sara-grant-'+secrets.token_hex(16),
           'studio_project_id':pid,'source_project_revision_id':rid,
           'accepted_audio_artifact_id':aid,'wav_sha256':aid,
           'decoded_pcm_sha256':pcm_digest,'sample_rate':rate,'channels':channels,
           'source_pcm_frames':count,'resolved_start_sample':start,
           'resolved_end_sample_exclusive':end,'resolved_start_frame':frame0,
           'resolved_end_frame_exclusive':frame1,'fps_numerator':fps_num,
           'fps_denominator':fps_den,'cinema_project_id':cinema,
           'rights_status':rights_status,
           'production_timeline_digest':observed['revision'].get('productionTimelineDigest'),
           'lyric_timeline_revision_digest':observed['revision'].get('lyricTimelineDigest'),
           'section_id':section_id,'issued_at':now,'expires_at':now+300,
           'claim_ceiling':'SIGNED_ISSUER_AUTHORIZED_NOT_CINEMA_MEASURED_OR_APPROVED'}
    if scope=='private_cinema_pilot':
        grant.update({'scope':'private_cinema_pilot',
                      'commercial_release_authorized':False,
                      'claim_ceiling':'PRIVATE_NONCOMMERCIAL_CINEMA_PILOT_ONLY_NOT_RELEASE_CLEARED'})
    # DJ marks are not playable scratch evidence; no synthetic DJ cue truth.
    signed=hmac.new(ring.require_active_key(),_canonical(grant),hashlib.sha256).hexdigest()
    return {**grant,'signature':signed}
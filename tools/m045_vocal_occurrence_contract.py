"""R30 Studio-owned *projection* of lyric words to provisional vocal occurrences.

This module does not persist a LyricTimelineRevision, add project authority, or
qualify acoustic word timing. Input `studio_project` MUST come from an already
lawfully authorized Studio project/open operation; this pure projection is NOT
an authorization endpoint. Studio retains immutable lyric and revision truth.

A candidate can be inspected in private, but not promoted as a verified
word-onset timeline or passed to cinema as acoustic truth. Independent acoustic
annotation evidence and a rightful Studio issuer are intentionally required
for the future verification transition; they are NOT implemented here.
"""

from __future__ import annotations

from typing import Any


class VocalOccurrenceHeld(ValueError):
    """A proposal is stale, invalid, unverifiable, or claims unearned truth."""


_ALLOWED_PROPOSAL = frozenset({
    'expectedProjectRevisionId', 'expectedLyricRevisionId',
    'expectedSourceArtifactId', 'expectedSourceAudioDigest', 'occurrences',
})
_ALLOWED_OCCURRENCE = frozenset({
    'wordId', 'proposedOnsetSample', 'proposedEndSample', 'method',
})
_UNVERIFIED_METHODS = frozenset({'candidate_audio_assisted', 'human_unreviewed'})


def _dict(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise VocalOccurrenceHeld(f'{label} must be a mapping')
    return value


def _natural(value: Any) -> bool:
    return type(value) is int and value >= 0


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def project_occurrences(studio_project: dict, proposal: dict) -> dict:
    """Create a read-only, unverified candidate subordinate to exact Studio IDs.

    No caller-provided truth fields are copied into a qualified status. The
    underlying Studio operation must have authenticated project/revision/audio
    ancestry before this helper runs; this function only checks consistency.
    """
    project = _dict(studio_project, 'studio project')
    request = _dict(proposal, 'proposal')
    if set(request) != _ALLOWED_PROPOSAL:
        raise VocalOccurrenceHeld('unexpected or missing proposal field')
    manifest = _dict(project.get('manifest'), 'project manifest')
    revision = _dict(project.get('revision'), 'project revision')
    lyric = _dict(project.get('lyricTimeline'), 'lyric timeline')
    if not (_nonempty(manifest.get('projectId')) and
            manifest['projectId'] == revision.get('projectId')):
        raise VocalOccurrenceHeld('Studio project identity inconsistent')
    if not (_nonempty(revision.get('revisionId')) and
            request['expectedProjectRevisionId'] == revision['revisionId']):
        raise VocalOccurrenceHeld('STALE_PROJECT_REVISION')
    if not (_nonempty(lyric.get('revisionId')) and
            request['expectedLyricRevisionId'] == lyric['revisionId']):
        raise VocalOccurrenceHeld('STALE_LYRIC_REVISION')
    if not (_nonempty(lyric.get('sourceArtifactId')) and
            request['expectedSourceArtifactId'] == lyric['sourceArtifactId']):
        raise VocalOccurrenceHeld('SOURCE_ARTIFACT_IDENTITY_CHANGED')
    if not (_nonempty(lyric.get('sourceAudioDigest')) and
            request['expectedSourceAudioDigest'] == lyric['sourceAudioDigest']):
        raise VocalOccurrenceHeld('DECODED_AUDIO_IDENTITY_CHANGED')
    if not (_positive(lyric.get('sourceSampleRate')) and
            type(lyric.get('sourceChannels')) is int and lyric['sourceChannels'] in (1, 2) and
            _positive(lyric.get('decodedFrameCount'))):
        raise VocalOccurrenceHeld('invalid Studio sample-clock identity')
    if lyric.get('status') not in ('corrected', 'guided_candidate'):
        raise VocalOccurrenceHeld('VOCAL_ONSET_UNVERIFIED: no Studio lyric candidate')
    studio_words = lyric.get('words')
    if not isinstance(studio_words, list) or not studio_words or len(studio_words) > 256:
        raise VocalOccurrenceHeld('VOCAL_ONSET_UNVERIFIED: no bounded Studio words')
    word_by_id = {}
    for word in studio_words:
        w = _dict(word, 'Studio lyric word')
        wid = w.get('id')
        if not _nonempty(wid) or wid in word_by_id or not _nonempty(w.get('text')):
            raise VocalOccurrenceHeld('invalid Studio lyric word identity')
        a, b = w.get('decodedSampleStart'), w.get('decodedSampleEnd')
        if not (_natural(a) and _positive(b) and a < b <= lyric['decodedFrameCount']):
            raise VocalOccurrenceHeld('invalid Studio lyric word sample bounds')
        word_by_id[wid] = w
    inputs = request['occurrences']
    if not isinstance(inputs, list) or not 0 < len(inputs) <= 256:
        raise VocalOccurrenceHeld('nonempty bounded occurrence subset required')
    results, seen = [], set()
    previous_start = -1
    for value in inputs:
        row = _dict(value, 'provisional occurrence')
        if set(row) != _ALLOWED_OCCURRENCE:
            raise VocalOccurrenceHeld('unsupported/provenance-claim occurrence field')
        wid = row['wordId']
        if not isinstance(wid, str) or wid not in word_by_id or wid in seen:
            raise VocalOccurrenceHeld('unrecognized/duplicate Studio occurrence ID')
        if not isinstance(row.get('method'), str) or row['method'] not in _UNVERIFIED_METHODS:
            raise VocalOccurrenceHeld('unverified alignment method required')
        start, end = row['proposedOnsetSample'], row['proposedEndSample']
        s = word_by_id[wid]
        a, b = s['decodedSampleStart'], s['decodedSampleEnd']
        if not (_natural(start) and _positive(end) and a <= start < end <= b
                and start > previous_start):
            raise VocalOccurrenceHeld('candidate timing outside Studio word bounds')
        seen.add(wid)
        previous_start = start
        results.append({
            'wordId': wid, 'wordText': s['text'],
            'proposedOnsetSample': start, 'proposedEndSample': end,
            'method': row['method'], 'verificationState': 'VOCAL_ONSET_UNVERIFIED',
        })
    return {
        'schemaVersion': 'studio.vocalOccurrenceProjection.candidate.v1',
        'projectId': manifest['projectId'],
        'projectRevisionId': revision['revisionId'],
        'lyricTimelineRevisionId': lyric['revisionId'],
        'sourceArtifactId': lyric['sourceArtifactId'],
        'sourceAudioDigest': lyric['sourceAudioDigest'],
        'sourceSampleRate': lyric['sourceSampleRate'],
        'decodedFrameCount': lyric['decodedFrameCount'],
        'candidateOccurrences': results,
        'verificationState': 'VOCAL_ONSET_UNVERIFIED',
        'productionQualified': False,
        'creativeApproved': False,
        'commercialReleaseAuthorized': False,
    }


def require_verified_vocal_onsets(projection: dict) -> None:
    """Fail closed until trusted Studio acoustic-attestation issuer exists.

    The presence of arbitrary fields or an untrusted `verified` boolean can
    never turn a candidate into a certified LyricTimelineRevision.
    """
    _dict(projection, 'projection')
    raise VocalOccurrenceHeld('VOCAL_ONSET_UNVERIFIED: trusted Studio evidence issuer required')

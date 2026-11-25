"""Fail-closed, test-side Studio R25 private real-media receipt verification.

This is *not* a host rights issuer or source of music truth. Use only after an
already-authorized Studio project/read operation; verify the project graph and
lawful media readbacks before the browser harness declares real-media mode.
Synthetic unit-test fixtures never count as successful real-media execution.
"""
from __future__ import annotations
import hashlib
import io
import re
import wave

# Independently decoded and source-fingerprinted real masters. These are
# comparisons for R25's exact *fixed* test cohort, never project authority.
EXPECTED_MASTERS = {
    'Turn The Noise Back On': {
        'sourceSha256': 'ea55f2178c735a45b28d0416d7f8e04dc5243fff93ce4aa00d530844a23c1627',
        'wavSha256': '6dcf6984e2899eb694507009b7743872fbb84ae0a30a64f68d922acbd1d8b980',
        'pcmSha256': 'e2f0208c39cede2033178aff049d4b4bb4fbae7f33c656e5f5dc5d07a6bc064d',
        'frames': 13069476,
    },
    'If This Is All I Get': {
        'sourceSha256': '4832c5c311acd6645346fbd5e25ab50422894b43a568a9dd27a5b50f8425c74f',
        'wavSha256': 'd889ccf2f55ac4b59c242b2377b8bbf3ea9f1310357816a343805522ba99c025',
        'pcmSha256': '5c13dbcf0b59b56e691ea0a77d18b831f60158cf280c141fc81519cc5ae9612f',
        'frames': 12789596,
    },
    'Outlaws and Echoes': {
        'sourceSha256': '5f34b55921cf805096956471ac9e2ee2606c69c8818540a914c0fd01d38feb8d',
        'wavSha256': '871a091d2f5b0a03f7f0a4f2917901b84ed42ba24efadae4ec1f635bc388e2a6',
        'pcmSha256': '00388e5dadf019b2cf878b7e7ed658e599e20b63b3118dab85957a5b511c794b',
        'frames': 9632036,
    },
}

class StrictStagingDenied(ValueError):
    """The browser fixture must not claim strict real-media success."""

_HEX64 = re.compile(r'[0-9a-f]{64}\Z')
_HEX32 = re.compile(r'[0-9a-f]{32}\Z')


def _hex(value, pattern):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _wav(data: bytes):
    try:
        if not isinstance(data, bytes):
            raise ValueError('not bytes')
        with wave.open(io.BytesIO(data), 'rb') as file:
            if (file.getframerate(), file.getnchannels(), file.getsampwidth(),
                    file.getcomptype()) != (44100, 2, 2, 'NONE'):
                raise ValueError('not 44.1-kHz PCM16 stereo')
            frames = file.getnframes()
            pcm = file.readframes(frames)
            if len(pcm) != frames * 4:
                raise ValueError('incomplete decoded samples')
    except (ValueError, EOFError, wave.Error) as exc:
        raise StrictStagingDenied('R32_WAV_INVALID') from exc
    return frames, hashlib.sha256(pcm).hexdigest(), hashlib.sha256(data).hexdigest()


def _read(operation, root, request, principal, label):
    try:
        result = operation(root, request, principal_id=principal)
    except (PermissionError, FileNotFoundError, ValueError, KeyError, OSError) as exc:
        raise StrictStagingDenied(label) from exc
    return result


def verify_real_staging(root, principal, originals, latest, read_project, read_audio):
    """Checks fixed real-master bytes, Studio ancestry, and lawful R2 CAS readback.

    Important: this procedure is a test precondition, not a grant or approval.
    Its absence from production creates no product operation or project state.
    """
    if (not isinstance(originals, list) or len(originals) != len(EXPECTED_MASTERS)
        or any(not isinstance(row, dict) for row in originals)
        or {r.get('title') for r in originals} != set(EXPECTED_MASTERS)):
        raise StrictStagingDenied('R32_REAL_MEDIA_INVENTORY_INVALID')
    first = None
    for row in originals:
        expected = EXPECTED_MASTERS[row['title']]
        if (row.get('sourceSha256') != expected['sourceSha256']
            or row.get('artifactId') != expected['wavSha256']
            or type(row.get('decoded44100Frames')) is not int
            or row['decoded44100Frames'] != expected['frames']
            or row.get('decoded44100PcmSha256') != expected['pcmSha256']
            or not _hex(row.get('projectId'), _HEX32)
            or not _hex(row.get('revisionId'), _HEX64)):
            raise StrictStagingDenied('R32_REAL_MEDIA_SOURCE_IDENTITY_MISMATCH')
        if (row.get('rightsStatus') != 'UNVERIFIED_HELD'
            or row.get('privatePilotAuthorized') is not True
            or row.get('commercialReleaseAuthorized') is not False):
            raise StrictStagingDenied('R32_REAL_MEDIA_RIGHTS_HELD_REQUIRED')
        historical = _read(read_project, root,
            {'projectId': row['projectId'], 'revisionId': row['revisionId']},
            principal, 'R32_LAWFUL_PROJECT_READ_DENIED')
        if not isinstance(historical, dict):
            raise StrictStagingDenied('R32_LAWFUL_PROJECT_READ_DENIED')
        revision = historical.get('revision') or {}
        spec = (historical.get('songSpec') or {}).get('artistMasterImport') or {}
        if (revision.get('revisionId') != row['revisionId']
            or revision.get('projectId') != row['projectId']
            or expected['sourceSha256'] not in revision.get('sourceAssetDigests', [])
            or row['artifactId'] not in revision.get('outputArtifactIds', [])
            or spec.get('sourceSha256') != expected['sourceSha256']):
            raise StrictStagingDenied('R32_REVISION_SOURCE_BINDING_MISMATCH')
        if (spec.get('rightsStatus') != 'UNVERIFIED_HELD'
            or spec.get('privatePilotAuthorized') is not True
            or spec.get('commercialReleaseAuthorized') is not False):
            raise StrictStagingDenied('R32_REAL_MEDIA_RIGHTS_HELD_REQUIRED')
        wav = _read(read_audio, root, {'projectId': row['projectId'],
            'revisionId': row['revisionId'], 'artifactId': row['artifactId']},
            principal, 'R32_LAWFUL_AUDIO_READ_DENIED')
        frames, pcm_sha, wav_sha = _wav(wav)
        if frames != expected['frames'] or pcm_sha != expected['pcmSha256'] or wav_sha != expected['wavSha256']:
            raise StrictStagingDenied('R32_REAL_MEDIA_WAV_IDENTITY_MISMATCH')
        if row['title'] == 'Turn The Noise Back On':
            first = row
    if not isinstance(latest, dict) or first is None:
        raise StrictStagingDenied('R32_R2_PROVENANCE_MISSING')
    if (latest.get('state') != 'EDITED_UNAPPROVED'
        or latest.get('creativeApproved') is not False
        or latest.get('productionQualified') is not False
        or latest.get('projectId') != first['projectId']
        or latest.get('sourceRevisionId') != first['revisionId']
        or not _hex(latest.get('revisionId'), _HEX64)
        or not _hex(latest.get('artifactId'), _HEX64)
        or latest['revisionId'] == first['revisionId']
        or latest['artifactId'] == first['artifactId']):
        raise StrictStagingDenied('R32_R2_PROVENANCE_UNVERIFIED')
    selected = _read(read_project, root, {'projectId': first['projectId']},
        principal, 'R32_LAWFUL_R2_PROJECT_READ_DENIED')
    if (not isinstance(selected, dict)
        or (selected.get('manifest') or {}).get('currentRevisionId') != latest['revisionId']):
        raise StrictStagingDenied('R32_R2_CURRENT_REVISION_MISMATCH')
    rev = selected.get('revision') or {}
    if (rev.get('revisionId') != latest['revisionId']
        or rev.get('parentRevisionId') != first['revisionId']
        or rev.get('projectId') != first['projectId']
        or first['sourceSha256'] not in rev.get('sourceAssetDigests', [])
        or latest['artifactId'] not in rev.get('outputArtifactIds', [])):
        raise StrictStagingDenied('R32_R2_ANCESTRY_MISMATCH')
    decoded = _read(read_audio, root, {'projectId':first['projectId'],
        'revisionId':latest['revisionId'],'artifactId':latest['artifactId']},
        principal, 'R32_LAWFUL_R2_AUDIO_READ_DENIED')
    frames, _, digest = _wav(decoded)
    if frames != EXPECTED_MASTERS[first['title']]['frames'] or digest != latest['artifactId']:
        raise StrictStagingDenied('R32_R2_WAV_IDENTITY_MISMATCH')
    return {'verifiedMasterCount':3,'r1R2RevisionBound':True,
        'productionQualified':False,'commercialReleaseAuthorized':False}

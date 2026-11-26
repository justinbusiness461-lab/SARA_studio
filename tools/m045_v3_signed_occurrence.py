"""Studio-owned, *non-publishing* V3 vocal evidence verifier.

Only a Studio caller that already obtained its principal-authorized ProjectRevision
and lawful CAS bytes may use this helper. Key arguments MUST be resolved by the
host's trusted registry; accepting public keys from user payloads is forbidden.
Structural verification and cryptographic reference tests do not prove the
witness actually heard a lyric or grant a Studio LyricTimelineRevision commit.
No endpoint, musical source of truth, release permission or auto-issuer here.

Wire format uses canonical JSON with decimal strings for sample/epoch integers
(instead of JavaScript BigInt), allowing signed evidence across Python and TS.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import re
import wave

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class StudioEvidenceDenied(ValueError):
    """Unlawful or non-canonical musical evidence; cannot issue Studio truth."""


def _deny(message):
    raise StudioEvidenceDenied(message)


def canonical_bytes(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False).encode('utf-8')
    except (TypeError, ValueError) as error:
        raise StudioEvidenceDenied('NON_CANONICAL_EVIDENCE') from error


def digest_hex(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _dec(value):
    if not isinstance(value, str) or not re.fullmatch(r'0|[1-9][0-9]*', value):
        _deny('INVALID_DECIMAL_SAMPLE_OR_EPOCH')
    return int(value)


def _key_bytes(key):
    if not isinstance(key, Ed25519PublicKey):
        _deny('HOST_TRUST_ROOT_REQUIRED')
    from cryptography.hazmat.primitives import serialization
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _verify_signature(key, content, encoded, error):
    _key_bytes(key)
    try:
        if not isinstance(encoded, str):
            raise ValueError('signature not a string')
        signature = base64.b64decode(encoded, validate=True)
        if len(signature) != 64:
            raise ValueError('not an Ed25519 signature')
        key.verify(signature, canonical_bytes(content))
    except (InvalidSignature, binascii.Error, ValueError, TypeError) as cause:
        raise StudioEvidenceDenied(error) from cause


def _wav_info(data):
    if not isinstance(data, bytes) or not data:
        _deny('DECODED_WAV_REQUIRED')
    try:
        with wave.open(io.BytesIO(data), 'rb') as audio:
            if audio.getcomptype() != 'NONE' or audio.getsampwidth() != 2 or audio.getnchannels() not in (1, 2):
                _deny('DECODE_PROFILE_UNSUPPORTED')
            rate, channels, frames = audio.getframerate(), audio.getnchannels(), audio.getnframes()
            pcm = audio.readframes(frames)
    except (wave.Error, EOFError) as exc:
        raise StudioEvidenceDenied('DECODED_WAV_INVALID') from exc
    if rate <= 0 or frames <= 0 or len(pcm) != frames * channels * 2:
        _deny('DECODED_WAV_FRAME_MISMATCH')
    return {'sha': hashlib.sha256(data).hexdigest(), 'pcmSha': hashlib.sha256(pcm).hexdigest(),
            'rate': rate, 'channels': channels, 'frames': frames}


def verify_vocal_evidence(signed, *, studio_project, source_audio_bytes,
                          decoded_wav_bytes, evidence, grant, trusted_issuer_key,
                          trusted_observer_key, trusted_issuer_key_id, trusted_observer_key_id):
    """Verify exact project and signal, witnessed geometry and BOTH Ed25519 signatures.

    This function expects a lawful, externally principal-authorized Studio open
    and CAS readback; it NEVER performs or replaces authorization itself.
    """
    if not isinstance(signed, dict) or set(signed) != {'schemaId','schemaVersion','payload','payloadDigestHex','attestation'}:
        _deny('SIGNED_OCCURRENCE_FIELDS_INVALID')
    if signed['schemaId'] != 'sj3.studio.vocal-occurrence' or signed['schemaVersion'] != 3:
        _deny('SIGNED_OCCURRENCE_SCHEMA_INVALID')
    payload, attest = signed['payload'], signed['attestation']
    if not isinstance(payload, dict) or not isinstance(attest, dict):
        _deny('SIGNED_OCCURRENCE_MALFORMED')
    required = {'occurrenceId','lyricTokenRef','sourceProjectRevisionId',
        'sourceAudioArtifactId','sourceAudioArtifactDigest','decodedAudioArtifactId',
        'decodedPcmDigest','sourceSampleRate','onsetSample','coordinateSystem','observationWindowId',
        'boundaryStatus','onsetVisibility','issuerPrincipalId','issuerVersion',
        'authorizationGrantId','observationEvidenceDigest'}
    if set(payload) != required or set(attest) != {'algorithm','keyId','signatureBase64'}:
        _deny('SIGNED_OCCURRENCE_FIELDS_INVALID')
    if not all(isinstance(payload[k], str) and payload[k] for k in required):
        _deny('SIGNED_OCCURRENCE_FIELDS_INVALID')
    if payload['occurrenceId'] != 'DENIAL_01' or payload['lyricTokenRef'] != 'denial-chorus-w001':
        _deny('SINGLE_OCCURRENCE_SCOPE_DENIED')
    if payload['coordinateSystem'] != 'PCM_ARTIFACT_START':
        _deny('WRONG_SOURCE_SAMPLE_ORIGIN')
    if payload['boundaryStatus'] != 'FULLY_OBSERVED' or payload['onsetVisibility'] != 'OBSERVED_INSIDE_WINDOW':
        _deny('ONSET_QUALIFICATION_NOT_EARNED')
    if attest['algorithm'] != 'ED25519' or not isinstance(attest['keyId'], str) or not attest['keyId']:
        _deny('ISSUER_ATTESTATION_METADATA_INVALID')
    if not isinstance(trusted_issuer_key_id, str) or attest['keyId'] != trusted_issuer_key_id:
        _deny('ISSUER_KEY_ID_MISMATCH')
    if not _sha(signed['payloadDigestHex']) or signed['payloadDigestHex'] != digest_hex(payload):
        _deny('SIGNED_OCCURRENCE_DIGEST_MISMATCH')
    if not isinstance(grant, dict) or grant.get('authorizationGrantId') != payload['authorizationGrantId']:
        _deny('AUTHORIZATION_GRANT_ID_MISMATCH')
    if grant.get('current') is not True or grant.get('principalId') != payload['issuerPrincipalId']:
        _deny('AUTHORIZATION_NOT_CURRENT_OR_PRINCIPAL')
    if _dec(grant.get('revocationEpoch')) < 0 or _dec(grant.get('observedAtEpochMs')) >= _dec(grant.get('expiresAtEpochMs')):
        _deny('AUTHORIZATION_GRANT_EXPIRED')
    project = studio_project
    if not isinstance(project, dict) or not all(isinstance(project.get(k), dict) for k in ('manifest','revision','lyricTimeline')):
        _deny('LAWFUL_STUDIO_PROJECT_SNAPSHOT_REQUIRED')
    manifest, revision, lyric = project['manifest'], project['revision'], project['lyricTimeline']
    if (not manifest.get('projectId') or manifest.get('projectId') != revision.get('projectId')
        or revision.get('revisionId') != payload['sourceProjectRevisionId']
        or not revision.get('lyricTimelineDigest')):
        _deny('STUDIO_PROJECT_REVISION_MISMATCH')
    info = _wav_info(decoded_wav_bytes)
    if not isinstance(source_audio_bytes, bytes):
        _deny('SOURCE_ARTIFACT_READBACK_REQUIRED')
    source_digest = hashlib.sha256(source_audio_bytes).hexdigest()
    if (payload['sourceAudioArtifactId'] != source_digest
        or payload['sourceAudioArtifactDigest'] != source_digest
        or payload['decodedAudioArtifactId'] != info['sha']
        or payload['decodedPcmDigest'] != info['pcmSha']
        or _dec(payload['sourceSampleRate']) != info['rate']):
        _deny('CANONICAL_SIGNAL_IDENTITY_MISMATCH')
    if source_digest not in revision.get('sourceAssetDigests', []):
        _deny('ARTIFACT_NOT_IN_REVISION')
    if info['sha'] not in revision.get('sourceAssetDigests', []):
        _deny('LYRIC_WAV_NOT_PROJECT_SOURCE')
    if (lyric.get('sourceArtifactId') != info['sha']
        or lyric.get('sourceAudioDigest') != info['pcmSha']
        or lyric.get('sourceSampleRate') != info['rate']
        or lyric.get('sourceChannels') != info['channels']
        or lyric.get('decodedFrameCount') != info['frames']):
        _deny('LYRIC_TIMELINE_SIGNAL_MISMATCH')
    matches = [w for w in lyric.get('words', []) if isinstance(w, dict) and w.get('id') == payload['lyricTokenRef']]
    if len(matches) != 1:
        _deny('WORD_NOT_IN_STUDIO_LYRIC_TIMELINE')
    start_word, end_word = matches[0].get('decodedSampleStart'), matches[0].get('decodedSampleEnd')
    onset = _dec(payload['onsetSample'])
    if (type(start_word) is not int or type(end_word) is not int
        or not start_word <= onset < end_word <= info['frames']):
        _deny('ONSET_NOT_WITHIN_STUDIO_WORD')
    if not isinstance(evidence, dict) or set(evidence) != {'window','observation','witnessAttestation'}:
        _deny('WITNESS_EVIDENCE_MISSING')
    window, observation, witness_attestation = evidence['window'], evidence['observation'], evidence['witnessAttestation']
    if not all(isinstance(x, dict) for x in (window, observation, witness_attestation)):
        _deny('WITNESS_EVIDENCE_MALFORMED')
    if set(window) != {'observationWindowId','occurrenceId','sourceDecodedAudioArtifactId','sourcePcmDigest',
                       'sourceStartSample','sourceEndSampleExclusive','boundaryStatus'}:
        _deny('WINDOW_FIELDS_INVALID')
    if set(observation) != {'observationWindowId','occurrenceId','localOnsetSample',
        'preOnsetContextSample','onsetVisibility','sourcePcmDigest','windowDigestHex',
        'observerPrincipalId','observerEvidenceRefs'}:
        _deny('WITNESS_FIELDS_INVALID')
    if (window['boundaryStatus'] != 'FULLY_OBSERVED'
        or window['observationWindowId'] != payload['observationWindowId']
        or window['occurrenceId'] != payload['occurrenceId']
        or window['sourceDecodedAudioArtifactId'] != info['sha']
        or window['sourcePcmDigest'] != info['pcmSha']):
        _deny('OBSERVATION_WINDOW_NOT_AUTHENTICATED')
    a, b = _dec(window['sourceStartSample']), _dec(window['sourceEndSampleExclusive'])
    local, pre = _dec(observation['localOnsetSample']), _dec(observation['preOnsetContextSample'])
    if not (a < b <= info['frames'] and 0 <= pre < local < b-a):
        _deny('INSUFFICIENT_ONSET_PRE_CONTEXT_OR_WINDOW')
    if (observation['observationWindowId'] != window['observationWindowId']
        or observation['occurrenceId'] != payload['occurrenceId']
        or observation['onsetVisibility'] != 'OBSERVED_INSIDE_WINDOW'
        or observation['sourcePcmDigest'] != info['pcmSha']
        or observation['windowDigestHex'] != digest_hex(window)
        or payload['observationEvidenceDigest'] != digest_hex(observation)
        or not isinstance(observation['observerEvidenceRefs'], list)
        or not observation['observerEvidenceRefs']
        or any(not isinstance(x, str) or not x for x in observation['observerEvidenceRefs'])
        or not isinstance(observation['observerPrincipalId'], str)
        or observation['observerPrincipalId'] == payload['issuerPrincipalId']):
        _deny('OBSERVATION_WITNESS_IDENTITY_MISMATCH')
    if onset != a + local:
        _deny('ONSET_NOT_DERIVED_FROM_WITNESS')
    if _key_bytes(trusted_observer_key) == _key_bytes(trusted_issuer_key):
        _deny('WITNESS_ISSUER_KEY_NOT_INDEPENDENT')
    if (set(witness_attestation) != {'algorithm','keyId','signatureBase64'}
        or witness_attestation.get('algorithm') != 'ED25519'
        or not witness_attestation.get('keyId')):
        _deny('WITNESS_ATTESTATION_INVALID')
    if not isinstance(trusted_observer_key_id, str) or witness_attestation['keyId'] != trusted_observer_key_id:
        _deny('WITNESS_KEY_ID_MISMATCH')
    _verify_signature(trusted_observer_key, observation, witness_attestation.get('signatureBase64'), 'WITNESS_SIGNATURE_INVALID')
    _verify_signature(trusted_issuer_key, payload, attest.get('signatureBase64'), 'OCCURRENCE_SIGNATURE_INVALID')
    return dict(payload)


def sign_studio_receipt(receipt_id, signed, verified_payload, grant,
                        host_studio_private_key, *, key_id, issued_at_epoch_ms):
    """Host-only signing primitive; doesn't mutate Studio revision or publish Proof.

    Treat its output as a CANDIDATE until a rightful Studio transaction persists
    an immutable occurrence association and the consumer independently rereads it.
    """
    if not receipt_id or not key_id or type(issued_at_epoch_ms) is not int or issued_at_epoch_ms < 0:
        _deny('ISSUER_RECEIPT_FIELDS_INVALID')
    if signed.get('payload') != verified_payload or signed.get('payloadDigestHex') != digest_hex(verified_payload):
        _deny('VERIFIED_PAYLOAD_BINDING_MISMATCH')
    if (grant.get('authorizationGrantId') != verified_payload.get('authorizationGrantId')
        or grant.get('principalId') != verified_payload.get('issuerPrincipalId')
        or grant.get('current') is not True
        or issued_at_epoch_ms >= _dec(grant.get('expiresAtEpochMs'))):
        _deny('ISSUER_GRANT_NOT_CURRENT')
    unsigned = {'schemaId':'sj3.studio.occurrence-admission-receipt','schemaVersion':3,
        'receiptId':receipt_id,'payload':verified_payload,
        'signedOccurrenceDigestHex':signed['payloadDigestHex'],
        'authorizationGrantId':grant['authorizationGrantId'],
        'authorizationRevocationEpoch':grant['revocationEpoch'],
        'issuedAtEpochMs':str(issued_at_epoch_ms),
        'issuerPrincipalId':verified_payload['issuerPrincipalId'],'authorityRef':'SARA_STUDIO'}
    try:
        signature = host_studio_private_key.sign(canonical_bytes(unsigned))
    except (AttributeError, TypeError) as error:
        raise StudioEvidenceDenied('HOST_SIGNING_KEY_REQUIRED') from error
    return {**unsigned,'receiptDigestHex':digest_hex(unsigned),
        'receiptAttestation':{'algorithm':'ED25519','keyId':key_id,
            'signatureBase64':base64.b64encode(signature).decode('ascii')}}


def verify_studio_receipt(receipt, trusted_studio_key, *, trusted_key_id, authorized_principal):
    """Cryptographically checks format/digest/signature, not live grant currentness."""
    if not isinstance(receipt, dict):
        _deny('STUDIO_RECEIPT_MALFORMED')
    fields={'schemaId','schemaVersion','receiptId','payload','signedOccurrenceDigestHex',
        'authorizationGrantId','authorizationRevocationEpoch','issuedAtEpochMs',
        'issuerPrincipalId','authorityRef','receiptDigestHex','receiptAttestation'}
    if set(receipt) != fields:
        _deny('STUDIO_RECEIPT_FIELDS_INVALID')
    if (receipt['schemaId'] != 'sj3.studio.occurrence-admission-receipt'
        or receipt['schemaVersion'] != 3 or receipt['authorityRef'] != 'SARA_STUDIO'):
        _deny('STUDIO_RECEIPT_SCHEMA_INVALID')
    if not isinstance(receipt['payload'], dict) or not isinstance(receipt['receiptAttestation'], dict):
        _deny('STUDIO_RECEIPT_MALFORMED')
    p = receipt['payload']
    if (receipt['issuerPrincipalId'] != p.get('issuerPrincipalId')
        or receipt['authorizationGrantId'] != p.get('authorizationGrantId')
        or receipt['signedOccurrenceDigestHex'] != digest_hex(p)):
        _deny('STUDIO_RECEIPT_PAYLOAD_MISMATCH')
    _dec(receipt['authorizationRevocationEpoch']); _dec(receipt['issuedAtEpochMs'])
    sig=receipt['receiptAttestation']
    if set(sig) != {'algorithm','keyId','signatureBase64'} or sig['algorithm'] != 'ED25519' or not sig['keyId']:
        _deny('STUDIO_RECEIPT_ATTESTATION_INVALID')
    if not isinstance(trusted_key_id, str) or sig['keyId'] != trusted_key_id:
        _deny('RECEIPT_KEY_ID_MISMATCH')
    if not isinstance(authorized_principal, str) or receipt['issuerPrincipalId'] != authorized_principal:
        _deny('RECEIPT_ISSUER_PRINCIPAL_MISMATCH')
    unsigned={k:v for k,v in receipt.items() if k not in ('receiptDigestHex','receiptAttestation')}
    if receipt['receiptDigestHex'] != digest_hex(unsigned):
        _deny('STUDIO_RECEIPT_DIGEST_MISMATCH')
    _verify_signature(trusted_studio_key, unsigned, sig['signatureBase64'], 'STUDIO_RECEIPT_SIGNATURE_INVALID')
    return dict(p)


def verify_vocal_evidence_from_studio(root, principal_id, project_id, revision_id,
    signed, evidence, grant, trusted_issuer_key, trusted_observer_key,
    trusted_issuer_key_id, trusted_observer_key_id):
    """Lawful Studio entrypoint; authorization precedes every source CAS read.

    This is still a *reference checker*, not a publication endpoint. An
    authorized principal selects an exact historical or current revision;
    Studio's existing project and project_audio_bytes owners authorize it.
    Only after membership is confirmed may source CAS be read. The raw source
    must be a revision member and both hashes must validate. No CAS scan.
    """
    if not all(isinstance(x, str) and x for x in (principal_id,project_id,revision_id)):
        _deny('STUDIO_PROJECT_AUTHORIZATION_REQUIRED')
    from studio_server import project_operation, artifact_bytes
    try:
        # Membership and revision association are decided by Studio, not here.
        snapshot = project_operation(root, {'projectId':project_id,'revisionId':revision_id},
                                     principal_id=principal_id)
    except (PermissionError, ValueError, KeyError, OSError) as exc:
        raise StudioEvidenceDenied('STUDIO_PROJECT_AUTHORIZATION_DENIED') from exc
    try:
        revision = snapshot['revision']
        if revision['projectId'] != project_id or revision['revisionId'] != revision_id:
            _deny('STUDIO_SELECTED_REVISION_MISMATCH')
        payload = signed['payload']
        source_id, decoded_id = payload['sourceAudioArtifactId'], payload['decodedAudioArtifactId']
        if source_id not in revision['sourceAssetDigests']:
            _deny('ARTIFACT_NOT_IN_REVISION')
        if (decoded_id not in revision['sourceAssetDigests']
                or snapshot.get('lyricTimeline', {}).get('sourceArtifactId') != decoded_id):
            _deny('LYRIC_WAV_NOT_PROJECT_SOURCE')
        # Source WAV is a verified Studio ProjectRevision source, NOT necessarily
        # an output render. project_audio_bytes only authorizes output renders;
        # selected historical revision + source membership precede both CAS reads.
        wav = artifact_bytes(root, decoded_id)
        raw = artifact_bytes(root, source_id)
    except StudioEvidenceDenied:
        raise
    except (PermissionError, ValueError, KeyError, OSError, TypeError) as exc:
        raise StudioEvidenceDenied('STUDIO_LAWFUL_AUDIO_READ_DENIED') from exc
    return verify_vocal_evidence(
        signed,studio_project=snapshot,source_audio_bytes=raw,decoded_wav_bytes=wav,
        evidence=evidence,grant=grant,trusted_issuer_key=trusted_issuer_key,
        trusted_observer_key=trusted_observer_key,
        trusted_issuer_key_id=trusted_issuer_key_id,
        trusted_observer_key_id=trusted_observer_key_id,
    )

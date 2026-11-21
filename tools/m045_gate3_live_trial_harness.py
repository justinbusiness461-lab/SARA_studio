"""R15-A offline Gate 3 post-inference adapter — no outbound execution or GPU.

This handler deliberately cannot upgrade the R11 DRY_RUN_ONLY authorization
to a paid-provider capability. It accepts ONLY a local, exact-class waveform
fixture, consumes R11's durable single-use host token and delegates all CAS,
revision association and recovery to GenerationAttemptOwner + Studio.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import math
import re
import secrets
import struct
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

from m045_gate3_authorization import Gate3AuthorizationStore,validate as validate_scope
from m045_generation_attempt import native_atomic_write_bytes
from m045_bs1770_reference import measure_reference_pcm16
from platform_identity import PlatformDenied

_MAX_INPUT_BYTES=12*1024*1024
_MAX_OUTPUT_BYTES=20*44100*4+128
_HEX64=re.compile(r'[a-f0-9]{64}\Z')

@dataclass(frozen=True)
class LoopbackWavTransport:
    """Non-network fixture; refuses subclasses with custom network behavior."""
    wav_bytes: bytes

def _run_media_tool(argv, audio):
    try:
        proc=subprocess.run(argv,input=audio,capture_output=True,timeout=25,
                            check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ValueError('GATE3_LOCAL_MEDIA_ENGINE_UNAVAILABLE') from exc
    if proc.returncode:
        raise ValueError('GATE3_PROVIDER_AUDIO_UNDECODABLE')
    return proc.stdout

def _physical_decode(raw,scope):
    if not isinstance(raw,bytes) or not 44<=len(raw)<=_MAX_INPUT_BYTES:
        raise ValueError('GATE3_PROVIDER_BYTES_UNQUALIFIED')
    data=_run_media_tool(['ffprobe','-v','error','-select_streams','a:0',
        '-show_entries','stream=codec_name,channels,sample_rate,duration',
        '-of','json','-i','pipe:0'],raw)
    try:
        streams=json.loads(data)['streams']
        stream=streams[0]
        if stream['codec_name']!='pcm_s16le':
            raise ValueError('GATE3_PROVIDER_CODEC_UNQUALIFIED')
        if int(stream['channels']) not in (1,2) or not 8000<=int(stream['sample_rate'])<=96000:
            raise ValueError('GATE3_PROVIDER_CHANNELS_OR_RATE_INVALID')
    except (KeyError,IndexError,TypeError,ValueError) as exc:
        raise ValueError('GATE3_PROVIDER_PROBE_INVALID') from exc
    raw_pcm=_run_media_tool(['ffmpeg','-nostdin','-v','error','-threads','1',
        '-f','wav','-i','pipe:0','-ar','44100','-ac','2',
        '-acodec','pcm_s16le','-f','s16le','pipe:1'],raw)
    if len(raw_pcm)>_MAX_OUTPUT_BYTES or len(raw_pcm)%4:
        raise ValueError('GATE3_PCM_BOUNDS_INVALID')
    frames=len(raw_pcm)//4
    if (frames<44100//2 or frames>20*44100
          or frames>math.floor(44100*scope['maxAudioDurationSec'])+1):
        raise ValueError('GATE3_AUDIO_DURATION_EXCEEDS_SCOPE')
    max_sample=max(abs(s) for (s,) in struct.iter_unpack('<h',raw_pcm))
    if max_sample>=32750:
        raise ValueError('GATE3_SAMPLE_CLIPPING_DENIED')
    buf=io.BytesIO()
    with wave.open(buf,'wb') as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(44100)
        audio.writeframes(raw_pcm)
    output=buf.getvalue()
    physical=measure_reference_pcm16(output)
    if physical['true_peak_dbtp']>=-0.1:
        raise ValueError('GATE3_TRUE_PEAK_CLIPPING_DENIED')
    return output,physical

def _signature_fields(data):
    return json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def _sign_receipt(payload,host_key):
    if not isinstance(host_key,bytes) or len(host_key)<32:
        raise PlatformDenied('GATE3_LISTENING_SIGNER_NOT_CONFIGURED')
    data=_signature_fields(payload)
    return {**payload,'receiptDigestSha256':hashlib.sha256(data).hexdigest(),
            'hostSignatureHmacSha256':hmac.new(host_key,data,'sha256').hexdigest()}

def verify_gate3_listening_receipt(receipt,host_key):
    if not isinstance(receipt,dict) or not isinstance(host_key,bytes) or len(host_key)<32:
        return False
    try:
        payload={k:v for k,v in receipt.items() if k not in
                 {'receiptDigestSha256','hostSignatureHmacSha256'}}
        data=_signature_fields(payload)
        return (hmac.compare_digest(receipt['receiptDigestSha256'],hashlib.sha256(data).hexdigest())
             and hmac.compare_digest(receipt['hostSignatureHmacSha256'],
                     hmac.new(host_key,data,'sha256').hexdigest()))
    except (KeyError,TypeError,ValueError):
        return False

def run_bounded_gate3_trial_pipeline(*,root,principal_id,scope,spend_store,
    spend_token,loopback_transport,receipt_signing_key,allow_live_network=False):
    """Offline-only loopback integration; no network provider is wired.

    The existing Gate3 spend token is NOT a live authorization, even when
    admitted by a host. A true paid executor requires an independent provider
    cost-cap/rights/checkout authority and is outside this implementation.
    """
    if allow_live_network is not False:
        raise PlatformDenied('GATE3_LIVE_EXECUTOR_NOT_INSTALLED')
    if type(loopback_transport) is not LoopbackWavTransport:
        raise PlatformDenied('GATE3_OFFLINE_LOOPBACK_TRANSPORT_REQUIRED')
    if not isinstance(loopback_transport.wav_bytes,bytes):
        raise ValueError('GATE3_LOOPBACK_BYTES_REQUIRED')
    validate_scope(scope)
    if not isinstance(spend_store,Gate3AuthorizationStore):
        raise PlatformDenied('GATE3_CANONICAL_TOKEN_OWNER_REQUIRED')
    if not isinstance(receipt_signing_key,bytes) or len(receipt_signing_key)<32:
        raise PlatformDenied('GATE3_LISTENING_SIGNER_NOT_CONFIGURED')
    from studio_server import project_operation,project_audio_bytes,make_m045_native_owner
    root=Path(root).resolve()
    active=project_operation(root,{'projectId':scope['projectId']},
                             principal_id=principal_id)
    if active['manifest']['currentRevisionId']!=scope['baseRevisionId']:
        raise PlatformDenied('GATE3_STALE_STUDIO_SOURCE')
    # One-shot canonical token is consumed *before* any provider-like work.
    # Corrupt/missing fixture burns the token but never promotes CURRENT.
    challenge=spend_store.redeem(principal_id,spend_token,scope)
    if (challenge['state']!='DRY_RUN_ONLY' or challenge['trialAuthorized']
        or challenge['remoteExecutionEnabled']):
        raise PlatformDenied('GATE3_TOKEN_NOT_OFFLINE_ONLY')
    normalized,physical=_physical_decode(loopback_transport.wav_bytes,scope)
    digest=hashlib.sha256(normalized).hexdigest()
    expected=scope['baseRevisionId']
    delegate_token=secrets.token_urlsafe(48)
    owner=make_m045_native_owner(root,scoped_principal=principal_id,
                                host_delegation_token=delegate_token)
    def stage(stage_dir,song_spec,prompt,lyrics,seed,params):
        stage_dir=Path(stage_dir)
        audio_path=stage_dir/'output.wav'
        native_atomic_write_bytes(audio_path,normalized)
        native_atomic_write_bytes(stage_dir/'provider-receipt.json',
            _signature_fields({'source_type':'OPEN_WEIGHT_REMOTE_PROVIDER',
               'rights_status':'OPEN_WEIGHT_UNVERIFIED_TRAINING_DATA',
               'preservation_tier':'P3',
               'model_id':scope['modelId'],'model_version':scope['modelId'],
               'checkpoint_sha256':scope['checkpointManifestSha256'],
               'seed':seed,'audio_sha256':digest,
               'transport':'OFFLINE_LOOPBACK_ONLY',
               'external_provider_calls':0,'charges_incurred_usd':0}))
        return audio_path
    operation=owner.execute_attempt(
        headers={'Authorization':'Bearer '+delegate_token},
        project_id=scope['projectId'],base_revision_id=expected,
        expected_current_revision_id=expected,
        idempotency_key='gate3-'+hashlib.sha256(spend_token.encode()).hexdigest(),
        model_id=scope['modelId'],model_version=scope['modelId'],seed=0,
        song_spec=active['songSpec'],
        prompt='Gate3 exact revision offline validation fixture',
        lyrics=None,params={'music_length_ms':round(1000*physical['samples_per_channel']/44100)},
        synthesize_to_stage_fn=stage)
    if operation['state']!='COMMITTED':
        raise PlatformDenied('GATE3_REVISION_NOT_CURRENT_COMMITTED')
    revision=operation['revision']['revisionId']
    reread=project_audio_bytes(root,{'projectId':scope['projectId'],
        'revisionId':revision,'artifactId':digest},principal_id=principal_id)
    if reread!=normalized:
        raise PlatformDenied('GATE3_IMMUTABLE_AUDIO_READBACK_MISMATCH')
    receipt=_sign_receipt({
        'schemaVersion':'sara.gate3.listening.evaluation.v1',
        'mode':'DRY_RUN_ONLY','sourceProjectId':scope['projectId'],
        'sourceProjectRevisionId':expected,
        'outputProjectRevisionId':revision,
        'audioArtifactSha256':digest,
        'providerModelId':scope['modelId'],
        'checkpointManifestSha256':scope['checkpointManifestSha256'],
        'sampleRateHz':44100,'channels':2,'sampleWidthBytes':2,
        'samplesPerChannel':physical['samples_per_channel'],
        'integratedLufsReference':physical['integrated_lufs'],
        'truePeakDbtp4xReference':physical['true_peak_dbtp'],
        'meterConformance':physical['meterConformance'],
        'meterImplementation':physical['peakImplementation'],
        'preservationTier':'P3','rightsStatus':'UNVERIFIED_HELD',
        'creativeApproved':False,'audioListenedByHuman':False,
        'artistListeningRequired':True,
        'releaseReady':False,'remoteProviderCalled':False,
        'gpuAllocated':False,'chargesIncurredUsd':0,
        'maxUsdCentsScope':scope['maxUsdCents'],
        'maxAudioDurationSec':scope['maxAudioDurationSec']
    },receipt_signing_key)
    # Informational proof is subordinate to the immutable Studio revision.
    # It cannot authorize CAS, grant rights, or select a project revision.
    receipt_path=root/'projects'/scope['projectId']/'gate3-listening-receipts'/(digest+'.json')
    native_atomic_write_bytes(receipt_path,_signature_fields(receipt))
    return {'state':'COMMITTED','mode':'DRY_RUN_ONLY',
            'projectId':scope['projectId'],'revisionId':revision,'artifactId':digest,
            'preservationTier':'P3','rightsStatus':'UNVERIFIED_HELD',
            'creativeApproved':False,'releaseReady':False,
            'networkCallsMade':0,'gpuAllocated':False,'chargesIncurredUsd':0,
            'listeningReceipt':receipt}

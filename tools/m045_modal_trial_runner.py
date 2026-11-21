"""R10-A: prepare an ACE-Step Gate-3 trial WITHOUT networking, deploying or GPU.

This module has no transport adapter by design.  A host-approved bounded trial
MUST be implemented in a separate independently authorized owner change, with
pricing and checkpoint admission, before any paid effect can occur.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit
from m045_modal_trial_preflight import zero_spend_modal_preflight

_FIELDS={'mode','execute','operation','requestedDurationSec','httpTimeoutSec','maxSpendUsd','gpuSecondsCap'}
_REPAINT_FIELDS={'sourceProjectRevisionId','targetStartFrame','targetEndFrame','protectedOutsidePcmSha256'}
_HEX=re.compile(r'[a-f0-9]{64}\Z')

def _number(value,low,high):
    return type(value) in (int,float) and math.isfinite(value) and low<=value<=high

def _validated_env(environment):
    if not isinstance(environment,dict) or environment.get('SARA_GATE3_SPEND_AUTHORIZED')!='1':
        raise ValueError('GATE3_OPERATOR_SPEND_FLAG_ABSENT_DRY_RUN_ONLY')
    endpoint=environment.get('SARA_ACESTEP_ENDPOINT_URL','')
    key=environment.get('SARA_ACESTEP_API_KEY','')
    if not isinstance(endpoint,str) or not isinstance(key,str):
        raise ValueError('GATE3_HOST_PROVIDER_CONFIG_INVALID')
    try:u=urlsplit(endpoint)
    except ValueError:raise ValueError('GATE3_ENDPOINT_INVALID')
    if (u.scheme!='https' or not u.hostname or
            not (u.hostname=='modal.run' or u.hostname.endswith('.modal.run'))
            or u.username is not None or u.password is not None or u.port is not None
            or u.query or u.fragment or '\\' in endpoint or len(endpoint)>512):
        raise ValueError('GATE3_ENDPOINT_UNQUALIFIED')
    if len(key)<32 or len(key)>512 or key.strip()!=key or any(ord(c)<33 or ord(c)>126 for c in key):
        raise ValueError('GATE3_API_KEY_UNQUALIFIED')
    # Never expose either provider credential or endpoint in receipts.
    return hashlib.sha256(endpoint.encode()).hexdigest()

def prepare_gate3_trial(modal_source,request,environment):
    """Inspect bounded policy and source. This NEVER returns permission to spend.

    Even a valid operator flag is insufficient: model checkpoint, provider
    price quote, independent rights, and artist approval remain separate HOLDs.
    """
    if not isinstance(request,dict) or not _FIELDS<=set(request):
        raise ValueError('GATE3_REQUEST_FIELDS_INVALID')
    if request['mode']!='ZERO_SPEND_DRY_RUN' or request['execute'] is not False:
        raise ValueError('GATE3_LIVE_EXECUTION_NOT_IMPLEMENTED')
    operation=request['operation']
    if operation not in ('FULL_SONG','SELECTIVE_REPAINT'):
        raise ValueError('GATE3_OPERATION_INVALID')
    if not (_number(request['requestedDurationSec'],0.01,20)
            and _number(request['httpTimeoutSec'],1,180)
            and _number(request['maxSpendUsd'],0,1)
            and type(request['gpuSecondsCap']) is int
            and 1<=request['gpuSecondsCap']<=180):
        raise ValueError('GATE3_TRIAL_BOUNDS_UNQUALIFIED')
    if operation=='FULL_SONG' and set(request)!=_FIELDS:
        raise ValueError('GATE3_REQUEST_FIELDS_INVALID')
    if operation=='SELECTIVE_REPAINT':
        if set(request)!=_FIELDS|_REPAINT_FIELDS:
            raise ValueError('GATE3_REPAINT_SCOPE_REQUIRED')
        if (not isinstance(request['sourceProjectRevisionId'],str)
                or not _HEX.fullmatch(request['sourceProjectRevisionId'])
                or any(type(request[k]) is not int for k in ('targetStartFrame','targetEndFrame'))
                or not 0<=request['targetStartFrame']<request['targetEndFrame']<=20*44100
                or not isinstance(request['protectedOutsidePcmSha256'],str)
                or not _HEX.fullmatch(request['protectedOutsidePcmSha256'])):
            raise ValueError('GATE3_REPAINT_SCOPE_UNQUALIFIED')
    endpoint_digest=_validated_env(environment)
    # Existing static preflight owns pinned source and one-container policy;
    # it intentionally doesn't import Modal nor touch its API.
    gpu_cap=request['gpuSecondsCap']
    source=zero_spend_modal_preflight(modal_source,{
        'mode':'ZERO_SPEND_PREFLIGHT','gpuSecondsCap':gpu_cap,
        'songSecondsCap':int(math.ceil(request['requestedDurationSec'])),
        'maxSpendUsd':0,'execute':False})
    if request['httpTimeoutSec']>source['serviceTimeoutSeconds']:
        raise ValueError('GATE3_TIMEOUT_EXCEEDS_HOST_BOUND')
    audit={
        'schema':'sara.gate3.trial.audit.v1','state':'DRY_RUN_ONLY',
        'operation':operation,'requestedDurationSec':request['requestedDurationSec'],
        'httpTimeoutSec':request['httpTimeoutSec'],'maxSpendUsd':request['maxSpendUsd'],
        'maxGpuSeconds':gpu_cap,'maxContainers':source['maxContainers'],
        'maxConcurrentInputs':source['maxConcurrentInputs'],
        'sourceSha256':source['sourceSha256'],'upstreamCommit':source['upstreamCommit'],
        'endpointConfigSha256':endpoint_digest,
        'gpuAllocated':False,'remoteExecutionEnabled':False,'trialAuthorized':False,
        'chargesIncurredUsd':0,'networkCallsMade':0,'checkpointVerified':False,
        'providerPricingVerified':False,'rightsVerified':False,
        'preservationP1Certified':False,'creativeApproved':False,
        'gateHolds':['PAID_PROVIDER_NOT_CONNECTED','INDEPENDENT_COST_ENFORCEMENT_REQUIRED',
                     'LICENSE_AND_MODEL_CHECKPOINT_NOT_VERIFIED','REAL_MEDIA_NOT_RENDERED',
                     'HUMAN_CREATIVE_APPROVAL_REQUIRED']}
    if operation=='SELECTIVE_REPAINT':
        audit['sourceProjectRevisionId']=request['sourceProjectRevisionId']
        audit['repaintWindowFrames']=[request['targetStartFrame'],request['targetEndFrame']]
        audit['protectedOutsideExpectedPcmSha256']=request['protectedOutsidePcmSha256']
    audit['auditDigest']=hashlib.sha256(json.dumps(audit,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return audit

def audit_existing_audio(root,reference,principal_id):
    """Read only a lawful existing Studio revision's media, no CAS publication."""
    from studio_server import project_operation,project_audio_bytes
    from m045_bs1770_reference import measure_reference_pcm16
    if not isinstance(reference,dict) or set(reference)!={'projectId','revisionId','artifactId'}:
        raise ValueError('GATE3_AUDIO_REFERENCE_INVALID')
    authorized=project_operation(root,{'projectId':reference['projectId'],
          'revisionId':reference['revisionId']},principal_id=principal_id)
    if reference['artifactId'] not in authorized['revision']['outputArtifactIds']:
        raise ValueError('GATE3_SOURCE_NOT_REVISION_BOUND')
    data=project_audio_bytes(root,reference,principal_id=principal_id)
    meter=measure_reference_pcm16(data)
    return {'schema':'sara.gate3.existing.audio.audit.v1',
        'sourceProjectRevisionId':reference['revisionId'],
        'sourceArtifactId':hashlib.sha256(data).hexdigest(),
        'sampleRateHz':44100,'channels':2,'sampleWidthBytes':2,
        'integratedLufsReference':meter['integrated_lufs'],
        'truePeakDbtpReference':meter['true_peak_dbtp'],
        'releaseCleared':False,'trialAuthorized':False,'newAudioGenerated':False,
        'casPublished':False,'creativeApproved':False}

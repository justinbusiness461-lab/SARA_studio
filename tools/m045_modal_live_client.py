"""R16 bounded ACE-Step JSON/WAV HTTP transport — localhost tests only.

The real Modal outbound path is a *non-activated contract*: a signed R11
Gate3 token is DRY_RUN_ONLY, and a client timeout/estimated price is not an
independent provider-side hard billing cap. No HTTPS Modal call is authorized
by this code, regardless of environment flags. Only explicitly opted-in
127.0.0.1 loopback HTTP tests can cross a socket boundary.

CAS, ProjectRevision and rights authority remain with Studio and the existing
GenerationAttemptOwner, never with this provider client or response headers.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from m045_gate3_authorization import Gate3AuthorizationStore,validate as validate_scope
from platform_identity import PlatformDenied


class ModalTransportUnavailable(PlatformDenied):
    http_status = 503


class RemoteSubmissionUncertain(RuntimeError):
    """A POST may have been accepted; never auto-retry this spend token."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        raise ModalTransportUnavailable('GATE3_REDIRECT_NOT_AUTHORIZED')


@dataclass(frozen=True)
class ModalAceStepHttpProvider:
    endpoint_url: str
    environment: dict
    loopback_test_mode: bool = False
    http_timeout_sec: float = 120.0
    host_call_supervisor_factory: object = None
    host_call_supervisor: object = None

    def _preflight(self,scope,request=None):
        validate_scope(scope)
        if (not isinstance(self.environment,dict)
            or self.environment.get('SARA_GATE3_LIVE_NETWORK_ENABLED')!='1'):
            raise ModalTransportUnavailable('GATE3_NETWORK_OPERATOR_FLAG_ABSENT')
        key=self.environment.get('SARA_ACESTEP_API_KEY','')
        if (not isinstance(key,str) or not 32<=len(key)<=512
            or any(ord(c)<33 or ord(c)>126 for c in key)):
            raise ModalTransportUnavailable('GATE3_PROVIDER_BEARER_NOT_CONFIGURED')
        if (type(self.http_timeout_sec) not in (int,float)
            or not math.isfinite(self.http_timeout_sec)
            or not 0<self.http_timeout_sec<=120
            or self.http_timeout_sec>scope['maxContainerRuntimeSec']):
            raise ValueError('GATE3_HARD_TIMEOUT_OUT_OF_SCOPE')
        if not isinstance(self.endpoint_url,str) or len(self.endpoint_url)>512:
            raise ModalTransportUnavailable('GATE3_PROVIDER_URL_UNQUALIFIED')
        try: u=urllib.parse.urlsplit(self.endpoint_url)
        except ValueError as exc:raise ModalTransportUnavailable('GATE3_PROVIDER_URL_UNQUALIFIED') from exc
        if (not u.hostname or u.username or u.password or u.fragment or u.query
            or u.path!='/infer' or '\\' in self.endpoint_url):
            raise ModalTransportUnavailable('GATE3_PROVIDER_URL_UNQUALIFIED')
        loopback=(u.scheme=='http' and u.hostname in ('127.0.0.1','localhost')
                  and u.port is not None and 0<u.port<=65535)
        modal=(u.scheme=='https' and (u.hostname=='modal.run'
                       or u.hostname.endswith('.modal.run'))
               and u.port is None)
        if not (loopback or modal):
            raise ModalTransportUnavailable('GATE3_PROVIDER_URL_NOT_ALLOWLISTED')
        if not (loopback and self.loopback_test_mode is True):
            # Host-side independently enforced $1 absolute billing cap,
            # actual checkpoint/license proof and operator authority are not
            # installed. Environment flags and a token cannot substitute.
            raise ModalTransportUnavailable('GATE3_REAL_MODAL_PROVIDER_COST_CAP_NOT_CERTIFIED')
        if request is not None:self._validate_request(scope,request)
        return key

    @staticmethod
    def _validate_request(scope,request):
        base={'prompt','lyrics','audio_duration','audio_format','seed','task_type'}
        if not isinstance(request,dict) or not base<=set(request):
            raise ValueError('GATE3_MODAL_REQUEST_FIELDS_INVALID')
        task=request['task_type']
        allowed=base if task=='text2music' else base|{'repainting_start','repainting_end','src_audio_base64'}
        if task not in ('text2music','repaint') or set(request)!=allowed:
            raise ValueError('GATE3_MODAL_REQUEST_FIELDS_INVALID')
        if (not isinstance(request['prompt'],str) or not request['prompt'].strip()
            or len(request['prompt'])>6000
            or not isinstance(request['lyrics'],str) or len(request['lyrics'])>5000
            or request['audio_format']!='wav'
            or type(request['seed']) is not int
            or not 0<=request['seed']<2**31):
            raise ValueError('GATE3_MODAL_REQUEST_INVALID')
        t=request['audio_duration']
        if (type(t) not in (int,float) or not math.isfinite(t)
            or not 0<t<=scope['maxAudioDurationSec']<=20):
            raise ValueError('GATE3_MODAL_DURATION_UNQUALIFIED')
        if task=='repaint':
            a,b=request['repainting_start'],request['repainting_end']
            raw=request['src_audio_base64']
            if (type(a) not in (int,float) or type(b) not in (int,float)
                or not (math.isfinite(a) and math.isfinite(b) and 0<=a<b<=t)
                or not isinstance(raw,str) or len(raw)>16*1024*1024):
                raise ValueError('GATE3_MODAL_REPAINT_SCOPE_INVALID')
            try:source=base64.b64decode(raw,validate=True)
            except (ValueError,TypeError) as exc:raise ValueError('GATE3_MODAL_REPAINT_SOURCE_INVALID') from exc
            if len(source)<44 or len(source)>12*1024*1024:
                raise ValueError('GATE3_MODAL_REPAINT_SOURCE_INVALID')

    def _request_remote_cancel_if_bound(self,reason):
        supervisor=self.host_call_supervisor
        if supervisor is None:
            return None
        # A consumer cannot install an arbitrary remote-call ID: the trusted
        # host creates a supervisor inside the exact GenerationAttempt stage.
        if type(supervisor) is not ModalFunctionCallSupervisor:
            raise ModalTransportUnavailable('GATE3_UNTRUSTED_FUNCTION_CALL_SUPERVISOR')
        try:
            return supervisor.cancel_on_uncertain(reason)
        except (Exception,):
            # Cancellation might have reached the provider; the supervisor
            # records durable CANCEL_INTENT_DURABLE before dispatch.
            # Never turn the provider outage into a retry.
            return None

    def fetch_approved_loopback(self,*,principal_id,spend_token,scope,spend_store,request):
        # Preflight before token redemption, then REDEEM before opening any socket.
        key=self._preflight(scope,request)
        if not isinstance(spend_store,Gate3AuthorizationStore):
            raise ModalTransportUnavailable('GATE3_CANONICAL_SPEND_AUTHORITY_REQUIRED')
        receipt=spend_store.redeem(principal_id,spend_token,scope)
        if (receipt.get('state')!='DRY_RUN_ONLY'
            or receipt.get('remoteExecutionEnabled') is not False
            or receipt.get('trialAuthorized') is not False):
            raise ModalTransportUnavailable('GATE3_OFFLINE_TOKEN_AUTHORITY_MISMATCH')
        payload=json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        req=urllib.request.Request(self.endpoint_url,data=payload,method='POST',
            headers={'Content-Type':'application/json','Accept':'audio/wav',
                     'Authorization':'Bearer '+key})
        # No redirects, proxies or implicit cross-origin bearer forwarding.
        opener=urllib.request.build_opener(_NoRedirect(),urllib.request.ProxyHandler({}))
        start=time.monotonic()
        try:
            with opener.open(req,timeout=self.http_timeout_sec) as response:
                if response.status!=200 or response.headers.get_content_type()!='audio/wav':
                    raise ModalTransportUnavailable('GATE3_PROVIDER_RESPONSE_NOT_WAV')
                cents=response.headers.get('X-Estimated-Gpu-Cost-Cents')
                if not isinstance(cents,str) or not re.fullmatch(r'\d{1,9}',cents):
                    raise ModalTransportUnavailable('GATE3_COST_ESTIMATE_MISSING')
                estimate=int(cents)
                if estimate>scope['maxUsdCents']:
                    raise ModalTransportUnavailable('GATE3_PROVIDER_ESTIMATE_EXCEEDS_BUDGET')
                raw=response.read(12*1024*1024+1)
                if not 44<=len(raw)<=12*1024*1024:
                    raise ValueError('GATE3_PROVIDER_AUDIO_SIZE_INVALID')
        except urllib.error.HTTPError as exc:
            # Even HTTP-500 can be a chargeable submission: preserve ambiguity.
            if exc.code>=500:
                self._request_remote_cancel_if_bound('HTTP_5XX')
                raise RemoteSubmissionUncertain('GATE3_PROVIDER_HTTP_OUTCOME_UNKNOWN') from exc
            raise ModalTransportUnavailable('GATE3_PROVIDER_HTTP_DENIED') from exc
        except PlatformDenied:
            # PlatformDenied inherits PermissionError/OSError; our definitive
            # cost/rights/redirect denial must NEVER be reported as a network
            # failure eligible for ambiguous-effect reconciliation.
            raise
        except (urllib.error.URLError,TimeoutError,socket.timeout,OSError) as exc:
            self._request_remote_cancel_if_bound('HTTP_TIMEOUT')
            raise RemoteSubmissionUncertain('GATE3_PROVIDER_TIMEOUT_OR_IO_OUTCOME_UNKNOWN') from exc
        except (KeyboardInterrupt,SystemExit):
            self._request_remote_cancel_if_bound('CLIENT_ABORT')
            raise
        elapsed=time.monotonic()-start
        if elapsed>self.http_timeout_sec:
            self._request_remote_cancel_if_bound('HTTP_TIMEOUT')
            raise RemoteSubmissionUncertain('GATE3_PROVIDER_WALLCLOCK_HARD_TIMEOUT')
        return {'wave_bytes':raw,'elapsed_wall_seconds':round(elapsed,6),
            'estimated_gpu_cost_cents_unverified':estimate,
            'estimated_cost_source':'UNTRUSTED_LOOPBACK_PROVIDER_HEADER',
            'provider_spend_hard_cap_verified':False,
            'provider_execution_mode':'LOCAL_LOOPBACK_HTTP',
            'local_loopback_http_calls':1,
            'external_provider_calls':0,
            'external_charges_incurred_usd':0}

def run_bounded_local_http_gate3_trial(*,root,principal_id,scope,spend_store,
                                      spend_token,provider,request,
                                      receipt_signing_key):
    """Durable GenerationAttempt PREPARING before localhost POST; never real Modal.

    Host authorization, source membership, immutable ProjectRevision/CAS and
    P1 exact-region splicing stay in their existing canonical Studio owners.
    Unknown HTTP effects remain SUBMISSION_UNCERTAIN: no blind retries.
    """
    from pathlib import Path
    from m045_gate3_live_trial_harness import (_physical_decode,
        _signature_fields,_publish_gate3_audition)
    from m045_generation_attempt import native_atomic_write_bytes
    from m045_bs1770_reference import measure_reference_pcm16
    from m045_repaint import read_pcm16_wav,bar_sample_window
    from studio_server import project_operation,project_audio_bytes,make_m045_native_owner
    if type(provider) is not ModalAceStepHttpProvider:
        raise ModalTransportUnavailable('GATE3_HTTP_PROVIDER_TYPE_UNQUALIFIED')
    if provider.host_call_supervisor is not None:
        # The direct caller cannot prebind an arbitrary Modal ID. It must be
        # constructed by a trusted host factory for the newly created
        # GenerationAttempt's *actual* durable staging directory.
        raise ModalTransportUnavailable('GATE3_UNBOUND_HOST_CALL_HANDLE_DENIED')
    if (not isinstance(receipt_signing_key,bytes)
        or len(receipt_signing_key)<32):
        raise ModalTransportUnavailable('GATE3_SIGNER_REQUIRED')
    validate_scope(scope)
    provider._preflight(scope)  # no socket yet; impossible to reach real Modal
    if not isinstance(request,dict):
        raise ValueError('GATE3_REQUEST_REQUIRED')
    root=Path(root).resolve()
    active=project_operation(root,{'projectId':scope['projectId']},
                             principal_id=principal_id)
    expected=scope['baseRevisionId']
    if active['manifest']['currentRevisionId']!=expected:
        raise ModalTransportUnavailable('GATE3_EXPECTED_CURRENT_STALE')
    task=request.get('task_type')
    if task not in ('text2music','repaint'):
        raise ValueError('GATE3_TASK_TYPE_INVALID')
    # Do not let caller supply an authority-replacing audio object. Repaint
    # source is bound to the selected exact Studio revision, never browser bytes.
    repaint=task=='repaint'
    required={'prompt','lyrics','audio_duration','audio_format','seed','task_type'}
    if set(request)!=(required|({'repainting_start','repainting_end','src_audio_base64'} if repaint else set())):
        raise ValueError('GATE3_REQUEST_FIELDS_INVALID')
    if repaint and request['src_audio_base64'] is not None:
        raise ModalTransportUnavailable('GATE3_BROWSER_SUPPLIED_REPAINT_SOURCE_DENIED')
    # Preflight no-source fields by shape before acquiring a durable attempt.
    validation=dict(request)
    if repaint:
        # All source material is recovered by the canonical GenerationAttempt;
        # the dummy is used only after binding it inside its durable stage.
        validation['src_audio_base64']=base64.b64encode(b'RIFF'+b'\x00'*40).decode()
    provider._validate_request(scope,validation)
    duration=request['audio_duration']
    params={'music_length_ms':int(round(duration*1000))}
    if repaint:
        from m045_repaint import bar_sample_window
        pid=scope['projectId']
        outputs=active['revision'].get('outputArtifactIds',[])
        if len(outputs)!=1:
            raise ModalTransportUnavailable('GATE3_REPAINT_EXACT_SOURCE_REQUIRED')
        original=project_audio_bytes(root,{'projectId':pid,'revisionId':expected,
               'artifactId':outputs[0]},principal_id=principal_id)
        _,frames=read_pcm16_wav(original)
        # Explicit frame coordinates have no ambiguity about canonical bars.
        start=request['repainting_start']
        end=request['repainting_end']
        if (abs(round(start*44100)-start*44100)>1e-6
            or abs(round(end*44100)-end*44100)>1e-6):
            raise ValueError('GATE3_REPAINT_NOT_SAMPLE_ALIGNED')
        # Bar ranges must be deterministic and correspond EXACTLY to the
        # canonical SongSpec meter/tempo, not user-provided clock offsets.
        spec=active['songSpec']
        track_ids=[t['track_id'] for t in spec.get('tracks',[])]
        if not track_ids:
            raise ModalTransportUnavailable('GATE3_REPAINT_TARGET_TRACK_MISSING')
        first,last=None,None
        for i in range(1,64):
            for j in range(i+1,65):
                try:a,b=bar_sample_window(spec,i,j,frames)
                except ValueError:continue
                if a==round(start*44100) and b==round(end*44100):
                    first,last=i,j
                    break
            if first is not None:break
        if first is None:
            raise ModalTransportUnavailable('GATE3_REPAINT_BAR_POSITION_UNQUALIFIED')
        if abs(frames/44100-duration)>1/44100:
            raise ValueError('GATE3_REPAINT_DURATION_NOT_SOURCE_BOUND')
        params.update({'edit_mode':'repaint','start_bar':first,'end_bar':last,
                       'target_track_id':track_ids[0]})
    auth_token=__import__('secrets').token_urlsafe(48)
    owner=make_m045_native_owner(root,scoped_principal=principal_id,
                                host_delegation_token=auth_token)
    meta={}
    def synth(stage_dir,song_spec,prompt,lyrics,seed,attempt_params):
        stage_dir=Path(stage_dir)
        outbound=dict(request)
        if repaint:
            source_path=stage_dir/'repaint-source.wav'
            source=source_path.read_bytes()
            region=attempt_params['_m045_repaint']
            if hashlib.sha256(source).hexdigest()!=region['source_sha256']:
                raise ModalTransportUnavailable('GATE3_STAGE_SOURCE_PROVENANCE_DENIED')
            outbound['src_audio_base64']=base64.b64encode(source).decode()
            outbound['repainting_start']=region['start_sample']/44100
            outbound['repainting_end']=region['end_sample']/44100
        # The provider itself atomically consumes the host-signed token
        # BEFORE opening any socket. No other path can activate it.
        active_provider=provider
        if provider.host_call_supervisor_factory is not None:
            from dataclasses import replace
            factory=provider.host_call_supervisor_factory
            if not callable(factory):
                raise ModalTransportUnavailable('GATE3_TRUSTED_HOST_FACTORY_REQUIRED')
            supervisor=factory(stage_dir,principal_id,scope)
            if (type(supervisor) is not ModalFunctionCallSupervisor
                or supervisor.stage_dir!=stage_dir.resolve()
                or supervisor.principal_id!=principal_id
                or supervisor.project_id!=scope['projectId']
                or supervisor.source_revision_id!=scope['baseRevisionId']
                or supervisor.attempt_id!=stage_dir.name[:-len('.stage')]):
                raise ModalTransportUnavailable('GATE3_CALL_ID_WRONG_ATTEMPT_OWNER')
            supervisor._read() # ID must be durable before possible effect.
            active_provider=replace(provider,host_call_supervisor=supervisor,
                                    host_call_supervisor_factory=None)
        transport=active_provider.fetch_approved_loopback(
             principal_id=principal_id,spend_token=spend_token,scope=scope,
             spend_store=spend_store,request=outbound)
        normalized,physical=_physical_decode(transport['wave_bytes'],scope)
        length=physical['samples_per_channel']
        if abs(length-44100*duration)>1:
            raise ValueError('GATE3_PROVIDER_OUTPUT_LENGTH_NOT_REQUESTED')
        media_sha=hashlib.sha256(normalized).hexdigest()
        native_atomic_write_bytes(stage_dir/'output.wav',normalized)
        native_atomic_write_bytes(stage_dir/'provider-receipt.json',_signature_fields({
            'source_type':'OPEN_WEIGHT_REMOTE_PROVIDER',
            'rights_status':'OPEN_WEIGHT_UNVERIFIED_TRAINING_DATA',
            'preservation_tier':'P2' if repaint else 'P3',
            'model_id':scope['modelId'],'model_version':scope['modelId'],
            'checkpoint_sha256':scope['checkpointManifestSha256'],
            'seed':seed,'audio_sha256':media_sha,
            'transport':'LOCAL_LOOPBACK_HTTP_TEST',
            'estimated_cost_cents_unverified':transport['estimated_gpu_cost_cents_unverified'],
            'provider_spend_hard_cap_verified':False,
            'external_provider_calls':0,'charges_incurred_usd':0}))
        meta.update(transport)
        return stage_dir/'output.wav'
    synth.supports_repaint=True
    synth.supports_remote_resume=True
    synth.model_id=scope['modelId']
    synth.model_version=scope['modelId']
    result=owner.execute_attempt(headers={'Authorization':'Bearer '+auth_token},
        project_id=scope['projectId'],base_revision_id=expected,
        expected_current_revision_id=expected,
        idempotency_key='gate3-http-'+hashlib.sha256(spend_token.encode()).hexdigest(),
        model_id=scope['modelId'],model_version=scope['modelId'],
        seed=request['seed'],song_spec=active['songSpec'],
        prompt=request['prompt'],lyrics=request['lyrics'],params=params,
        synthesize_to_stage_fn=synth)
    if result['state']!='COMMITTED':
        raise ModalTransportUnavailable('GATE3_COMMIT_NOT_CERTIFIED_RECONCILE_REQUIRED')
    revision=result['revision']['revisionId']
    digest=result['attempt']['artifact_digest']
    stored=project_audio_bytes(root,{'projectId':scope['projectId'],
        'revisionId':revision,'artifactId':digest},principal_id=principal_id)
    if hashlib.sha256(stored).hexdigest()!=digest:
        raise ModalTransportUnavailable('GATE3_CAS_READBACK_MISMATCH')
    physical=measure_reference_pcm16(stored)
    tier='P1' if repaint else 'P3'
    evidence={}
    if repaint:
        old_pcm,frames=read_pcm16_wav(original)
        new_pcm,new_frames=read_pcm16_wav(stored)
        a,b=bar_sample_window(active['songSpec'],params['start_bar'],params['end_bar'],frames)
        if (frames!=new_frames or old_pcm[:a*4]!=new_pcm[:a*4]
                or old_pcm[b*4:]!=new_pcm[b*4:]):
            raise ModalTransportUnavailable('GATE3_P1_OUTSIDE_WINDOW_CHANGED')
        evidence={'sourceArtifactSha256':outputs[0],
                  'p1OutsidePrefixSha256':hashlib.sha256(new_pcm[:a*4]).hexdigest(),
                  'p1OutsideSuffixSha256':hashlib.sha256(new_pcm[b*4:]).hexdigest(),
                  'declaredEditWindowSamples':[a,b]}
    return _publish_gate3_audition(root,scope,expected,revision,digest,stored,
        physical,receipt_signing_key,preservation_tier=tier,extra_receipt={
            'transportKind':'LOCAL_LOOPBACK_HTTP',
            'providerElapsedWallSeconds':meta['elapsed_wall_seconds'],
            'estimatedGpuCostCentsUnverified':meta['estimated_gpu_cost_cents_unverified'],
            'estimatedGpuCostSource':meta['estimated_cost_source'],
            'providerSpendHardCapVerified':False,
            'localLoopbackHttpCalls':1,
            'externalProviderCalls':0,
            'remoteProviderCalled':False,
            'gpuAllocated':False,
            'audioGenerationVerified':False,
            **evidence
        },extra_result={'localLoopbackHttpCalls':1,'networkCallsMade':0,
                        'providerSpendHardCapVerified':False})


# R17: one-call GPU exposure reference is not an enforceable account budget.
# Modal publishes this specific L40S rate; CPU, memory, warmup, repeated inputs,
# pricing changes and real cancellation delay remain independently unqualified.
def compute_modal_l40s_exposure_reference(*,gpu_rate_usd_per_second,
                                          runtime_seconds,
                                          scaledown_window_seconds,
                                          max_containers):
    from decimal import Decimal,InvalidOperation
    if (type(runtime_seconds) is not int or runtime_seconds!=120
        or type(scaledown_window_seconds) is not int or scaledown_window_seconds!=30
        or type(max_containers) is not int or max_containers!=1):
        raise ValueError('GATE3_EXPOSURE_PROFILE_NOT_BOUNDED')
    if not isinstance(gpu_rate_usd_per_second,Decimal):
        raise ValueError('GATE3_GPU_RATE_DECIMAL_REQUIRED')
    rate=gpu_rate_usd_per_second
    if not rate.is_finite() or rate<=0:
        raise ValueError('GATE3_GPU_RATE_INVALID')
    running=Decimal(runtime_seconds)*rate
    max_reference=Decimal(runtime_seconds+scaledown_window_seconds)*rate
    return {'gpuRateUsdPerSecond':str(rate),
            'runtimeOnlyGpuUsd':str(running.quantize(Decimal('0.000001'))),
            'runtimePlusIdleGpuUsd':str(max_reference.quantize(Decimal('0.000001'))),
            'scope':'SINGLE_FUNCTION_INPUT_GPU_ONLY_REFERENCE',
            'assumptions':['NO_ADDITIONAL_INPUT','NO_RETRY','ONE_GPU_CONTAINER',
                'STARTUP_OVERHEAD_NOT_BOUNDED','CPU_MEMORY_NOT_INCLUDED',
                'NO_PROVIDER_BILLING_ENFORCEMENT','REFERENCE_NOT_COST_CEILING'],
            'totalProviderBillingCapVerified':False}


_MODAL_ID=re.compile(r'fc-[A-Za-z0-9_-]{8,128}\Z')
def _validated_call_id(call_id):
    if not isinstance(call_id,str) or not _MODAL_ID.fullmatch(call_id):
        raise ModalTransportUnavailable('GATE3_MODAL_CALL_ID_NOT_HOST_QUALIFIED')
    return call_id


def modal_sdk_host_call_resolver(call_id):
    """Host-only adapter: requires independently qualified Modal SDK/session.

    Do not call without independent spend grant, checkpoint and billing policy.
    Import is delayed: source/tests never create a live Modal session.
    """
    _validated_call_id(call_id)
    import modal
    return modal.FunctionCall.from_id(call_id)


def cancel_remote_attempt(call_id,*,terminate_containers=True,host_call_resolver=None):
    """Request termination of an identified Modal FunctionCall, not an HTTP URL.

    A successful SDK call is *CANCEL_DISPATCHED*, not independent assurance
    that a GPU has stopped or that a billing threshold was enforced.
    """
    _validated_call_id(call_id)
    if terminate_containers is not True or not callable(host_call_resolver):
        raise ModalTransportUnavailable('GATE3_HOST_MODAL_CANCEL_AUTHORITY_MISSING')
    call=host_call_resolver(call_id)
    if not callable(getattr(call,'cancel',None)):
        raise ModalTransportUnavailable('GATE3_HOST_MODAL_CALL_HANDLE_INVALID')
    call.cancel(terminate_containers=True)
    return {'callId':call_id,'status':'CANCEL_DISPATCHED_UNVERIFIED',
            'containerTerminationVerified':False,'billingHardCapVerified':False}


def poll_remote_attempt(call_id,*,host_call_resolver=None):
    """Never spawn, resubmit or use a remote result as Studio revision authority."""
    _validated_call_id(call_id)
    if not callable(host_call_resolver):
        raise ModalTransportUnavailable('GATE3_HOST_MODAL_POLL_AUTHORITY_MISSING')
    call=host_call_resolver(call_id)
    if not callable(getattr(call,'get',None)):
        raise ModalTransportUnavailable('GATE3_HOST_MODAL_CALL_HANDLE_INVALID')
    try:
        result=call.get(timeout=0)
    except (TimeoutError,):
        return {'callId':call_id,'status':'PENDING',
                'containerTerminationVerified':False,'billingHardCapVerified':False}
    except Exception as exc:
        # Do not guess from unknown SDK errors whether a GPU stopped.  The
        # exception is never surfaced with secrets or remote object content.
        if exc.__class__.__name__ in ('TimeoutError','Timeout','FunctionTimeoutError'):
            return {'callId':call_id,'status':'PENDING',
                    'containerTerminationVerified':False,'billingHardCapVerified':False}
        if exc.__class__.__name__ in ('CancelledError','FunctionCallCancelledError'):
            return {'callId':call_id,'status':'CANCELLED_REPORTED_UNVERIFIED',
                    'containerTerminationVerified':False,'billingHardCapVerified':False}
        return {'callId':call_id,'status':'UNKNOWN_NEEDS_HOST_REVIEW',
                'containerTerminationVerified':False,'billingHardCapVerified':False}
    return {'callId':call_id,'status':'COMPLETED_UNVERIFIED',
            'resultAvailable':True,
            'acceptedStudioArtifact':False,
            'containerTerminationVerified':False,'billingHardCapVerified':False}


class ModalFunctionCallSupervisor:
    """Durable source-bound call-ID receipt subordinate to an existing attempt.

    It cannot create, authorize, resubmit or promote a GenerationAttempt. The
    caller MUST have already passed Studio principal/project/revision/attempt
    checks; the stage directory must belong to that existing attempt.
    """
    _RECORD='modal-function-call.json'
    def __init__(self,*,stage_dir,principal_id,project_id,source_revision_id,
                 attempt_id,host_call_resolver):
        from pathlib import Path
        self.stage_dir=Path(stage_dir).resolve()
        self.principal_id=principal_id
        self.project_id=project_id
        self.source_revision_id=source_revision_id
        self.attempt_id=attempt_id
        self.host_call_resolver=host_call_resolver
        if (not all(isinstance(v,str) and 1<=len(v)<=256 and
                    all(c.isalnum() or c in '_-:' for c in v)
                    for v in (principal_id,project_id,source_revision_id,attempt_id))
            or self.stage_dir.name!=attempt_id+'.stage'
            or not self.stage_dir.is_dir() or self.stage_dir.is_symlink()
            or not callable(host_call_resolver)):
            raise ModalTransportUnavailable('GATE3_EXISTING_HOST_ATTEMPT_REQUIRED')
        self.path=self.stage_dir/self._RECORD
    def _identity(self):
        return {'schemaVersion':'sara.modal.call.control.v1',
                'principalId':self.principal_id,'projectId':self.project_id,
                'sourceRevisionId':self.source_revision_id,'attemptId':self.attempt_id}
    def _read(self):
        import json
        if not self.path.is_file() or self.path.is_symlink():
            raise ModalTransportUnavailable('GATE3_DURABLE_HOST_CALL_ID_MISSING')
        try:doc=json.loads(self.path.read_bytes())
        except (ValueError,OSError) as exc:
            raise ModalTransportUnavailable('GATE3_DURABLE_HOST_CALL_ID_INVALID') from exc
        if (not isinstance(doc,dict)
            or any(doc.get(k)!=v for k,v in self._identity().items())
            or doc.get('callId')!=_validated_call_id(doc.get('callId'))
            or doc.get('state') not in ('CALL_ID_DURABLE','CANCEL_INTENT_DURABLE',
                                       'CANCEL_DISPATCHED_UNVERIFIED')):
            raise ModalTransportUnavailable('GATE3_OWNER_OR_CALL_ID_CONFLICT')
        return doc
    def _write(self,doc):
        from m045_generation_attempt import native_atomic_write_bytes
        payload=json.dumps(doc,sort_keys=True,separators=(',',':')).encode('utf-8')
        native_atomic_write_bytes(self.path,payload)
        if self.path.read_bytes()!=payload:
            raise ModalTransportUnavailable('GATE3_CALL_ID_DURABLE_READBACK_MISMATCH')
    def bind(self,call_id):
        call_id=_validated_call_id(call_id)
        if self.path.exists():
            prior=self._read()
            if prior['callId']!=call_id:
                raise ModalTransportUnavailable('GATE3_CALL_ID_REBIND_DENIED')
            return prior
        doc={**self._identity(),'callId':call_id,'state':'CALL_ID_DURABLE',
             'remoteEffect':'POSSIBLE_UNVERIFIED','billingHardCapVerified':False}
        self._write(doc)
        return doc
    def cancel_on_uncertain(self,reason):
        if reason not in ('HTTP_TIMEOUT','CLIENT_ABORT','HTTP_5XX','UNKNOWN_REMOTE_EFFECT'):
            raise ValueError('GATE3_CANCEL_REASON_INVALID')
        record=self._read()
        if record['state']!='CALL_ID_DURABLE':
            raise ModalTransportUnavailable('GATE3_CANCEL_ALREADY_DISPATCHED_OR_UNCERTAIN')
        record={**record,'state':'CANCEL_INTENT_DURABLE','cancelReason':reason}
        self._write(record) # durable intent BEFORE network control effect
        result=cancel_remote_attempt(record['callId'],terminate_containers=True,
                                    host_call_resolver=self.host_call_resolver)
        record={**record,'state':result['status']}
        self._write(record)
        return result
    def poll(self):
        record=self._read()
        return poll_remote_attempt(record['callId'],
                                   host_call_resolver=self.host_call_resolver)

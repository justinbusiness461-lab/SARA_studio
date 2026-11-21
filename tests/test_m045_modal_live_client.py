"""Round 16 RED: 127.0.0.1-only HTTP transport, reusable Studio Gate3.
No Modal endpoint calls, GPUs, web browsing or real inference."""
import hashlib
import io
import json
import math
import struct
import threading
import time
import unittest
import wave
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import test_platform_identity_and_catalog as platform_fixture
SPEC=platform_fixture.SPEC
from test_m045_gate3_live_trial_harness import KEY,CHECKPOINT,wav_of
from m045_gate3_authorization import Gate3AuthorizationStore
from platform_identity import PlatformDenied
from studio_server import project_operation,project_audio_bytes

class HTTPStub(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        if self.path!='/infer':self.send_error(404);return
        length=int(self.headers.get('Content-Length','0'))
        if length>20000000:self.send_error(413);return
        body=self.rfile.read(length)
        self.server.request_log.append((json.loads(body),dict(self.headers)))
        if self.server.delay:
            time.sleep(self.server.delay)
        response=self.server.audio
        code=self.server.status
        self.send_response(code)
        self.send_header('Content-Type','audio/wav')
        self.send_header('X-Estimated-Gpu-Cost-Cents',str(self.server.cost_cents))
        self.send_header('Content-Length',str(len(response)))
        self.end_headers()
        try:self.wfile.write(response)
        except BrokenPipeError:pass

class ModalLoopbackContract(unittest.TestCase):
    def setUp(self):
        f=platform_fixture.PlatformHTTP('test_acc01_entry_does_not_bootstrap_local_user')
        f.setUp();self.addCleanup(f.doCleanups);self.f=f
        self.user=f.signup('r16_artist')
        f.login('r16_artist')
        self.src=f.project(self.user['principalId'])
        self.store=Gate3AuthorizationStore(f.root,KEY)
        self.scope={'projectId':self.src['projectId'],'baseRevisionId':self.src['revisionId'],
           'modelId':'acestep-v15-turbo','checkpointManifestSha256':CHECKPOINT,
           'maxUsdCents':100,'maxAudioDurationSec':20,'maxContainerRuntimeSec':180,'ttlSeconds':300}
        self.server=ThreadingHTTPServer(('127.0.0.1',0),HTTPStub)
        self.server.audio=wav_of(seconds=1)
        self.server.request_log=[]
        self.server.status=200
        self.server.cost_cents=3
        self.server.delay=0
        thr=threading.Thread(target=self.server.serve_forever,daemon=True);thr.start()
        self.addCleanup(lambda:self.server.server_close())
        self.addCleanup(lambda:self.server.shutdown())
        self.addCleanup(lambda:thr.join(timeout=3))
        self.url='http://127.0.0.1:'+str(self.server.server_address[1])+'/infer'
        self.env={'SARA_GATE3_LIVE_NETWORK_ENABLED':'1',
                  'SARA_ACESTEP_API_KEY':'x'*40}
    def token(self,scope=None):
        scope=scope or self.scope
        pending=self.store.request(self.user['principalId'],scope)
        return self.store.admit_host(pending['requestId'],lambda _:True)
    def current(self):
        return project_operation(self.f.root,{'projectId':self.src['projectId']},
                                 principal_id=self.user['principalId'])['manifest']['currentRevisionId']
    def adapter(self,**overrides):
        from m045_modal_live_client import ModalAceStepHttpProvider
        env=overrides.pop('environment',self.env)
        return ModalAceStepHttpProvider(endpoint_url=overrides.pop('endpoint_url',self.url),
              environment=env,loopback_test_mode=overrides.pop('loopback_test_mode',True),
              http_timeout_sec=overrides.pop('http_timeout_sec',3),**overrides)
    def execute(self,**kw):
        from m045_gate3_live_trial_harness import run_bounded_gate3_trial_pipeline
        scope=kw.pop('scope',self.scope);token=kw.pop('token',None) or self.token(scope)
        return run_bounded_gate3_trial_pipeline(root=self.f.root,
          principal_id=self.user['principalId'],scope=scope,spend_store=self.store,
          spend_token=token,loopback_transport=None,receipt_signing_key=KEY,
          http_transport=kw.pop('transport',self.adapter()),
          trial_request=kw.pop('request',{'prompt':'Outlaw Hypno-Rock Country-Hop',
            'lyrics':'Original local synthetic test lyric','audio_duration':1.0,
            'audio_format':'wav','seed':117,'task_type':'text2music'}),**kw)
    def test_no_environment_flag_cannot_open_socket_or_advance_revision(self):
        for value in (None,'0','true','yes',' 1 '):
            env=dict(self.env)
            if value is None:env.pop('SARA_GATE3_LIVE_NETWORK_ENABLED')
            else:env['SARA_GATE3_LIVE_NETWORK_ENABLED']=value
            before=self.current()
            with self.subTest(value=value),self.assertRaises((PlatformDenied,ValueError)):
                self.execute(transport=self.adapter(environment=env))
            self.assertEqual(self.server.request_log,[])
            self.assertEqual(self.current(),before)
    def test_bearer_missing_or_invalid_url_denied_before_socket(self):
        bad_urls=['http://example.org/infer','https://evil.modal.run.attacker.example/infer',
            'http://127.0.0.2/infer','https://user:pass@example.modal.run/infer',
            'https://example.com/infer']
        for url in bad_urls:
            with self.subTest(url=url),self.assertRaises((PlatformDenied,ValueError)):
                self.execute(transport=self.adapter(endpoint_url=url))
        with self.assertRaises((PlatformDenied,ValueError)):
            self.execute(transport=self.adapter(environment={'SARA_GATE3_LIVE_NETWORK_ENABLED':'1',
                                                             'SARA_ACESTEP_API_KEY':'short'}))
        self.assertEqual(self.server.request_log,[])
    def test_no_host_verified_spend_cap_can_activate_real_modal(self):
        adapter=self.adapter(endpoint_url='https://models.modal.run/infer',loopback_test_mode=False)
        with patch('urllib.request.urlopen') as io_call:
            with self.assertRaises((PlatformDenied,ValueError)):
                self.execute(transport=adapter)
            io_call.assert_not_called()
        self.assertEqual(self.server.request_log,[])
    def test_missing_expired_replayed_token_and_wrong_owner_fail_before_http(self):
        from m045_gate3_live_trial_harness import run_bounded_gate3_trial_pipeline
        with self.assertRaises((PlatformDenied,ValueError)):
            self.execute(token='g3-'+('0'*128))
        self.assertEqual(self.server.request_log,[])
        expired=self.token()
        with patch('m045_gate3_authorization.time.time',return_value=time.time()+1000):
            with self.assertRaises((PlatformDenied,ValueError)):
                self.execute(token=expired)
        self.assertEqual(self.server.request_log,[])
        token=self.token()
        self.execute(token=token)
        count=len(self.server.request_log)
        with self.assertRaises((PlatformDenied,ValueError)):self.execute(token=token)
        self.assertEqual(len(self.server.request_log),count)
    def test_full_twenty_second_ace_step_contract_canonical_commit_audition_zip(self):
        from m045_gate3_live_trial_harness import verify_gate3_listening_receipt
        import zipfile
        self.server.audio=wav_of(seconds=20)
        old=self.current()
        req={'prompt':'Outlaw Hypno-Rock Country-Hop™ — Southern baritone, hypnotic groove',
             'lyrics':'Original test verse, no copyrighted text','audio_duration':20.0,
             'audio_format':'wav','seed':71,'task_type':'text2music'}
        result=self.execute(request=req)
        self.assertEqual(result['state'],'COMMITTED')
        self.assertNotEqual(self.current(),old)
        self.assertEqual(len(self.server.request_log),1)
        data,headers=self.server.request_log[0]
        self.assertEqual(data,req)
        self.assertEqual(headers['Authorization'],'Bearer '+'x'*40)
        r=result['listeningReceipt']
        self.assertTrue(verify_gate3_listening_receipt(r,KEY))
        self.assertEqual(r['samplesPerChannel'],882000)
        self.assertIsInstance(r['integratedLufsReference'],float)
        self.assertIsInstance(r['truePeakDbtp4xReference'],float)
        self.assertEqual(r['preservationTier'],'P3')
        self.assertEqual(r['rightsStatus'],'UNVERIFIED_HELD')
        self.assertFalse(r['creativeApproved'])
        self.assertFalse(result['releaseReady'])
        self.assertEqual(r['transportKind'],'LOCAL_LOOPBACK_HTTP')
        self.assertGreaterEqual(r['providerElapsedWallSeconds'],0)
        self.assertEqual(r['estimatedGpuCostCentsUnverified'],3)
        self.assertFalse(r['providerSpendHardCapVerified'])
        self.assertFalse(r['gpuAllocated'])
        self.assertEqual(result['chargesIncurredUsd'],0)
        zip_path=self.f.root/'projects'/self.src['projectId']/'gate3-listening-receipts'/(result['artifactId']+'.zip')
        with zipfile.ZipFile(zip_path) as z:
            w=z.read('audio.wav')
            self.assertEqual(json.loads(z.read('listening-receipt.json')),r)
        self.assertEqual(w,project_audio_bytes(self.f.root,{'projectId':self.src['projectId'],
            'revisionId':self.current(),'artifactId':result['artifactId']},
            principal_id=self.user['principalId']))
    def test_invalid_or_clipped_provider_wav_and_budget_overrun_fail_closed(self):
        for audio,cents in [(b'not a wav',3),(wav_of(amplitude=32767),3),(wav_of(),101)]:
            self.server.audio=audio;self.server.cost_cents=cents
            old=self.current()
            with self.subTest(cents=cents,audio_len=len(audio)),self.assertRaises((ValueError,PlatformDenied)):
                self.execute()
            self.assertEqual(self.current(),old)
    def test_http500_and_timeout_denied_without_current_promotion_or_auto_retry(self):
        from m045_generation_attempt import AttemptLifecycleState
        self.server.status=500;old=self.current()
        with self.assertRaises((PlatformDenied,RuntimeError)):
            self.execute()
        self.assertEqual(self.current(),old)
        self.server.status=200
        self.server.delay=.35
        adapter=self.adapter(http_timeout_sec=.1)
        before=len(self.server.request_log)
        with self.assertRaises((PlatformDenied,RuntimeError)):
            self.execute(transport=adapter)
        self.assertEqual(self.current(),old)
        self.assertEqual(len(self.server.request_log),before+1)
    def test_selective_repaint_p1_outside_window_and_historical_r2_preserved(self):
        from m045_repaint import bar_sample_window,read_pcm16_wav
        from m045_gate3_live_trial_harness import verify_gate3_listening_receipt
        # Repaint authority requires 44.1kHz canonical SongSpec; this fixture
        # adds no new timing owner or browser-derived position.
        spec={**SPEC,'timebase':{**SPEC['timebase'],'sample_rate':44100,'meter':'4/4'}}
        old=self.current()
        revision=project_operation(self.f.root,{'projectId':self.src['projectId'],
           'expectedCurrentRevisionId':old,'songSpec':spec,
           'outputArtifactIds':[self.src['artifactId']]},commit=True,
           principal_id=self.user['principalId'])
        self.scope={**self.scope,'baseRevisionId':revision['revision']['revisionId']}
        self.server.audio=wav_of(amplitude=2000,seconds=10)
        r2=self.execute(request={'prompt':'Outlaw Hypno-Rock Country-Hop','lyrics':'original test',
            'audio_duration':10.0,'audio_format':'wav','seed':13,'task_type':'text2music'})
        r2_id=r2['revisionId'];self.assertEqual(self.current(),r2_id)
        original=project_audio_bytes(self.f.root,{'projectId':self.src['projectId'],
          'revisionId':r2_id,'artifactId':r2['artifactId']},principal_id=self.user['principalId'])
        self.scope={**self.scope,'baseRevisionId':r2_id}
        self.server.audio=wav_of(amplitude=1300,seconds=10)
        request={'prompt':'Surgical local bass change','lyrics':'original test',
            'audio_duration':10.0,'audio_format':'wav','seed':14,'task_type':'repaint',
            'repainting_start':2.0,'repainting_end':4.0,
            'src_audio_base64':None}
        result=self.execute(request=request)
        self.assertEqual(self.current(),result['revisionId'])
        self.assertEqual(result['preservationTier'],'P1')
        self.assertTrue(verify_gate3_listening_receipt(result['listeningReceipt'],KEY))
        rr=project_audio_bytes(self.f.root,{'projectId':self.src['projectId'],
          'revisionId':result['revisionId'],'artifactId':result['artifactId']},
          principal_id=self.user['principalId'])
        source_pcm,frame_count=read_pcm16_wav(original)
        new_pcm,_=read_pcm16_wav(rr)
        a,b=bar_sample_window(spec,2,3,frame_count)
        self.assertEqual(source_pcm[:a*4],new_pcm[:a*4])
        self.assertEqual(source_pcm[b*4:],new_pcm[b*4:])
        self.assertNotEqual(source_pcm[a*4:b*4],new_pcm[a*4:b*4])
        # Historical R2 remains recoverable and does not become current.
        self.assertEqual(project_audio_bytes(self.f.root,{'projectId':self.src['projectId'],
          'revisionId':r2_id,'artifactId':r2['artifactId']},
          principal_id=self.user['principalId']),original)
        wire,headers=self.server.request_log[-1]
        self.assertEqual(wire['task_type'],'repaint')
        self.assertGreater(len(wire['src_audio_base64']),1000)
        self.assertEqual(wire['repainting_start'],2.0)
        self.assertEqual(wire['repainting_end'],4.0)
    def test_unsafe_scope_duration_and_timeout_rejected_without_http(self):
        for bad in [{'maxUsdCents':101},{'maxAudioDurationSec':21},
                    {'checkpointManifestSha256':'not-a-checkpoint'}]:
            with self.subTest(bad=bad),self.assertRaises((ValueError,PlatformDenied)):
                self.execute(scope={**self.scope,**bad})
        with self.assertRaises((ValueError,PlatformDenied)):
            self.execute(transport=self.adapter(http_timeout_sec=181))
        self.assertEqual(self.server.request_log,[])
if __name__=='__main__':unittest.main()

"""R15-A/B RED: offline post-inference provenance and SoundCloud PKCE never spend."""
import hashlib,io,math,struct,unittest,wave
from test_platform_identity_and_catalog import PlatformHTTP,SPEC,fixture_wav
from m045_gate3_authorization import Gate3AuthorizationStore
from platform_identity import PlatformDenied

KEY=b'host-local-gate3-test-signing-key-material-v1'
CHECKPOINT=hashlib.sha256(b'pinned-test-only-ACE-step-checkpoint').hexdigest()

def wav_of(amplitude=1000,seconds=1.0,rate=48000):
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate)
        frames=int(rate*seconds)
        data=bytearray()
        for n in range(frames):
            v=int(amplitude*math.sin(2*math.pi*220*n/rate))
            data+=struct.pack('<hh',v,v)
        w.writeframes(data)
    return out.getvalue()

class Gate3LoopbackTrial(unittest.TestCase):
    def setUp(self):
        f=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
        f.setUp();self.f=f;self.addCleanup(f.doCleanups)
        self.a=f.signup('trial_artist');self.ca,_=f.login('trial_artist')
        self.other=f.signup('other_artist','another strong password!')
        self.src=f.project(self.a['principalId'])
        self.store=Gate3AuthorizationStore(f.root,KEY)
        self.scope={'projectId':self.src['projectId'],'baseRevisionId':self.src['revisionId'],
            'modelId':'acestep-v15-turbo','checkpointManifestSha256':CHECKPOINT,
            'maxUsdCents':100,'maxAudioDurationSec':20,'maxContainerRuntimeSec':180,
            'ttlSeconds':300}
    def token(self):
        pending=self.store.request(self.a['principalId'],self.scope)
        return self.store.admit_host(pending['requestId'],lambda _:True)
    def current(self):
        from studio_server import project_operation
        return project_operation(self.f.root,{'projectId':self.src['projectId']},
            principal_id=self.a['principalId'])['manifest']['currentRevisionId']
    def execute(self,audio=None,token=None,**kw):
        from m045_gate3_live_trial_harness import LoopbackWavTransport,run_bounded_gate3_trial_pipeline
        return run_bounded_gate3_trial_pipeline(root=self.f.root,
            principal_id=self.a['principalId'],scope=self.scope,
            spend_store=self.store,spend_token=token or self.token(),
            loopback_transport=LoopbackWavTransport(audio if audio is not None else wav_of()),
            receipt_signing_key=KEY,**kw)
    def test_valid_loopback_decodes_measures_commits_with_signed_unapproved_receipt(self):
        from m045_gate3_live_trial_harness import verify_gate3_listening_receipt
        from studio_server import project_audio_bytes,project_operation
        old=self.current()
        result=self.execute()
        self.assertEqual(result['state'],'COMMITTED')
        self.assertNotEqual(self.current(),old)
        self.assertEqual(result['mode'],'DRY_RUN_ONLY')
        self.assertEqual(result['networkCallsMade'],0)
        self.assertEqual(result['gpuAllocated'],False)
        self.assertEqual(result['chargesIncurredUsd'],0)
        self.assertEqual(result['rightsStatus'],'UNVERIFIED_HELD')
        self.assertEqual(result['preservationTier'],'P3')
        self.assertFalse(result['creativeApproved'])
        self.assertFalse(result['releaseReady'])
        receipt=result['listeningReceipt']
        self.assertTrue(verify_gate3_listening_receipt(receipt,KEY))
        self.assertEqual(receipt['sampleRateHz'],44100)
        self.assertEqual(receipt['channels'],2)
        self.assertEqual(receipt['sampleWidthBytes'],2)
        self.assertIsInstance(receipt['integratedLufsReference'],float)
        self.assertIsInstance(receipt['truePeakDbtp4xReference'],float)
        self.assertEqual(receipt['sourceProjectRevisionId'],old)
        self.assertEqual(receipt['outputProjectRevisionId'],self.current())
        ref={'projectId':self.src['projectId'],'revisionId':self.current(),
             'artifactId':receipt['audioArtifactSha256']}
        wav=project_audio_bytes(self.f.root,ref,principal_id=self.a['principalId'])
        self.assertEqual(hashlib.sha256(wav).hexdigest(),receipt['audioArtifactSha256'])
        self.assertEqual(project_operation(self.f.root,{'projectId':ref['projectId']},
            principal_id=self.a['principalId'])['revision']['outputArtifactIds'],[ref['artifactId']])
    def test_corrupt_provider_bytes_cannot_advance_current(self):
        before=self.current()
        with self.assertRaises(ValueError):self.execute(audio=b'RIFFnotawav')
        self.assertEqual(self.current(),before)
    def test_clipped_loopback_audio_cannot_advance_current(self):
        before=self.current()
        with self.assertRaises(ValueError):self.execute(audio=wav_of(amplitude=32767))
        self.assertEqual(self.current(),before)
    def test_longer_than_scope_duration_cannot_advance_current(self):
        before=self.current()
        scope={**self.scope,'maxAudioDurationSec':1}
        token=self.store.admit_host(
            self.store.request(self.a['principalId'],scope)['requestId'],lambda _:True)
        from m045_gate3_live_trial_harness import LoopbackWavTransport,run_bounded_gate3_trial_pipeline
        with self.assertRaises(ValueError):
            run_bounded_gate3_trial_pipeline(root=self.f.root,principal_id=self.a['principalId'],
              scope=scope,spend_store=self.store,spend_token=token,
              loopback_transport=LoopbackWavTransport(wav_of(seconds=2)),
              receipt_signing_key=KEY)
        self.assertEqual(self.current(),before)
    def test_failed_decode_consumes_token_and_retry_requires_new_host_authorization(self):
        t=self.token();prior=self.current()
        with self.assertRaises(ValueError):self.execute(audio=b'RIFFnotawav',token=t)
        self.assertEqual(self.current(),prior)
        with self.assertRaises(PlatformDenied):self.execute(token=t)
        self.assertEqual(self.current(),prior)

    def test_token_double_redeem_denied_without_changing_current_again(self):
        token=self.token()
        self.execute(token=token)
        current=self.current()
        with self.assertRaises(PlatformDenied):self.execute(token=token)
        self.assertEqual(self.current(),current)
    def test_foreign_principal_and_untrusted_transport_denied(self):
        from m045_gate3_live_trial_harness import run_bounded_gate3_trial_pipeline
        token=self.token()
        with self.assertRaises((PlatformDenied,PermissionError)):
            run_bounded_gate3_trial_pipeline(root=self.f.root,
             principal_id=self.other['principalId'],scope=self.scope,
             spend_store=self.store,spend_token=token,loopback_transport=wav_of(),
             receipt_signing_key=KEY)
        with self.assertRaises((PlatformDenied,ValueError)):
            self.execute(token=token,allow_live_network=True)
        self.assertEqual(self.current(),self.scope['baseRevisionId'])
    def test_stale_revision_at_token_redemption_blocks_promotion(self):
        from studio_server import project_operation
        token=self.token()
        base=self.current()
        project_operation(self.f.root,{'projectId':self.src['projectId'],
          'expectedCurrentRevisionId':base,'songSpec':SPEC,
          'outputArtifactIds':[self.src['artifactId']]},
          commit=True,principal_id=self.a['principalId'])
        newer=self.current()
        with self.assertRaises((PlatformDenied,ValueError)):self.execute(token=token)
        self.assertEqual(self.current(),newer)
    def test_receipt_tampering_and_wrong_signer_fail(self):
        from m045_gate3_live_trial_harness import verify_gate3_listening_receipt
        receipt=self.execute()['listeningReceipt']
        self.assertFalse(verify_gate3_listening_receipt(receipt|{'creativeApproved':True},KEY))
        self.assertFalse(verify_gate3_listening_receipt(receipt,b'another-test-key-that-is-long-enough-32bytes'))
    def test_default_no_transport_stays_zero_spend_and_denies_live(self):
        from m045_gate3_live_trial_harness import run_bounded_gate3_trial_pipeline
        before=self.current()
        with self.assertRaises((ValueError,PlatformDenied)):
            run_bounded_gate3_trial_pipeline(root=self.f.root,principal_id=self.a['principalId'],
              scope=self.scope,spend_store=self.store,spend_token=self.token(),
              loopback_transport=None,receipt_signing_key=KEY)
        self.assertEqual(self.current(),before)

    def test_human_listening_zip_is_exact_audio_and_signed_receipt_not_publication(self):
        import zipfile,json
        from studio_server import project_audio_bytes
        from m045_gate3_live_trial_harness import verify_gate3_listening_receipt
        result=self.execute()
        location=self.f.root/'projects'/self.src['projectId']/'gate3-listening-receipts'/(
            result['artifactId']+'.zip')
        self.assertTrue(location.is_file())
        self.assertEqual(hashlib.sha256(location.read_bytes()).hexdigest(),result['listeningBundleSha256'])
        with zipfile.ZipFile(location) as bundle:
            self.assertEqual(set(bundle.namelist()),{'audio.wav','listening-receipt.json','listening-rubric.txt'})
            wav=bundle.read('audio.wav')
            receipt=json.loads(bundle.read('listening-receipt.json'))
            rubric=bundle.read('listening-rubric.txt').decode('utf-8')
        self.assertEqual(wav,project_audio_bytes(self.f.root,{
            'projectId':self.src['projectId'],'revisionId':result['revisionId'],
            'artifactId':result['artifactId']},principal_id=self.a['principalId']))
        self.assertTrue(verify_gate3_listening_receipt(receipt,KEY))
        self.assertEqual(receipt,result['listeningReceipt'])
        self.assertIn('Human listening',rubric)
        self.assertIn('not creative approval',rubric.lower())
        self.assertFalse(result['listeningBundlePublished'])

class SoundCloudOfflineAdapter(unittest.TestCase):
    def setUp(self):
        f=PlatformHTTP('test_acc01_entry_does_not_bootstrap_local_user')
        f.setUp();self.f=f;self.addCleanup(f.doCleanups)
        self.a=f.signup('sc_artist');self.ca,_=f.login('sc_artist')
        self.p=f.project(self.a['principalId'])
    def adapter(self,**kw):
        from platform_soundcloud_adapter import SoundCloudReleaseAdapter
        return SoundCloudReleaseAdapter(self.f.root,client_id='test-local-client-id',
          redirect_uri='http://127.0.0.1/callback',**kw)
    def test_pkce_challenge_state_are_s256_correct_unique_and_no_remote_call(self):
        import base64
        from urllib.parse import urlsplit,parse_qs
        a=self.adapter()
        one=a.prepare_authorization()
        two=a.prepare_authorization()
        self.assertNotEqual(one['state'],two['state'])
        self.assertNotEqual(one['codeVerifier'],two['codeVerifier'])
        expected=base64.urlsafe_b64encode(hashlib.sha256(one['codeVerifier'].encode()).digest()).rstrip(b'=').decode()
        self.assertEqual(one['codeChallenge'],expected)
        q=parse_qs(urlsplit(one['authorizationUrl']).query)
        self.assertEqual(q['code_challenge_method'],['S256'])
        self.assertEqual(q['state'],[one['state']])
        self.assertEqual(one['networkCallsMade'],0)
        self.assertEqual(one['external_dsp_published'],False)
    def test_missing_credentials_fail_closed_provider_503(self):
        from platform_soundcloud_adapter import SoundCloudReleaseAdapter,SoundCloudUnavailable
        missing=SoundCloudReleaseAdapter(self.f.root,client_id='',redirect_uri='')
        with self.assertRaises(SoundCloudUnavailable) as e:missing.prepare_authorization()
        self.assertEqual(e.exception.http_status,503)
        with self.assertRaises(SoundCloudUnavailable) as e:missing.prepare_upload('rp-'+'0'*64,self.a['principalId'])
        self.assertEqual(e.exception.http_status,503)
    def test_release_package_builds_repeatable_nonpublishable_upload_intent(self):
        from studio_server import configure_platform_publication_rights
        from platform_release_gateway import StudioReleaseGateway
        from platform_soundcloud_adapter import SoundCloudUnavailable
        gateway=StudioReleaseGateway(self.f.root)
        p=self.p;principal=self.a['principalId']
        policy=lambda pid,rid,aid,actor:'ARTIST_OWNED' if (pid,rid,aid,actor)==(
           p['projectId'],p['revisionId'],p['artifactId'],principal) else None
        payload={'projectId':p['projectId'],'revisionId':p['revisionId'],
          'artifactId':p['artifactId'],'title':SPEC['title'],'artistHandle':'sc_artist',
          'genre':'Outlaw Hypno-Rock Country-Hop','coverArtSha256':'b'*64,
          'rightsStatus':'ARTIST_ORIGINAL'}
        token=gateway.approve(principal,payload|{'confirmRelease':True})['approvalToken']
        package=gateway.prepare(principal,payload|{'approvalToken':token},policy)
        adapter=self.adapter(rights_policy=policy)
        one=adapter.prepare_upload(package['packageId'],principal)
        two=adapter.prepare_upload(package['packageId'],principal)
        self.assertEqual(one,two)
        self.assertEqual(one['idempotencyKey'],two['idempotencyKey'])
        self.assertEqual(one['sourceRevisionId'],p['revisionId'])
        self.assertEqual(one['artifactSha256'],p['artifactId'])
        self.assertEqual(one['state'],'UPLOAD_HELD')
        self.assertFalse(one['external_dsp_published'])
        self.assertFalse(one['content_id_entitled'])
        with self.assertRaises((PermissionError,SoundCloudUnavailable)):
            adapter.prepare_upload(package['packageId'],'acct-'+'0'*32)
    def test_forged_package_and_stale_revision_fail_before_upload(self):
        from platform_soundcloud_adapter import SoundCloudReleaseAdapter
        adapter=self.adapter(rights_policy=lambda *args:'ARTIST_OWNED')
        with self.assertRaises((PermissionError,ValueError)):
            adapter.prepare_upload('rp-'+'f'*64,self.a['principalId'])
        self.assertEqual(adapter.network_calls_made,0)
    def test_upload_and_oauth_exchange_are_unimplemented_even_with_configuration(self):
        from platform_soundcloud_adapter import SoundCloudUnavailable
        adapter=self.adapter()
        with self.assertRaises(SoundCloudUnavailable):
            adapter.exchange_code_for_token('code','state')
        with self.assertRaises(SoundCloudUnavailable):
            adapter.execute_upload({'idempotencyKey':'x'})
        self.assertEqual(adapter.network_calls_made,0)
if __name__=='__main__':unittest.main()

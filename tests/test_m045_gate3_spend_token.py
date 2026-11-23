"""R11-A RED: true host-gated single-use authorization, no Modal network."""
import concurrent.futures,hashlib,unittest
from test_platform_identity_and_catalog import PlatformHTTP
from platform_identity import PlatformDenied,PlatformConflict
from m045_gate3_authorization import Gate3AuthorizationStore

HOST_KEY=b'test-only-host-signing-key-material-at-least-32-bytes'
CHECKPOINT=hashlib.sha256(b'test-only-ACE-step-model').hexdigest()
class Gate3SpendTokenTests(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP('test_acc01_entry_does_not_bootstrap_local_user');self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.user=self.fx.signup();self.cookie,_=self.fx.login();self.p=self.fx.project(self.user['principalId'])
  self.store=Gate3AuthorizationStore(self.fx.root,host_signing_key=HOST_KEY)
  self.scope={'projectId':self.p['projectId'],'baseRevisionId':self.p['revisionId'],
              'modelId':'acestep-v15-turbo','checkpointManifestSha256':CHECKPOINT,
              'maxUsdCents':100,'maxAudioDurationSec':20,'maxContainerRuntimeSec':180,'ttlSeconds':300}
 def admit(self):
  pending=self.store.request(self.user['principalId'],self.scope)
  token=self.store.admit_host(pending['requestId'],lambda claim:claim=={**self.scope,'principalId':self.user['principalId']})
  return pending,token
 def test_host_denial_and_no_browser_self_issue(self):
  p=self.store.request(self.user['principalId'],self.scope)
  self.assertEqual(p['state'],'PENDING_HOST_APPROVAL');self.assertNotIn('token',str(p))
  with self.assertRaises(PlatformDenied):self.store.admit_host(p['requestId'],lambda _:False)
  with self.assertRaises(PlatformDenied):self.store.redeem(self.user['principalId'],'g3-'+('0'*128),self.scope)
 def test_one_time_host_admission_redemption_and_cold_reopen(self):
  _,token=self.admit()
  reopened=Gate3AuthorizationStore(self.fx.root,host_signing_key=HOST_KEY)
  receipt=reopened.redeem(self.user['principalId'],token,self.scope)
  self.assertEqual(receipt['state'],'DRY_RUN_ONLY')
  self.assertFalse(receipt['trialAuthorized'])
  self.assertEqual(receipt['maxUsdCents'],100)
  with self.assertRaises(PlatformDenied):reopened.redeem(self.user['principalId'],token,self.scope)
 def test_reject_tampering_foreign_user_and_stale_revision(self):
  _,token=self.admit()
  with self.assertRaises(PlatformDenied):self.store.redeem('foreign',token,self.scope)
  tampered=token[:-1]+('0' if token[-1]!='0' else '1')
  self.assertNotEqual(tampered,token)  # Tamper must differ even if token originally ends in 0.
  with self.assertRaises(PlatformDenied):self.store.redeem(self.user['principalId'],tampered,self.scope)
  with self.assertRaises(PlatformConflict):self.store.redeem(self.user['principalId'],token,{**self.scope,'maxUsdCents':99})
  self.store.redeem(self.user['principalId'],token,self.scope)
 def test_budget_model_ttl_and_duration_rejections(self):
  for key,bad in [('maxUsdCents',101),('maxUsdCents',-1),('modelId','other'),
      ('maxAudioDurationSec',21),('maxContainerRuntimeSec',181),('ttlSeconds',901),
      ('checkpointManifestSha256','0')]:
   with self.subTest(key=key):
    with self.assertRaises((ValueError,PlatformDenied)):
     self.store.request(self.user['principalId'],{**self.scope,key:bad})
 def test_concurrent_claim_only_one_wins(self):
  _,token=self.admit()
  def claim(_):
   try:return self.store.redeem(self.user['principalId'],token,self.scope)['state']
   except (PlatformDenied,PlatformConflict):return 'DENIED'
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   states=list(pool.map(claim,range(2)))
  self.assertEqual(sorted(states),['DENIED','DRY_RUN_ONLY'])
 def test_host_cannot_approve_after_revision_change(self):
  pending=self.store.request(self.user['principalId'],self.scope)
  from studio_server import project_operation
  current=project_operation(self.fx.root,{'projectId':self.p['projectId']},principal_id=self.user['principalId'])
  project_operation(self.fx.root,{'projectId':self.p['projectId'],
     'expectedCurrentRevisionId':self.p['revisionId'],'songSpec':current['songSpec'],
     'outputArtifactIds':current['revision']['outputArtifactIds']},commit=True,principal_id=self.user['principalId'])
  with self.assertRaises(PlatformConflict):self.store.admit_host(pending['requestId'],lambda _:True)
if __name__=='__main__':unittest.main()

# Integrated API check: requester controls neither signing authority nor host approval.
class Gate3HttpSecurity(unittest.TestCase):
 def test_authenticated_pending_request_and_host_admission_redeem(self):
  import os
  from unittest.mock import patch
  fx=PlatformHTTP('test_acc01_entry_does_not_bootstrap_local_user');fx.setUp();self.addCleanup(fx.doCleanups)
  principal=fx.signup()['principalId'];cookie,_=fx.login();project=fx.project(principal)
  scope={'projectId':project['projectId'],'baseRevisionId':project['revisionId'],
         'modelId':'acestep-v15-turbo','checkpointManifestSha256':CHECKPOINT,
         'maxUsdCents':100,'maxAudioDurationSec':20,'maxContainerRuntimeSec':180,'ttlSeconds':300}
  with patch.dict(os.environ,{'SARA_GATE3_HOST_SIGNING_KEY':HOST_KEY.decode()}):
   self.assertEqual(fx.api('/api/m045/gate3/request-spend',scope)[0],403)
   status,_,p=fx.api('/api/m045/gate3/request-spend',scope,cookie=cookie)
   self.assertEqual(status,202,p);self.assertEqual(p['state'],'PENDING_HOST_APPROVAL')
   self.assertEqual(fx.api('/api/m045/gate3/redeem',{'spendToken':'g3-'+'0'*128,'scope':scope},cookie=cookie)[0],403)
   t=Gate3AuthorizationStore(fx.root,HOST_KEY).admit_host(p['requestId'],lambda _:True)
   status,_,receipt=fx.api('/api/m045/gate3/redeem',{'spendToken':t,'scope':scope},cookie=cookie)
   self.assertEqual(status,200,receipt)
   self.assertEqual(receipt['state'],'DRY_RUN_ONLY');self.assertFalse(receipt['trialAuthorized'])
   self.assertEqual(fx.api('/api/m045/gate3/redeem',{'spendToken':t,'scope':scope},cookie=cookie)[0],403)
  self.assertEqual(fx.api('/api/m045/gate3/request-spend',scope,cookie=cookie)[0],503)

class Gate3ExpiryAndStale(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP('test_acc01_entry_does_not_bootstrap_local_user');self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.principal=self.fx.signup()['principalId'];self.fx.login();self.p=self.fx.project(self.principal)
  self.s=Gate3AuthorizationStore(self.fx.root,HOST_KEY)
  self.scope={'projectId':self.p['projectId'],'baseRevisionId':self.p['revisionId'],
              'modelId':'acestep-v15-turbo','checkpointManifestSha256':CHECKPOINT,
              'maxUsdCents':100,'maxAudioDurationSec':20,'maxContainerRuntimeSec':180,'ttlSeconds':2}
 def test_expired_host_token_cannot_be_redeemed(self):
  from unittest.mock import patch
  request=self.s.request(self.principal,self.scope)
  token=self.s.admit_host(request['requestId'],lambda _:True)
  import time
  with patch('m045_gate3_authorization.time.time',return_value=time.time()+10):
   with self.assertRaises(PlatformDenied):self.s.redeem(self.principal,token,self.scope)
 def test_stale_revision_after_admission_fails_closed_without_consume(self):
  request=self.s.request(self.principal,self.scope)
  token=self.s.admit_host(request['requestId'],lambda _:True)
  from studio_server import project_operation
  p=project_operation(self.fx.root,{'projectId':self.p['projectId']},principal_id=self.principal)
  project_operation(self.fx.root,{'projectId':self.p['projectId'],
     'expectedCurrentRevisionId':self.p['revisionId'],'songSpec':p['songSpec'],
     'outputArtifactIds':p['revision']['outputArtifactIds']},commit=True,principal_id=self.principal)
  with self.assertRaises(PlatformConflict):self.s.redeem(self.principal,token,self.scope)
 def test_key_rotation_invalidates_old_token(self):
  request=self.s.request(self.principal,self.scope)
  token=self.s.admit_host(request['requestId'],lambda _:True)
  rotated=Gate3AuthorizationStore(self.fx.root,b'rotated-test-only-host-signing-key-32-plus-bytes')
  with self.assertRaises(PlatformDenied):rotated.redeem(self.principal,token,self.scope)

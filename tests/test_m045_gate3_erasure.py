"""R11 security regression: new principal-bearing Gate3 table must not break erasure."""
import hashlib,unittest
import test_platform_identity_and_catalog as fixture
from platform_identity import PlatformStore,PlatformDenied
from m045_gate3_authorization import Gate3AuthorizationStore
KEY=b'host-only-ephemeral-token-erasure-test-key-material'
class Gate3ErasureBoundary(unittest.TestCase):
 def setUp(self):
  self.fx=fixture.PlatformHTTP('test_acc01_entry_does_not_bootstrap_local_user')
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.principal=self.fx.signup()['principalId'];self.cookie,_=self.fx.login()
  self.identity=PlatformStore(self.fx.root)
  self.approvals=Gate3AuthorizationStore(self.fx.root,KEY)
 def test_reviewed_empty_approval_table_does_not_hold_unrelated_account_erasure(self):
  self.assertEqual(self.fx.api('/api/me',{'confirm':'DELETE_MY_ACCOUNT'},method='DELETE',cookie=self.cookie)[0],202)
  result=self.identity.process_account_erasure_lifecycle(studio_root=self.fx.root)
  self.assertEqual(result['completed'],1,result)
  self.assertEqual(result['held'],0,result)
 def test_pending_and_admitted_tokens_are_revoked_during_account_purge(self):
  project=self.fx.project(self.principal)
  scope={'projectId':project['projectId'],'baseRevisionId':project['revisionId'],
         'modelId':'acestep-v15-turbo','checkpointManifestSha256':hashlib.sha256(b'model').hexdigest(),
         'maxUsdCents':100,'maxAudioDurationSec':20,'maxContainerRuntimeSec':180,'ttlSeconds':300}
  p=self.approvals.request(self.principal,scope)
  token=self.approvals.admit_host(p['requestId'],lambda _:True)
  self.assertEqual(self.fx.api('/api/me',{'confirm':'DELETE_MY_ACCOUNT'},method='DELETE',cookie=self.cookie)[0],202)
  self.assertEqual(self.identity.process_pending_account_erasures()['processed'],1)
  with self.identity._db() as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM gate3_spend_requests WHERE principal=?',(self.principal,)).fetchone()[0],0)
  with self.assertRaises(PlatformDenied):self.approvals.redeem(self.principal,token,scope)
  with self.assertRaises(PlatformDenied):self.approvals.admit_host(p['requestId'],lambda _:True)
if __name__=='__main__':unittest.main()

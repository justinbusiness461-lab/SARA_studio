"""R9 host policy is not outside the R8 account erasure completion scope."""
import unittest
from platform_identity import PlatformStore,PlatformDenied
from m045_host_authorities import HostRightsRegistry
from test_platform_identity_and_catalog import PlatformHTTP

class HostRightsErasureCrossBoundary(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.account=self.fx.signup();self.cookie,_=self.fx.login()
  self.store=PlatformStore(self.fx.root)
 def test_host_rights_identity_prevents_false_erasure_complete(self):
  record={'principalId':self.account['principalId'],
          'projectId':'a'*32,'revisionId':'b'*64,'artifactId':'c'*64,
          'eventId':None,'status':'LICENSE_CLEARED','evidenceSha256':'d'*64}
  rights=HostRightsRegistry(self.fx.root)
  rights.import_attestations([record])
  self.assertEqual(self.fx.api('/api/me',{'confirm':'DELETE_MY_ACCOUNT'},method='DELETE',cookie=self.cookie)[0],202)
  self.assertEqual(self.store.process_pending_account_erasures()['processed'],1)
  with self.assertRaisesRegex(PlatformDenied,'ERASURE_HOST_RIGHTS_PERSONAL_IDENTITY_HELD'):
   self.store.complete_account_erasure(self.account['principalId'],studio_root=self.fx.root)
  self.assertIsNone(self.store.account_erasure_completion_receipt(self.account['principalId']))
  self.assertEqual(self.store.process_account_erasure_lifecycle(studio_root=self.fx.root)['held'],1)

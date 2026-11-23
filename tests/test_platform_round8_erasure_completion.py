"""R8-B RED: accountable completion only when personal media ownership is absent."""
import hashlib,json,unittest
from platform_identity import PlatformStore,PlatformDenied
from test_platform_identity_and_catalog import PlatformHTTP

class ErasureCompletionTests(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.account=self.fx.signup();self.cookie,_=self.fx.login()
  self.store=PlatformStore(self.fx.root)
 def request_and_mutable_purge(self):
  code,_,result=self.fx.api('/api/me',{'confirm':'DELETE_MY_ACCOUNT'},method='DELETE',cookie=self.cookie)
  self.assertEqual(code,202,result)
  self.assertEqual(self.store.process_pending_account_erasures()['processed'],1)
 def test_unowned_media_account_may_complete_with_durable_receipt(self):
  self.request_and_mutable_purge()
  owner=self.account['principalId']
  receipt=self.store.complete_account_erasure(owner,studio_root=self.fx.root)
  self.assertEqual(receipt['state'],'ERASURE_COMPLETED')
  self.assertTrue(receipt['eligibleDataErasureComplete'])
  self.assertFalse(receipt['allHistoricalRecordsDestroyed'])
  self.assertEqual(receipt,self.store.account_erasure_completion_receipt(owner))
  self.assertEqual(receipt,self.store.complete_account_erasure(owner,studio_root=self.fx.root))
  self.assertEqual(len(receipt['receiptSha256']),64)
  with self.store._db() as db:
   self.assertEqual(db.execute('SELECT state FROM account_erasure_requests WHERE principal=?',(owner,)).fetchone()[0],'COMPLETED')
  self.assertEqual(self.fx.api('/api/auth/login',{'handle':'artist_a','password':'strong secret phrase A!'})[0],403)
 def test_retained_music_project_must_hold_not_fake_completion(self):
  self.fx.project(self.account['principalId'])
  self.request_and_mutable_purge()
  with self.assertRaises(PlatformDenied):
   self.store.complete_account_erasure(self.account['principalId'],studio_root=self.fx.root)
  with self.store._db() as db:
   self.assertEqual(db.execute('SELECT state FROM account_erasure_requests WHERE principal=?',(self.account['principalId'],)).fetchone()[0],'PURGED_MUTABLE')
 def test_unpurged_and_wrong_owner_cannot_complete(self):
  with self.assertRaises(PlatformDenied):
   self.store.complete_account_erasure(self.account['principalId'],studio_root=self.fx.root)
 def test_future_unclassified_personal_table_prevents_false_completion(self):
  self.request_and_mutable_purge()
  with self.store._db() as db:
   db.execute("CREATE TABLE future_sensitive_store(principal TEXT,data TEXT)")
   db.execute("INSERT INTO future_sensitive_store VALUES(?,?)",
      (self.account['principalId'],"old personal history"))
  with self.assertRaisesRegex(PlatformDenied,"ERASURE_SCHEMA_UNREVIEWED"):
   self.store.complete_account_erasure(self.account['principalId'],studio_root=self.fx.root)
  with self.store._db() as db:
   self.assertEqual(db.execute("SELECT state FROM account_erasure_requests WHERE principal=?",
      (self.account['principalId'],)).fetchone()[0],"PURGED_MUTABLE")

class FullErasureLifecycleWorker(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.account=self.fx.signup();self.cookie,_=self.fx.login()
  self.store=PlatformStore(self.fx.root)
 def test_worker_advances_pending_to_completed_with_idempotent_receipt(self):
  self.assertEqual(self.fx.api('/api/me',{'confirm':'DELETE_MY_ACCOUNT'},method='DELETE',cookie=self.cookie)[0],202)
  result=self.store.process_account_erasure_lifecycle(studio_root=self.fx.root)
  self.assertEqual(result['mutableProcessed'],1)
  self.assertEqual(result['completed'],1)
  self.assertEqual(result['held'],0)
  receipt=result['receipts'][0]
  self.assertEqual(receipt,self.store.account_erasure_completion_receipt(self.account['principalId']))
  self.assertEqual(self.store.process_account_erasure_lifecycle(studio_root=self.fx.root)['completed'],0)
 def test_worker_holds_nonempty_project_and_preserves_history(self):
  project=self.fx.project(self.account['principalId'])
  self.fx.api('/api/me',{'confirm':'DELETE_MY_ACCOUNT'},method='DELETE',cookie=self.cookie)
  result=self.store.process_account_erasure_lifecycle(studio_root=self.fx.root)
  self.assertEqual(result['completed'],0)
  self.assertEqual(result['held'],1)
  self.assertEqual(result['holds'][0]['reason'],'ERASURE_HELD_IMMUTABLE_PROJECT_DATA')
  import studio_server as studio
  current=studio.project_operation(self.fx.root,{'projectId':project['projectId']},principal_id=self.account['principalId'])
  self.assertEqual(current['revision']['revisionId'],project['revisionId'])

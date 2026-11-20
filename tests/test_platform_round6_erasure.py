"""R6 RED -> GREEN: public account deletion and retention-aware mutable purge."""
import unittest
from platform_identity import PlatformStore
from platform_social import SocialStore
from platform_workspaces import WorkspaceStore
from test_platform_identity_and_catalog import PlatformHTTP

class AccountDeletionWebAndWorker(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.a=self.fx.signup()
  self.cookie,_=self.fx.login()
 def test_anonymous_public_web_page_no_capability_and_truthful_pending_receipt(self):
  status,headers,body=self.fx.req("/account/delete",cap=False)
  self.assertEqual(status,200,body[:250])
  self.assertIn("text/html",headers.get("Content-Type",""))
  self.assertIn(b"/api/account/delete-request",body)
  self.assertIn(b"ERASURE_PENDING",body)
  self.assertNotIn(b"window.__STUDIO_SESSION__",body)
  self.assertEqual(self.fx.api("/api/me",cap=False)[0],403)
 def test_pending_worker_purges_mutable_data_without_claiming_immutable_media_erase(self):
  from platform_identity import PlatformStore
  store=PlatformStore(self.fx.root)
  principal=self.a["principalId"]
  second=self.fx.signup("artist_b","another strong password!")
  own=SocialStore(self.fx.root)
  own.create_playlist(principal,"My playlist","private")
  own.create_album(principal,"My album draft")
  own.create_playlist(second["principalId"],"Their playlist","private")
  WorkspaceStore(self.fx.root).create(principal,"My private draft")
  with store._db() as db:
   db.execute("UPDATE accounts SET bio='private profile' WHERE principal=?",(principal,))
   db.execute("INSERT INTO social_comments VALUES(?,?,?,?,?)",
      ("comment-1",principal,"pub-unpublished","private words",10))
  code,_,request=self.fx.api("/api/me",{"confirm":"DELETE_MY_ACCOUNT"},method="DELETE",cookie=self.cookie)
  self.assertEqual(code,202,request)
  self.assertFalse(request["erasureComplete"])
  result=store.process_pending_account_erasures()
  self.assertEqual(result["processed"],1,result)
  self.assertFalse(result["erasureComplete"])
  self.assertIn("immutable_project_revisions",result["retainedDataClasses"])
  with store._db() as db:
   row=db.execute("SELECT handle,display_name,bio,status FROM accounts WHERE principal=?",(principal,)).fetchone()
   self.assertNotEqual(row["handle"],"artist_a")
   self.assertEqual(row["bio"],"")
   self.assertEqual(row["status"],"erased_partial")
   for table,key in (("sessions","principal"),("social_playlists","principal"),
       ("social_albums","principal"),("social_comments","author"),
       ("platform_workspaces","owner")):
    self.assertEqual(db.execute(f"SELECT count(*) FROM {table} WHERE {key}=?",(principal,)).fetchone()[0],0,table)
   self.assertEqual(db.execute("SELECT count(*) FROM social_playlists WHERE principal=?",(second["principalId"],)).fetchone()[0],1)
   self.assertEqual(db.execute("SELECT state FROM account_erasure_requests WHERE principal=?",(principal,)).fetchone()[0],"PURGED_MUTABLE")
  self.assertEqual(store.process_pending_account_erasures()["processed"],0)
  self.assertIsNone(store.public_profile("artist_a"))
  self.assertEqual(self.fx.api("/api/auth/login",{"handle":"artist_a","password":"strong secret phrase A!"})[0],403)
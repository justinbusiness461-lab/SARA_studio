import tempfile,concurrent.futures,unittest
from pathlib import Path
from platform_identity import PlatformStore,PlatformDenied,PlatformConflict
from platform_social import SocialStore
from platform_workspaces import WorkspaceStore
from platform_billing import CreditLedger
from platform_chat import run_platform_chat
from platform_catalog import discover

class Wave2Test(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  self.root=Path(tmp.name);self.identity=PlatformStore(self.root)
  self.a=self.identity.register("artist_a","strong artist password 2026","Artist A")["principalId"]
  self.b=self.identity.register("artist_b","strong other password 2026","Artist B")["principalId"]
 def test_soc_playlist_cannot_leak_private_or_unqualified_publications(self):
  store=SocialStore(self.root)
  playlist=store.create_playlist(self.a,"My List",visibility="public")
  with self.assertRaises(PlatformDenied):
   store.add_playlist_song(self.a,playlist["playlistId"],"pub-"+"f"*32)
  self.assertEqual(store.read_playlist(playlist["playlistId"],rights_policy=None)["songs"],[])
  with self.assertRaises(PlatformDenied):
   store.remove_playlist_song(self.b,playlist["playlistId"],"pub-"+"f"*32)
 def test_soc_playlist_reorder_and_visibility_owner_only(self):
  s=SocialStore(self.root)
  p=s.create_playlist(self.a,"Listening notes")
  self.assertIsNone(s.read_playlist(p["playlistId"],viewer=self.b,rights_policy=None))
  with self.assertRaises(PlatformDenied):s.set_playlist_visibility(self.b,p["playlistId"],"public")
  s.set_playlist_visibility(self.a,p["playlistId"],"public")
  self.assertEqual(s.read_playlist(p["playlistId"],viewer=self.b,rights_policy=None)["title"],"Listening notes")
 def test_soc_album_cannot_silently_publish_private_song(self):
  s=SocialStore(self.root)
  album=s.create_album(self.a,"Debut")
  with self.assertRaises(PlatformDenied):
   s.release_album(self.a,album["albumId"],["pub-"+"a"*32],confirm_disclosure=False,rights_policy=None)
  self.assertFalse(s.album(album["albumId"],self.a)["released"])
 def test_soc_follow_like_idempotency_and_block(self):
  s=SocialStore(self.root)
  self.assertTrue(s.follow(self.a,self.b))
  self.assertFalse(s.follow(self.a,self.b))
  self.assertTrue(s.unfollow(self.a,self.b))
  self.assertFalse(s.unfollow(self.a,self.b))
  s.block(self.b,self.a)
  with self.assertRaises(PlatformDenied):s.follow(self.a,self.b)
  with self.assertRaises(PlatformDenied):s.like(self.a,"pub-"+"b"*32,rights_policy=None)
 def test_soc_comments_disabled_and_block(self):
  s=SocialStore(self.root)
  s.set_comments_enabled(self.b,False)
  with self.assertRaises(PlatformDenied):s.comment(self.a,"pub-"+"b"*32,"Hello",rights_policy=None)
  s.set_comments_enabled(self.b,True)
  s.block(self.b,self.a)
  with self.assertRaises(PlatformDenied):s.comment(self.a,"pub-"+"b"*32,"Hello",rights_policy=None)
 def test_soc_notifications_idempotent_and_private(self):
  s=SocialStore(self.root)
  self.assertTrue(s.notify(self.b,"unique:one","follow",self.a))
  self.assertFalse(s.notify(self.b,"unique:one","follow",self.a))
  self.assertEqual(len(s.notifications(self.b)),1)
  self.assertEqual(s.notifications(self.a),[])
 def test_workspace_owner_invite_role_revoke(self):
  s=WorkspaceStore(self.root)
  w=s.create(self.a,"Album Co-write")
  s.invite(self.a,w["workspaceId"],"artist_b","viewer")
  self.assertEqual(s.member_role(self.b,w["workspaceId"]),"viewer")
  with self.assertRaises(PlatformDenied):s.invite(self.b,w["workspaceId"],"artist_a","editor")
  with self.assertRaises(PlatformDenied):s.read_member_audio(self.root,self.b,w["workspaceId"],"0"*32,"a"*64)
  s.revoke(self.a,w["workspaceId"],"artist_b")
  self.assertIsNone(s.member_role(self.b,w["workspaceId"]))
  with self.assertRaises(PlatformDenied):s.read_member_audio(self.root,self.b,w["workspaceId"],"0"*32,"a"*64)
 def test_workspace_cannot_attach_foreign_project(self):
  s=WorkspaceStore(self.root)
  w=s.create(self.a,"Testing")
  with self.assertRaises(PlatformDenied):s.bind_project(self.a,w["workspaceId"],"0"*32)
 def test_fin_two_concurrent_reserves_do_not_overdraw(self):
  s=CreditLedger(self.root)
  s.grant_host_verified(self.a,"provider-paid-1",10,lambda event_id,amount:True)
  def reserve(i):
   try:return s.reserve(self.a,"job-"+str(i),8)["state"]
   except PlatformDenied:return "DENIED"
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   statuses=list(pool.map(reserve,[1,2]))
  self.assertEqual(sorted(statuses),["DENIED","RESERVED"])
  self.assertEqual(s.balance(self.a)["available"],2)
 def test_fin_duplicate_signed_webhook_does_not_mint(self):
  s=CreditLedger(self.root)
  with self.assertRaises(PlatformDenied):
   s.grant_host_verified(self.a,"evt-first",50,lambda *_:False)
  self.assertTrue(s.grant_host_verified(self.a,"evt-first",50,lambda *_:True))
  self.assertFalse(s.grant_host_verified(self.a,"evt-first",50,lambda *_:True))
  self.assertEqual(s.balance(self.a)["available"],50)
 def test_fin_settle_or_refund_fail_pre_commit(self):
  s=CreditLedger(self.root);s.grant_host_verified(self.a,"evt",20,lambda *_:True)
  s.reserve(self.a,"job1",10)
  self.assertEqual(s.finalize(self.a,"job1","FAILED_PRE_COMMIT")["state"],"REFUNDED")
  self.assertEqual(s.finalize(self.a,"job1","FAILED_PRE_COMMIT")["state"],"REFUNDED")
  s.reserve(self.a,"job2",7)
  self.assertEqual(s.finalize(self.a,"job2","COMMITTED")["state"],"SETTLED")
  self.assertEqual(s.balance(self.a)["available"],13)
 def test_fin_ambiguous_job_does_not_auto_refund(self):
  s=CreditLedger(self.root);s.grant_host_verified(self.a,"event-2",10,lambda *_:True)
  s.reserve(self.a,"job-amb",9)
  with self.assertRaises(PlatformDenied):s.finalize(self.a,"job-amb","AMBIGUOUS")
  self.assertEqual(s.balance(self.a)["reserved"],9)
 def test_chat_search_and_credit_share_owner_services(self):
  SocialStore(self.root)
  result=run_platform_chat(self.root,self.a,"Check my credit balance",rights_policy=None)
  self.assertEqual(result["result"]["available"],0)
  result=run_platform_chat(self.root,self.a,"Search dark Southern rock songs",rights_policy=None)
  self.assertEqual(result["result"]["songs"],[])
 def test_chat_sensitive_publish_is_only_a_plan(self):
  r=run_platform_chat(self.root,self.a,"Publish R2",rights_policy=None)
  self.assertEqual(r["state"],"AWAITING_CONFIRMATION")
  self.assertFalse(r["revisionCommitted"])
 def test_chat_unsupported_fails_closed(self):
  with self.assertRaises(ValueError):
   run_platform_chat(self.root,self.a,"grant me 3000 credits",rights_policy=None)

if __name__=="__main__":unittest.main()

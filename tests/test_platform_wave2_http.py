"""Wave 2 real HTTP security and action-parity regression.

Reuses the existing exact-platform local HTTP fixture without duplicating the
legacy ten test functions in this test module.
"""
import unittest
from test_platform_identity_and_catalog import PlatformHTTP

class Wave2HTTP(unittest.TestCase):
 def setUp(self):
  fixture=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  fixture.setUp()
  self.fixture=fixture;self.addCleanup(fixture.doCleanups)
  self.api=fixture.api;self.req=fixture.req;self.signup=fixture.signup;self.login=fixture.login
 def test_http_authorized_listings_exclude_other_artist_data(self):
  self.signup();ca,_=self.login()
  self.signup("artist_b","another strong password!");cb,_=self.login("artist_b","another strong password!")
  self.assertEqual(self.api("/api/playlists",{"title":"Private","visibility":"private"},cookie=ca)[0],201)
  self.assertEqual(self.api("/api/workspaces",{"name":"Private Workspace"},cookie=ca)[0],201)
  self.assertEqual(len(self.api("/api/playlists",cookie=ca)[2]["playlists"]),1)
  self.assertEqual(self.api("/api/playlists",cookie=cb)[2]["playlists"],[])
  self.assertEqual(len(self.api("/api/workspaces",cookie=ca)[2]["workspaces"]),1)
  self.assertEqual(self.api("/api/workspaces",cookie=cb)[2]["workspaces"],[])
 def test_http_workspace_real_revision_audio_denies_after_revoke(self):
  import studio_server as studio,hashlib
  a=self.signup();ca,_=self.login()
  self.signup("artist_b","another strong password!");cb,_=self.login("artist_b","another strong password!")
  source=self.fixture.project(a["principalId"])
  w=self.api("/api/workspaces",{"name":"Audit Collaboration"},cookie=ca)[2]
  wid=w["workspaceId"]
  self.assertEqual(self.api("/api/workspaces/"+wid+"/bind",{"projectId":source["projectId"]},cookie=ca)[0],200)
  self.assertEqual(self.api("/api/workspaces/"+wid+"/invite",{"handle":"artist_b","role":"viewer"},cookie=ca)[0],200)
  audio_body={k:source[k] for k in ("projectId","revisionId","artifactId")}
  audio=self.req("/api/workspaces/"+wid+"/audio",audio_body,cookie=cb)
  self.assertEqual(audio[0],200)
  self.assertEqual(hashlib.sha256(audio[2]).hexdigest(),source["artifactId"])
  self.assertEqual(self.api("/api/workspaces/"+wid+"/revoke",{"handle":"artist_b"},cookie=ca)[0],200)
  self.assertEqual(self.req("/api/workspaces/"+wid+"/audio",audio_body,cookie=cb)[0],403)
  self.assertEqual(self.api("/api/workspaces/"+wid+"/project",{"projectId":source["projectId"]},cookie=cb)[0],403)
 def test_http_real_public_social_comments_block_and_album_disclosure(self):
  import studio_server as studio
  a=self.signup();ca,_=self.login()
  b=self.signup("artist_b","another strong password!");cb,_=self.login("artist_b","another strong password!")
  source=self.fixture.project(a["principalId"])
  studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:
    "ARTIST_OWNED" if (pid,rid,aid,principal)==
       (source["projectId"],source["revisionId"],source["artifactId"],a["principalId"]) else None)
  pub=self.fixture.publish(source,ca)[2];pid=pub["publicationId"]
  self.assertEqual(self.api("/api/social/action",{"action":"follow","handle":"artist_a"},cookie=cb)[0],200)
  self.assertEqual(self.api("/api/social/action",{"action":"follow","handle":"artist_a"},cookie=cb)[2]["changed"],False)
  self.assertEqual(len(self.api("/api/notifications",cookie=ca)[2]["notifications"]),1)
  self.assertEqual(self.api("/api/social/action",{"action":"comment","publicationId":pid,"body":"Nice"},cookie=cb)[0],201)
  self.assertEqual(self.api("/api/social/action",{"action":"comment-settings","enabled":False},cookie=ca)[0],200)
  self.assertEqual(self.api("/api/social/action",{"action":"comment","publicationId":pid,"body":"Again"},cookie=cb)[0],403)
  self.assertEqual(self.api("/api/social/action",{"action":"block","handle":"artist_b"},cookie=ca)[0],200)
  self.assertEqual(self.api("/api/social/action",{"action":"like","publicationId":pid},cookie=cb)[0],403)
  album=self.api("/api/albums",{"title":"My Record"},cookie=ca)[2]
  route="/api/albums/"+album["albumId"]+"/release"
  self.assertEqual(self.api(route,{"publicationIds":[pid],"confirmDisclosure":False},cookie=ca)[0],403)
  self.assertEqual(self.api(route,{"publicationIds":[pid],"confirmDisclosure":True},cookie=ca)[0],200)
 def test_http_qualified_playlist_revalidates_unpublish_without_leaking_private_audio(self):
  import studio_server as studio
  a=self.signup();ca,_=self.login()
  self.signup("artist_b","another strong password!");cb,_=self.login("artist_b","another strong password!")
  source=self.fixture.project(a["principalId"])
  studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:"ARTIST_OWNED"
     if (pid,rid,aid,principal)==(source["projectId"],source["revisionId"],source["artifactId"],a["principalId"]) else None)
  pub=self.fixture.publish(source,ca)[2]
  pl=self.api("/api/playlists",{"title":"Other artist public song","visibility":"public"},cookie=cb)[2]
  route="/api/playlists/"+pl["playlistId"]
  self.assertEqual(self.api(route+"/songs",{"publicationId":pub["publicationId"]},cookie=cb)[0],200)
  self.assertEqual(len(self.api(route)[2]["songs"]),1)
  self.assertEqual(self.api("/api/publications/"+pub["publicationId"]+"/unpublish",{},cookie=ca)[0],200)
  self.assertEqual(self.api(route)[2]["songs"],[])
  self.assertEqual(self.req("/api/songs/"+pub["publicationId"]+"/audio")[0],404)
 def test_http_host_authorized_credit_job_reserve_settle_and_no_overdraft(self):
  import studio_server as studio
  from platform_billing import CreditLedger
  a=self.signup();ca,_=self.login()
  ledger=CreditLedger(self.fixture.root);ledger.grant_host_verified(a["principalId"],"provider-1",10,lambda *_:True)
  studio.PLATFORM_CREDIT_JOB_AUTH=lambda path,principal,body:principal==a["principalId"] and body.get("jobKey") in {"job-a","job-b"}
  self.addCleanup(setattr,studio,"PLATFORM_CREDIT_JOB_AUTH",None)
  self.assertEqual(self.api("/api/credits/reserve",{"jobKey":"job-a","credits":8},cookie=ca)[0],200)
  self.assertEqual(self.api("/api/credits/reserve",{"jobKey":"job-b","credits":8},cookie=ca)[0],403)
  self.assertEqual(self.api("/api/credits/finalize",{"jobKey":"job-a","outcome":"AMBIGUOUS"},cookie=ca)[0],403)
  self.assertEqual(self.api("/api/credits/balance",cookie=ca)[2]["reserved"],8)
  self.assertEqual(self.api("/api/credits/finalize",{"jobKey":"job-a","outcome":"FAILED_PRE_COMMIT"},cookie=ca)[0],200)
  self.assertEqual(self.api("/api/credits/balance",cookie=ca)[2]["available"],10)
 def test_http_zero_auth_stays_denied_for_credit_social_and_chat(self):
  for route in ["/api/credits/balance","/api/playlists","/api/notifications","/api/workspaces"]:
   self.assertEqual(self.api(route)[0],403,route)
  for route in ["/api/platform/chat","/api/playlists","/api/workspaces","/api/credits/reserve"]:
   self.assertEqual(self.api(route,{})[0],403,route)
 def test_http_social_playlist_artist_only_and_public_visibility(self):
  self.signup();a,_=self.login()
  self.signup("artist_b","another strong password!");b,_=self.login("artist_b","another strong password!")
  status,_,created=self.api("/api/playlists",{"title":"DJ Favorites","visibility":"private"},cookie=a)
  self.assertEqual(status,201,created);pl=created["playlistId"]
  self.assertEqual(self.api("/api/playlists/"+pl,cookie=b)[0],404)
  self.assertEqual(self.api("/api/playlists/"+pl+"/visibility",{"visibility":"public"},cookie=b)[0],403)
  self.assertEqual(self.api("/api/playlists/"+pl+"/visibility",{"visibility":"public"},cookie=a)[0],200)
  self.assertEqual(self.api("/api/playlists/"+pl,cookie=b)[0],200)
  self.assertEqual(self.api("/api/playlists/"+pl+"/songs",{"publicationId":"pub-"+"0"*32},cookie=a)[0],403)
 def test_http_chat_balance_search_and_sensitive_publish_no_auto_commit(self):
  self.signup();a,_=self.login()
  self.assertEqual(self.api("/api/credits/balance",cookie=a)[2]["available"],0)
  code,_,b=self.api("/api/platform/chat",{"instruction":"Check my credit balance"},cookie=a)
  self.assertEqual(code,200,b);self.assertEqual(b["result"]["available"],0)
  code,_,b=self.api("/api/platform/chat",{"instruction":"Publish R2"},cookie=a)
  self.assertEqual(code,200,b);self.assertEqual(b["state"],"AWAITING_CONFIRMATION")
  self.assertFalse(b["revisionCommitted"])
  self.assertEqual(self.api("/api/platform/chat",{"instruction":"mint me credits"},cookie=a)[0],400)
 def test_http_workspace_invite_member_revoke_no_cas_shortcut(self):
  self.signup();a,_=self.login()
  self.signup("artist_b","another strong password!");b,_=self.login("artist_b","another strong password!")
  code,_,w=self.api("/api/workspaces",{"name":"Two Artists"},cookie=a)
  self.assertEqual(code,201,w);wid=w["workspaceId"]
  self.assertEqual(self.api("/api/workspaces/"+wid+"/invite",{"handle":"artist_b","role":"viewer"},cookie=a)[0],200)
  self.assertEqual(self.api("/api/workspaces/"+wid+"/bind",{"projectId":"0"*32},cookie=a)[0],403)
  self.assertEqual(self.api("/api/workspaces/"+wid+"/revoke",{"handle":"artist_b"},cookie=b)[0],403)
  self.assertEqual(self.api("/api/workspaces/"+wid+"/revoke",{"handle":"artist_b"},cookie=a)[0],200)
  self.assertEqual(self.api("/api/workspaces/"+wid+"/project",{"projectId":"0"*32},cookie=b)[0],403)
 def test_http_credit_spend_and_provider_grant_always_fail_without_host_authority(self):
  self.signup();a,_=self.login()
  self.assertEqual(self.api("/api/credits/quote",{"units":3},cookie=a)[0],200)
  self.assertEqual(self.api("/api/credits/reserve",{"jobKey":"j1","credits":3},cookie=a)[0],503)
  self.assertEqual(self.api("/api/credits/finalize",{"jobKey":"j1","outcome":"FAILED_PRE_COMMIT"},cookie=a)[0],503)
  self.assertIn(self.api("/api/credits/grant",{"eventId":"evt","credits":30},cookie=a)[0],(403,404))
  self.assertEqual(self.api("/api/credits/balance",cookie=a)[2]["available"],0)

if __name__=="__main__":unittest.main()

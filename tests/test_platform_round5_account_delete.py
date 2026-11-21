"""Native store in-app and externally accessible account-erasure request controls.

A request cannot claim physical data erasure: project histories and media require
separately certified destruction/retention processing. Immediate session and
public-catalog shutdown is atomic, not optional.
"""
import unittest
import studio_server as studio

class AccountDeletionRequestHTTP(unittest.TestCase):
 def setUp(self):
  from test_platform_identity_and_catalog import PlatformHTTP
  self.fx=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.user=self.fx.signup()
  self.cookie,_=self.fx.login()
 def test_inapp_delete_requires_explicit_confirmation_then_revokes_access(self):
  self.assertEqual(self.fx.api("/api/me",{},method="DELETE",cookie=self.cookie)[0],400)
  self.assertEqual(self.fx.api("/api/me",cookie=self.cookie)[0],200)
  result=self.fx.api("/api/me",{"confirm":"DELETE_MY_ACCOUNT"},method="DELETE",cookie=self.cookie)
  self.assertEqual(result[0],202,result[2])
  self.assertEqual(result[2]["state"],"ERASURE_PENDING")
  self.assertFalse(result[2].get("erasureComplete",True))
  self.assertEqual(self.fx.api("/api/me",cookie=self.cookie)[0],403)
  self.assertEqual(self.fx.api("/api/auth/login",{"handle":"artist_a","password":"strong secret phrase A!"})[0],403)
 def test_external_web_deletion_works_without_app_capability_but_requires_credentials_and_origin(self):
  body={"handle":"artist_a","password":"strong secret phrase A!","confirm":"DELETE_MY_ACCOUNT"}
  self.assertEqual(self.fx.api("/api/account/delete-request",{**body,"password":"wrong credentials here"},cap=False)[0],403)
  code,_,result=self.fx.api("/api/account/delete-request",body,cap=False)
  self.assertEqual(code,202,result)
  self.assertEqual(result["state"],"ERASURE_PENDING")
  self.assertEqual(self.fx.api("/api/me",cookie=self.cookie)[0],403)
 def test_request_unpublishes_existing_public_song_and_preserves_revision_evidence(self):
  ref=self.fx.project(self.user["principalId"])
  studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:
    "ARTIST_OWNED" if (pid,rid,aid,principal)==(ref["projectId"],ref["revisionId"],
      ref["artifactId"],self.user["principalId"]) else None)
  pub=self.fx.publish(ref,self.cookie)[2]["publicationId"]
  self.assertEqual(self.fx.req("/api/songs/"+pub+"/audio")[0],200)
  code,_,r=self.fx.api("/api/me",{"confirm":"DELETE_MY_ACCOUNT"},method="DELETE",cookie=self.cookie)
  self.assertEqual(code,202,r)
  self.assertEqual(self.fx.req("/api/songs/"+pub+"/audio")[0],404)
  # Original ProjectRevision has not silently disappeared during pending erasure.
  obs=studio.project_operation(self.fx.root,{"projectId":ref["projectId"]},principal_id=self.user["principalId"])
  self.assertEqual(obs["revision"]["revisionId"],ref["revisionId"])

if __name__=="__main__":unittest.main()

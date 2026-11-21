"""R9-A RED: host-only durable signing + rights, negative controls."""
import base64,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import studio_server as studio
from test_platform_identity_and_catalog import PlatformHTTP
from test_platform_round7_scratch_rights import RightsBoundScratchHTTP

class HostRightsConfigHTTP(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.account=self.fx.signup();self.cookie,_=self.fx.login()
  self.song=self.fx.project(self.account['principalId'])
  self.previous=(studio.M045_GRANT_SIGNING_RING,studio.M045_GRANT_RIGHTS_POLICY,
                 studio.PLATFORM_SCRATCH_RIGHTS_POLICY,studio.PLATFORM_PUBLICATION_RIGHTS)
  self.addCleanup(self.restore)
  studio.M045_GRANT_SIGNING_RING=None;studio.M045_GRANT_RIGHTS_POLICY=None
  studio.PLATFORM_SCRATCH_RIGHTS_POLICY=None;studio.PLATFORM_PUBLICATION_RIGHTS=None
  self.song_right={
    'principalId':self.account['principalId'],'projectId':self.song['projectId'],
    'revisionId':self.song['revisionId'],'artifactId':self.song['artifactId'],
    'eventId':None,'status':'ARTIST_ORIGINAL','evidenceSha256':'d'*64}
  self.key=base64.b64encode(b'A'*32).decode()
 def restore(self):
  (studio.M045_GRANT_SIGNING_RING,studio.M045_GRANT_RIGHTS_POLICY,
    studio.PLATFORM_SCRATCH_RIGHTS_POLICY,studio.PLATFORM_PUBLICATION_RIGHTS)=self.previous
 def install(self,records=None,revoked=(),active='new-signing-key'):
  from m045_host_authorities import configure_host_authorities_from_env
  e={'SARA_HOST_SIGNING_KEYS_JSON':json.dumps({'keys':[{'keyId':'new-signing-key','secretBase64':self.key,'revoked':'new-signing-key' in revoked}]}),
     'SARA_ACTIVE_KEY_ID':active,
     'SARA_SAMPLE_RIGHTS_REGISTRY_JSON':json.dumps(records if records is not None else [self.song_right])}
  with patch.dict(os.environ,e):
   return configure_host_authorities_from_env(self.fx.root)
 def grant(self):
  return self.fx.api('/api/m045/soundtrack-grant',{
   'projectId':self.song['projectId'],'revisionId':self.song['revisionId'],
   'artifactId':self.song['artifactId'],'cinemaProjectId':'cinema-1',
   'sectionId':'intro','fps':'24/1'},cookie=self.cookie)
 def test_unconfigured_503_then_configured_grant_and_publication_200(self):
  self.assertEqual(self.grant()[0],503)
  self.assertEqual(self.fx.publish(self.song,self.cookie)[0],503)
  result=self.install()
  self.assertEqual(result['configured'],True)
  self.assertEqual(self.grant()[0],200,self.grant())
  self.assertEqual(self.fx.publish(self.song,self.cookie)[0],201)
  self.assertNotIn(self.key,json.dumps(result))
 def test_unverified_host_assertion_cannot_grant_or_publish(self):
  self.install([{**self.song_right,'status':'UNVERIFIED_HELD'}])
  self.assertEqual(self.grant()[0],403)
  self.assertEqual(self.fx.publish(self.song,self.cookie)[0],403)
 def test_revoked_key_does_not_install_and_never_issue(self):
  with self.assertRaises((ValueError,PermissionError)):
   self.install(revoked=['new-signing-key'])
  self.assertEqual(self.grant()[0],503)
 def test_runtime_revoked_signer_refuses_new_signature_with_403(self):
  from m045_soundtrack_grant import HostSigningKeyRing
  self.install()
  ring=studio.M045_GRANT_SIGNING_RING
  studio.M045_GRANT_SIGNING_RING=HostSigningKeyRing(ring.active_key_id,ring.keys_by_id,
    frozenset({ring.active_key_id}))
  self.assertEqual(self.grant()[0],403)

 def test_rights_revocation_closes_existing_pub_reads_and_new_grants(self):
  from m045_host_authorities import HostRightsRegistry
  self.install()
  code,_,pub=self.fx.publish(self.song,self.cookie)
  self.assertEqual(code,201,pub)
  HostRightsRegistry(self.fx.root).revoke(self.song_right,'HOST_REVOKED')
  self.assertEqual(self.grant()[0],403)
  self.assertEqual(self.fx.req('/api/songs/'+pub['publicationId']+'/audio')[0],404)
  self.assertEqual(self.fx.publish(self.song,self.cookie)[0],403)
 def test_cross_owner_digest_and_unattested_event_must_not_grant(self):
  self.install()
  other=self.fx.signup('artist_b','another strong password!')
  cb,_=self.fx.login('artist_b','another strong password!')
  self.assertEqual(self.fx.api('/api/m045/soundtrack-grant',{
   'projectId':self.song['projectId'],'revisionId':self.song['revisionId'],
   'artifactId':self.song['artifactId'],'cinemaProjectId':'cinema-1',
   'sectionId':'intro','fps':'24/1'},cookie=cb)[0],403)
 def test_malformed_partial_environment_rejected_before_install(self):
  from m045_host_authorities import configure_host_authorities_from_env
  with patch.dict(os.environ,{'SARA_HOST_SIGNING_KEYS_JSON':'{}',
   'SARA_ACTIVE_KEY_ID':'missing','SARA_SAMPLE_RIGHTS_REGISTRY_JSON':'[]'}):
   with self.assertRaises((ValueError,PermissionError)):
    configure_host_authorities_from_env(self.fx.root)
  self.assertEqual(self.grant()[0],503)

class HostScratchRegistryHTTP(unittest.TestCase):
 def setUp(self):
  self.fx=RightsBoundScratchHTTP(methodName='test_missing_host_policy_and_spoofed_rights_fail_closed')
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.prior=(studio.M045_GRANT_SIGNING_RING,studio.M045_GRANT_RIGHTS_POLICY,studio.PLATFORM_PUBLICATION_RIGHTS)
  self.addCleanup(self.restore)
 def restore(self):
  (studio.M045_GRANT_SIGNING_RING,studio.M045_GRANT_RIGHTS_POLICY,studio.PLATFORM_PUBLICATION_RIGHTS)=self.prior
 def test_source_event_rights_host_bound_scratch_wav_and_revocation(self):
  from m045_host_authorities import configure_host_authorities_from_env,HostRightsRegistry
  record={'principalId':self.fx.owner['principalId'],
   'projectId':self.fx.ref['projectId'],'revisionId':self.fx.ref['revisionId'],
   'artifactId':self.fx.sample_id,'eventId':self.fx.eid,
   'status':'ARTIST_ORIGINAL','evidenceSha256':'e'*64}
  environ={'SARA_HOST_SIGNING_KEYS_JSON':json.dumps({'keys':[{'keyId':'k','secretBase64':base64.b64encode(b'K'*32).decode()}]}),
           'SARA_ACTIVE_KEY_ID':'k',
           'SARA_SAMPLE_RIGHTS_REGISTRY_JSON':json.dumps([record])}
  with patch.dict(os.environ,environ):
   configure_host_authorities_from_env(self.fx.fx.root)
  code,_,render=self.fx.render()
  self.assertEqual(code,200,render)
  self.assertEqual(render['sampleRightsStatus'],'ARTIST_ORIGINAL')
  # No duplicate success possible from same current revision, regardless of
  # what license material the browser claims.
  self.assertEqual(self.fx.render()[0],409)
  HostRightsRegistry(self.fx.fx.root).revoke(record,'HOST_REVOKED')
  self.assertEqual(HostRightsRegistry(self.fx.fx.root).scratch(
    self.fx.owner['principalId'],self.fx.ref['projectId'],
    self.fx.ref['revisionId'],self.fx.eid,self.fx.sample_id),None)

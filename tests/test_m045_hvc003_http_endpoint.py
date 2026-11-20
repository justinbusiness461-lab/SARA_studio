"""HVC003 real localhost HTTP gate: host configuration, principal, digest, rights and truth."""
import hashlib, io, json, socketserver, struct, tempfile, threading, unittest
import urllib.error, urllib.request, wave
from pathlib import Path
import studio_server as studio
from m045_soundtrack_grant import HostSigningKeyRing, verify_issued_grant_signature

SPEC={'song_id':'hvc003-http','timebase':{'initial_bpm':120,'ticks_per_quarter_note':960},
      'structure':{'sections':[{'id':'intro','start_tick':0,'end_tick':3840}]},
      'tracks':[{'track_id':'guitar','events':[]}]}
KEY=b'host_test_only_long_enough_secret_do_not_publish'
class Hvc003HttpEndpoint(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name)/'exports'
  self.orig=(studio.EXPORT_ROOT,studio.PORT,studio.M045_GRANT_SIGNING_RING,studio.M045_GRANT_RIGHTS_POLICY)
  self.addCleanup(self.restore)
  self.wav=self._wav()
  self.aid=hashlib.sha256(self.wav).hexdigest()
  studio._publish_cas_exact(self.root,self.aid,self.wav)
  self.a=self.project('a'*32,'owner-a')
  self.b=self.project('b'*32,'owner-b') # same CAS object, distinct authorization
  self.ring=HostSigningKeyRing('k1',{'k1':KEY},frozenset())
  studio.M045_GRANT_SIGNING_RING=None
  studio.M045_GRANT_RIGHTS_POLICY=None
  self.httpd=socketserver.TCPServer(('127.0.0.1',0),studio.StudioHandler)
  studio.EXPORT_ROOT=self.root;studio.PORT=self.httpd.server_address[1]
  self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True);self.thread.start()
  self.addCleanup(self.stop_server)
  self.owner_a=studio.issue_studio_session('owner-a')
  self.owner_b=studio.issue_studio_session('owner-b')

 def restore(self):
  studio.EXPORT_ROOT,studio.PORT,studio.M045_GRANT_SIGNING_RING,studio.M045_GRANT_RIGHTS_POLICY=self.orig

 def stop_server(self):
  self.httpd.shutdown();self.httpd.server_close();self.thread.join(timeout=5)

 def _wav(self):
  o=io.BytesIO()
  with wave.open(o,'wb') as f:
   f.setnchannels(2);f.setsampwidth(2);f.setframerate(44100)
   f.writeframes(struct.pack('<hh',1200,-1200)*44100*2)
  return o.getvalue()

 def project(self,pid,principal):
  first=studio.project_operation(self.root,{'projectId':pid,'expectedCurrentRevisionId':None,
     'songSpec':SPEC},commit=True,principal_id=principal)
  return studio.project_operation(self.root,{'projectId':pid,
     'expectedCurrentRevisionId':first['revision']['revisionId'],
     'songSpec':SPEC,'outputArtifactIds':[self.aid]},commit=True,principal_id=principal)

 def grant_payload(self,project=None):
  project=project or self.a
  return {'projectId':project['manifest']['projectId'],'revisionId':project['revision']['revisionId'],
    'artifactId':self.aid,'cinemaProjectId':'cinema-1','sectionId':'intro','fps':'24/1'}

 def authorize(self):
  own=self.grant_payload()
  def rights(pid,rid,aid,principal):
   if (pid,rid,aid,principal)==(own['projectId'],own['revisionId'],self.aid,'owner-a'):
    return 'ARTIST_OWNED'
   return None
  studio.configure_m045_soundtrack_grant(self.ring,rights)

 def call(self,body=None,session=None,capability=True):
  h={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{studio.PORT}'}
  if capability:h['X-Studio-Capability']=studio.CAPABILITY
  if session:h['X-Studio-Session']=session
  req=urllib.request.Request(f'http://127.0.0.1:{studio.PORT}/api/m045/soundtrack-grant',
     data=json.dumps(body if body is not None else self.grant_payload()).encode('utf-8'),headers=h)
  try:
   with urllib.request.urlopen(req,timeout=10) as response:return response.status,json.loads(response.read())
  except urllib.error.HTTPError as error:return error.code,json.loads(error.read())

 def test_host_not_configured_returns_503_blocked(self):
  code,body=self.call(session=self.owner_a)
  self.assertEqual(code,503)
  self.assertEqual(body.get('status'),'BLOCKED')
  self.assertEqual(studio.M045_GRANT_SIGNING_RING,None)

 def test_missing_or_foreign_session_is_403(self):
  self.authorize()
  self.assertEqual(self.call()[0],403)
  self.assertEqual(self.call(session='fake')[0],403)
  self.assertEqual(self.call(session=self.owner_a,capability=False)[0],403)
  self.assertEqual(self.call(session=self.owner_b)[0],403)

 def test_cas_same_digest_different_owner_does_not_grant(self):
  self.authorize()
  self.assertEqual(self.call(self.grant_payload(self.b),session=self.owner_a)[0],403)
  self.assertEqual(self.call(self.grant_payload(self.b),session=self.owner_b)[0],403)

 def test_host_configured_returns_200_and_signature_cannot_synthesize_cinema(self):
  self.authorize()
  code,grant=self.call(session=self.owner_a)
  self.assertEqual(code,200,grant)
  self.assertEqual(grant['schema_version'],'sara.soundtrack.grant.v1')
  self.assertEqual(grant['resolved_start_sample'],0)
  self.assertEqual(grant['resolved_end_sample_exclusive'],88200)
  self.assertTrue(verify_issued_grant_signature(grant,self.ring))
  self.assertEqual(grant['claim_ceiling'],'SIGNED_ISSUER_AUTHORIZED_NOT_CINEMA_MEASURED_OR_APPROVED')
  self.assertEqual(self.a['revision']['revisionId'],
    studio.project_operation(self.root,{'projectId':'a'*32},principal_id='owner-a')['manifest']['currentRevisionId'])
  revoked=HostSigningKeyRing('k1',{'k1':KEY},frozenset({'k1'}))
  self.assertFalse(verify_issued_grant_signature(grant,revoked))
  self.assertFalse(verify_issued_grant_signature({**grant,'cinema_project_id':'foreign'},self.ring))

 def test_client_sample_override_rejected_and_no_valid_grant(self):
  self.authorize()
  code,body=self.call({**self.grant_payload(),'resolved_start_sample':0},session=self.owner_a)
  self.assertEqual(code,403,body)
  self.assertEqual(body['status'],'DENY')

if __name__=='__main__':unittest.main()

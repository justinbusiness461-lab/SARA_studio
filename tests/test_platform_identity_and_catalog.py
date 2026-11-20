"""PLATFORM-01/02 RED-first: identity, session, profile, lawful release and discovery."""
import concurrent.futures, hashlib, io, json, socketserver, struct, tempfile, threading
import unittest, urllib.error, urllib.parse, urllib.request, wave
from pathlib import Path
import studio_server as studio

SPEC={"song_id":"platform-qa","title":"Platform Fixture",
"timebase":{"initial_bpm":120,"ticks_per_quarter_note":960},
"structure":{"sections":[{"id":"intro","start_tick":0,"end_tick":3840}]},
"tracks":[{"track_id":"lead","events":[]}]}
def fixture_wav():
 out=io.BytesIO()
 with wave.open(out,"wb") as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
  w.writeframes(struct.pack("<hh",1700,-1700)*44100)
 return out.getvalue()

class PlatformHTTP(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name)
  self.old=(studio.EXPORT_ROOT,studio.PORT,studio.PLATFORM_MODE,studio.PLATFORM_PUBLICATION_RIGHTS)
  self.addCleanup(self.restore)
  studio.EXPORT_ROOT=self.root;studio.PLATFORM_MODE=True;studio.PLATFORM_PUBLICATION_RIGHTS=None
  self.server=socketserver.ThreadingTCPServer(("127.0.0.1",0),studio.StudioHandler)
  studio.PORT=self.server.server_address[1]
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.addCleanup(self.shutdown)
 def restore(self):
  studio.EXPORT_ROOT,studio.PORT,studio.PLATFORM_MODE,studio.PLATFORM_PUBLICATION_RIGHTS=self.old
 def shutdown(self):
  self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
 def req(self,path,body=None,cookie=None,method=None,cap=True):
  headers={"Origin":f"http://127.0.0.1:{studio.PORT}"}
  if cap:headers["X-Studio-Capability"]=studio.CAPABILITY
  if body is not None:headers["Content-Type"]="application/json"
  if cookie:headers["Cookie"]=cookie
  req=urllib.request.Request(f"http://127.0.0.1:{studio.PORT}"+path,
     data=None if body is None else json.dumps(body).encode(),headers=headers,
     method=method or ("POST" if body is not None else "GET"))
  try:
   with urllib.request.urlopen(req,timeout=10) as r:return r.status,dict(r.headers),r.read()
  except urllib.error.HTTPError as e:return e.code,dict(e.headers),e.read()
 def api(self,*args,**kw):
  status,headers,body=self.req(*args,**kw)
  return status,headers,json.loads(body) if body and body[:1] in (b"{",b"[") else body
 def signup(self,handle="artist_a",password="strong secret phrase A!"):
  status,h,b=self.api("/api/auth/signup",{"handle":handle,"password":password,"displayName":handle})
  self.assertEqual(status,201,b)
  return b
 def login(self,handle="artist_a",password="strong secret phrase A!"):
  status,h,b=self.api("/api/auth/login",{"handle":handle,"password":password})
  self.assertEqual(status,200,b)
  cookie=h.get("Set-Cookie","").split(";",1)[0]
  self.assertTrue(cookie.startswith("sara_session="),h)
  self.assertNotIn("password",json.dumps(b).lower())
  return cookie,b
 def project(self,principal):
  old=studio.project_operation(self.root,{"expectedCurrentRevisionId":None,"songSpec":SPEC},commit=True,principal_id=principal)
  audio=fixture_wav();digest=hashlib.sha256(audio).hexdigest()
  studio._publish_cas_exact(self.root,digest,audio)
  new=studio.project_operation(self.root,{"projectId":old["manifest"]["projectId"],
      "expectedCurrentRevisionId":old["revision"]["revisionId"],"songSpec":SPEC,
      "outputArtifactIds":[digest]},commit=True,principal_id=principal)
  return {"projectId":new["manifest"]["projectId"],"revisionId":new["revision"]["revisionId"],
       "artifactId":digest,"sourceAudio":audio}
 def publish(self,project,cookie):
  return self.api("/api/publications",{k:v for k,v in project.items() if k in ("projectId","revisionId","artifactId")}
   | {"confirmPublic":True},cookie=cookie)
 def test_acc01_entry_does_not_bootstrap_local_user(self):
  code,h,page=self.req("/")
  self.assertEqual(code,200)
  self.assertNotIn(b"window.__STUDIO_SESSION__=",page)
  self.assertIn(b"window.__SARA_PLATFORM_MODE__=true",page)
  self.assertEqual(self.api("/api/me")[0],403)
  self.assertEqual(self.api("/api/me",cookie="sara_session=forged")[0],403)
 def test_acc02_signup_login_cross_session_and_revoke(self):
  owner=self.signup()
  cookie,_=self.login()
  code,h,me=self.api("/api/me",cookie=cookie)
  self.assertEqual((code,me["account"]["principalId"]),(200,owner["principalId"]))
  self.assertEqual(self.api("/api/me/sessions",cookie=cookie)[0],200)
  sessions=self.api("/api/me/sessions",cookie=cookie)[2]["sessions"]
  self.assertGreaterEqual(len(sessions),1)
  target=sessions[0]["sessionId"]
  self.assertEqual(self.api("/api/me/sessions/revoke",{"sessionId":target},cookie=cookie)[0],200)
  self.assertEqual(self.api("/api/me",cookie=cookie)[0],403)
  self.assertEqual(self.api("/api/auth/login",{"handle":"artist_a","password":"bad"})[0],403)
 def test_acc03_concurrent_handle_uniqueness_and_bio_sanitization(self):
  def signup(i):
   return self.api("/api/auth/signup",{"handle":"simultaneous","password":"strong passphrase 321!","displayName":"artist"})[0]
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   statuses=list(pool.map(signup,[1,2]))
  self.assertEqual(sorted(statuses),[201,409])
  self.signup("artist_a")
  cookie,_=self.login()
  c,h,b=self.api("/api/me/profile",{"displayName":"A","bio":"<script>evil()</script>hello","handle":"artist_a"},cookie=cookie,method="PUT")
  self.assertEqual(c,200,b)
  self.assertNotIn("<script>",b["profile"]["bio"])
  self.assertEqual(self.api("/api/me/profile",cookie=cookie)[2]["profile"]["displayName"],"A")
 def test_acc04_cross_owner_cas_and_public_deny(self):
  a=self.signup();ca,_=self.login()
  b=self.signup("artist_b","another strong password!");
  cb,_=self.login("artist_b","another strong password!")
  proj=self.project(a["principalId"])
  foreign={k:proj[k] for k in ("projectId","revisionId","artifactId")}
  # Owner API must still reject another principal even if CAS audio exists.
  body={"projectId":proj["projectId"],"revisionId":proj["revisionId"],"artifactId":proj["artifactId"]}
  code,_,_=self.api("/api/projects/audio",body,cookie=cb)
  self.assertEqual(code,403)
  studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:"ARTIST_OWNED")
  self.assertEqual(self.publish(foreign,cb)[0],403)
 def test_acc05_legacy_mutations_are_not_user_bound_and_must_be_blocked(self):
  self.signup()
  cookie,_=self.login()
  for route in ["/api/write_production_file","/api/dispatch_neural_compilation",
                "/api/local_neural_vocal_synthesis","/api/m045/attempts",
                "/api/m045/attempts/take-audio","/api/m045/attempts/select-take",
                "/api/m045/attempts/reconcile"]:
   for cookie_used in (None,cookie):
    status,_,_=self.api(route,{},cookie=cookie_used)
    self.assertEqual(status,403,(route,cookie_used is not None,status))
  # Newly admitted scratch render has independent host rights and canonical
  # revision membership; no session still 403 and missing host policy 503.
  self.assertEqual(self.api("/api/m045/scratch/render",{},cookie=None)[0],403)
  self.assertEqual(self.api("/api/m045/scratch/render",{
    "projectId":"0"*32,"revisionId":"f"*64,"baseArtifactId":"f"*64,
    "sampleAssetDigests":{}},cookie=cookie)[0],503)
 def test_pub01_no_public_listing_without_approval(self):
  a=self.signup();ca,_=self.login();p=self.project(a["principalId"])
  self.assertEqual(self.api("/api/explore")[2]["songs"],[])
  self.assertEqual(self.api("/api/search?q=Platform")[2]["songs"],[])
  self.assertEqual(self.publish(p,ca)[0],503)  # Host rights proof absent.
 def test_pub02_unbound_cas_and_rights_always_fail_closed(self):
  a=self.signup();ca,_=self.login();p=self.project(a["principalId"])
  studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:
    "ARTIST_OWNED" if (pid,rid,aid,principal)==(p["projectId"],p["revisionId"],p["artifactId"],a["principalId"]) else None)
  orphan=hashlib.sha256(b"orphan").hexdigest()
  studio._publish_cas_exact(self.root,orphan,b"orphan")
  self.assertEqual(self.publish({**p,"artifactId":orphan},ca)[0],403)
  self.assertEqual(self.api("/api/publications",{**{k:p[k] for k in ("projectId","revisionId","artifactId")}, "confirmPublic":True,"rightsStatus":"LICENSE_CLEARED"},cookie=ca)[0],400)
 def test_pub03_explicit_publication_explore_search_stream_unpublish(self):
  a=self.signup();ca,_=self.login();p=self.project(a["principalId"])
  studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:
    "ARTIST_OWNED" if (pid,rid,aid,principal)==(p["projectId"],p["revisionId"],p["artifactId"],a["principalId"]) else None)
  code,_,pub=self.publish(p,ca)
  self.assertEqual(code,201,pub)
  self.assertTrue(pub["publicationId"])
  self.assertEqual(self.api("/api/explore")[2]["songs"][0]["publicationId"],pub["publicationId"])
  self.assertEqual(self.api("/api/search?q=Platform")[2]["songs"][0]["publicationId"],pub["publicationId"])
  self.assertEqual(self.api("/api/artists/artist_a")[2]["songs"][0]["publicationId"],pub["publicationId"])
  self.assertEqual(self.api("/api/songs/"+pub["publicationId"])[0],200)
  audio=self.req("/api/songs/"+pub["publicationId"]+"/audio")
  self.assertEqual((audio[0],audio[2]),(200,p["sourceAudio"]))
  code,_,_=self.api("/api/publications/"+pub["publicationId"]+"/unpublish",{},cookie=ca)
  self.assertEqual(code,200)
  self.assertEqual(self.api("/api/explore")[2]["songs"],[])
  self.assertEqual(self.req("/api/songs/"+pub["publicationId"]+"/audio")[0],404)
 def test_pub04_historical_takes_cannot_become_public(self):
  a=self.signup();ca,_=self.login();p=self.project(a["principalId"])
  pnew=studio.project_operation(self.root,{"projectId":p["projectId"],
   "expectedCurrentRevisionId":p["revisionId"],"songSpec":SPEC},commit=True,principal_id=a["principalId"])
  studio.configure_platform_publication_rights(lambda *_:"ARTIST_OWNED")
  self.assertEqual(self.publish(p,ca)[0],403)
 def test_profile_and_session_survive_fresh_store(self):
  a=self.signup();ca,_=self.login()
  from platform_identity import PlatformStore
  reopened=PlatformStore(self.root)
  self.assertEqual(reopened.session_principal(ca.split("=",1)[1]),a["principalId"])
  self.assertEqual(reopened.public_profile("artist_a")["handle"],"artist_a")

if __name__=="__main__":unittest.main()

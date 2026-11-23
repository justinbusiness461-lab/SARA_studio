import hashlib,io,json,socketserver,struct,sys,wave
from pathlib import Path
sys.path.insert(0,'tools')
import studio_server as s
from platform_identity import PlatformStore
s.PLATFORM_MODE=True
s.EXPORT_ROOT=Path(sys.argv[1])
account=PlatformStore(s.EXPORT_ROOT).register('release_artist','test-only strong passphrase 2026','Release Artist')
spec={'song_id':'platform-release-fixture','title':'Public Release Fixture','timebase':{'initial_bpm':120,'ticks_per_quarter_note':960},'structure':{'sections':[{'id':'intro','start_tick':0,'end_tick':3840}]},'tracks':[{'track_id':'lead','events':[]}]}
r1=s.project_operation(s.EXPORT_ROOT,{'expectedCurrentRevisionId':None,'songSpec':spec},commit=True,principal_id=account['principalId'])
out=io.BytesIO()
with wave.open(out,'wb') as w:
 w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100);w.writeframes(struct.pack('<hh',1700,-1700)*44100)
wav=out.getvalue();aid=hashlib.sha256(wav).hexdigest()
s._publish_cas_exact(s.EXPORT_ROOT,aid,wav)
r2=s.project_operation(s.EXPORT_ROOT,{'projectId':r1['manifest']['projectId'],'expectedCurrentRevisionId':r1['revision']['revisionId'],'songSpec':spec,'outputArtifactIds':[aid]},commit=True,principal_id=account['principalId'])
source=(r2['manifest']['projectId'],r2['revision']['revisionId'],aid,account['principalId'])
s.configure_platform_publication_rights(lambda pid,rid,artifact,principal:'ARTIST_OWNED' if (pid,rid,artifact,principal)==source else None)
with socketserver.ThreadingTCPServer(('127.0.0.1',0),s.StudioHandler) as http:
 s.PORT=http.server_address[1]
 print(json.dumps({'port':s.PORT,'projectId':source[0],'revisionId':source[1],'artifactId':aid}),flush=True)
 http.serve_forever()

"""Local opt-in platform A/B diagnostic fixture. Synthetic only; no real user audio."""
import hashlib,io,json,math,socketserver,struct,sys,wave
from pathlib import Path
sys.path.insert(0,'tools')
import studio_server as studio
from platform_identity import PlatformStore
studio.PLATFORM_MODE=True
studio.EXPORT_ROOT=Path(sys.argv[1])
principal=PlatformStore(studio.EXPORT_ROOT).register(
 "ab_diagnostic","synthetic test passphrase 2026","AB Probe")["principalId"]
spec={"song_id":"ab-probe","title":"Synthetic A/B Owner Probe",
 "timebase":{"initial_bpm":120,"ticks_per_quarter_note":960},
 "structure":{"sections":[{"id":"intro","start_tick":0,"end_tick":3840}]},
 "tracks":[{"track_id":"lead","events":[]}]}
r0=studio.project_operation(studio.EXPORT_ROOT,{"expectedCurrentRevisionId":None,"songSpec":spec},
 commit=True,principal_id=principal)
prior=r0
playable=[]
for pitch in (220,330):
 buf=io.BytesIO()
 with wave.open(buf,'wb') as out:
  out.setnchannels(2);out.setsampwidth(2);out.setframerate(44100)
  data=bytearray()
  for i in range(44100*2):
   v=int(5000*math.sin(2*math.pi*pitch*i/44100))
   data+=struct.pack('<hh',v,v)
  out.writeframes(bytes(data))
 wav=buf.getvalue();digest=hashlib.sha256(wav).hexdigest()
 studio._publish_cas_exact(studio.EXPORT_ROOT,digest,wav)
 next_rev=studio.project_operation(studio.EXPORT_ROOT,{"projectId":prior["manifest"]["projectId"],
   "expectedCurrentRevisionId":prior["revision"]["revisionId"],
   "songSpec":spec,"outputArtifactIds":[digest]},commit=True,principal_id=principal)
 playable.append({"revisionId":next_rev["revision"]["revisionId"],"digest":digest})
 prior=next_rev
with socketserver.ThreadingTCPServer(('127.0.0.1',0),studio.StudioHandler) as http:
 studio.PORT=http.server_address[1]
 print(json.dumps({"port":studio.PORT,"projectId":prior["manifest"]["projectId"],
   "current":playable[-1],"historical":playable[0]}),flush=True)
 http.serve_forever()

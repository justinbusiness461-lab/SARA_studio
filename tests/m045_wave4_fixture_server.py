"""Independent localhost fixture for real Wave004 UI→authorized HTTP→revision readback."""
from pathlib import Path
import hashlib,io,json,math,socketserver,struct,sys,wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import studio_server as s
s.EXPORT_ROOT=Path(sys.argv[1])
spec={"song_id":"wave4-ui","title":"Wave4 UI fixture",
 "timebase":{"ticks_per_quarter_note":960,"initial_bpm":96,"key":"E minor","meter":"4/4","sample_rate":44100},
 "structure":{"sections":[{"id":"verse1","name":"Verse 1","start_tick":0,"end_tick":3840}]},
 "tracks":[{"track_id":"bass","name":"Bass","type":"INSTRUMENT",
            "events":[{"type":"NOTE_ON","tick":0,"note_number":36,"velocity":110,"duration_ticks":480}]}]}
r1=s.project_operation(s.EXPORT_ROOT,{"expectedCurrentRevisionId":None,
 "songSpec":spec,"sourceAssetDigests":[],"outputArtifactIds":[]},commit=True)
pid=r1["manifest"]["projectId"]
buf=io.BytesIO();rate=44100
with wave.open(buf,"wb") as w:
 w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate)
 pcm=bytearray()
 for i in range(round(rate*.9)):
  val=int(32767*.13*math.sin(2*math.pi*997*i/rate))
  pcm.extend(struct.pack("<hh",val,val))
 w.writeframes(pcm)
data=buf.getvalue();digest=hashlib.sha256(data).hexdigest()
s._publish_cas_exact(s.EXPORT_ROOT,digest,data)
r2=s.project_operation(s.EXPORT_ROOT,{"projectId":pid,
 "expectedCurrentRevisionId":r1["revision"]["revisionId"],"songSpec":spec,
 "sourceAssetDigests":[],"outputArtifactIds":[digest]},commit=True)
with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as server:
 s.PORT=server.server_address[1]
 print(json.dumps({"port":s.PORT,"projectId":pid,"revisionId":r2["revision"]["revisionId"],"artifactId":digest}),flush=True)
 server.serve_forever()

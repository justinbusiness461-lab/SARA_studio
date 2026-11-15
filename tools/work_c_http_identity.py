"""Work C real HTTP identity probe; retained media, no render/listening claim."""
import hashlib,io,json,re,subprocess,sys,tempfile,urllib.request,urllib.error,wave
from pathlib import Path
ROOT=Path.cwd(); OUT=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/work-c-http'); OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def pcm(b):
 with wave.open(io.BytesIO(b)) as w:
  result=(w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes(),w.readframes(w.getnframes()))
 independent=subprocess.run(['ffmpeg','-v','error','-i','pipe:0','-f','s16le','-acodec','pcm_s16le','pipe:1'],input=b,capture_output=True,check=True).stdout
 assert independent==result[-1]
 return result
class Client:
 def __init__(self,base,ua):
  self.base=base;self.ua=ua
  page=urllib.request.urlopen(base).read().decode()
  self.cap=json.loads(re.search(r'window\.__STUDIO_CAPABILITY__=("[^"]+")',page)[1])
  self.session=json.loads(re.search(r'window\.__STUDIO_SESSION__=("[^"]+")',page)[1])
 def post(self,path,payload,session=True):
  headers={'Origin':self.base,'Content-Type':'application/json','X-Studio-Capability':self.cap,'User-Agent':self.ua}
  if session:headers['X-Studio-Session']=self.session
  req=urllib.request.Request(self.base+'/api/projects/'+path,data=json.dumps(payload).encode(),headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=30) as r:return r.status,r.headers.get('Content-Type'),r.read()
  except urllib.error.HTTPError as e:return e.code,e.headers.get('Content-Type'),e.read()
 def operation(self,path,payload):
  status,_,body=self.post(path,payload);assert status==200,(status,body[:200]);return json.loads(body)
def boot(state):
 code='''import sys,socketserver
from pathlib import Path
sys.path.insert(0,"tools")
import studio_server as s
s.EXPORT_ROOT=Path(sys.argv[1])
with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as httpd:
 s.PORT=httpd.server_address[1]; print(s.PORT,flush=True);httpd.serve_forever()
'''
 p=subprocess.Popen([sys.executable,'-u','-c',code,str(state)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
 line=p.stdout.readline();assert line.strip().isdigit(),line
 return p,'http://127.0.0.1:'+line.strip()
fixtures=[json.loads((ROOT/f'evidence/m044/integration/{n}.json').read_text()) for n in ['R1','R2']]
bytes_=[(ROOT/f'evidence/m044/integration/{n}.wav').read_bytes() for n in ['R1','R2']]
for f,b in zip(fixtures,bytes_):assert sha(b) in f['revision']['outputArtifactIds']
media=[pcm(b) for b in bytes_]
uas={'desktop':'Mozilla/5.0 (X11; Linux x86_64) WorkC-HTTP','phone':'Mozilla/5.0 (Linux; Android 15) Mobile WorkC-HTTP'}
rows=[];checks=[];proc=None
with tempfile.TemporaryDirectory(prefix='work-c-http-state-') as state:
 try:
  proc,base=boot(state);client=Client(base,uas['desktop']);published=[]
  for i in range(2):
   req={'expectedCurrentRevisionId':None if i==0 else published[0]['revision']['revisionId'],'songSpec':fixtures[i]['songSpec'],'sourceAssetDigests':[],'outputArtifactIds':[]}
   if i:req['projectId']=published[0]['manifest']['projectId']
   draft=client.operation('commit',req)
   pub=client.operation('render',{'projectId':draft['manifest']['projectId'],'sourceRevisionId':draft['revision']['revisionId'],'operationId':'retained-http-'+str(i),'filename':f'R{i+1}.wav','subdirectory':'work-c','data_bytes':list(bytes_[i])})
   published.append(pub)
  pid=published[1]['manifest']['projectId'];r2id=published[1]['revision']['revisionId']
  for phase in ['before-restart','cold-reopen']:
   if phase=='cold-reopen':
    proc.kill();proc.wait();proc,base=boot(state)
   for label,ua in uas.items():
    c=Client(base,ua)
    current=c.operation('open',{'projectId':pid});assert current['manifest']['currentRevisionId']==r2id
    for i,p in enumerate(published):
     rid=p['revision']['revisionId'];digest=sha(bytes_[i]);payload={'projectId':pid,'revisionId':rid,'artifactId':digest}
     snapshot=c.operation('open',{'projectId':pid,'revisionId':rid});assert snapshot['revision']['outputArtifactIds'].count(digest)==1
     status,ctype,body=c.post('audio',payload);assert status==200 and ctype=='audio/wav'
     assert body==bytes_[i] and sha(body)==digest
     assert pcm(body)==media[i]
     objects=list(Path(state).glob('objects/'+digest[:2]+'/'+digest));assert len(objects)==1 and objects[0].read_bytes()==body
     rows.append({'phase':phase,'client':label,'projectId':pid,'revisionId':rid,'artifactSHA256':digest,'networkPCM_SHA256':sha(media[i][-1]),'httpStatus':status,'contentType':ctype,'bytes':len(body),'bindingCount':1,'R2Current':True})
    bad={'projectId':pid,'revisionId':published[0]['revision']['revisionId'],'artifactId':sha(bytes_[1])}
    status,_,body=c.post('audio',bad);assert status==403 and body[:4]!=b'RIFF';checks.append({'phase':phase,'client':label,'wrongRevisionStatus':status})
    status,_,body=c.post('audio',payload,session=False);assert status==403 and body[:4]!=b'RIFF';checks.append({'phase':phase,'client':label,'anonymousStatus':status})
 finally:
  if proc is not None:proc.kill();proc.wait()
receipt={'sourceSHA':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'method':'real localhost HTTP POST through unmodified StudioHandler; retained WAV upload through existing producer; fresh process restart; new sessions; no rerender','rows':rows,'negativeChecks':checks,'networkArtifactIdentity':'PASS_BOUNDED_RETAINED_MEDIA','networkDecodedPCMIdentity':'PASS_BOUNDED_RETAINED_MEDIA','normalColdReopen':'PASS','browserPlayback':'UNVERIFIED_AF_UNIX_BLOCKED','musicalPositionAlignment':'UNVERIFIED','sixViewportParity':'UNVERIFIED_NO_RS001_CANDIDATE','userAgentCeiling':'Desktop/phone User-Agent headers are not browser/device/viewport parity; both sessions resolve existing local-studio-user, not two principals','listening':'NOT_PERFORMED'}
(OUT/'http-identity-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'HTTP_media_responses':len(rows),'negativeChecks':len(checks),'verdict':receipt['networkArtifactIdentity']}))

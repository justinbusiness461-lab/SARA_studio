import sys,json,hashlib,tempfile,subprocess,wave,io
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path.cwd()/'tools'))
import studio_server as s
out=Path('evidence/m044/work-c-main-physical'); out.mkdir(parents=True,exist_ok=True)
node = "const {generate}=require('./tools/m044-session.cjs');const {transposeSection}=require('./tools/scorecore.cjs');const a=generate('96 BPM E minor dark Southern hip-hop instrumental',44044);const section=a.structure.sections[3];const b=transposeSection(a,{sectionId:section.id,trackId:'bass',semitones:-12});console.log(JSON.stringify({a,b,section}));"
specs=json.loads(subprocess.check_output(['node','-e',node]))
import copy
expected=copy.deepcopy(specs['a']); note_count=0
for track in expected['tracks']:
 if track['track_id']=='bass':
  for event in track['events']:
   if event['type']=='NOTE_ON' and specs['section']['start_tick'] <= event['tick'] < specs['section']['end_tick']:
    event['note_number']-=12;note_count+=1
assert note_count>0 and expected==specs['b']
root=Path(tempfile.mkdtemp(prefix='work-c-media-'))
h=lambda x:hashlib.sha256(x).hexdigest()
r=[]; media=[]; arrays=[]
for i,key in enumerate(['a','b']):
 req={'songSpec':specs[key],'sourceAssetDigests':[],'outputArtifactIds':[], 'expectedCurrentRevisionId':None if i==0 else r[0]['revision']['revisionId']}
 if i: req.update(projectId=r[0]['manifest']['projectId'],operationId='work-c-verse2-bass-minus12')
 draft=s.project_operation(root,req,commit=True)
 rendered=s.render_publish_operation(root,{'projectId':draft['manifest']['projectId'],'sourceRevisionId':draft['revision']['revisionId'],'operationId':'render:'+draft['revision']['revisionId'],'filename':f'R{i+1}.wav','subdirectory':'work-c'})
 r.append(rendered); artifact=rendered['revision']['outputArtifactIds'][0]
 wav=s.project_audio_bytes(root,{'projectId':rendered['manifest']['projectId'],'revisionId':rendered['revision']['revisionId'],'artifactId':artifact})
 assert h(wav)==artifact and wav==s.artifact_bytes(root,artifact)
 (out/f'R{i+1}.wav').write_bytes(wav)
 with wave.open(io.BytesIO(wav)) as w: rate=w.getframerate(); channels=w.getnchannels(); frames=w.getnframes(); pcm=w.readframes(frames)
 decoded=subprocess.run(['ffmpeg','-v','error','-i','pipe:0','-f','s16le','-acodec','pcm_s16le','pipe:1'],input=wav,capture_output=True,check=True).stdout
 assert decoded==pcm
 a=np.frombuffer(decoded,dtype='<i2').reshape(-1,channels); arrays.append(a)
 media.append({'revisionId':rendered['revision']['revisionId'],'artifactSHA256':artifact,'PCM_SHA256':h(decoded),'ffmpegPCMMatch':True,'sampleRate':rate,'channels':channels,'frames':frames,'durationSeconds':frames/rate,'samplePeak':float(np.max(np.abs(a.astype(float)))/32768),'dcPerChannel':(a.mean(axis=0)/32768).tolist(),'clippedSamples':int(np.sum((a==-32768)|(a==32767))),'stereoChannelsIdentical':bool(np.array_equal(a[:,0],a[:,1])),'silentFrames':int(np.sum(np.all(a==0,axis=1)))})
 print('rendered',i+1,flush=True)
start=round(specs['section']['start_tick']/960*60/96*rate);stop=round(specs['section']['end_tick']/960*60/96*rate);tail=round(.1*rate)
changed=np.any(arrays[0]!=arrays[1],axis=1); outside=changed.copy();outside[start:stop+tail]=False
pid=r[1]['manifest']['projectId']
code='import sys,json;sys.path.insert(0,"tools");import studio_server as s;print(json.dumps(s.project_operation(sys.argv[1],{"projectId":sys.argv[2]})))'
cold=json.loads(subprocess.check_output([sys.executable,'-c',code,str(root),pid]))
assert cold['revision']['revisionId']==r[1]['revision']['revisionId']
for item in media:
 assert h(s.project_audio_bytes(root,{'projectId':pid,'revisionId':item['revisionId'],'artifactId':item['artifactSHA256']}))==item['artifactSHA256']
receipt={'sourceSHA':'749127ce0ce2cd08cdc5a6354626a078064f4704','media':media,'targetNotesTransposedExactlyMinus12':note_count,'nonTargetSongSpecConserved':True,'editIntervalFrames':[start,stop],'declaredTailFrames':tail,'changedFrames':int(changed.sum()),'outsideEditAndTailChangedFrames':int(outside.sum()),'firstChangedFrame':int(np.flatnonzero(changed)[0]),'lastChangedFrame':int(np.flatnonzero(changed)[-1]),'coldReopenR2Current':True,'lawfulAccessorBytesEqualAuthoritativeArtifacts':True,'HTTPBytes':'UNVERIFIED_EXECUTOR_SOCKET_RESTRICTION','browserAB':'UNVERIFIED_EXECUTOR_SOCKET_RESTRICTION','truePeak':'NOT_MEASURED','LUFS_I':'NOT_MEASURED','listening':'NOT_PERFORMED'}
(out/'physical-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n'); print(json.dumps(receipt,indent=2))

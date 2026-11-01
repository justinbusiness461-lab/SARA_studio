"""Independent sample-coordinate measurement; signal-placement reference only."""
import hashlib,json,pathlib,statistics,sys,wave

def measure(words,truth,rate,frames,digest):
 assert type(rate) is int and rate>0
 assert len(words)==len(truth) and len({w['id'] for w in words})==len(words)
 rows=[];last=0
 for w,t in zip(words,truth):
  a,b=w['decodedSampleStart'],w['decodedSampleEnd']
  assert type(a) is int and type(b) is int and 0<=a<b<=frames and a>=last
  last=b;x=a-t['decodedSampleStart'];y=b-t['decodedSampleEnd']
  rows.append(dict(observationId=w['id'],text=w['text'],sourceAudioDigest=digest,decodedSampleStart=a,decodedSampleEnd=b,startSecondsDerived=a/rate,endSecondsDerived=b/rate,startErrorSamples=x,endErrorSamples=y,startErrorMs=x*1000/rate,endErrorMs=y*1000/rate))
 return dict(words=rows,medianAbsoluteStartErrorMs=statistics.median(abs(r['startErrorMs']) for r in rows),medianAbsoluteEndErrorMs=statistics.median(abs(r['endErrorMs']) for r in rows),maxAbsoluteBoundaryErrorMs=max(abs(r[k]) for r in rows for k in ('startErrorMs','endErrorMs')))

if __name__=='__main__':
 neutral=[dict(id='n',text='neutral',decodedSampleStart=10,decodedSampleEnd=20)]
 assert measure(neutral,neutral,1000,30,'neutral')['maxAbsoluteBoundaryErrorMs']==0
 for a,b in [(0,0),(-1,2),(20,31),(1.5,3)]:
  try:measure([dict(neutral[0],decodedSampleStart=a,decodedSampleEnd=b)],neutral,1000,30,'neutral')
  except AssertionError:pass
  else:raise AssertionError('invalid range accepted')
 root=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2])
 p=json.loads((root/'evidence/m043/lyric-discriminator.json').read_text());m=p['fixture'];r1=p['R1']['lyricTimeline'];r2=p['R2']['lyricTimeline']
 with wave.open(str(root/'evidence/m043/fixtures/rise-higher.wav')) as w:
  pcm=w.readframes(w.getnframes());assert w.getframerate()==m['sourceSampleRate'] and w.getnframes()==m['decodedFrameCount']
 assert hashlib.sha256(pcm).hexdigest()==m['sourceAudioDigest']==r1['sourceAudioDigest']==r2['sourceAudioDigest']
 assert r2['parentRevisionId']==r1['revisionId']
 assert [(w['id'],w['decodedSampleStart'],w['decodedSampleEnd']) for w in r1['words']]==[(w['id'],w['decodedSampleStart'],w['decodedSampleEnd']) for w in r2['words']]
 for r in (r1,r2):
  for phrase in r['phrases']:
   assert all(phrase['decodedSampleStart']<=w['decodedSampleStart']<w['decodedSampleEnd']<=phrase['decodedSampleEnd'] for w in r['words'])
 result=measure(r2['words'],m['knownWords'],m['sourceSampleRate'],m['decodedFrameCount'],m['sourceAudioDigest'])
 result.update(freeze='076aed8d438a938119a7c2d5b34bb5eeb3ba4409',neutralHarnessChecks=5,recoveryChecks=p['checks'],R1=r1['revisionId'],R2=r2['revisionId'],ceiling='synthetic isolated speech, supplied text; signal placement, not phoneme annotation; no ASR claim',timingToleranceMs=10)
 assert result['maxAbsoluteBoundaryErrorMs']<=10 and all(c['pass'] for c in p['checks'])
 out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

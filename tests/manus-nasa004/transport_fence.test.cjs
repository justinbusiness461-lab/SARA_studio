'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {TransportFence}=require('./transport_fence.cjs');
const R1='1'.repeat(64), R2='2'.repeat(64), A='a'.repeat(64), B='b'.repeat(64);
const ok=(f,r)=>f.complete(r,{decoded:true,bindingVerified:true,digest:r.artifactId});

test('current R2 arrives; late R1 cannot publish',()=>{
  const f=new TransportFence(); f.acceptServerAuthority({currentRevisionId:R1,currentArtifactId:A});
  const r1=f.beginCurrent().request;
  f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:B});
  const r2=f.beginCurrent().request;
  assert.equal(ok(f,r2).published,true);
  assert.equal(ok(f,r1).published,false);
  assert.deepEqual(f.snapshot().playback,{revisionId:R2,artifactId:B,kind:'current'});
});

test('explicit historical selection remains history, does not make R1 current',()=>{
  const f=new TransportFence();f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:B});
  const r=f.beginHistorical(R1,A).request;assert.equal(ok(f,r).published,true);
  assert.equal(f.snapshot().authority.currentRevisionId,R2);
  assert.equal(f.snapshot().playback.kind,'historical');
});

test('invalid or unverifiable audio cannot be played',()=>{
 const f=new TransportFence();f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:B});
 let r=f.beginCurrent().request;
 assert.equal(f.complete(r,{decoded:true,bindingVerified:true,digest:A}).published,false);
 assert.equal(f.snapshot().playback,null);
 assert.equal(f.snapshot().selected.state,'UNAVAILABLE');
});

test('unverified revision binding rejects even a decodable digest-correct WAV',()=>{
 const f=new TransportFence();f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:B});
 const r=f.beginCurrent().request;
 assert.equal(f.complete(r,{decoded:true,bindingVerified:false,digest:B}).reason,'AUDIO_UNAVAILABLE');
});

test('missing current audio never silently falls back to R1',()=>{
 const f=new TransportFence();f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:null});
 assert.equal(f.beginCurrent().status,'UNAVAILABLE');assert.equal(f.snapshot().playback,null);
});

test('abort disables late completion, without changing canonical revision',()=>{
 const f=new TransportFence();f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:B});
 const r=f.beginCurrent().request;f.abort();
 assert.equal(ok(f,r).published,false);assert.equal(f.snapshot().authority.currentRevisionId,R2);
});

test('rapid 60-request switching admits only the last',()=>{
 const f=new TransportFence();f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:B});
 const requests=[];
 for(let i=0;i<60;i++) requests.push(i%2 ? f.beginCurrent().request : f.beginHistorical(R1,A).request);
 for(let i=0;i<59;i++) assert.equal(ok(f,requests[i]).published,false);
 assert.equal(ok(f,requests[59]).published,true);
 assert.equal(f.snapshot().playback.revisionId,R2);
});

test('current server revision changes between request and publish',()=>{
 const f=new TransportFence();f.acceptServerAuthority({currentRevisionId:R1,currentArtifactId:A});
 const r=f.beginCurrent().request;
 f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:B});
 assert.equal(ok(f,r).published,false);assert.equal(f.snapshot().authority.currentRevisionId,R2);
});

test('request object forgery does not gain publication rights',()=>{
 const f=new TransportFence();f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:B});
 const r=f.beginCurrent().request;
 assert.equal(ok(f,{...r}).published,false);
 assert.equal(ok(f,r).published,true);
});

test('a stale historical result cannot replace explicitly selected current R2',()=>{
 const f=new TransportFence();f.acceptServerAuthority({currentRevisionId:R2,currentArtifactId:B});
 const old=f.beginHistorical(R1,A).request;
 const now=f.beginCurrent().request;
 assert.equal(ok(f,old).published,false);assert.equal(ok(f,now).published,true);
 assert.equal(f.snapshot().playback.kind,'current');
});

'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {createHash}=require('node:crypto');
const bridge=require('../native-bridge.js');
const old=()=>({Capacitor:globalThis.Capacitor});
const restore=x=>{globalThis.Capacitor=x.Capacitor};
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
test('NS-001 native bridge denies web fallback for secure credential',async()=>{
  const previous=old();try{
    delete globalThis.Capacitor;
    await assert.rejects(bridge.credentialGet('key'),/NATIVE_HOST_CAPABILITY_UNAVAILABLE/);
  }finally{restore(previous)}
});
test('NS-002 native credential key and value inputs are bounded',async()=>{
  await assert.rejects(bridge.credentialSet('../key','abc'),/INVALID_SECURE_CREDENTIAL/);
  await assert.rejects(bridge.credentialSet('key','x'.repeat(8193)),/INVALID_SECURE_CREDENTIAL/);
});
test('NS-003 native file import must verify SHA and remain unassigned',async()=>{
  const prev=old();try{
    const bytes=Buffer.from('R8 source');
    globalThis.Capacitor={isNativePlatform:()=>true,Plugins:{SaraFiles:{pick:async()=>({
      name:'my.wav',base64:bytes.toString('base64'),sha256:digest(bytes)})}}};
    const result=await bridge.importFile();
    assert.equal(result.sha256,digest(bytes));
    assert.equal(result.authority,'UNASSIGNED_LOCAL_IMPORT');
  }finally{restore(prev)}
});
test('NS-004 native file rejects invalid digest even if plugin returns a file',async()=>{
  const prev=old();try{
    globalThis.Capacitor={isNativePlatform:()=>true,Plugins:{SaraFiles:{pick:async()=>({
      name:'bad.wav',base64:Buffer.from('mismatch').toString('base64'),sha256:'f'.repeat(64)})}}};
    await assert.rejects(bridge.importFile(),/NATIVE_IMPORT_SHA256_MISMATCH/);
  }finally{restore(prev)}
});
test('NS-005 export rejects false sha before native save',async()=>{
  const prev=old();try{
    let called=0;
    globalThis.Capacitor={isNativePlatform:()=>true,Plugins:{SaraFiles:{save:()=>{called++;return {}}}}};
    await assert.rejects(bridge.exportFile('mix.wav',new Uint8Array([2,3]),'a'.repeat(64)),/NATIVE_EXPORT_SHA256_MISMATCH/);
    assert.equal(called,0);
  }finally{restore(prev)}
});
test('NS-006 audio-route guard requires actual native session plugin',async()=>{
  const prev=old();try{
    globalThis.Capacitor={isNativePlatform:()=>true,Plugins:{}};
    assert.throws(()=>bridge.listenAudioRouteGuard(()=>{}),/NATIVE_HOST_CAPABILITY_UNAVAILABLE/);
  }finally{restore(prev)}
});
test('NS-007 disconnected audio route and lost focus pause immediately',async()=>{
  const prev=old();try{
    let cb,pauses=[];
    globalThis.Capacitor={isNativePlatform:()=>true,Plugins:{
      SaraAudioSession:{addListener:(event,callback)=>{assert.equal(event,'stateChange');cb=callback;return {remove(){}}}}}};
    bridge.listenAudioRouteGuard(reason=>pauses.push(reason));
    cb({type:'headphonesDisconnected'});
    cb({type:'audioFocusLost'});
    cb({type:'routeRestored'});
    cb({type:'unknown'});
    assert.deepEqual(pauses,['headphonesDisconnected','audioFocusLost']);
  }finally{restore(prev)}
});
test('NS-008 native store receipts cannot directly assert credits or verification',()=>{
  assert.throws(()=>bridge.nativeReceiptForHost({
    store:'apple',transactionId:'abc',productId:'credits.10',receipt:'opaque',credits:100000
  }),/INVALID_NATIVE_STORE_EVIDENCE_FIELDS/);
  const evidence=bridge.nativeReceiptForHost({store:'apple',transactionId:'txn-001',
      productId:'credits.10',receipt:'signed-on-device-but-unverified'});
  assert.deepEqual(Object.keys(evidence).sort(),['productId','receipt','store','transactionId']);
  assert.equal(evidence.verified,undefined);
});
test('NS-009 release config denies remote URLs, requires both native binaries for ship',()=>{
  const config=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../capacitor.config.json'),'utf8'));
  assert.match(fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8'),/src="native-bridge\.js"/);
  assert.match(fs.readFileSync(require('node:path').join(__dirname,'../app-ui.js'),'utf8'),/listenAudioRouteGuard/);
  assert.equal(config.appId,'com.sj3.sarastudio');
  assert.equal(config.server?.androidScheme,'https');
  assert.equal(config.android?.allowMixedContent,false);
  assert.equal(config.server?.url,undefined);
  const policy=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../capacitor.release-policy.json'),'utf8'));
  assert.equal(policy.productionReleaseAuthorized,false);
  assert.equal(policy.ios.requiredPhysicalDeviceQa,true);
  assert.equal(policy.android.requiredPhysicalDeviceQa,true);
  assert.equal(policy.stores.billing.hostVerifiedOnly,true);
});

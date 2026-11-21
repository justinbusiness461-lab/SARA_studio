const test=require('node:test');
const assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const bridge=require('../native-bridge.js');

test('web environment rejects native secure storage and never falls back to localStorage',async()=>{
  const old=globalThis.Capacitor;
  try {
    delete globalThis.Capacitor;
    await assert.rejects(bridge.credentialGet('session'),/NATIVE_HOST_CAPABILITY_UNAVAILABLE/);
    await assert.rejects(bridge.credentialSet('session','token'),/NATIVE_HOST_CAPABILITY_UNAVAILABLE/);
    assert.equal(bridge.isNative(),false);
  } finally {globalThis.Capacitor=old;}
});
test('native file import verifies physical SHA256 and rejects forged checksum',async()=>{
  const old=globalThis.Capacitor;
  const oldCrypto=globalThis.crypto;
  const raw=Buffer.from('accepted local imported bytes');
  const digest=require('node:crypto').createHash('sha256').update(raw).digest('hex');
  const plugins={SaraFiles:{pick:async()=>({name:'sample.wav',base64:raw.toString('base64'),sha256:digest})}};
  try {
    globalThis.crypto=webcrypto;
    globalThis.Capacitor={isNativePlatform:()=>true,Plugins:plugins};
    const result=await bridge.importFile();
    assert.deepEqual(Buffer.from(result.bytes),raw);
    assert.equal(result.sha256,digest);
    assert.equal(result.authority,'UNASSIGNED_LOCAL_IMPORT');
    plugins.SaraFiles.pick=async()=>({name:'sample.wav',base64:raw.toString('base64'),sha256:'0'.repeat(64)});
    await assert.rejects(bridge.importFile(),/NATIVE_IMPORT_SHA256_MISMATCH/);
  } finally {globalThis.Capacitor=old;globalThis.crypto=oldCrypto;}
});
test('native plugin absence and mismatched export never claim local file publication',async()=>{
  const old=globalThis.Capacitor;
  const oldCrypto=globalThis.crypto;
  try {
    globalThis.crypto=webcrypto;
    globalThis.Capacitor={isNativePlatform:()=>true,Plugins:{}};
    await assert.rejects(bridge.credentialGet('session'),/NATIVE_HOST_CAPABILITY_UNAVAILABLE/);
    await assert.rejects(bridge.exportFile('x.wav',new Uint8Array([1]),'f'.repeat(64)),/NATIVE_EXPORT_SHA256_MISMATCH/);
    assert.throws(()=>bridge.listenAudioSession(()=>{}),/NATIVE_HOST_CAPABILITY_UNAVAILABLE/);
  } finally {globalThis.Capacitor=old;globalThis.crypto=oldCrypto;}
});

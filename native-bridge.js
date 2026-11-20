/* S.A.R.A. Studio native capability adapter. No music/revision authority lives here. */
(function(scope){
  'use strict';
  const MAX_BINARY_BYTES = 20 * 1024 * 1024;
  function nativePlugin(name) {
    const cap = scope.Capacitor;
    if (!cap || typeof cap.isNativePlatform !== 'function' ||
        !cap.isNativePlatform() || !cap.Plugins || !cap.Plugins[name]) {
      throw new Error('NATIVE_HOST_CAPABILITY_UNAVAILABLE:' + name);
    }
    return cap.Plugins[name];
  }
  function bytesFromBase64(encoded) {
    if (typeof encoded !== 'string' || encoded.length > Math.ceil(MAX_BINARY_BYTES*4/3)+8 ||
        encoded.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(encoded)) {
      throw new Error('INVALID_NATIVE_BINARY');
    }
    const decoded = scope.atob(encoded);
    if (decoded.length > MAX_BINARY_BYTES) throw new Error('NATIVE_FILE_TOO_LARGE');
    return Uint8Array.from(decoded, c => c.charCodeAt(0));
  }
  function b64(bytes) {
    const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    if (view.byteLength > MAX_BINARY_BYTES) throw new Error('NATIVE_FILE_TOO_LARGE');
    let text='';
    for(let i=0;i<view.byteLength;i+=8192) text+=String.fromCharCode(...view.subarray(i,i+8192));
    return scope.btoa(text);
  }
  async function digest(bytes) {
    if(!scope.crypto || !scope.crypto.subtle) throw new Error('NATIVE_CRYPTO_REQUIRED');
    const hash = await scope.crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(hash)].map(v=>v.toString(16).padStart(2,'0')).join('');
  }
  function exactDigest(value) {
    if(typeof value!=='string' || !/^[0-9a-f]{64}$/.test(value)) throw new Error('INVALID_SHA256');
    return value;
  }
  const api = Object.freeze({
    isNative: () => !!(scope.Capacitor && scope.Capacitor.isNativePlatform && scope.Capacitor.isNativePlatform()),
    async credentialGet(key) {
      if(typeof key!=='string' || !/^[A-Za-z0-9._:-]{1,120}$/.test(key)) throw new Error('INVALID_SECURE_KEY');
      return nativePlugin('SaraSecureStore').get({key});
    },
    async credentialSet(key,value) {
      if(typeof key!=='string' || !/^[A-Za-z0-9._:-]{1,120}$/.test(key) ||
        typeof value!=='string' || value.length>8192) throw new Error('INVALID_SECURE_CREDENTIAL');
      return nativePlugin('SaraSecureStore').set({key,value});
    },
    async credentialRemove(key) {
      if(typeof key!=='string' || !/^[A-Za-z0-9._:-]{1,120}$/.test(key)) throw new Error('INVALID_SECURE_KEY');
      return nativePlugin('SaraSecureStore').remove({key});
    },
    async importFile() {
      const raw = await nativePlugin('SaraFiles').pick();
      const bytes = bytesFromBase64(raw.base64);
      if(await digest(bytes)!==exactDigest(raw.sha256)) throw new Error('NATIVE_IMPORT_SHA256_MISMATCH');
      return Object.freeze({name:raw.name,bytes,sha256:raw.sha256,authority:'UNASSIGNED_LOCAL_IMPORT'});
    },
    async exportFile(name,bytes,expectedSha256) {
      if(typeof name!=='string' || !/^[^\\/\u0000-\u001f]{1,120}$/.test(name)) throw new Error('INVALID_EXPORT_NAME');
      const view=bytes instanceof Uint8Array?bytes:new Uint8Array(bytes);
      const calculated=await digest(view);
      if(calculated!==exactDigest(expectedSha256)) throw new Error('NATIVE_EXPORT_SHA256_MISMATCH');
      return nativePlugin('SaraFiles').save({name,base64:b64(view),sha256:calculated});
    },
    listenAudioSession(callback) {
      if(typeof callback!=='function') throw new Error('AUDIO_SESSION_LISTENER_REQUIRED');
      return nativePlugin('SaraAudioSession').addListener('stateChange', callback);
    }
  });
  scope.SaraNativeBridge=api;
  if(typeof module!=='undefined' && module.exports) module.exports=api;
})(typeof window!=='undefined'?window:globalThis);

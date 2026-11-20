'use strict';
// Replays the EXACT current restoreProjectFromStorage function in a deterministic
// dependency harness; no reimplementation of the algorithm under test.
const test = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const src = readFileSync(join(__dirname, '..', 'app-ui.js'), 'utf8');
const from = src.indexOf('async function restoreProjectFromStorage() {');
const to = src.indexOf('\n}\n', from);
assert.ok(from >= 0 && to > from);
const exact = src.slice(from, to + 2);
const deps = ['$', 'localStorage', 'projectRequest', 'loadProjectObject', 'showProjectAuthority',
  'render', 'resetProjectComparison', 'setStatus', 'verifyPlayableRevision',
  'revisionRef', 'setABControls', 'clearVerifiedPlayback', 'recoverM045Proof',
  'm045PublishProof', 'window', 'invalidateProjectOpen', 'publishABSwitchState'];
const prepare = new Function(...deps,
  'let m045RequestToken=0, projectOpenGenerationToken=0, activeProjectOpenToken=0;\n' +
  'let abRevisions={r1:null,r2:null}, abRequestGeneration=0, activeABSwitch=null, m045LocksDirty=false;\n' +
  'let durableProjectRef=null;\n' + exact + '\nreturn restoreProjectFromStorage;');
function deferred() { let resolve, reject; const promise=new Promise((a,b)=>{resolve=a; reject=b;}); return {promise,resolve,reject}; }
function opened(id) { return {manifest:{projectId:id,currentRevisionId:id+'-R1'},revision:{revisionId:id+'-R1',parentRevisionId:null,outputArtifactIds:[id+'-WAV']},songSpec:{title:id,prompt:'fixture'}}; }
function fixture(gateAudio=false) {
  const state={selected:'A',shown:null,transport:null,lastStatus:null,loads:[],proof:null,clears:0};
  const elements=new Map();
  const $=id=>id==='projectId'?{get value(){return state.selected;},set value(v){state.selected=v;}}:(elements.get(id)|| (elements.set(id,{value:'',textContent:'',disabled:false}),elements.get(id)));
  const opens={A:deferred(),B:deferred()};const decodes={A:deferred(),B:deferred()};
  const restore=prepare($,{getItem:()=>null},async(kind,payload)=>{assert.equal(kind,'open');state.loads.push(payload.projectId);return opens[payload.projectId].promise;},
    ()=>({ok:true}),result=>{state.shown=result.manifest.projectId;},()=>{},()=>{state.proof=null;},
    value=>{state.lastStatus=value;},
    async (result,guard)=>{const id=result.manifest.projectId;if(gateAudio)await decodes[id].promise;if(guard&&!guard())return null;state.transport=id;state.proof=id;return {revisionId:result.revision.revisionId};},
    result=>({projectId:result.manifest.projectId,revisionId:result.revision.revisionId,artifactId:result.revision.outputArtifactIds[0]}),
    ()=>{},()=>{state.transport=null;state.proof=null;state.clears++;},
    ()=>Promise.resolve(),()=>{}, {__M044_AB_PROOF__:null,__M044_PLAYBACK_PROOF__:null},()=>{},()=>{});
  return {state,opens,decodes,restore};
}
const drain=()=>new Promise(r=>setImmediate(r));
test('positive: sequential A then B retains latest B',async()=>{const f=fixture();const a=f.restore();f.opens.A.resolve(opened('A'));await a;f.state.selected='B';const b=f.restore();f.opens.B.resolve(opened('B'));await b;assert.equal(f.state.shown,'B');assert.equal(f.state.transport,'B');});
test('newer B wins when older A server open resolves after B',async()=>{const f=fixture();const a=f.restore();f.state.selected='B';const b=f.restore();f.opens.B.resolve(opened('B'));await b;f.opens.A.resolve(opened('A'));await a;assert.equal(f.state.shown,'B');assert.equal(f.state.transport,'B');});
test('newer B wins when older A WAV verification resolves after B',async()=>{const f=fixture(true);const a=f.restore();f.opens.A.resolve(opened('A'));await drain();f.state.selected='B';const b=f.restore();f.opens.B.resolve(opened('B'));await drain();f.decodes.B.resolve();await b;f.decodes.A.resolve();await a;assert.equal(f.state.shown,'B');assert.equal(f.state.transport,'B');assert.equal(f.state.proof,'B');});
test('newest open failure leaves no previous playback proof',async()=>{const f=fixture();const a=f.restore();f.opens.A.resolve(opened('A'));await a;assert.equal(f.state.transport,'A');f.state.selected='B';const b=f.restore();f.opens.B.reject(Error('injected failure'));await assert.rejects(b,/injected failure/);assert.equal(f.state.transport,null);assert.equal(f.state.proof,null);});
'use strict';
// Executes unchanged product functions in a VM with injected IO failures.
// This is source-function execution, not a browser or HTTP qualification.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const root = path.resolve(process.argv[2] || '.');
const source = fs.readFileSync(path.join(root, 'app-ui.js'), 'utf8');
function span(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a);
  assert.ok(a >= 0 && b > a, 'product source boundary changed');
  return source.slice(a, b);
}
(async () => {
  const results = [];
  for (const failure of ['project-open', 'audio-fetch']) {
    const elements = {btnPlay:{disabled:false}, abStatus:{textContent:'Selected R1 · historical'}};
    const context = {
      window:{__M044_AB_PROOF__:{toRevisionId:'r1',toArtifactId:'a1'}},
      URL:{revokeObjectURL(){}}, $: id => elements[id],
      setStatus(message){ elements.status = message; },
      studioProjectHeaders(){ return {}; },
      async projectRequest(){
        if (failure === 'project-open') throw new Error('injected project open failure');
        return {manifest:{projectId:'p'},revision:{revisionId:'r2',outputArtifactIds:['a2']}};
      },
      async fetch(){return {ok:false,status:503,async json(){return {error:'injected audio failure'}}};}
    };
    vm.createContext(context);
    vm.runInContext(`let verifiedPlayback={projectId:'p',revisionId:'r1',artifactId:'a1',media:{currentTime:2,paused:true,pause(){}}};
let verifiedPlaybackSource=null, playing=false;
let abRevisions={r1:{projectId:'p',revisionId:'r1',artifactId:'a1'},r2:{projectId:'p',revisionId:'r2',artifactId:'a2'}};
let abRequestGeneration=0;
` + span('function clearVerifiedPlayback()', 'async function sha256Hex')
 + span('async function projectAudioBytes(', 'async function renderAndVerifyRevision(')
 + span('function publishABSwitchState(', 'async function applyVerse2BassOctave(')
 + span('async function selectABRevision(', 'let durableProjectRef =')
 + `\nasync function click(){return selectABRevision('R2').catch(e=>setStatus('A/B failed: '+e.message,'warn'));}`,context);
    await context.click();
    const observed = {
      failure, switchState:context.window.__M044_AB_SWITCH__.state,
      target:context.window.__M044_AB_SWITCH__.targetRevisionId,
      playbackProof:context.window.__M044_PLAYBACK_PROOF__,
      abProof:context.window.__M044_AB_PROOF__,
      playDisabled:elements.btnPlay.disabled,
      status:elements.status, label:elements.abStatus.textContent
    };
    assert.equal(observed.switchState,'TARGET_LOADING');
    assert.equal(observed.playbackProof,null);
    assert.equal(observed.abProof.toRevisionId,'r1');
    assert.equal(observed.playDisabled,true);
    results.push(observed);
  }
  console.log(JSON.stringify({sourceSha256:crypto.createHash('sha256').update(source).digest('hex'),
    evidence:'SOURCE_FUNCTION_VM_ONLY',defectReproduced:results.length,expectedRepair:'FAILED state and invalidated prior A/B success proof for active generation',results},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});

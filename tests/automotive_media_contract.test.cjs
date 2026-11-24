'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createCarMediaBridge, carDisplayPolicy } = require('../tools/automotive_media_contract.cjs');

const granted = () => [
  { mediaId: 'opaque-current-1', title: 'Test song', artist: 'DJ RezrXtion', durationMs: 10500, isPlayable: true },
  { mediaId: 'opaque-history-2', title: 'Earlier revision', artist: 'DJ RezrXtion', durationMs: 10500, isPlayable: true }
];

test('native car surface is never an authority owner', async () => {
  const bridge = createCarMediaBridge({
    listAuthorized: async () => granted(),
    resolveForPlayback: async mediaId => ({ mediaId, playableUrl: 'https://studio.example/short-lived-bound-stream', expiresAtMs: Date.now() + 30000, sourceRevisionId: 'R2', artifactId: 'A2' })
  });
  const rows = await bridge.browse();
  assert.equal(rows.length, 2);
  for (const row of rows) {
    assert.deepEqual(Object.keys(row).sort(), ['artist','durationMs','mediaId','title']);
    assert.equal('playableUrl' in row, false);
    assert.equal('projectId' in row, false);
    assert.equal('currentRevisionId' in row, false);
  }
});

test('playback rereads authoritative binding for each request including history', async () => {
  const calls = [];
  const bridge = createCarMediaBridge({
    listAuthorized: async () => granted(),
    resolveForPlayback: async id => { calls.push(id); return { mediaId:id, playableUrl:'https://example.org/play', expiresAtMs:Date.now()+30000, sourceRevisionId:id==='opaque-current-1'?'R2':'R1', artifactId:id==='opaque-current-1'?'A2':'A1' }; }
  });
  await bridge.browse();
  assert.equal((await bridge.play('opaque-history-2')).sourceRevisionId, 'R1');
  assert.equal((await bridge.play('opaque-current-1')).sourceRevisionId, 'R2');
  assert.deepEqual(calls, ['opaque-history-2','opaque-current-1']);
});

test('reject malformed and expired stream grants; do not synthesize fallback', async () => {
  const bridge = createCarMediaBridge({ listAuthorized:async()=>granted(), resolveForPlayback:async()=>({playableUrl:'file:///private.wav',expiresAtMs:Date.now()+30000,sourceRevisionId:'R1',artifactId:'A1'}) });
  await assert.rejects(bridge.play('opaque-history-2'), /stream|grant/i);
  const expired = createCarMediaBridge({ listAuthorized:async()=>granted(), resolveForPlayback:async id=>({mediaId:id,playableUrl:'https://example.org/play',expiresAtMs:Date.now()-1000,sourceRevisionId:'R1',artifactId:'A1'}) });
  await assert.rejects(expired.play('opaque-history-2'), /expired|grant/i);
});

test('car UI never exposes arbitrary editor, unsafe visualizers, or sliders while driving', () => {
  const driving = carDisplayPolicy({platform:'android-auto', driving:true, hostSupportsPresets:true});
  assert.equal(driving.playback, true);
  assert.equal(driving.presetActions, true);
  assert.equal(driving.visualizer, false);
  assert.equal(driving.fineEqSliders, false);
  assert.equal(driving.editor, false);
  const parkedAAOS = carDisplayPolicy({platform:'android-automotive', driving:false, hostSupportsParkedScreens:true, parkedExperienceApproved:true});
  assert.equal(parkedAAOS.visualizer, true);
  assert.equal(carDisplayPolicy({platform:'android-auto',driving:false}).visualizer, false);
});

test('refuse external media ids and never play by arbitrary file path or digest', async () => {
  let called = false;
  const bridge = createCarMediaBridge({listAuthorized: async()=>granted(), resolveForPlayback:async()=>{called=true;return {};}});
  await assert.rejects(bridge.play('../workspace/studio_exports/audio.wav'), /media id/i);
  await assert.rejects(bridge.play('sha256:'+'b'.repeat(64)), /media id/i);
  assert.equal(called,false);
});

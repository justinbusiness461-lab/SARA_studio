'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {assertClockProgress, assertMediaIdentity, assertABMediaReadback} = require('../tools/m045_browser_media_clock.cjs');
const ids = {revisionId:'r'.repeat(64), artifactId:'a'.repeat(64)};
function capture(t=1.3, now=1000, extra={}) {
  return { ...ids, currentTimeSec:t, durationSec:300, readyState:4, paused:false, ended:false, observedAtMs:now, ...extra };
}
test('current selected media really advances instead of only UI flag', () => {
  const before=capture(1.3,1000),after=capture(1.55,1280);
  assert.deepEqual(assertClockProgress(before,after,ids), {advanceSec:0.25,observedElapsedMs:280});
});
test('fake started flag does not substitute for actual advancing clock', () => {
  assert.throws(()=>assertClockProgress(capture(),capture(1.3,1500),ids),/MEDIA_CLOCK_NOT_ADVANCING/);
});
test('no media element means no certification',()=>{
  assert.throws(()=>assertClockProgress(capture(),null,ids),/MEDIA_SNAPSHOT_INVALID/);
});
test('decoded audio must be ready and playing rather than merely loadable',()=>{
  for(const change of [{readyState:1},{paused:true},{ended:true},{durationSec:0},{currentTimeSec:Infinity}]){
    assert.throws(()=>assertClockProgress(capture(),capture(1.7,1500,change),ids),/MEDIA_CLOCK_/);
  }
});
test('foreign/stale artifact or revision cannot borrow playback',()=>{
  for (const change of [{revisionId:'x'.repeat(64)},{artifactId:'x'.repeat(64)}]){
    assert.throws(()=>assertClockProgress(capture(),capture(1.7,1500,change),ids),/MEDIA_IDENTITY_MISMATCH/);
  }
});
test('seek jumps do not qualify as a naturally advancing audio clock',()=>{
  assert.throws(()=>assertClockProgress(capture(),capture(150,1400),ids),/MEDIA_CLOCK_IMPLAUSIBLE_ADVANCE/);
});
test('wall-clock rollback does not qualify as progress',()=>{
  assert.throws(()=>assertClockProgress(capture(),capture(1.5,900),ids),/MEDIA_CLOCK_INVALID_OBSERVATION_TIME/);
});
test('readback rejects a mismatched source',()=>{
  assert.throws(()=>assertMediaIdentity(capture(1.5,1200,{artifactId:'other'}),ids),/MEDIA_IDENTITY_MISMATCH/);
});
test('A/B UI proof and actual media sample must agree at selected revision',()=>{
  const ui={fromPositionSec:11.2,toPositionSec:11.215};
  const actual=capture(11.26,2100);
  assert.equal(assertABMediaReadback(ui,actual,ids).uiDriftSec.toFixed(3),'0.015');
});
test('A/B fails when UI proof claims a position media did not reach',()=>{
  assert.throws(()=>assertABMediaReadback({fromPositionSec:11.2,toPositionSec:11.2},capture(12.5,2100),ids),/AB_MEDIA_READBACK_MISMATCH/);
});
test('A/B rejects NaN/missing/invented UI attestation',()=>{
  for(const proof of [null,{}, {fromPositionSec:0,toPositionSec:NaN}, {fromPositionSec:0.2,toPositionSec:0.3}]){
    assert.throws(()=>assertABMediaReadback(proof,capture(),ids),/AB_.*INVALID|AB_POSITION_DRIFT/);
  }
});

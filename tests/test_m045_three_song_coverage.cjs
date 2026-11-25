'use strict';
/** Source-level proof gate tests; do not substitute for live real-media Chromium. */
const test = require('node:test');
const assert = require('node:assert/strict');
const { assertThreeSongBrowserCoverage } = require('../tools/m045_three_song_coverage.cjs');
const SONGS = ['Turn The Noise Back On','If This Is All I Get','Outlaws and Echoes'];
function valid() {
  const rows=[];
  for(const width of [390,1440]){
    for(const title of SONGS) rows.push({title,width,revisionId:'r1',artifactId:'a1',mediaClockAdvanceSec:.2,mediaObservedElapsedMs:250});
    rows.push({ab:'R1->R2',width,r1PositionDriftSec:.02,r2PositionDriftSec:.02,
      independentR1LagSec:.07,independentR2LagSec:.06});
  }
  return rows;
}
test('exact six song/viewport clocks and two A/B transitions admit reference only',()=>{
  assert.deepEqual(assertThreeSongBrowserCoverage(valid()), {clockCount:6,abCount:2,widths:[390,1440]});
});
test('mobile R1 to R2 A/B cannot silently disappear',()=>{
  assert.throws(()=>assertThreeSongBrowserCoverage(valid().filter(x=>!(x.ab&&x.width===390))),/AB_COVERAGE/);
});
test('desktop R1 to R2 A/B cannot silently disappear',()=>{
  assert.throws(()=>assertThreeSongBrowserCoverage(valid().filter(x=>!(x.ab&&x.width===1440))),/AB_COVERAGE/);
});
test('mobile playback clock must actually advance',()=>{
  const rows=valid();rows[0]={...rows[0],mediaClockAdvanceSec:0};
  assert.throws(()=>assertThreeSongBrowserCoverage(rows),/CLOCK/);
});
test('all three songs at each width required; neither width may be skipped',()=>{
  for(const width of [390,1440]){
    const rows=valid().filter(x=>!(x.title==='If This Is All I Get' && x.width===width));
    assert.throws(()=>assertThreeSongBrowserCoverage(rows),/CLOCK_COVERAGE/);
  }
});
test('duplicate, unlisted song or unexpected viewport cannot inflate coverage',()=>{
  const rows=valid();
  assert.throws(()=>assertThreeSongBrowserCoverage([...rows,rows[0]]),/CLOCK_COVERAGE/);
  assert.throws(()=>assertThreeSongBrowserCoverage([...rows,{...rows[0],title:'Invented'}]),/CLOCK_COVERAGE/);
  assert.throws(()=>assertThreeSongBrowserCoverage([...rows,{...rows[0],width:1024}]),/UNEXPECTED_VIEWPORT/);
});
test('each independent A/B transition must respect 50ms UI position bound',()=>{
  for(const width of [390,1440]){
    for(const field of ['r1PositionDriftSec','r2PositionDriftSec']){
      const rows=valid(); const ab=rows.find(x=>x.ab && x.width===width);ab[field]=.050001;
      assert.throws(()=>assertThreeSongBrowserCoverage(rows),/AB_DRIFT/);
    }
  }
});
test('A/B independent sampled media readings retain 150ms observation ceiling',()=>{
  const rows=valid();rows.find(x=>x.ab).independentR2LagSec=.151;
  assert.throws(()=>assertThreeSongBrowserCoverage(rows),/AB_MEDIA_READBACK/);
});
test('all clock and A/B numbers must be finite and nonnegative',()=>{
  for(const v of [NaN,Infinity,-1,null,'0.02']){
    const rows=valid();rows[1].mediaClockAdvanceSec=v;
    assert.throws(()=>assertThreeSongBrowserCoverage(rows),/CLOCK/);
    const ab=valid();ab.find(x=>x.ab).r1PositionDriftSec=v;
    assert.throws(()=>assertThreeSongBrowserCoverage(ab),/AB_DRIFT/);
  }
});
test('unrecognized A/B event cannot be normalized into a passing proof',()=>{
  const rows=valid(); rows.find(x=>x.ab).ab='R1->R3';
  assert.throws(()=>assertThreeSongBrowserCoverage(rows),/AB_COVERAGE/);
});

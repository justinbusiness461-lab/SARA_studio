'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {parsePrompt}=(()=>{const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
 const ctx={window:{},Date,Math};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../app-core.js'),'utf8'),ctx);return {parsePrompt:ctx.parsePrompt};})();
const ScoreCore=require('../scorecore.js');
const fixture=()=>JSON.parse(JSON.stringify(parsePrompt('94 BPM F# minor southern scratch', {seed:42})));

test('scratch grid toggles one exact canonical marker and leaves all other events P0-identical',()=>{
 const original=fixture(), before=JSON.stringify(original);
 const result=ScoreCore.toggleScratchMarker(original,{sectionId:original.structure.sections[1].id,
     stepIndex:3,technique:'chirp',deck:'A'});
 assert.equal(JSON.stringify(original),before);
 const scratch=result.tracks.find(t=>t.track_id==='dj_scratch');
 assert.equal(scratch.type,'DJ');
 assert.equal(scratch.events.length,1);
 const marker=scratch.events[0];
 assert.equal(marker.type,'DJ_SCRATCH_MARKER');
 assert.equal(marker.tick,original.structure.sections[1].start_tick+3*480);
 assert.equal(marker.sample_index,ScoreCore.djTickToSample(result,marker.tick));
 assert.equal(marker.technique,'chirp');
 const after=ScoreCore.toggleScratchMarker(result,{sectionId:original.structure.sections[1].id,
   stepIndex:3,technique:'chirp',deck:'A'});
 assert.equal(after.tracks.find(t=>t.track_id==='dj_scratch').events.length,0);
 for(let i=0;i<original.tracks.length;i++)
   assert.deepEqual(result.tracks[i],original.tracks[i]);
});
test('two deck markers at same tick coexist with deterministic identities',()=>{
 let s=fixture(),sec=s.structure.sections[1];
 s=ScoreCore.toggleScratchMarker(s,{sectionId:sec.id,stepIndex:0,technique:'baby',deck:'A'});
 s=ScoreCore.toggleScratchMarker(s,{sectionId:sec.id,stepIndex:0,technique:'2_click_flare',deck:'B'});
 const events=s.tracks.find(t=>t.track_id==='dj_scratch').events;
 assert.equal(events.length,2);
 assert.notEqual(events[0].event_id,events[1].event_id);
});
test('Sonic Lock and invalid step/technique/deck fail without mutating SongSpec',()=>{
 const s=fixture(),sec=s.structure.sections[1];const frozen=JSON.stringify(s);
 for(const bad of [{stepIndex:16},{stepIndex:-1},{technique:'foreign'}, {deck:'C'}]){
   assert.throws(()=>ScoreCore.toggleScratchMarker(s,
    {sectionId:sec.id,stepIndex:4,technique:'baby',deck:'A',...bad}));
 }
 assert.equal(JSON.stringify(s),frozen);
 const lock={...s,structure:{sections:s.structure.sections.map(x=>x.id===sec.id?{...x,sonic_lock:true}:x)}};
 assert.throws(()=>ScoreCore.toggleScratchMarker(lock,
   {sectionId:sec.id,stepIndex:0,technique:'baby',deck:'A'}),/Sonic Lock/);
 const x=ScoreCore.toggleScratchMarker(s,{sectionId:sec.id,stepIndex:0,technique:'baby',deck:'A'});
 x.tracks.find(t=>t.track_id==='dj_scratch').sonic_lock=true;
 assert.throws(()=>ScoreCore.toggleScratchMarker(x,
   {sectionId:sec.id,stepIndex:1,technique:'chirp',deck:'B'}),/Sonic Lock/);
});
test('sample clocks are rational-rounded and report event render as UNQUALIFIED',()=>{
 const s=fixture();assert.equal(ScoreCore.djTickToSample(s,0),0);
 assert.equal(ScoreCore.djTickToSample(s,960),Math.round(44100*60/94));
 const x=ScoreCore.toggleScratchMarker(s,{sectionId:s.structure.sections[0].id,stepIndex:2,
   technique:'two_deck_juggle',deck:'A'});
 assert.equal(x.tracks.find(t=>t.track_id==='dj_scratch').events[0].audio_status,'UNRENDERED_SOURCE_ASSET_REQUIRED');
});

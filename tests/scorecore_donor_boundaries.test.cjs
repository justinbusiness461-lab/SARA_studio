'use strict';
// M044 SJ3 donor Wave 001: source-level regression for existing ScoreCore.
// Run: node --test tests/scorecore_donor_boundaries.test.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const { transposeSection } = require('../tools/scorecore.cjs');

function fixture() {
  return {
    timebase: {ticks_per_quarter_note:960, initial_bpm:96, key:'E minor', meter:'4/4'},
    structure: {sections:[
      {id:'verse1',start_tick:0,end_tick:3840},
      {id:'chorus1',start_tick:3840,end_tick:7680},
      {id:'verse2',start_tick:7680,end_tick:11520}
    ]},
    tracks:[
      {track_id:'bass',type:'BASS',events:[
        {type:'NOTE_ON',tick:100,duration_ticks:400,note_number:40},
        {type:'NOTE_ON',tick:4000,duration_ticks:400,note_number:44},
        {type:'NOTE_ON',tick:8000,duration_ticks:400,note_number:47}
      ]},
      {track_id:'guitar',type:'LEAD',events:[
        {type:'NOTE_ON',tick:4000,duration_ticks:300,note_number:67}
      ]}
    ]
  };
}
test('baseline: targeted bass transpose preserves non-targets and input', () => {
  const before=fixture(), source=JSON.stringify(before);
  const after=transposeSection(before,{sectionId:'chorus1',trackId:'bass',semitones:-12});
  assert.equal(JSON.stringify(before),source);
  assert.deepEqual(after.tracks[0].events.map(e=>e.note_number),[40,32,47]);
  assert.equal(after.tracks[1].events[0].note_number,67);
});
test('reject overlapping named sections instead of ambiguous target', () => {
  const before=fixture();
  before.structure.sections[0].end_tick=4800;
  const source=JSON.stringify(before);
  assert.throws(()=>transposeSection(before,{sectionId:'chorus1',trackId:'bass',semitones:-12}),/overlap|ambiguous/i);
  assert.equal(JSON.stringify(before),source);
});
test('reject unsafe integer section ticks', () => {
  const before=fixture(), max=Number.MAX_SAFE_INTEGER;
  before.structure.sections[1].start_tick=max+1;
  before.structure.sections[1].end_tick=max+1000;
  before.tracks[0].events[1].tick=max+2;
  before.tracks[0].events[1].duration_ticks=10;
  assert.throws(()=>transposeSection(before,{sectionId:'chorus1',trackId:'bass',semitones:-12}),/safe|tick|bound/i);
});
test('baseline: note crossing selected section rejects', () => {
  const before=fixture();
  before.tracks[0].events[1].tick=3800;
  assert.throws(()=>transposeSection(before,{sectionId:'chorus1',trackId:'bass',semitones:-12}),/crosses/);
});
test('reject unsafe note end arithmetic before silent precision loss', () => {
  const before=fixture(), max=Number.MAX_SAFE_INTEGER;
  before.structure.sections[1]={id:'chorus1',start_tick:max-100,end_tick:max};
  before.structure.sections.pop();
  before.tracks[0].events[1]={type:'NOTE_ON',tick:max-5,duration_ticks:20,note_number:44};
  assert.throws(()=>transposeSection(before,{sectionId:'chorus1',trackId:'bass',semitones:-12}),/safe|overflow/i);
});

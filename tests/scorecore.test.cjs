const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { musicIntent, compileIntent, transposeSection } = require('../tools/scorecore.cjs');
const ctx = { console, window: {}, document: { getElementById: () => null } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, '../app-core.js'), 'utf8'), ctx);
const generate = (prompt, opts) => JSON.parse(JSON.stringify(ctx.parsePrompt(prompt, opts)));
const song = () => compileIntent(musicIntent('dark 102 BPM E minor blues guitar', { seed: 44 }), generate);

test('intent retains prompt, explicit musical constraints and reproducible seed', () => {
  const i = musicIntent('dark 102 BPM E minor blues guitar', { seed: 44 });
  assert.equal(i.bpm, 102); assert.equal(i.key, 'E minor'); assert.equal(i.meter, '4/4');
  const s = compileIntent(i, generate);
  assert.equal(s.timebase.initial_bpm, 102); assert.equal(s.timebase.key, 'E minor');
  assert.equal(s.generation_seed, 44); assert.ok(s.structure.sections.length > 0);
});
test('unsupported meter and contradictory explicit tempo fail rather than silently coerce', () => {
  assert.throws(() => musicIntent('a waltz in 3/4'), /meter/);
  assert.throws(() => musicIntent('102 BPM then 120 BPM'), /tempo/);
  assert.throws(() => musicIntent('999 BPM'), /tempo/);
});
test('unsupported keys and invalid seeds fail explicitly', () => {
  assert.throws(() => musicIntent('B major'), /key/);
  assert.throws(() => musicIntent('102 BPM', { seed: -1 }), /seed/);
});
test('bass octave edit changes only notes starting inside the chosen section', () => {
  const before = song(), original = JSON.stringify(before), sec = before.structure.sections[2];
  const after = transposeSection(before, { sectionId: sec.id, trackId: 'bass', semitones: -12 });
  assert.equal(JSON.stringify(before), original);
  let changed = 0;
  const expected = JSON.parse(original);
  for (const e of expected.tracks.find(t => t.track_id === 'bass').events) {
    if (e.type === 'NOTE_ON' && e.tick >= sec.start_tick && e.tick < sec.end_tick) { e.note_number -= 12; changed++; }
  }
  assert.ok(changed > 0); assert.deepEqual(after, expected);
});
test('invalid target, ambiguous IDs and out of range pitches fail atomically', () => {
  const s = song(), original = JSON.stringify(s), id = s.structure.sections[2].id;
  for (const request of [
    { sectionId: 'missing', trackId: 'bass', semitones: -12 },
    { sectionId: id, trackId: 'missing', semitones: -12 },
    { sectionId: id, trackId: 'bass', semitones: -128 },
    { sectionId: id, trackId: 'drums', semitones: -12 },
    { sectionId: id, trackId: 'bass', semitones: 0.5 }
  ]) assert.throws(() => transposeSection(s, request));
  assert.equal(JSON.stringify(s), original);
  s.structure.sections.push({ ...s.structure.sections[2] });
  assert.throws(() => transposeSection(s, { sectionId: id, trackId: 'bass', semitones: -12 }), /ambiguous/);
});
test('section end is exclusive and straddling-note edits require explicit later policy', () => {
  const s = song(), sec = s.structure.sections[2], bass = s.tracks.find(t => t.track_id === 'bass');
  bass.events.push({ type: 'NOTE_ON', tick: sec.end_tick, duration_ticks: 100, note_number: 60 });
  const a = transposeSection(s, { sectionId: sec.id, trackId: 'bass', semitones: -12 });
  assert.equal(a.tracks.find(t => t.track_id === 'bass').events.at(-1).note_number, 60);
  bass.events.push({ type: 'NOTE_ON', tick: sec.start_tick - 1, duration_ticks: 2, note_number: 60 });
  assert.throws(() => transposeSection(s, { sectionId: sec.id, trackId: 'bass', semitones: -12 }), /crosses/);
});

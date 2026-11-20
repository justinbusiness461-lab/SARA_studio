'use strict';

// M044 adapter candidate. SongSpec remains owned by app-core.parsePrompt;
// ProjectRevision/ProductionTimeline remain owned by studio_server.py.
// No persistence, rendering, lyric mutation or certification authority here.
const KEYS = ['F# minor', 'A minor', 'C minor', 'D minor', 'E minor', 'G major'];

/** @typedef {{version:1,prompt:string,bpm:number,key:string,meter:'4/4',seed:number}} MusicIntent */
/** Bounded prompt admission: unsupported explicit constraints fail closed. */
function musicIntent(prompt, { seed = 0 } = {}) {
  if (typeof prompt !== 'string' || !prompt.trim()) throw new Error('prompt required');
  if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) throw new Error('invalid seed');
  const tempos = [...prompt.matchAll(/\b(\d+(?:\.\d+)?)\s*bpm\b/gi)].map(m => Number(m[1]));
  const bpm = tempos[0] ?? 102;
  if (!Number.isInteger(bpm) || bpm < 60 || bpm > 180 || tempos.some(n => n !== bpm)) throw new Error('unsupported or conflicting tempo');
  const meters = [...prompt.matchAll(/\b(\d+)\s*\/\s*(\d+)\b/g)].map(m => m[1] + '/' + m[2]);
  if (meters.some(m => m !== '4/4') || /\bwaltz\b/i.test(prompt)) throw new Error('unsupported meter');
  const requested = [...prompt.matchAll(/\b([a-g](?:#|b)?)\s+(minor|major)\b/gi)].map(m => m[1][0].toUpperCase() + m[1].slice(1) + ' ' + m[2].toLowerCase());
  const key = requested[0] ?? 'F# minor';
  if (!KEYS.includes(key) || requested.some(k => k !== key)) throw new Error('unsupported or conflicting key');
  return Object.freeze({ version: 1, prompt, bpm, key, meter: '4/4', seed });
}

function compileIntent(intent, parsePrompt) {
  if (typeof parsePrompt !== 'function') throw new Error('existing parsePrompt owner required');
  const admitted = musicIntent(intent.prompt, { seed: intent.seed });
  for (const field of ['version', 'bpm', 'key', 'meter']) {
    if (intent[field] !== admitted[field]) throw new Error('intent mismatch: ' + field);
  }
  const spec = parsePrompt(admitted.prompt, { seed: admitted.seed });
  if (spec.timebase.initial_bpm !== admitted.bpm || spec.timebase.key !== admitted.key || spec.timebase.meter !== admitted.meter) throw new Error('compiler constraint mismatch');
  return spec;
}

/** Immutable local edit; only NOTE_ON pitches fully contained in [start,end).
 * Crossing notes fail closed until the owner chooses a split/tie policy.
 */
function transposeSection(spec, { sectionId, trackId, semitones }) {
  if (!Number.isInteger(semitones) || semitones < -127 || semitones > 127) throw new Error('invalid semitones');
  const sections = spec.structure.sections.filter(s => s.id === sectionId);
  const tracks = spec.tracks.filter(t => t.track_id === trackId);
  if (sections.length !== 1 || tracks.length !== 1) throw new Error('missing or ambiguous edit target');
  const section = sections[0], track = tracks[0];
  const start = section.start_tick, end = section.end_tick;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || end <= start) throw new Error('invalid section bounds: safe integer ticks required');
  // An edit cannot target a unique musical section if two named sections overlap.
  for (const other of spec.structure.sections) {
    if (other === section) continue;
    if (!Number.isSafeInteger(other.start_tick) || !Number.isSafeInteger(other.end_tick) ||
        other.start_tick < 0 || other.end_tick <= other.start_tick) {
      throw new Error('invalid neighboring section bounds: safe integer ticks required');
    }
    if (other.start_tick < end && other.end_tick > start) throw new Error('ambiguous overlapping sections');
  }
  if (track.type === 'DRUMS' || track.type === 'VOCAL') throw new Error('unsupported track type');
  let count = 0;
  for (const e of track.events) {
    if (e.type !== 'NOTE_ON') continue;
    if (!Number.isSafeInteger(e.tick) || !Number.isSafeInteger(e.duration_ticks) ||
        e.tick < 0 || e.duration_ticks <= 0 || !Number.isSafeInteger(e.tick + e.duration_ticks)) {
      throw new Error('unsafe note interval: safe integer ticks required');
    }
    const stop = e.tick + e.duration_ticks;
    if (e.tick < end && stop > start && (e.tick < start || stop > end)) throw new Error('note crosses edit section');
    if (e.tick >= start && e.tick < end) {
      if (!Number.isInteger(e.note_number) || e.note_number + semitones < 0 || e.note_number + semitones > 127) throw new Error('pitch outside MIDI range');
      count++;
    }
  }
  if (!count) throw new Error('no editable notes');
  const result = JSON.parse(JSON.stringify(spec));
  for (const e of result.tracks.find(t => t.track_id === trackId).events) {
    if (e.type === 'NOTE_ON' && e.tick >= start && e.tick < end) e.note_number += semitones;
  }
  return result;
}

const ScoreCore = { musicIntent, compileIntent, transposeSection };
if (typeof module !== 'undefined' && module.exports) module.exports = ScoreCore;
else window.ScoreCore = ScoreCore;

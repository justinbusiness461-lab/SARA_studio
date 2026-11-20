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
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end <= start) throw new Error('invalid section bounds');
  if (track.type === 'DRUMS' || track.type === 'VOCAL') throw new Error('unsupported track type');
  let count = 0;
  for (const e of track.events) {
    if (e.type !== 'NOTE_ON') continue;
    if (!Number.isInteger(e.tick) || !Number.isInteger(e.duration_ticks) || e.duration_ticks <= 0) throw new Error('invalid note interval');
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

// Scratch Surgeon symbolic grid: ScoreCore owns events, not source media.
const DJ_TECHNIQUES = Object.freeze(['baby','chirp','2_click_flare','two_deck_juggle']);

function djTickToSample(spec, tick) {
  const tb = spec && spec.timebase;
  if (!tb || tb.meter !== '4/4' || tb.sample_rate !== 44100 ||
      tb.ticks_per_quarter_note !== 960 ||
      !Number.isInteger(tb.initial_bpm) || tb.initial_bpm < 60 || tb.initial_bpm > 180 ||
      !Number.isSafeInteger(tick) || tick < 0)
    throw new Error('unsupported DJ timeline');
  const numerator = BigInt(tick) * 60n * 44100n;
  const denominator = BigInt(tb.initial_bpm) * 960n;
  const result = (numerator * 2n + denominator) / (2n * denominator);
  if (result > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('DJ sample overflow');
  return Number(result);
}

function toggleScratchMarker(spec, {sectionId, stepIndex, technique, deck}) {
  if (!spec || !spec.structure || !Array.isArray(spec.structure.sections) ||
      !Array.isArray(spec.tracks)) throw new Error('SongSpec required');
  if (!Number.isInteger(stepIndex) || stepIndex < 0 || stepIndex >= 16)
    throw new Error('invalid DJ step');
  if (!DJ_TECHNIQUES.includes(technique)) throw new Error('unsupported scratch technique');
  if (deck !== 'A' && deck !== 'B') throw new Error('invalid DJ deck');
  const sections = spec.structure.sections.filter(sec => sec.id === sectionId);
  if (sections.length !== 1) throw new Error('missing or ambiguous section');
  const sec=sections[0], tick=sec.start_tick + stepIndex*480;
  if (!Number.isSafeInteger(sec.start_tick) || !Number.isSafeInteger(sec.end_tick)
      || tick < sec.start_tick || tick >= sec.end_tick)
    throw new Error('DJ grid outside target section');
  if (sec.sonic_lock === true) throw new Error('Sonic Lock protects section');
  const djTracks=spec.tracks.filter(track => track.track_id === 'dj_scratch');
  if (djTracks.length>1 || (djTracks.length===1 && djTracks[0].type!=='DJ'))
    throw new Error('DJ track identity collision');
  const original=djTracks[0];
  if (original && original.sonic_lock === true) throw new Error('Sonic Lock protects DJ track');
  const eventId='dj:'+sec.id+':'+tick+':'+deck;
  const edited=JSON.parse(JSON.stringify(spec));
  let track=edited.tracks.find(t=>t.track_id==='dj_scratch');
  if (!track) {
    track={track_id:'dj_scratch',name:'Scratch Surgeon',type:'DJ',muted:false,
      sonic_lock:false,volume_db:0,pan:0,events:[]};
    edited.tracks.push(track);
  }
  const matches=track.events.filter(e=>e.event_id===eventId);
  if (matches.length>1) throw new Error('duplicate DJ event identity');
  if (matches.length===1 && matches[0].type!=='DJ_SCRATCH_MARKER')
    throw new Error('DJ event identity collision');
  track.events=track.events.filter(e=>e.event_id!==eventId);
  if (!(matches.length===1 && matches[0].technique===technique)) {
    track.events.push({type:'DJ_SCRATCH_MARKER',event_id:eventId,tick,
      duration_ticks:480,deck,technique,
      sample_index:djTickToSample(spec,tick),
      audio_status:'UNRENDERED_SOURCE_ASSET_REQUIRED'});
    track.events.sort((a,b)=>(a.tick-b.tick) || String(a.event_id).localeCompare(String(b.event_id)));
  }
  return edited;
}

const ScoreCore = { musicIntent, compileIntent, transposeSection, toggleScratchMarker, djTickToSample, DJ_TECHNIQUES };
if (typeof module !== 'undefined' && module.exports) module.exports = ScoreCore;
else window.ScoreCore = ScoreCore;

'use strict';
// Executable local HTTP/filesystem/process proof. No browser or listening claim.
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const { spawn } = require('node:child_process'), net = require('node:net');
const assert = require('node:assert/strict'), crypto = require('node:crypto');
const equal = require('node:util').isDeepStrictEqual;
const { generate, render, renderCaptured, session } = require('./m044-session.cjs');
const root = path.resolve(__dirname, '..');
const out = path.resolve(process.argv[2] || path.join(root, 'evidence/m044/integration'));
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const checks = [], clone = o => JSON.parse(JSON.stringify(o));
function check(name, condition) { assert.ok(condition, name); checks.push(name); }
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const state = fs.mkdtempSync(path.join(os.tmpdir(), 'sf-m044-'));
  const socket = net.createServer(); await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
  const port = socket.address().port; await new Promise(resolve => socket.close(resolve));
  const origin = 'http://127.0.0.1:' + port;
  let process;
  const boot = async () => {
    const code = "import sys,pathlib;sys.path.insert(0,sys.argv[1]);import studio_server as s;s.PORT=int(sys.argv[2]);s.EXPORT_ROOT=pathlib.Path(sys.argv[3]);s.main()";
    process = spawn('python3', ['-u', '-c', code, path.join(root, 'tools'), String(port), state], { stdio: ['ignore', 'ignore', 'pipe'] });
    process.stderr.on('data', () => {});
    for (let i = 0; i < 100; i++) {
      try { return await session(origin); } catch (_) { await sleep(50); }
    }
    throw Error('server startup failed');
  };
  const kill = async () => {
    if (!process || process.exitCode !== null) return;
    const done = new Promise(resolve => process.once('exit', resolve));
    process.kill('SIGKILL'); await done;
  };
  try {
    let api = await boot();
    const spec = generate('dark 96 BPM E minor blues guitar', 44044);
    spec.title = 'M044 authority and locality fixture'; spec.song_id = 'm044-fixture-44044'; spec.created_at = '2026-11-01T00:00:00Z';
    // Four-bar engineering fixture, deliberately instrumental. Not benchmark art.
    const end = 4 * 4 * 960;
    spec.structure.sections = spec.structure.sections.slice(0, 2).map((s, i) => ({ ...s, role: 'none', lyrics: '', end_tick: i ? end : s.end_tick }));
    spec.tracks = spec.tracks.filter(t => t.type !== 'VOCAL').map(t => ({ ...t,
      events: t.events.filter(e => e.tick < end).map(e => ({ ...e, duration_ticks: Math.min(e.duration_ticks, end - e.tick) })) }));
    const source = await api.write(Buffer.from('M044 retained source-asset sentinel; not audio'));
    const r1Draft = await api.commit({ projectId: null, expectedCurrentRevisionId: null, songSpec: spec,
      sourceAssetDigests: [source.sha256], outputArtifactIds: [] });
    check('R1 persisted before rendering', r1Draft.revision.outputArtifactIds.length === 0);
    const pid = r1Draft.manifest.projectId;
    const r1 = await api.render(r1Draft);
    check('R1 render bound to exact spec and timeline', r1.revision.outputBindings.every(b => b.songSpecDigest === r1.revision.songSpecDigest && b.productionTimelineDigest === r1.revision.productionTimelineDigest));
    // Start real R1 work while R1 is current. Hold its completion until after R2.
    let release, started;
    const gate = new Promise(resolve => { release = resolve; });
    const start = new Promise(resolve => { started = resolve; });
    const old = renderCaptured(r1, 'late-r1-render', { render: async s => { started(); const b = await render(s); await gate; return b; },
      write: api.write, commit: api.commit });
    await start;
    const edit = { sectionId: spec.structure.sections[1].id, trackId: 'bass', semitones: -12 };
    const r2Draft = await api.edit(pid, r1.revision.revisionId, 'bass-octave-001', edit);
    const expected = clone(spec);
    let changed = 0;
    for (const e of expected.tracks.find(t => t.track_id === 'bass').events) {
      if (e.tick >= spec.structure.sections[1].start_tick && e.tick < end) { e.note_number -= 12; changed++; }
    }
    check('only targeted bass pitches changed', changed > 0 && equal(r2Draft.songSpec, expected));
    const replay = await api.edit(pid, r1.revision.revisionId, 'bass-octave-001', edit);
    check('identical edit replay returns same revision', replay.revision.revisionId === r2Draft.revision.revisionId);
    await assert.rejects(() => api.edit(pid, r1.revision.revisionId, 'bass-octave-001', { ...edit, semitones: -7 }), /409.*operation/);
    check('same operation ID changed payload rejects', true);
    await assert.rejects(() => api.edit(pid, r1.revision.revisionId, 'stale-edit', edit), /409/);
    check('stale edit rejects', true);
    // Delay a genuinely running R1 render until R2 is persisted. Its captured CAS
    // must fail; its persisted orphan bytes never become current R2 output.
    const r2 = await api.render(r2Draft);
    release(); const late = await old;
    check('late R1 render cannot replace R2 output', (await api.open(pid)).revision.revisionId === r2.revision.revisionId);
    check('source bindings preserved', JSON.stringify(r2.revision.sourceAssetDigests) === JSON.stringify(r1.revision.sourceAssetDigests));
    const historical = await api.open(pid, r1.revision.revisionId);
    check('R1 remains immutable and recoverable', equal(historical.revision, r1.revision) && equal(historical.songSpec, spec));
    check('late R1 binding persisted', late.historicalOutputBindings.length === 1 && equal(late.historicalOutputBindings, historical.historicalOutputBindings));
    const object = digest => fs.readFileSync(path.join(state, 'objects', digest.slice(0, 2), digest));
    const a = object(r1.revision.outputArtifactIds[0]), b = object(r2.revision.outputArtifactIds[0]);
    fs.writeFileSync(path.join(out, 'R1.wav'), a); fs.writeFileSync(path.join(out, 'R2.wav'), b);
    check('real PCM16 stereo WAVs', a.toString('ascii', 0, 4) === 'RIFF' && a.readUInt16LE(22) === 2 && a.readUInt16LE(34) === 16);
    check('artifact byte identities verified', sha(a) === r1.revision.outputArtifactIds[0] && sha(b) === r2.revision.outputArtifactIds[0]);
    const rate = a.readUInt32LE(24), frameBytes = 4, frames = (a.length - 44) / frameBytes;
    const startFrame = Math.round(spec.structure.sections[1].start_tick / 960 * 60 / 96 * rate);
    const stopFrame = Math.round(end / 960 * 60 / 96 * rate), tailFrames = Math.ceil(0.1 * rate);
    let first = null, last = null, count = 0, outside = 0;
    for (let i = 0; i < frames; i++) {
      if (!a.subarray(44 + i * 4, 48 + i * 4).equals(b.subarray(44 + i * 4, 48 + i * 4))) {
        if (first === null) first = i; last = i; count++;
        if (i < startFrame || i >= stopFrame + tailFrames) outside++;
      }
    }
    check('actual audio changed only inside edit plus declared 100ms tail', count > 0 && outside === 0);
    const priorProcessId = process.pid;
    await kill(); api = await boot();
    const reopened = await api.open(pid);
    check('cold process exact R2 recovered', process.pid !== priorProcessId && equal(reopened, r2));
    check('cold process R1 retained', equal((await api.open(pid, r1.revision.revisionId)).historicalOutputBindings, historical.historicalOutputBindings));
    const again = await api.edit(pid, r1.revision.revisionId, 'bass-octave-001', edit);
    check('cold replay does not advance or reapply edit', again.revision.revisionId === r2Draft.revision.revisionId && again.manifest.currentRevisionId === r2.revision.revisionId);
    const renderedAgain = await render(reopened.songSpec);
    check('cold reopened exact WAV reproduced', sha(renderedAgain) === sha(b));
    for (const [label, snapshot] of Object.entries({ R1: r1, R2: r2 })) fs.writeFileSync(path.join(out, label + '.json'), JSON.stringify(snapshot, null, 2));
    const receipt = { checks, testCounts: { passed: checks.length, failed: 0 }, environment: { node: global.process.version,
      platform: global.process.platform, renderer: 'web-audio-engine@0.13.4', server: 'python3; existing studio_server' },
      media: { sampleRate: rate, channels: 2, frames, duration: frames / rate, R1: { wavSha256: sha(a), pcmSha256: sha(a.subarray(44)) }, R2: { wavSha256: sha(b), pcmSha256: sha(b.subarray(44)) } },
      locality: { startFrame, stopFrame, tailFrames, changedFrames: count, first, last, outside },
      projectId: pid, R1: r1.revision, R2: r2.revision,
      ceiling: 'local headless renderer + HTTP + filesystem + SIGKILL/restart; dual mono; no browser, C physical qualification, D listening, benchmark quality or mission promotion' };
    fs.writeFileSync(path.join(out, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
    console.log(JSON.stringify({ passed: checks.length, failed: 0, media: receipt.media, locality: receipt.locality }, null, 2));
  } finally { await kill(); fs.rmSync(state, { recursive: true, force: true }); }
})().catch(error => { console.error(error); process.exitCode = 1; });

'use strict';

/*
 * NS001 independent RED: overlapping project-open requests.
 * This runs the exact restoreProjectFromStorage() function extracted from the
 * checked-out app-ui.js, using controlled asynchronous I/O dependencies.
 * It does not simulate/reimplement the algorithm under test.
 *
 * Run from the SARA_studio root:
 *     node --test tests/ns001-overlapping-project-open.red.test.cjs
 *
 * Expected baseline: positive sequential control PASS; two overlap cases RED.
 * These tests are deliberately submitted to a DRAFT QA branch. No product fix.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { createHash } = require('node:crypto');

const bytes = readFileSync(join(__dirname, '..', 'app-ui.js'));
const source = bytes.toString('utf8');
const gitBlob = createHash('sha1')
  .update('blob ' + bytes.length + '\0')
  .update(bytes).digest('hex');
const start = source.indexOf('async function restoreProjectFromStorage() {');
const end = source.indexOf('\n}\n', start);
assert.ok(start >= 0 && end > start, 'Must extract actual Studio project-open implementation');
const exact = source.slice(start, end + 2);

const dependencies = [
  '$', 'localStorage', 'projectRequest', 'loadProjectObject',
  'showProjectAuthority', 'render', 'resetProjectComparison',
  'setStatus', 'verifyPlayableRevision', 'revisionRef',
  'setABControls', 'clearVerifiedPlayback', 'abRevisions'
];

const prepare = new Function(...dependencies,
  exact + '\nreturn restoreProjectFromStorage;');

function deferred() {
  let resolve, reject;
  const promise = new Promise((a, b) => { resolve = a; reject = b; });
  return { promise, resolve, reject };
}

function opened(id) {
  return {
    status: 'SUCCESS',
    manifest: { projectId: id, currentRevisionId: id + '/R1' },
    revision: {
      revisionId: id + '/R1',
      outputArtifactIds: [id + '/wav'],
      parentRevisionId: null,
    },
    songSpec: { title: id, prompt: 'local bounded fixture' },
  };
}

function fixture({ gateAudio = false } = {}) {
  const state = {
    selected: 'A', shown: null, transport: null,
    lastStatus: null, resetCount: 0, requests: [],
  };
  const elementMap = new Map();
  const $ = id => {
    if (id === 'projectId') return {
      get value() { return state.selected; },
      set value(next) { state.selected = next; },
    };
    if (!elementMap.has(id))
      elementMap.set(id, { value: '', textContent: '', disabled: false });
    return elementMap.get(id);
  };
  const opens = { A: deferred(), B: deferred() };
  const decodes = { A: deferred(), B: deferred() };
  const request = async (route, payload) => {
    assert.equal(route, 'open');
    state.requests.push(payload.projectId);
    return opens[payload.projectId].promise;
  };
  const verify = async result => {
    const id = result.manifest.projectId;
    if (gateAudio) await decodes[id].promise;
    state.transport = id;
  };
  const restore = prepare(
    $, { getItem: () => null }, request,
    () => ({ ok: true }),
    result => { state.shown = result.manifest.projectId; },
    () => {},
    () => { state.resetCount += 1; state.transport = null; },
    message => { state.lastStatus = message; },
    verify,
    result => ({
      projectId: result.manifest.projectId,
      revisionId: result.revision.revisionId,
      artifactId: result.revision.outputArtifactIds[0],
    }),
    () => {},
    () => { state.transport = null; },
    { r1: null, r2: null },
  );
  return { state, opens, decodes, restore };
}

async function drainMicrotasks() {
  await new Promise(resolve => setImmediate(resolve));
}

test('positive control: sequential A then B selects B', async () => {
  const f = fixture();
  f.state.selected = 'A';
  const first = f.restore();
  f.opens.A.resolve(opened('A'));
  await first;
  f.state.selected = 'B';
  const second = f.restore();
  f.opens.B.resolve(opened('B'));
  await second;
  assert.equal(f.state.shown, 'B');
  assert.equal(f.state.transport, 'B');
});

test('RED: newer project B wins when older project A open response arrives last', async () => {
  const f = fixture();
  f.state.selected = 'A';
  const old = f.restore();
  f.state.selected = 'B';
  const latest = f.restore();
  f.opens.B.resolve(opened('B'));
  await latest;
  assert.equal(f.state.shown, 'B');
  assert.equal(f.state.transport, 'B');
  f.opens.A.resolve(opened('A'));
  await old;
  assert.equal(f.state.shown, 'B', 'Older open response must not replace latest selected project');
  assert.equal(f.state.transport, 'B', 'Older response must not replace B WAV transport');
});

test('RED: older project A audio verification cannot overwrite B transport', async () => {
  const f = fixture({ gateAudio: true });
  f.state.selected = 'A';
  const old = f.restore();
  f.opens.A.resolve(opened('A'));
  await drainMicrotasks();
  f.state.selected = 'B';
  const latest = f.restore();
  f.opens.B.resolve(opened('B'));
  await drainMicrotasks();
  f.decodes.B.resolve();
  await latest;
  assert.equal(f.state.shown, 'B');
  assert.equal(f.state.transport, 'B');
  f.decodes.A.resolve();
  await old;
  assert.equal(f.state.shown, 'B');
  assert.equal(f.state.transport, 'B', 'Late A audio must not overwrite verified B transport');
});

test.after(() => {
  // Printed to the test log, not treated as proof of product authority.
  process.stdout.write('NS001 audited app-ui.js Git blob: ' + gitBlob + '\n');
});

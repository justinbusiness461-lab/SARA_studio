'use strict';
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const { musicIntent, compileIntent, transposeSection } = require('./scorecore.cjs');
const root = path.resolve(__dirname, '..');
const clone = value => JSON.parse(JSON.stringify(value));

function context(audio = false) {
  const c = { console, window: {}, document: { getElementById: () => null } };
  if (audio) c.OfflineAudioContext = require('web-audio-engine').OfflineAudioContext;
  vm.createContext(c);
  vm.runInContext(fs.readFileSync(path.join(root, 'app-core.js'), 'utf8'), c);
  if (audio) {
    const ui = fs.readFileSync(path.join(root, 'app-ui.js'), 'utf8');
    const start = ui.indexOf('function audioBufferToWav('), end = ui.indexOf('async function exportWav()');
    if (start < 0 || end <= start) throw Error('existing renderer entrypoints unavailable');
    vm.runInContext(ui.slice(start, end), c);
  }
  return c;
}

function generate(prompt, seed) {
  const c = context();
  return clone(compileIntent(musicIntent(prompt, { seed }), c.parsePrompt));
}

async function render(spec) {
  const c = context(true);
  c.input = clone(spec);
  vm.runInContext('loadProjectObject(input)', c);
  const result = await vm.runInContext('renderMixBuffer()', c);
  if (!result.metrics.nonzero) throw Error('silent render');
  c.audio = result.buffer;
  return Buffer.from(vm.runInContext('audioBufferToWav(audio)', c));
}

// Capture before the first await. Completion can only attempt admission against
// that revision; 409 is terminal here and never causes an automatic fresh save.
async function renderCaptured(snapshot, operationId, io) {
  const captured = clone(snapshot);
  const bytes = await io.render(captured.songSpec);
  if (typeof io.publish !== 'function') throw Error('durable render publisher required');
  return io.publish({
    projectId: captured.manifest.projectId,
    sourceRevisionId: captured.revision.revisionId,
    operationId,
    filename: 'm044.wav',
    subdirectory: 'm044',
    data_bytes: Array.from(bytes)
  });
}

async function session(base) {
  const url = new URL(base);
  if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(url.hostname) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw Error('local studio origin required');
  const origin = url.origin;
  const page = await fetch(origin).then(r => r.text());
  const capability = page.match(/window\.__STUDIO_CAPABILITY__="([^"]+)"/);
  if (!capability) throw Error('studio capability unavailable');
  const post = async (route, payload) => {
    const response = await fetch(origin + '/api/' + route, { method: 'POST',
      headers: { 'Content-Type': 'application/json', Origin: origin, 'X-Studio-Capability': capability[1] },
      body: JSON.stringify(payload) });
    const result = await response.json();
    if (!response.ok || result.status !== 'SUCCESS') throw Error(response.status + ': ' + result.error);
    return result;
  };
  const commit = payload => post('projects/commit', payload);
  const open = (projectId, revisionId) => post('projects/open', { projectId, ...(revisionId ? { revisionId } : {}) });
  const write = bytes => post('write_production_file', { filename: 'm044.wav', subdirectory: 'm044', data_bytes: Array.from(bytes) });
  const publish = payload => post('projects/render', payload);
  return { open, commit, write, publish,
    render: snapshot => renderCaptured(snapshot, 'render:' + snapshot.revision.revisionId, { render, publish }),
    edit: async (projectId, expectedCurrentRevisionId, operationId, edit) => {
      // Resolve the immutable base, not whichever revision happens to be current.
      // Repeating this request regenerates exactly the same candidate payload;
      // the canonical server receipt prevents a second transposition.
      const base = await open(projectId, expectedCurrentRevisionId);
      return commit({ projectId, expectedCurrentRevisionId, operationId,
        songSpec: transposeSection(base.songSpec, edit), sourceAssetDigests: base.revision.sourceAssetDigests,
        outputArtifactIds: [], operationContext: { kind: 'transpose-section', edit } });
    }
  };
}

module.exports = { generate, render, renderCaptured, session };

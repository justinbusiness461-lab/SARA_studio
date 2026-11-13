'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, resolve } = require('node:path');
const { once } = require('node:events');
const { createInterface } = require('node:readline');
const { chromium } = require('playwright');

const root = resolve(__dirname, '..');

async function boot(workspace) {
  const server = spawn('python3', ['-u', '-c', `
import socketserver, sys
from pathlib import Path
sys.path.insert(0, "tools")
import studio_server as studio
studio.EXPORT_ROOT = Path(sys.argv[1])
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", 0), studio.StudioHandler) as httpd:
    studio.PORT = httpd.server_address[1]
    print(studio.PORT, flush=True)
    httpd.serve_forever()
`, workspace], { cwd: root, stdio: ['ignore', 'pipe', 'inherit'] });
  const closed = once(server, 'close');
  const lines = createInterface({ input: server.stdout });
  const port = await Promise.race([
    once(lines, 'line').then(([line]) => Number(line)),
    closed.then(([code]) => { throw new Error('Studio exited before startup: ' + code); }),
  ]);
  lines.close();
  return {
    url: 'http://127.0.0.1:' + port,
    stop: async () => {
      if (server.exitCode === null) server.kill('SIGKILL');
      await closed;
    }
  };
}

async function pageFor(browser, url) {
  const page = await browser.newPage({ serviceWorkers: 'block' });
  page.setDefaultTimeout(15000);
  await page.route('https://cdn.jsdelivr.net/**', route => route.abort());
  await page.goto(url);
  return page;
}


async function projectOpenInPage(page, payload) {
  return page.evaluate(async payload => {
    const response = await fetch('/api/projects/open', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Studio-Capability': window.__STUDIO_CAPABILITY__ || '',
        'X-Studio-Session': window.__STUDIO_SESSION__ || ''
      },
      body: JSON.stringify(payload)
    });
    return { status: response.status, body: await response.json() };
  }, payload);
}

function bassNotesInSection(spec, sectionIndex) {
  const section = spec.structure.sections[sectionIndex];
  return spec.tracks.find(t => t.track_id === 'bass').events
    .filter(e => e.type === 'NOTE_ON' && e.tick >= section.start_tick && e.tick < section.end_tick)
    .map(e => ({ tick: e.tick, note_number: e.note_number, duration_ticks: e.duration_ticks, velocity: e.velocity }));
}

function normalizedWithoutVerse2Bass(spec) {
  const clone = structuredClone(spec);
  const section = clone.structure.sections[3];
  const bass = clone.tracks.find(t => t.track_id === 'bass');
  bass.events = bass.events.map(e => {
    if (e.type === 'NOTE_ON' && e.tick >= section.start_tick && e.tick < section.end_tick) {
      return { ...e, note_number: '__EDIT_TARGET__' };
    }
    return e;
  });
  return clone;
}

test('Verse 2 Bass -12 creates lawful R2 and preserves non-target SongSpec', { timeout: 150000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-r2-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  const studio = await boot(workspace); t.after(studio.stop);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH }); t.after(() => browser.close());
  const page = await pageFor(browser, studio.url);

  await page.locator('#prompt').fill('96 BPM E minor dark Southern hip-hop instrumental');
  await page.locator('#btnCompile').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r1Proof = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  assert.ok(r1Proof?.revisionId && r1Proof?.artifactId);

  const r1Open = await projectOpenInPage(page, { projectId: r1Proof.projectId, revisionId: r1Proof.revisionId });
  assert.equal(r1Open.status, 200);
  const r1 = r1Open.body;

  assert.equal(await page.locator('#btnOctaveEdit').isDisabled(), false);
  await page.locator('#btnOctaveEdit').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r2Proof = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  assert.notEqual(r2Proof.revisionId, r1Proof.revisionId);
  assert.notEqual(r2Proof.artifactId, r1Proof.artifactId);

  const current = await projectOpenInPage(page, { projectId: r1Proof.projectId });
  assert.equal(current.status, 200);
  const r2 = current.body;
  assert.equal(r2.revision.revisionId, r2Proof.revisionId);
  assert.equal(r2.manifest.currentRevisionId, r2Proof.revisionId);

  const before = bassNotesInSection(r1.songSpec, 3);
  const after = bassNotesInSection(r2.songSpec, 3);
  assert.ok(before.length > 0);
  assert.equal(after.length, before.length);
  for (let i = 0; i < before.length; i++) {
    assert.equal(after[i].tick, before[i].tick);
    assert.equal(after[i].note_number, before[i].note_number - 12);
    assert.equal(after[i].duration_ticks, before[i].duration_ticks);
    assert.equal(after[i].velocity, before[i].velocity);
  }
  assert.deepEqual(normalizedWithoutVerse2Bass(r2.songSpec), normalizedWithoutVerse2Bass(r1.songSpec));

  const historical = await projectOpenInPage(page, { projectId: r1Proof.projectId, revisionId: r1Proof.revisionId });
  assert.equal(historical.status, 200);
  const hist = historical.body;
  assert.equal(hist.revision.revisionId, r1Proof.revisionId);
  assert.ok(hist.revision.outputArtifactIds.includes(r1Proof.artifactId));
});

test('R1/R2 A-B selects exact revision audio and preserves musical position', { timeout: 150000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-ab-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  const studio = await boot(workspace); t.after(studio.stop);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH }); t.after(() => browser.close());
  const page = await pageFor(browser, studio.url);

  await page.locator('#prompt').fill('96 BPM E minor dark Southern hip-hop instrumental');
  await page.locator('#btnCompile').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r1 = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  await page.locator('#btnOctaveEdit').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r2 = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);

  assert.equal(await page.locator('#btnABR1').isDisabled(), false);
  assert.equal(await page.locator('#btnABR2').isDisabled(), false);

  await page.locator('#btnPlay').click();
  await page.waitForFunction(() => window.__M044_PLAYBACK_STARTED__ === true);
  await page.waitForTimeout(250);
  await page.locator('#btnABR1').click();
  await page.waitForFunction(r1id => window.__M044_PLAYBACK_PROOF__?.revisionId === r1id, r1.revisionId, { timeout: 15000 });
  const ab1 = await page.evaluate(() => window.__M044_AB_PROOF__);
  assert.equal(ab1.fromRevisionId, r2.revisionId);
  assert.equal(ab1.toRevisionId, r1.revisionId);
  assert.ok(Math.abs(ab1.fromPositionSec - ab1.toPositionSec) <= 0.05);

  await page.locator('#btnABR2').click();
  await page.waitForFunction(r2id => window.__M044_PLAYBACK_PROOF__?.revisionId === r2id, r2.revisionId, { timeout: 15000 });
  const ab2 = await page.evaluate(() => window.__M044_AB_PROOF__);
  assert.equal(ab2.fromRevisionId, r1.revisionId);
  assert.equal(ab2.toRevisionId, r2.revisionId);
  assert.ok(Math.abs(ab2.fromPositionSec - ab2.toPositionSec) <= 0.05);
  assert.equal(await page.locator('#abStatus').textContent(), 'Selected R2 · current');
});

test('late R1 A-B response cannot replace newer R2 selection', { timeout: 150000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-ab-race-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  const studio = await boot(workspace); t.after(studio.stop);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH }); t.after(() => browser.close());
  const page = await pageFor(browser, studio.url);

  await page.locator('#prompt').fill('96 BPM E minor dark Southern hip-hop instrumental');
  await page.locator('#btnCompile').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r1 = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  await page.locator('#btnOctaveEdit').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r2 = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);

  await page.route('**/api/projects/audio', async route => {
    const req = route.request();
    let body = {};
    try { body = req.postDataJSON(); } catch (_) {}
    if (body.revisionId === r1.revisionId) {
      await new Promise(resolve => setTimeout(resolve, 700));
    }
    await route.continue();
  });

  const first = page.locator('#btnABR1').click();
  await page.waitForTimeout(50);
  const second = page.locator('#btnABR2').click();
  await Promise.allSettled([first, second]);
  await page.waitForTimeout(1000);

  const selected = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  assert.equal(selected.revisionId, r2.revisionId);
  assert.equal(await page.locator('#abStatus').textContent(), 'Selected R2 · current');
});

test('A/B exposes completion only after transport, proof, artifact and position agree', { timeout: 150000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-ab-complete-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  const studio = await boot(workspace); t.after(studio.stop);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH }); t.after(() => browser.close());
  const page = await pageFor(browser, studio.url);

  await page.locator('#prompt').fill('96 BPM E minor dark Southern hip-hop instrumental');
  await page.locator('#btnCompile').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r1 = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  await page.locator('#btnOctaveEdit').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r2 = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);

  await page.locator('#btnABR1').click();
  await page.waitForFunction(
    id => window.__M044_AB_SWITCH__?.state === 'COMPLETE' &&
          window.__M044_AB_SWITCH__?.targetRevisionId === id,
    r1.revisionId,
    { timeout: 15000 }
  );
  const first = await page.evaluate(() => ({
    playback: window.__M044_PLAYBACK_PROOF__,
    ab: window.__M044_AB_PROOF__,
    sw: window.__M044_AB_SWITCH__
  }));
  assert.equal(first.playback.revisionId, r1.revisionId);
  assert.equal(first.ab.toRevisionId, r1.revisionId);
  assert.equal(first.sw.targetRevisionId, r1.revisionId);
  assert.equal(first.sw.artifactId, r1.artifactId);
  assert.ok(Math.abs(first.ab.fromPositionSec - first.ab.toPositionSec) <= 0.05);

  await page.locator('#btnABR2').click();
  await page.waitForFunction(
    id => window.__M044_AB_SWITCH__?.state === 'COMPLETE' &&
          window.__M044_AB_SWITCH__?.targetRevisionId === id,
    r2.revisionId,
    { timeout: 15000 }
  );
  const second = await page.evaluate(() => ({
    playback: window.__M044_PLAYBACK_PROOF__,
    ab: window.__M044_AB_PROOF__,
    sw: window.__M044_AB_SWITCH__
  }));
  assert.equal(second.playback.revisionId, r2.revisionId);
  assert.equal(second.ab.toRevisionId, r2.revisionId);
  assert.equal(second.sw.targetRevisionId, r2.revisionId);
  assert.equal(second.sw.artifactId, r2.artifactId);
  assert.ok(Math.abs(second.ab.fromPositionSec - second.ab.toPositionSec) <= 0.05);
});
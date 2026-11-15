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
  page.setDefaultTimeout(20000);
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.ScoreCore !== 'undefined');
  return page;
}

async function reachR2(page) {
  await page.locator('#prompt').fill('96 BPM E minor dark Southern hip-hop instrumental');
  await page.locator('#btnCompile').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  await page.locator('#btnOctaveEdit').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r2 = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  assert.ok(r2 && r2.revisionId);
  return r2;
}

test('audio fetch failure during A/B publishes FAILED and clears stale success Proof', { timeout: 180000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-ab-fail-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  const studio = await boot(workspace); t.after(studio.stop);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  t.after(() => browser.close());
  const page = await pageFor(browser, studio.url);

  const r2 = await reachR2(page);
  await page.locator('#btnPlay').click();
  await page.waitForFunction(() => window.__M044_PLAYBACK_STARTED__ === true);
  await page.waitForTimeout(200);
  await page.locator('#btnABR1').click();
  await page.waitForFunction(() => window.__M044_AB_SWITCH__?.state === 'COMPLETE', null, { timeout: 20000 });
  const successProof = await page.evaluate(() => window.__M044_AB_PROOF__);
  assert.ok(successProof && successProof.toRevisionId);
  assert.equal(await page.evaluate(() => window.__M044_AB_SWITCH__.state), 'COMPLETE');

  await page.route('**/api/projects/audio', async route => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'injected audio failure' })
    });
  });

  await page.locator('#btnABR2').click();
  await page.waitForTimeout(2500);

  const after = await page.evaluate(() => ({
    switchState: window.__M044_AB_SWITCH__ && window.__M044_AB_SWITCH__.state,
    abProof: window.__M044_AB_PROOF__,
    playbackProof: window.__M044_PLAYBACK_PROOF__,
    abStatus: document.querySelector('#abStatus') && document.querySelector('#abStatus').textContent,
    status: document.querySelector('#status') && document.querySelector('#status').textContent,
    playDisabled: document.querySelector('#btnPlay') && document.querySelector('#btnPlay').disabled
  }));

  assert.equal(after.switchState, 'FAILED',
    'A/B switch state must be FAILED after audio verification fails; got ' + after.switchState);
  assert.equal(after.abProof, null,
    'Stale successful A/B Proof must be cleared on terminal failure');
  assert.equal(after.playbackProof, null,
    'Playback Proof must not claim a successful target after failure');
  assert.equal(after.playDisabled, true, 'Play must remain disabled after failed A/B');
  assert.ok(/fail|unavailable|couldn.?t load/i.test(String(after.abStatus) + ' ' + String(after.status)),
    'UI must show a truthful failure label; got abStatus=' + after.abStatus + ' status=' + after.status);
});

test('stale failed generation must not erase newer successful A/B', { timeout: 180000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-ab-stale-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  const studio = await boot(workspace); t.after(studio.stop);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  t.after(() => browser.close());
  const page = await pageFor(browser, studio.url);

  await reachR2(page);
  await page.locator('#btnPlay').click();
  await page.waitForFunction(() => window.__M044_PLAYBACK_STARTED__ === true);

  let releaseFail;
  const failGate = new Promise(resolve => { releaseFail = resolve; });
  let audioCalls = 0;
  await page.route('**/api/projects/audio', async route => {
    audioCalls += 1;
    if (audioCalls === 1) {
      await failGate;
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'late injected failure' })
      });
      return;
    }
    await route.continue();
  });

  const p1 = page.locator('#btnABR1').click();
  await page.waitForFunction(() => window.__M044_AB_SWITCH__?.state === 'TARGET_LOADING', null, { timeout: 10000 });
  await page.locator('#btnABR2').click();
  await page.waitForTimeout(300);
  releaseFail();
  await Promise.allSettled([p1]);
  await page.waitForTimeout(1500);

  const final = await page.evaluate(() => ({
    switchState: window.__M044_AB_SWITCH__ && window.__M044_AB_SWITCH__.state,
    abProof: window.__M044_AB_PROOF__,
    playback: window.__M044_PLAYBACK_PROOF__
  }));

  assert.equal(final.switchState, 'COMPLETE',
    'Newer successful switch must remain COMPLETE; got ' + final.switchState);
  assert.ok(final.abProof && final.playback,
    'Successful newer switch must retain Proofs');
});

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

test('fresh server/browser preserves R2 current, R1/R2 history, exact WAVs and A/B', { timeout: 150000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-r2-cold-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));

  let studio = await boot(workspace);
  let browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  let page = await pageFor(browser, studio.url);

  await page.locator('#prompt').fill('96 BPM E minor dark Southern hip-hop instrumental');
  await page.locator('#btnCompile').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r1 = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  await page.locator('#btnOctaveEdit').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });
  const r2 = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);

  const currentBefore = await projectOpenInPage(page, { projectId: r2.projectId });
  assert.equal(currentBefore.status, 200);
  assert.equal(currentBefore.body.revision.revisionId, r2.revisionId);
  const histBefore = await projectOpenInPage(page, { projectId: r1.projectId, revisionId: r1.revisionId });
  assert.equal(histBefore.status, 200);
  assert.equal(histBefore.body.revision.revisionId, r1.revisionId);

  await page.close();
  await browser.close();
  await studio.stop();

  studio = await boot(workspace); t.after(studio.stop);
  browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH }); t.after(() => browser.close());
  page = await pageFor(browser, studio.url);

  await page.locator('#projectId').fill(r2.projectId);
  await page.locator('#btnOpenProject').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 90000 });

  const reopened = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  assert.equal(reopened.revisionId, r2.revisionId);
  assert.equal(reopened.artifactId, r2.artifactId);

  const currentAfter = await projectOpenInPage(page, { projectId: r2.projectId });
  assert.equal(currentAfter.status, 200);
  assert.equal(currentAfter.body.manifest.currentRevisionId, r2.revisionId);
  assert.equal(currentAfter.body.revision.revisionId, r2.revisionId);

  const histAfter = await projectOpenInPage(page, { projectId: r1.projectId, revisionId: r1.revisionId });
  assert.equal(histAfter.status, 200);
  assert.equal(histAfter.body.revision.revisionId, r1.revisionId);
  assert.equal(histAfter.body.revision.outputArtifactIds.filter(x => x === r1.artifactId).length, 1);

  const r2Bindings = currentAfter.body.revision.outputArtifactIds.filter(x => x === r2.artifactId);
  assert.equal(r2Bindings.length, 1);

  // Product must reconstruct A/B handles from backend revision lineage after cold reopen.
  assert.equal(await page.locator('#btnABR1').isDisabled(), false);
  assert.equal(await page.locator('#btnABR2').isDisabled(), false);

  await page.locator('#btnPlay').click();
  await page.waitForFunction(() => window.__M044_PLAYBACK_STARTED__ === true);
  await page.waitForTimeout(250);

  await page.locator('#btnABR1').click();
  await page.waitForFunction(id => window.__M044_PLAYBACK_PROOF__?.revisionId === id, r1.revisionId, { timeout: 15000 });
  const r1After = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  const ab1 = await page.evaluate(() => window.__M044_AB_PROOF__);
  assert.equal(r1After.artifactId, r1.artifactId);
  assert.equal(r1After.wavSha256, r1.wavSha256);
  assert.ok(Math.abs(ab1.fromPositionSec - ab1.toPositionSec) <= 0.05);

  await page.locator('#btnABR2').click();
  await page.waitForFunction(id => window.__M044_PLAYBACK_PROOF__?.revisionId === id, r2.revisionId, { timeout: 15000 });
  const r2After = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  const ab2 = await page.evaluate(() => window.__M044_AB_PROOF__);
  assert.equal(r2After.artifactId, r2.artifactId);
  assert.equal(r2After.wavSha256, r2.wavSha256);
  assert.ok(Math.abs(ab2.fromPositionSec - ab2.toPositionSec) <= 0.05);

  assert.equal(await page.locator('#abStatus').textContent(), 'Selected R2 · current');
});
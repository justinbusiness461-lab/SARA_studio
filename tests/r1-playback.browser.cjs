'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
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
  page.setDefaultTimeout(10000);
  await page.route('https://cdn.jsdelivr.net/**', route => route.abort());
  await page.goto(url);
  return page;
}

test('Generate reaches verified revision-bound WAV before Play is enabled', { timeout: 60000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-r1-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  const studio = await boot(workspace); t.after(studio.stop);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH }); t.after(() => browser.close());
  const page = await pageFor(browser, studio.url);

  assert.equal(await page.locator('#btnPlay').isDisabled(), true, 'Play must begin disabled');
  await page.locator('#prompt').fill('96 BPM E minor dark Southern hip-hop instrumental');

  const commitP = page.waitForResponse(r => r.url().endsWith('/api/projects/commit'));
  const renderP = page.waitForResponse(r => r.url().endsWith('/api/projects/render'));
  const audioP = page.waitForResponse(r => r.url().endsWith('/api/projects/audio'));
  await page.locator('#btnCompile').click();

  const commit = await commitP, render = await renderP, audio = await audioP;
  assert.equal(commit.status(), 200);
  assert.equal(render.status(), 200);
  assert.equal(audio.status(), 200);

  const rendered = await render.json();
  const bytes = await audio.body();
  const digest = crypto.createHash('sha256').update(bytes).digest('hex');
  const artifactId = rendered.revision.outputArtifactIds[0];
  assert.equal(digest, artifactId);
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.', null, { timeout: 15000 });
  assert.equal(await page.locator('#status').textContent(), 'Audio verified. Ready to hear.');
  assert.equal(await page.locator('#btnPlay').isDisabled(), false);

  const proof = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  assert.deepEqual(
    { projectId: proof.projectId, revisionId: proof.revisionId, artifactId: proof.artifactId, wavSha256: proof.wavSha256 },
    { projectId: rendered.manifest.projectId, revisionId: rendered.revision.revisionId, artifactId, wavSha256: digest }
  );
  await page.locator('#btnPlay').click();
  await page.waitForFunction(() => window.__M044_PLAYBACK_STARTED__ === true);
});

test('audio retrieval failure never presents Generate as playable', { timeout: 60000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-r1-deny-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  const studio = await boot(workspace); t.after(studio.stop);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH }); t.after(() => browser.close());
  const page = await pageFor(browser, studio.url);
  await page.route('**/api/projects/audio', route => route.fulfill({
    status: 403, contentType: 'application/json',
    body: JSON.stringify({ status: 'DENY', error: 'fixture denial' })
  }));
  await page.locator('#prompt').fill('96 BPM E minor dark Southern hip-hop instrumental');
  await page.locator('#btnCompile').click();
  await page.waitForResponse(r => r.url().endsWith('/api/projects/render'));
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Audio unavailable'));
  assert.equal(await page.locator('#btnPlay').isDisabled(), true);
  assert.equal(await page.evaluate(() => window.__M044_PLAYBACK_PROOF__ || null), null);
});

test('fresh Studio process reopens exact R1 and refetches same authorized WAV', { timeout: 90000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-r1-reopen-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  let browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  t.after(async () => { try { await browser.close(); } catch (_) {} });

  let studio = await boot(workspace);
  let page = await pageFor(browser, studio.url);
  await page.locator('#prompt').fill('96 BPM E minor dark Southern hip-hop instrumental');
  await page.locator('#btnCompile').click();
  await page.waitForFunction(() => document.querySelector('#status').textContent === 'Audio verified. Ready to hear.');
  const first = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);
  await page.close();
  await browser.close();
  await studio.stop();

  studio = await boot(workspace); t.after(studio.stop);
  browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  page = await pageFor(browser, studio.url);
  await page.locator('#projectId').fill(first.projectId);
  const openP = page.waitForResponse(r => r.url().endsWith('/api/projects/open'));
  const audioP = page.waitForResponse(r => r.url().endsWith('/api/projects/audio'));
  await page.locator('#btnOpenProject').click();
  const opened = await (await openP).json();
  const audio = await audioP;
  const bytes = await audio.body();
  const digest = crypto.createHash('sha256').update(bytes).digest('hex');
  const second = await page.evaluate(() => window.__M044_PLAYBACK_PROOF__);

  assert.equal(opened.revision.revisionId, first.revisionId);
  assert.equal(second.projectId, first.projectId);
  assert.equal(second.revisionId, first.revisionId);
  assert.equal(second.artifactId, first.artifactId);
  assert.equal(digest, first.wavSha256);
  assert.equal(await page.locator('#btnPlay').isDisabled(), false);
});
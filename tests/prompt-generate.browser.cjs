const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, resolve } = require('node:path');
const { once } = require('node:events');
const { createInterface } = require('node:readline');
const { test } = require('node:test');
const { chromium } = require('playwright');

const root = resolve(__dirname, '..');

async function startStudio(t, workspace) {
  const server = spawn('python3', ['-u', '-c', `
import socketserver
import sys
from pathlib import Path

sys.path.insert(0, "tools")
import studio_server as studio

studio.EXPORT_ROOT = Path(sys.argv[1])
with socketserver.TCPServer(("127.0.0.1", 0), studio.StudioHandler) as httpd:
    studio.PORT = httpd.server_address[1]
    print(studio.PORT, flush=True)
    httpd.serve_forever()
`, workspace], { cwd: root, stdio: ['ignore', 'pipe', 'inherit'] });
  const closed = once(server, 'close');
  t.after(async () => {
    server.kill();
    await closed;
  });
  const lines = createInterface({ input: server.stdout });
  const port = await Promise.race([
    once(lines, 'line').then(([line]) => Number(line)),
    closed.then(([code]) => { throw new Error(`Studio exited before startup: ${code}`); }),
  ]);
  lines.close();
  assert.ok(Number.isInteger(port) && port > 0, 'Studio must report its listening port');
  return `http://127.0.0.1:${port}`;
}

test('Studio loads ScoreCore, persists Generate, and reopens the exact revision', { timeout: 30000 }, async t => {
  const workspace = mkdtempSync(join(tmpdir(), 'songforge-browser-'));
  t.after(() => rmSync(workspace, { recursive: true, force: true }));
  const url = await startStudio(t, workspace);
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || undefined,
  });
  t.after(() => browser.close());
  const page = await browser.newPage({ serviceWorkers: 'block' });
  page.setDefaultTimeout(5000);
  // The remote Cinema dependency is outside the Generate workflow.
  await page.route('https://cdn.jsdelivr.net/**', route => route.abort());
  const scoreCoreResponse = page.waitForResponse(url + '/scorecore.js');
  await page.goto(url);
  assert.equal((await scoreCoreResponse).status(), 200, 'ScoreCore must be served by Studio');
  assert.equal(await page.evaluate(() => typeof window.ScoreCore?.compileIntent), 'function');

  const prompt = '96 BPM E minor dark Southern hip-hop instrumental';
  await page.locator('#prompt').fill(prompt);
  const commitResponse = page.waitForResponse(url + '/api/projects/commit');
  await page.locator('#btnCompile').click();
  const commit = await commitResponse;
  assert.equal(commit.status(), 200);
  const created = await commit.json();
  assert.equal(created.status, 'SUCCESS');
  assert.equal(created.songSpec.prompt, prompt);
  assert.equal(created.songSpec.timebase.initial_bpm, 96);
  assert.equal(created.songSpec.timebase.key, 'E minor');
  assert.equal(created.manifest.currentRevisionId, created.revision.revisionId);

  await page.reload();
  await page.locator('#projectId').fill(created.manifest.projectId);
  const openResponse = page.waitForResponse(url + '/api/projects/open');
  await page.locator('#btnOpenProject').click();
  const opened = await openResponse;
  assert.equal(opened.status(), 200);
  const reopened = await opened.json();
  assert.equal(reopened.revision.revisionId, created.revision.revisionId);
  assert.deepEqual(reopened.songSpec, created.songSpec);
});

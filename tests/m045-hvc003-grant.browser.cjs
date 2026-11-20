'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os');
const {join,resolve}=require('node:path');
const {once}=require('node:events');
const {createInterface}=require('node:readline');
const {chromium}=require('playwright');

test('HVC003 mobile grant: 48px truthful HTTP-503 and success without film proof, stale response discarded',
 {timeout:70000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'sara-hvc003-ui-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const server=spawn('python3',['-u','tests/m045_wave4_fixture_server.py',dir],
  {cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');
 t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [line]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('fixture unavailable')})]);
 lines.close();
 const fixture=JSON.parse(line);
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('http://127.0.0.1:'+fixture.port+'/');
 const btn=page.locator('#m045CreateMusicVideo');
 const box=await btn.boundingBox();
 assert.ok(box&&box.width>=48&&box.height>=48,JSON.stringify(box));
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
 await page.locator('#projectId').fill(fixture.projectId);
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(()=>window.__M044_PLAYBACK_PROOF__?.artifactId,{timeout:18000});
 await page.locator('#m045Wave4Section').focus();
 await page.locator('#m045Wave4Section').selectOption('verse1');
 await page.locator('#m045CinemaProjectId').fill('cinema-1');
 // Real localhost StudioHandler: without installed host key/rights, 503.
 const blocked=page.waitForResponse(r=>r.url().endsWith('/api/m045/soundtrack-grant'));
 await btn.click();
 assert.equal((await blocked).status(),503);
 await page.waitForFunction(()=>document.querySelector('#m045SoundtrackGrantStatus').textContent.includes('NOT ISSUED'));
 assert.match(await page.locator('#m045SoundtrackGrantStatus').innerText(),/unconfigured/i);
 assert.doesNotMatch(await page.locator('#m045SoundtrackGrantStatus').innerText(),/GRANT ISSUED/);
 const fake={schema_version:'sara.soundtrack.grant.v1',
  studio_project_id:fixture.projectId,source_project_revision_id:fixture.revisionId,
  accepted_audio_artifact_id:fixture.artifactId,cinema_project_id:'cinema-1',
  resolved_start_frame:0,resolved_end_frame_exclusive:22,signature:'a'.repeat(64)};
 // Simulated authorization reply below verifies *UI presentation only*.
 // The Python HTTP integration suite verifies actual host signing and rights.
 await page.route('**/api/m045/soundtrack-grant',r=>r.fulfill({status:200,
  contentType:'application/json',body:JSON.stringify(fake)}));
 await btn.click();
 await page.waitForFunction(()=>document.querySelector('#m045SoundtrackGrantStatus').textContent.includes('GRANT ISSUED'));
 const issued=await page.locator('#m045SoundtrackGrantStatus').innerText();
 assert.match(issued,/Film NOT created or verified/);
 assert.doesNotMatch(issued,/movie completed|approved|PHYSICALLY VERIFIED/i);
 await page.unroute('**/api/m045/soundtrack-grant');
 let release;
 const delayed=new Promise(resolve=>{release=resolve;});
 let gotRequest;
 const didRequest=new Promise(resolve=>{gotRequest=resolve;});
 await page.route('**/api/m045/soundtrack-grant',async route=>{
  gotRequest();
  await delayed;
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fake)});
 });
 await btn.click();
 await didRequest;
 assert.match(await page.locator('#m045SoundtrackGrantStatus').innerText(),/Checking/);
 const response=page.waitForResponse(r=>r.url().endsWith('/api/m045/soundtrack-grant'));
 await page.locator('#btnNewProject').click();
 release();await response;
 await page.waitForFunction(()=>document.querySelector('#m045SoundtrackGrantStatus').textContent.includes('NOT ISSUED'),null,{timeout:5000});
 const stale=await page.locator('#m045SoundtrackGrantStatus').innerText();
 assert.doesNotMatch(stale,/GRANT ISSUED|Checking|Film created/);
 assert.deepEqual(errors,[]);
});

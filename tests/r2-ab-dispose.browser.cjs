'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os');
const {resolve,join}=require('node:path');
const {once}=require('node:events');
const {createInterface}=require('node:readline');
const {chromium}=require('playwright');

test('R1/R2 A/B releases old verified WAV decoders without losing 50ms position or revision authority',{timeout:80000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'sara-ab-dispose-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const server=spawn('python3',['-u','tests/platform_ab_source_fixture.py',dir],{
   cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');
 t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [header]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('fixture exited')})]);lines.close();
 const fixture=JSON.parse(header);
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.addInitScript(()=>{
  window.__TRACKED_AUDIO=[];
  const AudioClass=window.Audio;
  window.Audio=class extends AudioClass {
   constructor(...args){super(...args);window.__TRACKED_AUDIO.push(this);}
  };
 });
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 await page.goto('http://127.0.0.1:'+fixture.port);
 await page.locator('#platformHandle').fill('ab_diagnostic');
 await page.locator('#platformPassword').fill('synthetic test passphrase 2026');
 await page.locator('#platformSignIn').click();
 await page.waitForFunction(()=>document.body.classList.contains('platform-signed-in'));
 await page.locator('#platformNavStudio').click();
 await page.locator('#projectId').fill(fixture.projectId);
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(id=>window.__M044_PLAYBACK_PROOF__?.revisionId===id,
    fixture.current.revisionId,{timeout:25000});
 const before=await page.evaluate(()=>window.__TRACKED_AUDIO.length);
 assert.ok(before>=1,'real WAV decoder was created for current revision');
 await page.locator('#dockPlay').click();
 await page.waitForFunction(()=>window.__M044_PLAYBACK_STARTED__===true);
 await page.waitForTimeout(220);
 await page.locator('#btnABR1').click();
 await page.waitForFunction(id=>window.__M044_AB_SWITCH__?.state==='COMPLETE'&&
    window.__M044_PLAYBACK_PROOF__?.revisionId===id,fixture.historical.revisionId,{timeout:18000});
 const first=await page.evaluate(()=>({
  stale:window.__TRACKED_AUDIO.slice(0,-1).map(media=>({
    hasSource:!!media.getAttribute('src'),readyState:media.readyState,networkState:media.networkState})),
  switch:window.__M044_AB_SWITCH__,ab:window.__M044_AB_PROOF__,
 }));
 assert.ok(first.stale.length>0);
 assert.ok(first.stale.every(x=>!x.hasSource&&x.networkState===0),
    'stale WAV decoder remains attached after switch: '+JSON.stringify(first.stale));
 assert.ok(Math.abs(first.ab.fromPositionSec-first.ab.toPositionSec)<=0.05);
 await page.locator('#btnABR2').click();
 await page.waitForFunction(id=>window.__M044_AB_SWITCH__?.state==='COMPLETE'&&
    window.__M044_PLAYBACK_PROOF__?.revisionId===id,fixture.current.revisionId,{timeout:18000});
 const second=await page.evaluate(()=>({
  stale:window.__TRACKED_AUDIO.slice(0,-1).map(media=>({
    hasSource:!!media.getAttribute('src'),networkState:media.networkState})),
  proof:window.__M044_PLAYBACK_PROOF__,ab:window.__M044_AB_PROOF__,
 }));
 assert.ok(second.stale.every(x=>!x.hasSource&&x.networkState===0),
     JSON.stringify(second.stale));
 assert.equal(second.proof.artifactId,fixture.current.digest);
 assert.ok(Math.abs(second.ab.fromPositionSec-second.ab.toPositionSec)<=0.05);
});


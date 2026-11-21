'use strict';
const test=require('node:test'), assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),{mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os'),{join,resolve}=require('node:path');
const {once}=require('node:events'),{createInterface}=require('node:readline');
const {chromium}=require('playwright');
test('Round14 revision waveform markers, revocable preview and release package on 390px touchscreen', {timeout:110000}, async t=>{
 const dir=mkdtempSync(join(tmpdir(),'sara-r14-browser-')); t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const srv=spawn('python3',['-u','tests/platform_release_fixture.py',dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(srv,'close');t.after(async()=>{if(srv.exitCode===null)srv.kill('SIGKILL');await closed;});
 const lines=createInterface({input:srv.stdout});
 const [first]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('fixture exited')})]);lines.close();
 const f=JSON.parse(first);
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 await page.goto('http://127.0.0.1:'+f.port+'/');
 await page.locator('#platformHandle').fill('release_artist');
 await page.locator('#platformPassword').fill('test-only strong passphrase 2026');
 await page.locator('#platformSignIn').click();
 await page.waitForFunction(()=>document.body.classList.contains('platform-signed-in'));
 await page.locator('#platformNavStudio').click();
 await page.locator('#projectId').fill(f.projectId);
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(()=>window.__M044_PLAYBACK_PROOF__?.artifactId!==undefined,{timeout:35000});
 await page.locator('#platformR14Tools summary').click();
 const touch=await page.evaluate(()=>({
   controls:[...document.querySelectorAll('#platformR14Tools button')].map(e=>({id:e.id,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height})),
   timeline:document.getElementById('platformWaveformMarkersCanvas').getBoundingClientRect().height,
   overflow:document.documentElement.scrollWidth>innerWidth+1
 }));
 assert.ok(touch.controls.length>=4,JSON.stringify(touch));
 assert.ok(touch.controls.every(x=>x.width>=48&&x.height>=48),JSON.stringify(touch));
 assert.ok(touch.timeline>=48,JSON.stringify(touch));assert.equal(touch.overflow,false);
 await page.locator('#platformFeedbackPosition').fill('100');
 await page.locator('#platformFeedbackBeat').fill('bar 1 beat 1');
 await page.locator('#platformFeedbackBody').fill('Move snare');
 await page.locator('#platformFeedbackAdd').click();
 await page.waitForFunction(()=>document.querySelectorAll('#platformWaveformMarkers li').length===1,{timeout:10000});
 assert.match(await page.locator('#platformWaveformMarkers').innerText(),/Move snare/);
 await page.locator('#platformPreviewCreate').click();
 await page.waitForFunction(()=>document.getElementById('platformPreviewShareUrl').value.includes('token='),{timeout:10000});
 const url=await page.locator('#platformPreviewShareUrl').inputValue();
 assert.equal(await page.evaluate(async x=>(await fetch(x,{cache:'no-store'})).status,url),200);
 await page.locator('#platformPreviewRevoke').click();
 await page.waitForFunction(()=>document.getElementById('platformPreviewStatus').textContent.includes('REVOKED'),{timeout:10000});
 assert.equal(await page.evaluate(async x=>(await fetch(x,{cache:'no-store'})).status,url),403);
 await page.locator('#platformReleaseTitle').fill('Public Release Fixture');
 await page.locator('#platformReleaseGenre').fill('Outlaw Hypno-Rock Country-Hop');
 await page.locator('#platformReleaseCover').fill('b'.repeat(64));
 page.on('dialog',d=>d.accept());
 await page.locator('#platformReleasePrepare').click();
 await page.waitForFunction(()=>document.getElementById('platformReleaseStatus').textContent.includes('PREPARED_ONLY'),{timeout:15000});
 assert.match(await page.locator('#platformReleaseStatus').innerText(),/not published/i);
 assert.deepEqual(errors,[]);
});

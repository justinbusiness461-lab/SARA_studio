'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os');
const {join,resolve}=require('node:path');
const {once}=require('node:events');
const {createInterface}=require('node:readline');
const {chromium}=require('playwright');

const root=resolve(__dirname,'..');
async function boot(workspace){
 const py=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")',
 'import studio_server as s','s.EXPORT_ROOT=Path(sys.argv[1])','socketserver.TCPServer.allow_reuse_address=True',
 'with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
 ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const server=spawn('python3',['-u','-c',py,workspace],{cwd:root,stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');
 const lines=createInterface({input:server.stdout});
 const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('Studio failed startup')})]);lines.close();
 return {url:'http://127.0.0.1:'+port,stop:async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;}};
}
const proof=page=>page.evaluate(()=>window.__M044_PLAYBACK_PROOF__);
const abProof=page=>page.evaluate(()=>window.__M044_AB_PROOF__);
async function ready(page){await page.waitForFunction(()=>document.querySelector('#status').textContent==='Audio verified. Ready to hear.',null,{timeout:90000});return proof(page);}

test('RS-002 mobile 390px R1→R2→A/B→Proof→Restore, stale switch and failed reopen', {timeout:150000},async t=>{
 const workspace=mkdtempSync(join(tmpdir(),'sara-mobile-endurance-'));t.after(()=>rmSync(workspace,{recursive:true,force:true}));
 const studio=await boot(workspace);t.after(studio.stop);
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());await page.goto(studio.url);
 await page.locator('#prompt').fill('92 BPM E minor smoke country guitar groove');
 await page.locator('#studioModeChat').click();await page.locator('#btnCompile').click();const r1=await ready(page);
 assert.ok(r1?.projectId&&r1?.artifactId&&r1?.revisionId);
 assert.equal(await page.locator('#studioWaveformPreview').getAttribute('data-artifact-id'),r1.artifactId);
 await page.locator('#studioModeDj').click();
 const pads=page.locator('#djGrid .cell');assert.equal(await pads.count(),16);
 const padBounds=await pads.first().boundingBox();assert.ok(padBounds.width>=48&&padBounds.height>=48);
 const columns=await page.locator('#djGrid').evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length);
 assert.equal(columns,8,'mobile scratch grid must use two rows of eight pads');
 const lock=await page.locator('[data-lock]').first().boundingBox();assert.ok(lock.width>=48&&lock.height>=48);
 await page.locator('#studioModeChat').click();assert.equal(r1.wavSha256,r1.artifactId);
 await page.locator('#dockChangeOnly').click();
 await page.locator('#btnOctaveEdit').click();const r2=await page.waitForFunction(old=>window.__M044_PLAYBACK_PROOF__?.revisionId!==old&&document.querySelector('#status').textContent==='Audio verified. Ready to hear.',r1.revisionId,{timeout:90000}).then(()=>proof(page));
 assert.equal(r2.projectId,r1.projectId);assert.notEqual(r2.revisionId,r1.revisionId);assert.equal(r2.wavSha256,r2.artifactId);
 assert.equal(await page.locator('#btnABR1').isDisabled(),false);assert.equal(await page.locator('#btnABR2').isDisabled(),false);
 await page.locator('#dockPlay').click();await page.waitForFunction(()=>window.__M044_PLAYBACK_STARTED__===true);
 await page.waitForTimeout(220);await page.locator('#btnABR1').click();await page.waitForFunction(id=>window.__M044_AB_SWITCH__?.state==='COMPLETE'&&window.__M044_PLAYBACK_PROOF__?.revisionId===id,r1.revisionId,{timeout:15000});
 const ab1=await abProof(page);assert.equal(ab1.toRevisionId,r1.revisionId);assert.ok(Math.abs(ab1.fromPositionSec-ab1.toPositionSec)<=0.05);
 await page.locator('#btnABR2').click();await page.waitForFunction(id=>window.__M044_AB_SWITCH__?.state==='COMPLETE'&&window.__M044_PLAYBACK_PROOF__?.revisionId===id,r2.revisionId,{timeout:15000});
 const ab2=await abProof(page);assert.equal(ab2.toRevisionId,r2.revisionId);assert.ok(Math.abs(ab2.fromPositionSec-ab2.toPositionSec)<=0.05);
 await page.locator('#dockStop').click();
 await page.reload();await page.locator('#studioModeWorkstream').click();await page.locator('#btnOpenProject').click();
 await page.waitForFunction(id=>window.__M044_PLAYBACK_PROOF__?.revisionId===id,r2.revisionId,{timeout:15000});
 assert.equal((await proof(page)).artifactId,r2.artifactId);
 assert.equal(await page.locator('#studioWaveformPreview').getAttribute('data-artifact-id'),r2.artifactId);
 await page.locator('#btnABR1').click();await page.waitForFunction(id=>window.__M044_AB_SWITCH__?.state==='COMPLETE'&&window.__M044_PLAYBACK_PROOF__?.revisionId===id,r1.revisionId,{timeout:15000});
 await page.locator('#btnABR2').click();await page.waitForFunction(id=>window.__M044_AB_SWITCH__?.state==='COMPLETE'&&window.__M044_PLAYBACK_PROOF__?.revisionId===id,r2.revisionId,{timeout:15000});
 assert.equal((await proof(page)).artifactId,r2.artifactId);
 // Interrupted selection: a rejected new open must not leave the old proof playable.
 await page.route('**/api/projects/open',async route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({status:'ERROR',error:'RS002 injected outage'})}));
 await page.locator('#btnOpenProject').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('RS002 injected outage'));
 assert.equal(await proof(page),null);assert.equal(await abProof(page),null);assert.equal(await page.locator('#dockPlay').isDisabled(),true);
 await page.unroute('**/api/projects/open');await page.locator('#btnOpenProject').click();await page.waitForFunction(id=>window.__M044_PLAYBACK_PROOF__?.revisionId===id,r2.revisionId,{timeout:15000});
 assert.equal((await proof(page)).artifactId,r2.artifactId);
 // Actual authoritative current pointer never left R2 during historical A/B.
 const backend=await page.evaluate(async projectId=>{const r=await fetch('/api/projects/open',{method:'POST',headers:{'Content-Type':'application/json','X-Studio-Capability':window.__STUDIO_CAPABILITY__||'','X-Studio-Session':window.__STUDIO_SESSION__||''},body:JSON.stringify({projectId})});return r.json();},r2.projectId);
 assert.equal(backend.manifest.currentRevisionId,r2.revisionId);
});
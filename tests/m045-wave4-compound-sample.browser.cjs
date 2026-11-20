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
async function serverBoot(dir){
 const py=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")','import studio_server as s',
 's.EXPORT_ROOT=Path(sys.argv[1])','with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
 ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const server=spawn('python3',['-u','-c',py,dir],{cwd:root,stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');
 const lines=createInterface({input:server.stdout});
 const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('server exited before listening')})]);lines.close();
 return {url:'http://127.0.0.1:'+port,stop:async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed}};
}

test('Wave004 390px operator requests lawful plans and sample previews without current revision mutation',{timeout:150000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'sara-wave4-ui-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const srv=await serverBoot(dir);t.after(srv.stop);
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 await page.goto(srv.url);
 const ids=['m045Wave4CompoundBtn','m045Wave4SampleSlice','m045Wave4SampleBass','m045Wave4SampleMetal'];
 for(const id of ids){
  const bounds=await page.locator('#'+id).boundingBox();assert.ok(bounds&&bounds.width>=48&&bounds.height>=48,'touch target '+id);
 }
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
 await page.locator('#prompt').fill('90 BPM A minor groovy Southern baritone guitar bass and drums');
 await page.locator('#btnCompile').click();
 await page.waitForFunction(()=>window.__M044_PLAYBACK_PROOF__?.artifactId&&document.querySelector('#status').textContent==='Audio verified. Ready to hear.',null,{timeout:90000});
 const r1=await page.evaluate(()=>window.__M044_PLAYBACK_PROOF__);
 await page.locator('#m045Wave4CompoundIntent').fill('make the bass darker');
 await page.locator('#m045Wave4CompoundBtn').click();
 await page.waitForFunction(()=>document.querySelector('#m045Wave4PlanResult').textContent.includes('NON_AUTHORITATIVE_COMPOUND_PLAN'),null,{timeout:15000});
 const plan=await page.locator('#m045Wave4PlanResult').innerText();assert.match(plan,/"kind": "NON_AUTHORITATIVE_COMPOUND_PLAN"/);
 assert.match(plan,/"revisionCommitted": false|"projectRevisionCommitted": false/);
 await page.locator('#m045Wave4SampleSlice').click();
 await page.waitForFunction(()=>document.querySelector('#m045Wave4PlanResult').textContent.includes('NON_AUTHORITATIVE_SAMPLE_PREVIEW'),null,{timeout:15000});
 const selected=await page.evaluate(()=>({revision:window.__M044_PLAYBACK_PROOF__?.revisionId,candidate:document.querySelector('#m045Wave4SampleAudio').dataset.previewDigest,src:document.querySelector('#m045Wave4SampleAudio').src}));
 assert.equal(selected.revision,r1.revisionId);assert.match(selected.candidate,/^[a-f0-9]{64}$/);assert.match(selected.src,/^blob:/);
 // Distinct DSP effects must remain preview-only while original R1 stays selected.
 for(const id of ['m045Wave4SampleBass','m045Wave4SampleMetal']){
  await page.locator('#'+id).click();
  await page.waitForFunction(()=>document.querySelector('#m045Wave4ExtraStatus').textContent.includes('UNPUBLISHED SAMPLE PREVIEW'),null,{timeout:15000});
  assert.equal(await page.evaluate(()=>window.__M044_PLAYBACK_PROOF__?.revisionId),r1.revisionId);
  assert.match(await page.locator('#m045Wave4PlanResult').innerText(),/UNVERIFIED_HELD/);
 }
 await page.reload();
 assert.ok(await page.evaluate(()=>!document.querySelector('#m045Wave4SampleAudio').getAttribute('src')));
 await page.locator('#studioModeWorkstream').click();await page.locator('#btnOpenProject').click();
 await page.waitForFunction(id=>window.__M044_PLAYBACK_PROOF__?.revisionId===id,r1.revisionId,{timeout:15000});
 assert.equal(await page.evaluate(()=>window.__M044_PLAYBACK_PROOF__?.artifactId),r1.artifactId);
});
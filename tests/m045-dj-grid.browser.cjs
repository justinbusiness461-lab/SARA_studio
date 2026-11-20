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
const {installQaLongtasks,qaSnapshot}=require('./qa-longtasks.cjs');

test('Scratch Surgeon grid saves exact DJ event and restores via canonical revision',{timeout:90000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'djgrid-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const py=[
  'import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")',
  'import studio_server as s','s.EXPORT_ROOT=Path(sys.argv[1])',
  'with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
  ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'
 ].join('\n');
 const srv=spawn('python3',['-u','-c',py,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const done=once(srv,'close');
 t.after(async()=>{if(srv.exitCode===null)srv.kill('SIGKILL');await done;});
 const reader=createInterface({input:srv.stdout});
 const [port]=await Promise.race([once(reader,'line'),done.then(()=>{throw Error('server exited')})]);
 reader.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage({serviceWorkers:'block'});
 await installQaLongtasks(page);
 page.setDefaultTimeout(12000);
 await page.goto('http://127.0.0.1:'+port);
 await page.locator('#prompt').fill('94 BPM F# minor southern drum scratch');
 const commit=page.waitForResponse(r=>r.url().endsWith('/api/projects/commit'));
 // The 12s render-response budget begins when the render request is sent,
 // not before the preceding project commit. No deadline is enlarged.
 const renderRequested=page.waitForRequest(r=>r.url().endsWith('/api/projects/render'),{timeout:12000});
 await page.locator('#btnCompile').click();
 assert.equal((await commit).status(),200);
 const renderRequest=await renderRequested;
 let timeout;
 try{
   const result=await Promise.race([
     renderRequest.response(),
     new Promise((_,reject)=>{
       timeout=setTimeout(()=>reject(new Error('Render response exceeded original 12000ms phase budget')),12000);
     })
   ]);
   assert.ok(result,'render request completed without an HTTP response');
   assert.equal(result.status(),200);
 }finally{clearTimeout(timeout);}
 await page.waitForFunction(()=>document.querySelector('#projectRevision').textContent.includes('Saved revision'));
 const before=await page.locator('#projectRevision').innerText();
 try { await page.locator('#djDeck').selectOption('A'); }
 catch(error){console.log('DJ_ACTIVE_MEDIA_LONGTASKS',JSON.stringify(await qaSnapshot(page)));throw error;}
 await page.locator('#djTechnique').selectOption('chirp');
 await page.locator('[data-dj-step="3"]').click();
 const marker=await page.evaluate(()=>{
  const t=window.skeleton.tracks.find(t=>t.track_id==='dj_scratch');
  return t && t.events[0];
 });
 assert.equal(marker.type,'DJ_SCRATCH_MARKER');
 assert.equal(marker.technique,'chirp');
 assert.equal(marker.audio_status,'UNRENDERED_SOURCE_ASSET_REQUIRED');
 assert.equal(await page.locator('#projectRevision').innerText(),before);
 assert.match(await page.locator('#djGridStatus').innerText(),/UNRENDERED/);
 const saved=page.waitForResponse(r=>r.url().endsWith('/api/projects/commit'));
 await page.locator('#btnSave').click();
 assert.equal((await saved).status(),200);
 // The HTTP response can resolve before the UI installs the saved revision.
 // Assert observable committed authority, not a scheduling coincidence.
 await page.waitForFunction(previous =>
   document.querySelector('#projectRevision').textContent !== previous, before);
 const after=await page.locator('#projectRevision').innerText();
 assert.notEqual(after,before);
 await page.reload();
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(()=>!!window.skeleton?.tracks?.find(t=>t.track_id==='dj_scratch')?.events?.length);
 const restored=await page.evaluate(()=>window.skeleton.tracks.find(t=>t.track_id==='dj_scratch').events[0]);
 assert.deepEqual(JSON.parse(JSON.stringify(restored)),JSON.parse(JSON.stringify(marker)));
 await page.locator('#djDeck').selectOption('B');
 await page.locator('#djTechnique').selectOption('baby');
 await page.locator('[data-dj-step="3"]').click();
 assert.equal(await page.evaluate(()=>window.skeleton.tracks.find(t=>t.track_id==='dj_scratch').events.length),2);
});

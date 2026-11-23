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

async function studioFixture(t){
 const dir=mkdtempSync(join(tmpdir(),'r12-ux-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const py=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")',
  'import studio_server as s','s.EXPORT_ROOT=Path(sys.argv[1])',
  'with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
  ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const server=spawn('python3',['-u','-c',py,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');
 t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const reader=createInterface({input:server.stdout});
 const [port]=await Promise.race([once(reader,'line'),closed.then(()=>{throw Error('server stopped')})]);
 reader.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 return {browser,url:'http://127.0.0.1:'+port};
}

test('R12-A: six viewports keep accessible zoom, thumb dock and 3-column wide composition',{timeout:110000},async t=>{
 const {browser,url}=await studioFixture(t);
 for(const [width,height] of [[390,844],[430,932],[640,900],[768,900],[1024,768],[1440,900]]){
  const page=await browser.newPage({viewport:{width,height},serviceWorkers:'block'});
  await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
  await page.goto(url);
  const view=await page.evaluate(()=>({
   viewport:document.querySelector('meta[name=viewport]').content,
   cols:getComputedStyle(document.querySelector('.app')).gridTemplateColumns.split(' ').filter(Boolean).length,
   appWidth:document.querySelector('.app').getBoundingClientRect().width,
   scrollWidth:document.documentElement.scrollWidth,
   innerWidth,
   docks:[...document.querySelectorAll('#studioThumbDock button')].map(e=>({w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}))
  }));
  assert.doesNotMatch(view.viewport,/user-scalable=no|maximum-scale=1/);
  assert.ok(view.scrollWidth<=view.innerWidth+1,JSON.stringify({width,view}));
  if(width>=1024){assert.equal(view.cols,3,JSON.stringify({width,view})); assert.ok(view.appWidth>560);}
  for(const b of view.docks) assert.ok(b.w>=47.5&&b.h>=47.5,JSON.stringify({width,b}));
  await page.close();
 }
});

test('R12-B: PCM level never advertises playback until authorized WAV plays; generation stages never fake approval',{timeout:130000},async t=>{
 const {browser,url}=await studioFixture(t);
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 await page.goto(url);
 const stages=page.locator('#studioGenerationJourney [data-generation-stage]');
 assert.equal(await stages.count(),8);
 assert.match(await page.locator('#studioGenerationJourney').innerText(),/No paid provider execution authorized/i);
 assert.equal(await page.locator('#studioPcmLevel').getAttribute('data-state'),'idle');
 assert.equal(await page.locator('#studioPcmLevel').getAttribute('data-artifact-id'),null);
 await page.locator('#prompt').fill('96 BPM F# minor melodic southern rock');
 const render=page.waitForResponse(r=>r.url().endsWith('/api/projects/render'));
 await page.locator('#btnCompile').click();
 assert.equal((await render).status(),200);
 await page.waitForFunction(()=>document.getElementById('studioWaveformPreview').dataset.artifactId);
 assert.equal(await page.locator('#studioPcmLevel').getAttribute('data-state'),'idle');
 const verified=await page.locator('#studioWaveformPreview').getAttribute('data-artifact-id');
 await page.locator('#dockPlay').click();
 await page.waitForFunction(()=>document.getElementById('studioPcmLevel').dataset.state==='playing');
 assert.equal(await page.locator('#studioPcmLevel').getAttribute('data-artifact-id'),verified);
 await page.locator('#dockStop').click();
 await page.waitForFunction(()=>document.getElementById('studioPcmLevel').dataset.state==='idle');
 assert.equal(await page.locator('#studioPcmLevel').getAttribute('data-artifact-id'),null);
 assert.doesNotMatch(await page.locator('#studioGenerationJourney').innerText(),/creatively approved|provider charged/i);
 await page.close();
});


test('R12-C: committed receipt never claims new audio playable or creative approval without authoritative WAV',{timeout:90000},async t=>{
 const {browser,url}=await studioFixture(t);
 const page=await browser.newPage({viewport:{width:1024,height:768},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 await page.goto(url);
 await page.locator('#prompt').fill('94 BPM F# minor Southern hip hop guitar');
 const render=page.waitForResponse(r=>r.url().endsWith('/api/projects/render'));
 await page.locator('#btnCompile').click();
 assert.equal((await render).status(),200);
 await page.waitForFunction(()=>document.getElementById('studioWaveformPreview').dataset.artifactId);
 const original=await page.evaluate(()=>window.__M044_PLAYBACK_PROOF__.revisionId);
 await page.route('**/api/m045/attempts',async route=>{
  const payload=route.request().postDataJSON();
  await new Promise(r=>setTimeout(r,450));
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
   state:'COMMITTED',attempt:{idempotency_key:payload.idempotency_key,
   provenance:{provider_id:'controlled_test_only',rights_status:'UNVERIFIED_HELD',preservation_tier:'P3'}}
  })});
 });
 await page.locator('#btnM045Generate').click();
 await page.waitForFunction(()=>document.getElementById('studioGenerationJourney').dataset.activeStage==='PROCESSING');
 assert.match(await page.locator('#studioGenerationNote').innerText(),/GPU status unknown/);
 await page.waitForFunction(()=>document.getElementById('studioGenerationJourney').dataset.activeStage==='CANDIDATE');
 assert.match(await page.locator('#studioGenerationNote').innerText(),/reopen and verify WAV/);
 assert.equal(await page.evaluate(()=>window.__M044_PLAYBACK_PROOF__.revisionId),original);
 assert.equal(await page.locator('[data-generation-stage="APPROVE"]').getAttribute('data-stage-status'),'pending');
 await page.close();
});

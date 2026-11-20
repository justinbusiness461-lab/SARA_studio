'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),{mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os'),{join,resolve}=require('node:path');
const {once}=require('node:events'),{createInterface}=require('node:readline');
const {chromium}=require('playwright');
test('Wave004 six viewport shell shows truthful P3 candidate, studio-only preview, mastering preset',{timeout:100000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'m045-wave4-ui-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const py=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")','import studio_server as s','s.EXPORT_ROOT=Path(sys.argv[1])',
  'with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const server=spawn('python3',['-u','-c',py,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('server stopped')})]);lines.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 for(const [width,height] of [[360,800],[390,844],[412,915],[768,1024],[1024,768],[1440,900]]){
  const page=await browser.newPage({viewport:{width,height},serviceWorkers:'block'});
  await page.route('https://cdn.jsdelivr.net/**',route=>route.abort());
  await page.goto('http://127.0.0.1:'+port+'/');
  for(const id of ['m045Wave4Preview','m045Wave4Transcribe','m045Wave4Master','m045Wave4Preset','m045Wave4Status']){
   assert.equal(await page.locator('#'+id).count(),1,'missing '+id+' at '+width);
  }
  const shape=await page.evaluate(()=>({
   width:document.documentElement.scrollWidth,innerWidth,
   buttons:['m045Wave4Preview','m045Wave4Transcribe','m045Wave4Master'].map(id=>{const b=document.getElementById(id).getBoundingClientRect();return [b.width,b.height];}),
   status:document.getElementById('m045Wave4Status').textContent
  }));
  assert.ok(shape.width<=width+1,'overflow '+width+': '+JSON.stringify(shape));
  for(const [w,h] of shape.buttons) assert.ok(w>=48&&h>=48,'touch target '+width+': '+JSON.stringify(shape));
  assert.match(shape.status,/P3|UNVERIFIED/i);
  assert.doesNotMatch(shape.status,/P0 verified|RELEASE CLEARED/i);
  await page.close();
 }
});

test('Wave004 real authorized artist journey: FM preview, P3 estimate, mastered immutable R3',{timeout:90000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'m045-wave4-live-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const server=spawn('python3',['-u','tests/m045_wave4_fixture_server.py',dir],
   {cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');
 t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [line]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('fixture server stopped')})]);
 lines.close();
 const fixture=JSON.parse(line);
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',route=>route.abort());
 await page.goto('http://127.0.0.1:'+fixture.port+'/');
 await page.locator('#projectId').fill(fixture.projectId);
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(()=>!document.getElementById('dockPlay').disabled,{timeout:20000});
 assert.match(await page.locator('#studioHeaderRevision').textContent(),/^[a-f0-9]{12}$/);
 const calls=[];
 page.on('response',r=>{if(r.url().includes('/api/m045/'))calls.push([r.url().split('/').pop(),r.status()]);});
 await page.locator('#m045Wave4Preview').click();
 await page.waitForFunction(()=>document.getElementById('m045Wave4Status').textContent.includes('FM PREVIEW'),{timeout:25000});
 assert.match(await page.locator('#m045Wave4Audio').getAttribute('src'),/^blob:/);
 await page.locator('#m045Wave4Transcribe').click();
 await page.waitForFunction(()=>document.getElementById('m045Wave4Status').textContent.includes('P3 MIDI CANDIDATE'),{timeout:25000});
 assert.doesNotMatch(await page.locator('#m045Wave4Status').innerText(),/P0 verified/i);
 const master=page.waitForResponse(r=>r.url().endsWith('/api/m045/master'),{timeout:30000});
 await page.locator('#m045Wave4Master').click();
 const response=await master;
 assert.equal(response.status(),200,await response.text());
 const receipt=await response.json();
 await page.waitForFunction(()=>document.getElementById('m045Wave4Status').textContent.includes('Master revision VERIFIED'),{timeout:25000});
 const header=await page.locator('#studioHeaderRevision').innerText();
 assert.equal(header,receipt.revisionId.slice(0,12));
 assert.notEqual(receipt.revisionId,fixture.revisionId);
 assert.equal(receipt.rightsStatus,'UNVERIFIED_HELD');
 assert.equal(receipt.telemetry.true_peak_verified,true);
 assert.deepEqual(calls.slice(0,3).map(a=>a[0]),['preview-synth','transcribe-midi','master']);
 assert.deepEqual(calls.slice(0,3).map(a=>a[1]),[200,200,200]);
});

test('Wave004 unsaved mobile project fails visibly instead of rejecting a promise',{timeout:20000},async end=>{
 const dir=mkdtempSync(join(tmpdir(),'wave4-no-project-'));end.after(()=>rmSync(dir,{recursive:true,force:true}));
 const py=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")',
  'import studio_server as s','s.EXPORT_ROOT=Path(sys.argv[1])',
  'with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
  ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const server=spawn('python3',['-u','-c',py,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');end.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('server stopped')})]);lines.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});end.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('http://127.0.0.1:'+port+'/');
 await page.locator('#m045Wave4Master').click();
 await page.waitForTimeout(250);
 assert.match(await page.locator('#m045Wave4Status').innerText(),/NOT VERIFIED.*Save or open/);
 assert.deepEqual(errors,[]);
});

test('Wave004 corrupted mastered WAV cannot become verified merely because commit succeeded',{timeout:35000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'wave4-corrupt-after-master-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const server=spawn('python3',['-u','tests/m045_wave4_fixture_server.py',dir],
   {cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [line]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('fixture server stopped')})]);lines.close();
 const fixture=JSON.parse(line);
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 let corruptAfterMaster=false;
 page.on('request',r=>{if(r.url().endsWith('/api/m045/master'))corruptAfterMaster=true;});
 await page.route('**/api/projects/audio',r=>corruptAfterMaster?
   r.fulfill({status:200,contentType:'audio/wav',body:'deliberately-corrupted-wav'}):r.continue());
 await page.goto('http://127.0.0.1:'+fixture.port+'/');
 await page.locator('#projectId').fill(fixture.projectId);
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(()=>!document.getElementById('dockPlay').disabled,{timeout:15000});
 const receipt=page.waitForResponse(r=>r.url().endsWith('/api/m045/master'),{timeout:20000});
 await page.locator('#m045Wave4Master').click();
 assert.equal((await receipt).status(),200);
 await page.waitForFunction(()=>/Master revision|audio UNVERIFIED|reopen/i.test(document.getElementById('m045Wave4Status').textContent),{timeout:15000});
 const text=await page.locator('#m045Wave4Status').innerText();
 assert.doesNotMatch(text,/Master revision VERIFIED/);
 assert.match(text,/audio UNVERIFIED|do not retry/i);
});

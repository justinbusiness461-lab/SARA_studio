'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {spawn}=require('node:child_process');
const {mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os');
const {join,resolve}=require('node:path');
const {once}=require('node:events');
const {createInterface}=require('node:readline');
const {chromium}=require('playwright');

test('M045 Studio UI submits revision-fenced attempt and never fabricates physical proof', {timeout:90000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'m045-ui-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const python=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")','import studio_server as s','s.EXPORT_ROOT=Path(sys.argv[1])','with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as httpd:',' s.PORT=httpd.server_address[1]',' print(s.PORT,flush=True)',' httpd.serve_forever()'].join('\n');
 const srv=spawn('python3',['-u','-c',python,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(srv,'close');
 t.after(async()=>{if(srv.exitCode===null)srv.kill('SIGKILL');await closed});
 const reader=createInterface({input:srv.stdout});
 const [line]=await Promise.race([once(reader,'line'),closed.then(()=>{throw Error('server exited')})]);
 reader.close();
 const base='http://127.0.0.1:'+line;
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage({serviceWorkers:'block'});
 page.setDefaultTimeout(12000);
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 await page.goto(base);
 await page.locator('#prompt').fill('96 BPM E minor dark Southern hip hop');
 const commitResponse=page.waitForResponse(r=>r.url().endsWith('/api/projects/commit'));
 await page.locator('#btnCompile').click();
 assert.equal((await commitResponse).status(),200);
 let attempts=0;
 await page.route('**/api/m045/attempts',async route=>{
  attempts++;
  const payload=route.request().postDataJSON();
  assert.equal(typeof payload.expected_current_revision_id,'string');
  assert.equal(payload.model_id,'music_v2_5');
  assert.equal(route.request().headers()['authorization']?.startsWith('Bearer '),true);
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
   state:'COMMITTED',attempt:{idempotency_key:payload.idempotency_key,artifact_digest:'a'.repeat(64),
   provenance:{provider_id:'elevenlabs_music',preservation_tier:'P3',rights_status:'PROVIDER_TERMS_UNVERIFIED'}},
   revision:{revisionId:'r-qualified-by-test-only'}})});
 });
 await page.locator('#m045Duration').fill('180');
 await page.locator('#btnM045Generate').click();
 await page.locator('#m045Proof').getByText(/COMMITTED/).waitFor();
 assert.match(await page.locator('#m045Proof').innerText(),/P3/);
 assert.match(await page.locator('#m045Proof').innerText(),/PROVIDER_TERMS_UNVERIFIED/);
 assert.doesNotMatch(await page.locator('#m045Proof').innerText(),/PHYSICALLY_VERIFIED/);
 assert.equal(attempts,1);
 const opened = page.waitForResponse(r=>r.url().endsWith('/api/projects/open'));
 await page.locator('#btnOpenProject').click();
 const openedResponse = await opened;
 assert.equal(openedResponse.status(),200);
 const reopenedProject = await openedResponse.json();
 await page.waitForFunction(id=>document.querySelector('#projectRevision')?.textContent.includes(id),
   reopenedProject.revision.revisionId);
 const lock = page.locator('[data-lock]').first();
 await lock.click();
 await page.locator('#btnM045Generate').click();
 assert.equal(await page.evaluate(()=>m045LocksDirty),true);
 assert.equal(attempts,1);
 const lockSave = page.waitForResponse(r=>r.url().endsWith('/api/projects/commit'));
 await page.locator('#btnSave').click();
 const lockedResponse = await lockSave;
 assert.equal(lockedResponse.status(),200, JSON.stringify(await lockedResponse.json()));
 await page.locator('#btnM045Generate').click();
 assert.equal(await page.evaluate(()=>m045LocksDirty),false);
 assert.equal(await page.evaluate(()=>window.skeleton.tracks[0].sonic_lock),true);
 assert.equal(attempts,1);
 await page.route('**/api/m045/attempts/reconcile',async route=>{
  const body=route.request().postDataJSON();
  assert.ok(body.idempotency_key);
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
   state:'ASSOCIATED_HISTORICAL',attempt:{idempotency_key:body.idempotency_key,
   provenance:{provider_id:'elevenlabs_music',preservation_tier:'P3',rights_status:'PROVIDER_TERMS_UNVERIFIED'}},
   revision:{revisionId:'r-qualified-by-test-only'}})});
 });
 await page.reload();
 await page.locator('#btnOpenProject').click();
 await page.locator('#m045Proof').getByText(/ASSOCIATED_HISTORICAL/).waitFor();
 assert.match(await page.locator('#m045Proof').innerText(),/P3/);
 assert.doesNotMatch(await page.locator('#m045Proof').innerText(),/PHYSICALLY_VERIFIED/);
});

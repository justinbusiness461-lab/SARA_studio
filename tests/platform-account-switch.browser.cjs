'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),{mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os'),{join,resolve}=require('node:path');
const {once}=require('node:events'),{createInterface}=require('node:readline');
const {chromium}=require('playwright');
test('shared-device account B never reads cached A project/attempt pointer',{timeout:60000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'sara-account-switch-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const server=spawn('python3',['-u','tests/platform_release_fixture.py',dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [line]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('fixture server stopped')})]);lines.close();
 const fixture=JSON.parse(line);
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',route=>route.abort());
 await page.goto('http://127.0.0.1:'+fixture.port);
 await page.evaluate(id=>{
  localStorage.setItem('sf_project_ref',JSON.stringify({projectId:id,revisionId:'historic'}));
  localStorage.setItem('m045_attempt_pointer',JSON.stringify({projectId:id,attemptId:'private'}));
 },fixture.projectId);
 await page.locator('#platformHandle').fill('separate_b');
 await page.locator('#platformPassword').fill('another safe test password 2026');
 await page.locator('#platformDisplayName').fill('Different Artist');
 await page.locator('#platformSignUp').click();
 await page.waitForFunction(()=>document.body.classList.contains('platform-signed-in'));
 await page.locator('#platformNavStudio').click();
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Open failed')||
   document.querySelector('#status').textContent.includes('Opening selected project'),{timeout:8000});
 const result=await page.locator('#status').innerText();
 assert.match(result,/Enter a durable project ID/);
 assert.ok(!result.includes(fixture.projectId),'prior account ID exposed in current artist UI');
});

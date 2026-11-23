'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os');
const {join,resolve}=require('node:path');
const {once}=require('node:events');
const {createInterface}=require('node:readline');
const {chromium}=require('playwright');
const root=resolve(__dirname,'..');
const strictValue=process.env.SARA_R25_REAL_MEDIA_STRICT||'0';
if(!['0','1'].includes(strictValue)) throw new Error('R27_REAL_MEDIA_STRICT_INVALID');
const strictRealMedia=strictValue==='1';
async function boot(location){
 if(strictRealMedia&&(!process.env.SARA_R25_REAL_MEDIA_ROOT||!process.env.SARA_R25_REAL_MEDIA_RECEIPTS)){
  throw new Error('R27_REAL_MEDIA_REQUIRED');
 }
 const server=spawn('python3',['-u','tests/r25_three_song_fixture_server.py',location],{
  cwd:root,env:process.env,stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');
 const lines=createInterface({input:server.stdout});
 const info=await Promise.race([once(lines,'line').then(([line])=>JSON.parse(line)),closed.then(([code])=>{throw Error('fixture boot denied: '+code)})]);
 lines.close();
 return {url:'http://127.0.0.1:'+info.port,...info,stop:async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;}};
}
async function open(page, base, entry, revision) {
 await page.goto(base);
 await page.locator('#projectId').fill(entry.projectId);
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(id=>window.__M044_PLAYBACK_PROOF__?.revisionId===id,revision.revisionId,{timeout:90000});
 const proof=await page.evaluate(()=>window.__M044_PLAYBACK_PROOF__);
 assert.equal(proof.artifactId,revision.artifactId);
 assert.equal(proof.wavSha256,revision.artifactId);
 assert.equal(await page.locator('#status').textContent(),'Audio verified. Ready to hear.');
 return proof;
}
test('R25 three-song real or test-source cold open at mobile/desktop and exact R1/R2 A-B',{timeout:240000},async t=>{
 const temporary=mkdtempSync(join(tmpdir(),'sara-r25-cold-'));
 t.after(()=>rmSync(temporary,{recursive:true,force:true}));
 const startup=await boot(join(temporary,'studio'));
 const inventory=startup.songs;
 assert.equal(inventory.length,3);
 assert.equal(startup.strictRealMedia,strictRealMedia,'server mode must match requested mode');
 if(strictRealMedia) assert.equal(startup.stagingRealMedia,true,'synthetic startup forbidden in strict mode');
 await startup.stop(); // all project and media truth must survive a terminated server
 const runtime=await boot(join(temporary,'studio'));t.after(runtime.stop);
 assert.deepEqual(runtime.songs,inventory);
 assert.equal(runtime.strictRealMedia,strictRealMedia,'server mode changed across cold reopen');
 if(strictRealMedia) assert.equal(runtime.stagingRealMedia,true,'synthetic cold reopen forbidden');
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,args:['--no-sandbox']});t.after(()=>browser.close());
 const results=[];
 for(const width of [390,1440]){
  for(const entry of runtime.songs){
   const page=await browser.newPage({viewport:{width,height:width===390?844:900},serviceWorkers:'block'});
   page.setDefaultTimeout(30000);
   await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
   const proof=await open(page,runtime.url,entry,entry.selected);
   const geometry=await page.evaluate(()=>({innerWidth:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
   assert.ok(geometry.scrollWidth<=geometry.innerWidth+1,JSON.stringify(geometry));
   results.push({title:entry.title,width,revisionId:proof.revisionId,artifactId:proof.artifactId});
   if(width===1440&&entry.title==='Turn The Noise Back On'){
     // Audio proof publishes before its historical ancestor HTTP readback; do not race the readiness gate.
     await page.waitForFunction(()=>!document.querySelector('#btnABR1').disabled && !document.querySelector('#btnABR2').disabled,null,{timeout:30000});
     assert.equal(await page.locator('#btnABR1').isDisabled(),false);
     assert.equal(await page.locator('#btnABR2').isDisabled(),false);
     await page.locator('#btnPlay').click();
     await page.waitForFunction(()=>window.__M044_PLAYBACK_STARTED__===true,null,{timeout:18000});
     await page.waitForTimeout(250);
     await page.locator('#btnABR1').click();
     await page.waitForFunction(id=>window.__M044_PLAYBACK_PROOF__?.revisionId===id,entry.r1.revisionId,{timeout:60000});
     const r1proof=await page.evaluate(()=>({p:window.__M044_PLAYBACK_PROOF__,ab:window.__M044_AB_PROOF__}));
     assert.equal(r1proof.p.artifactId,entry.r1.artifactId);
     assert.ok(Math.abs(r1proof.ab.fromPositionSec-r1proof.ab.toPositionSec)<=0.05,JSON.stringify(r1proof.ab));
     await page.locator('#btnABR2').click();
     await page.waitForFunction(id=>window.__M044_PLAYBACK_PROOF__?.revisionId===id || window.__M044_AB_SWITCH__?.state==='FAILED',entry.selected.revisionId,{timeout:60000});
     const finalSwitch=await page.evaluate(()=>({state:window.__M044_AB_SWITCH__,status:document.querySelector('#status')?.textContent,abStatus:document.querySelector('#abStatus')?.textContent,proof:window.__M044_PLAYBACK_PROOF__}));
     assert.equal(finalSwitch.proof?.revisionId,entry.selected.revisionId,'REAL_MEDIA_R2_SWITCH_FAILURE '+JSON.stringify(finalSwitch));
     const r2proof=await page.evaluate(()=>({p:window.__M044_PLAYBACK_PROOF__,ab:window.__M044_AB_PROOF__}));
     assert.equal(r2proof.p.artifactId,entry.selected.artifactId);
     assert.ok(Math.abs(r2proof.ab.fromPositionSec-r2proof.ab.toPositionSec)<=0.05,JSON.stringify(r2proof.ab));
     results.push({ab:'R1->R2',r1PositionDriftSec:Math.abs(r1proof.ab.fromPositionSec-r1proof.ab.toPositionSec),r2PositionDriftSec:Math.abs(r2proof.ab.fromPositionSec-r2proof.ab.toPositionSec)});
   }
   await page.close();
  }
 }
 console.log('R25_COLD_REOPEN_PHYSICAL_EVIDENCE',JSON.stringify({realMedia:runtime.stagingRealMedia,strictRealMedia,certificationMode:strictRealMedia?'REAL_MEDIA_STRICT':'SYNTHETIC_FIXTURE_NOT_REAL_MEDIA_CERTIFICATION',inventory:results}));
});
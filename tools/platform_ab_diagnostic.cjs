'use strict';
/** One-shot executable diagnostics, intentionally NOT a PASS gate. */
const {spawn}=require('node:child_process');
const {mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os');
const {resolve,join}=require('node:path');
const {once}=require('node:events');
const {createInterface}=require('node:readline');
const {chromium}=require('playwright');
(async()=>{
 const dir=mkdtempSync(join(tmpdir(),'sara-ab-auth-probe-'));
 const server=spawn('python3',['-u','tests/platform_ab_source_fixture.py',dir],
   {cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');
 const lines=createInterface({input:server.stdout});
 const [line]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('fixture ended')})]);
 lines.close();
 const fixture=JSON.parse(line);
 let browser,page;const log=[];
 const snapshot=()=>page.evaluate(()=>({
  status:document.getElementById('status')?.textContent,
  abStatus:document.getElementById('abStatus')?.textContent,
  switch:window.__M044_AB_SWITCH__,ab:window.__M044_AB_PROOF__,
  playback:window.__M044_PLAYBACK_PROOF__,
  playerPaused:document.getElementById('btnPlay')?.textContent
 }));
 try{
  browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
  page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
  await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
  page.on('pageerror',e=>log.push({kind:'browser-error',error:String(e)}));
  await page.goto('http://127.0.0.1:'+fixture.port);
  await page.locator('#platformHandle').fill('ab_diagnostic');
  await page.locator('#platformPassword').fill('synthetic test passphrase 2026');
  await page.locator('#platformSignIn').click();
  await page.waitForFunction(()=>document.body.classList.contains('platform-signed-in'));
  await page.locator('#platformNavStudio').click();
  await page.locator('#projectId').fill(fixture.projectId);
  await page.locator('#btnOpenProject').click();
  await page.waitForFunction(ref=>window.__M044_PLAYBACK_PROOF__?.revisionId===ref,
   fixture.current.revisionId,{timeout:25000});
  log.push({kind:'opened',state:await snapshot()});
  await page.locator('#dockPlay').click();
  await page.waitForFunction(()=>window.__M044_PLAYBACK_STARTED__===true,{timeout:10000});
  await page.waitForTimeout(360);
  log.push({kind:'playing-before-switch',state:await snapshot()});
  for(const [id,expected] of [['btnABR1',fixture.historical.revisionId],
                              ['btnABR2',fixture.current.revisionId]]){
   await page.locator('#'+id).click();
   try{
    await page.waitForFunction(ref=>window.__M044_AB_SWITCH__?.state==='COMPLETE' &&
      window.__M044_PLAYBACK_PROOF__?.revisionId===ref,
      expected,{timeout:18000});
   }catch(error){
    log.push({kind:'ab-failure',button:id,error:String(error),state:await snapshot()});
    process.exitCode=1;break;
   }
   log.push({kind:'ab-complete',button:id,state:await snapshot()});
  }
  const final=log.at(-1)?.state;
  if(!final||final.switch?.state!=='COMPLETE'||
    Math.abs((final.ab?.fromPositionSec||0)-(final.ab?.toPositionSec||0))>0.05)process.exitCode=1;
 }catch(error){log.push({kind:'fatal',error:String(error)});process.exitCode=1;}
 finally{
  process.stdout.write(JSON.stringify({case:'PLATFORM_AB_AUTH_DIAGNOSTIC',
   fixture:{projectId:fixture.projectId,sourceRevisionIds:[fixture.historical.revisionId,fixture.current.revisionId]},
   events:log},null,2)+'\n');
  if(page)await page.close().catch(()=>{});
  if(browser)await browser.close().catch(()=>{});
  if(server.exitCode===null)server.kill('SIGKILL');await closed;
  rmSync(dir,{recursive:true,force:true});
 }
})().catch(error=>{process.stderr.write(String(error)+'\n');process.exitCode=1;});

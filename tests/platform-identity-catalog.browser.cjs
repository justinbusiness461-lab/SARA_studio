'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),{mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os'),{join,resolve}=require('node:path');
const {once}=require('node:events'),{createInterface}=require('node:readline');
const {chromium}=require('playwright');
test('platform 360/390 mobile sign-in, real profile, Explore empty, private Library and logout',{timeout:80000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'sara-platform-e2e-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const script=[
 'import socketserver,sys,json','from pathlib import Path','sys.path.insert(0,"tools")','import studio_server as s',
 's.PLATFORM_MODE=True','s.EXPORT_ROOT=Path(sys.argv[1])',
 'with socketserver.ThreadingTCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
 ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const server=spawn('python3',['-u','-c',script,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','ignore']});
 const closed=once(server,'close');t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('platform server stopped')})]);lines.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 for(const [width,height] of [[360,800],[390,844]]){
  const page=await browser.newPage({viewport:{width,height},serviceWorkers:'block'});
  await page.route('https://cdn.jsdelivr.net/**',route=>route.abort());
  const errors=[];page.on('pageerror',error=>errors.push(String(error)));
  await page.goto('http://127.0.0.1:'+port+'/');
  assert.equal(await page.locator('#platformSignUp').count(),1);
  await page.locator('#platformHandle').fill('tester'+width);
  await page.locator('#platformPassword').fill('strong enough password!2026');
  await page.locator('#platformDisplayName').fill('Test Artist');
  await page.locator('#platformSignUp').click();
  await page.waitForFunction(()=>document.body.classList.contains('platform-signed-in'),{timeout:10000});
  await page.locator('#platformNavExplore').click();
  await page.waitForFunction(()=>document.getElementById('platformExploreStatus').textContent.includes('EMPTY'),{timeout:15000});
  await page.locator('#platformNavLibrary').click();
  await page.waitForFunction(()=>document.getElementById('platformLibraryStatus').textContent.includes('EMPTY'),{timeout:15000});
  await page.locator('#platformNavProfile').click();
  await page.locator('#platformBio').fill('New artist');
  await page.locator('#platformSaveProfile').click();
  await page.waitForFunction(()=>document.getElementById('platformProfileStatus').textContent.includes('READY'),{timeout:12000});
  const dimensions=await page.evaluate(()=>({
    overflow:document.documentElement.scrollWidth>innerWidth+1,
    touch:[...document.querySelectorAll('#platformNavigation button')].map(x=>[x.getBoundingClientRect().width,x.getBoundingClientRect().height]),
    player:document.getElementById('platformMiniPlayer').getBoundingClientRect().height
  }));
  assert.equal(dimensions.overflow,false,JSON.stringify(dimensions));
  assert.ok(dimensions.touch.every(([w,h])=>w>=48&&h>=48),JSON.stringify(dimensions));
  assert.ok(dimensions.player>=48);
  const pageReload=page.waitForEvent('load',{timeout:10000});
  await page.locator('#platformLogout').click();
  await pageReload;
  await page.waitForFunction(()=>document.body.classList.contains('platform-signed-out'),{timeout:10000});
  const me=await page.evaluate(async()=> (await fetch('/api/me')).status);
  assert.equal(me,403);
  assert.deepEqual(errors,[]);
  await page.close();
 }
});

'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),{mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os'),{join,resolve}=require('node:path');
const {once}=require('node:events'),{createInterface}=require('node:readline');
const {chromium}=require('playwright');
test('Explore Rooms 360px private artist chat survives reload, never overflows mobile shell',{timeout:90000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'sara-rooms-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const script=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")','import studio_server as s',
 's.PLATFORM_MODE=True','s.EXPORT_ROOT=Path(sys.argv[1])','with socketserver.ThreadingTCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
 ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const proc=spawn('python3',['-u','-c',script,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','ignore']});
 const closed=once(proc,'close');t.after(async()=>{if(proc.exitCode===null)proc.kill('SIGKILL');await closed;});
 const lines=createInterface({input:proc.stdout});const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('server stopped')})]);lines.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:360,height:800},serviceWorkers:'block'});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('http://127.0.0.1:'+port+'/');
 await page.locator('#platformHandle').fill('roomartist');await page.locator('#platformPassword').fill('strong password 2026!');
 await page.locator('#platformDisplayName').fill('Room Artist');await page.locator('#platformSignUp').click();
 await page.waitForFunction(()=>document.body.classList.contains('platform-signed-in'));
 await page.locator('#platformNavExplore').click();await page.locator('#platformExploreTabRooms').click();
 await page.locator('#platformRoomName').fill('Songwriters Circle');await page.locator('#platformCreateRoom').click();
 await page.waitForFunction(()=>document.getElementById('platformRoomStatus').textContent.includes('READY'));
 await page.locator('#platformRoomReviewRefresh').waitFor({state:'visible',timeout:10000});
 await page.locator('#platformRoomComposer').fill('Verse one, take two');await page.locator('#platformRoomSend').click();
 await page.waitForFunction(()=>document.getElementById('platformRoomMessages').textContent.includes('Verse one, take two'));
 const layout=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,
  targets:[...document.querySelectorAll('#platformRoomView button, #platformExploreTabs button')].filter(e=>e.offsetParent!==null).map(x=>[x.offsetWidth,x.offsetHeight])}));
 assert.equal(layout.overflow,false,JSON.stringify(layout));assert.ok(layout.targets.every(([w,h])=>w>=48&&h>=48),JSON.stringify(layout));
 await page.reload();await page.waitForFunction(()=>document.body.classList.contains('platform-signed-in'));
 await page.locator('#platformNavExplore').click();await page.locator('#platformExploreTabRooms').click();
 await page.waitForFunction(()=>document.getElementById('platformRoomList').textContent.includes('Songwriters Circle'));
 await page.locator('#platformRoomList button').first().click();
 await page.waitForFunction(()=>document.getElementById('platformRoomMessages').textContent.includes('Verse one, take two'));
 assert.deepEqual(errors,[]);
});

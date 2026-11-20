'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),{mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os'),{join,resolve}=require('node:path');
const {once}=require('node:events'),{createInterface}=require('node:readline');
const {chromium}=require('playwright');
test('Wave2 360px real playlist, workspace, credits and Chat use authenticated account',{timeout:100000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'sara-platform-wave2-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const script=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")','import studio_server as s',
 's.PLATFORM_MODE=True','s.EXPORT_ROOT=Path(sys.argv[1])',
 'with socketserver.ThreadingTCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
 ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const server=spawn('python3',['-u','-c',script,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('server stopped')})]);lines.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:360,height:800},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',route=>route.abort());
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('http://127.0.0.1:'+port);
 await page.locator('#platformHandle').fill('wave2_artist');
 await page.locator('#platformPassword').fill('strong enough password!2026');
 await page.locator('#platformDisplayName').fill('Wave 2 Artist');
 await page.locator('#platformSignUp').click();
 await page.waitForFunction(()=>document.body.classList.contains('platform-signed-in'));
 await page.locator('#platformNavProfile').click();
 await page.locator('#platformPlaylistTitle').fill('My First Mix');
 await page.locator('#platformCreatePlaylist').click();
 await page.waitForFunction(()=>document.getElementById('platformPlaylistStatus').textContent.includes('READY'));
 assert.match(await page.locator('#platformMyPlaylists').innerText(),/My First Mix/);
 await page.locator('#platformWorkspaceName').fill('Producer Team');
 await page.locator('#platformCreateWorkspace').click();
 await page.waitForFunction(()=>document.getElementById('platformWorkspaceStatus').textContent.includes('READY'));
 assert.match(await page.locator('#platformMyWorkspaces').innerText(),/Producer Team/);
 await page.locator('#platformCreditsRefresh').click();
 await page.waitForFunction(()=>document.getElementById('platformCreditsStatus').textContent.includes('0 available'));
 await page.locator('#platformNavChat').click();
 await page.locator('#platformChatInstruction').fill('Check my credit balance');
 await page.locator('#platformChatSend').click();
 await page.waitForFunction(()=>document.getElementById('platformChatStatus').textContent.includes('EXECUTED'));
 assert.match(await page.locator('#platformChatResult').innerText(),/available/);
 await page.locator('#platformChatInstruction').fill('Publish R2');
 await page.locator('#platformChatSend').click();
 await page.waitForFunction(()=>document.getElementById('platformChatStatus').textContent.includes('AWAITING_CONFIRMATION'));
 // Chat must submit to the same Studio Generate click handler and await real owner proof.
 await page.locator('#platformChatInstruction').fill('Generate 96 BPM E minor dark Southern hip-hop instrumental');
 await page.locator('#platformChatSend').click();
 await page.waitForFunction(()=>window.__M044_PLAYBACK_PROOF__?.revisionId &&
   document.getElementById('status')?.textContent==='Audio verified. Ready to hear.',null,{timeout:70000});
 const verified=await page.evaluate(()=>window.__M044_PLAYBACK_PROOF__);
 assert.ok(verified.projectId&&verified.revisionId&&verified.artifactId);
 assert.equal(verified.wavSha256,verified.artifactId);
 const layout=await page.evaluate(()=>({
  overflow:document.documentElement.scrollWidth>window.innerWidth+1,
  touch:[...document.querySelectorAll('#platformShell button')].filter(e=>e.offsetParent!==null)
    .map(e=>({id:e.id,h:Math.round(e.getBoundingClientRect().height),w:Math.round(e.getBoundingClientRect().width)})),
 }));
 assert.equal(layout.overflow,false,JSON.stringify(layout));
 assert.ok(layout.touch.every(x=>x.h>=48&&x.w>=48),JSON.stringify(layout));
 assert.deepEqual(errors,[]);
});

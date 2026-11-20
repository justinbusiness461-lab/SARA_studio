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

test('RS-001/002 six viewport zero overflow, dock parity and thumbs-first layout',{timeout:145000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'rs-mobile-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const py=[
  'import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")',
  'import studio_server as s','s.EXPORT_ROOT=Path(sys.argv[1])',
  'with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
  ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'
 ].join('\n');
 const server=spawn('python3',['-u','-c',py,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');
 t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('server stopped')})]);
 lines.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const base='http://127.0.0.1:'+port;
 const viewports=[[1440,900],[1024,768],[768,900],[640,900],[430,932],[390,844]];
 for (const [width,height] of viewports) {
  const page=await browser.newPage({viewport:{width,height},serviceWorkers:'block'});
  await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
  await page.goto(base);
  const shape=await page.evaluate(()=>{
    const rect=id=>{const e=document.getElementById(id);const b=e.getBoundingClientRect();return {width:b.width,height:b.height,x:b.x,right:b.right,bottom:b.bottom}};
    return {
      appWidth:rect('studioProjectBar').width,bodyWidth:document.body.scrollWidth,documentWidth:document.documentElement.scrollWidth,
      innerWidth:window.innerWidth, dock:rect('studioThumbDock'),
      viewportHeight:window.innerHeight,
      buttons:[...document.querySelectorAll('#studioThumbDock button')].map(b=>({id:b.id,width:b.getBoundingClientRect().width,height:b.getBoundingClientRect().height,disabled:b.disabled})),
      zoom:document.querySelector('meta[name=viewport]').content
    };
  });
  if (width>=1024) assert.ok(shape.appWidth>=900,'desktop cap unexpectedly preserved: '+JSON.stringify(shape));
  assert.ok(shape.bodyWidth<=width+1,'body overflow '+width+': '+JSON.stringify(shape));
  assert.ok(shape.documentWidth<=width+1,'document overflow '+width+': '+JSON.stringify(shape));
  assert.equal(shape.dock.bottom,height,'dock pinned '+width);
  assert.match(shape.zoom,/viewport-fit=cover/);
  assert.doesNotMatch(shape.zoom,/user-scalable=no/);
  for (const button of shape.buttons) {
    assert.ok(button.width>=47.5 && button.height>=47.5,'touch size '+width+' '+JSON.stringify(button));
  }
  const screenRows=await page.evaluate(()=>[...document.querySelectorAll('#studioThumbDock button')].map(e=>({id:e.id,box:e.getBoundingClientRect()})));
  for(let i=0;i<screenRows.length;i++)for(let j=i+1;j<screenRows.length;j++){
    const a=screenRows[i].box,b=screenRows[j].box;
    const overlap=Math.min(a.right,b.right)-Math.max(a.left,b.left)>0&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>0;
    assert.ok(!overlap,'overlapping dock buttons '+width+' '+screenRows[i].id+'/'+screenRows[j].id);
  }
  await page.locator('#studioModeProof').click();
  assert.equal(await page.locator('#studioModeProof').getAttribute('aria-current'),'page');
  assert.equal(await page.locator('#m045StudioControls').evaluate(e=>document.activeElement===e),true);
  await page.locator('#dockChangeOnly').click();
  assert.equal(await page.locator('#m045TargetTrack').evaluate(e=>document.activeElement===e),true);
  await page.close();
 }
});
test('mobile project R1 save, cold reload and dock delegates to canonical transport without fake proof',{timeout:100000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'rs-mobile-project-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const py=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")',
  'import studio_server as s','s.EXPORT_ROOT=Path(sys.argv[1])',
  'with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
  ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const server=spawn('python3',['-u','-c',py,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(server,'close');t.after(async()=>{if(server.exitCode===null)server.kill('SIGKILL');await closed;});
 const lines=createInterface({input:server.stdout});
 const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('server stopped')})]);lines.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'});
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 await page.goto('http://127.0.0.1:'+port);
 assert.equal(await page.locator('#dockPlay').isDisabled(),true);
 await page.locator('#studioModeChat').click();
 await page.locator('#prompt').fill('94 BPM F# minor hypnotic southern bass');
 const commit=page.waitForResponse(r=>r.url().endsWith('/api/projects/commit'));
 const render=page.waitForResponse(r=>r.url().endsWith('/api/projects/render'));
 await page.locator('#btnCompile').click();
 assert.equal((await commit).status(),200);
 assert.equal((await render).status(),200);
 await page.waitForFunction(()=>document.getElementById('studioHeaderRevision').textContent!=='Draft');
 const savedRev=await page.locator('#studioHeaderRevision').innerText();
 assert.match(savedRev,/^[a-f0-9]{12}$/);
 await page.locator('#dockPlay').waitFor({state:'visible'});
 await page.waitForFunction(()=>!document.getElementById('dockPlay').disabled);
 await page.locator('#dockPlay').click();
 await page.waitForFunction(()=>/Stop/.test(document.getElementById('dockPlay').textContent));
 await page.locator('#dockStop').click();
 await page.waitForFunction(()=>/Play/.test(document.getElementById('dockPlay').textContent));
 await page.reload();
 await page.locator('#studioModeWorkstream').click();
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(()=>document.getElementById('studioHeaderRevision').textContent!=='Draft');
 assert.equal(await page.locator('#studioHeaderRevision').innerText(),savedRev);
 assert.match(await page.locator('#m045Proof').innerText(),/DECLARED|COMMITTED|UNVERIFIED/);
});

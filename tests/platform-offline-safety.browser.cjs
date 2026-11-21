'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),{mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os'),{join,resolve}=require('node:path');
const {once}=require('node:events'),{createInterface}=require('node:readline');
const {chromium}=require('playwright');
test('local offline ScoreCore shell contains zero session or capability bearer tokens',{timeout:40000},async t=>{
 const root=mkdtempSync(join(tmpdir(),'sara-offline-safe-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 const py=['import socketserver,sys','from pathlib import Path','sys.path.insert(0,"tools")',
  'import studio_server as s','s.EXPORT_ROOT=Path(sys.argv[1])',
  'with socketserver.ThreadingTCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
  ' s.PORT=srv.server_address[1]',' print(s.PORT,flush=True)',' srv.serve_forever()'].join('\n');
 const srv=spawn('python3',['-u','-c',py,root],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const closed=once(srv,'close');t.after(async()=>{if(srv.exitCode===null)srv.kill('SIGKILL');await closed;});
 const lines=createInterface({input:srv.stdout});
 const [port]=await Promise.race([once(lines,'line'),closed.then(()=>{throw Error('server stopped')})]);lines.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage();
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 await page.goto('http://127.0.0.1:'+port);
 await page.waitForFunction(()=>navigator.serviceWorker.controller!==null,{timeout:15000});
 const inspected=await page.evaluate(async()=>{
  const keys=await caches.keys();const name=keys.find(x=>x.includes('sanitized-offline'));
  const cache=await caches.open(name);const response=await cache.match('./index.html');
  return {name,html:response?await response.text():null};
 });
 assert.ok(inspected.name);
 assert.ok(inspected.html);
 assert.match(inspected.html,/__SARA_OFFLINE_SHELL__=true/);
 assert.doesNotMatch(inspected.html,/window\.__STUDIO_SESSION__/);
 assert.doesNotMatch(inspected.html,/window\.__STUDIO_CAPABILITY__/);
 await page.context().setOffline(true);
 await page.reload();
 const proof=await page.evaluate(()=>({offline:window.__SARA_OFFLINE_SHELL__,
  hasSession:typeof window.__STUDIO_SESSION__,hasCap:typeof window.__STUDIO_CAPABILITY__,
  scoreCore:typeof window.ScoreCore?.compileIntent}));
 assert.equal(proof.offline,true);
 assert.equal(proof.hasSession,'undefined');assert.equal(proof.hasCap,'undefined');
 assert.equal(proof.scoreCore,'function');
});

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

test('M045 real HTTP multi-take audition, explicit selections, cold browser reload and request fencing',{timeout:120000},async t=>{
 const dir=mkdtempSync(join(tmpdir(),'m045-multi-ab-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const py=[
  'import socketserver,sys,io,wave,pathlib',
  'from pathlib import Path',
  'sys.path.insert(0,"tools")',
  'import studio_server as s',
  's.EXPORT_ROOT=Path(sys.argv[1])',
  'def synth(stage,spec,prompt,lyrics,seed,params):',
  ' assert params["_m045_batch_count"]==3',
  ' outputs=[]',
  ' for i,value in enumerate((300,600,900)):',
  '  b=io.BytesIO()',
  '  with wave.open(b,"wb") as wav:',
  '   wav.setframerate(44100);wav.setnchannels(2);wav.setsampwidth(2)',
  '   wav.writeframes(value.to_bytes(2,"little",signed=True)*2*88200)',
  '  out=pathlib.Path(stage)/("take-%d.wav"%i)',
  '  out.write_bytes(b.getvalue()); outputs.append(out)',
  ' return outputs',
  'synth.supports_multitake=True',
  'synth.model_id="ace-step-1.5";synth.model_version="ace-step-1.5"',
  's.configure_m045_generation(s.make_m045_native_owner(s.EXPORT_ROOT),{"ace-step-1.5":synth})',
  'with socketserver.TCPServer(("127.0.0.1",0),s.StudioHandler) as srv:',
  ' s.PORT=srv.server_address[1]',
  ' print(s.PORT,flush=True)',
  ' srv.serve_forever()'
 ].join('\n');
 const srv=spawn('python3',['-u','-c',py,dir],{cwd:resolve(__dirname,'..'),stdio:['ignore','pipe','inherit']});
 const done=once(srv,'close');
 t.after(async()=>{if(srv.exitCode===null)srv.kill('SIGKILL');await done;});
 const reader=createInterface({input:srv.stdout});
 const [port]=await Promise.race([once(reader,'line'),done.then(()=>{throw Error('server exited')})]);
 reader.close();
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined});
 t.after(()=>browser.close());
 const page=await browser.newPage({serviceWorkers:'block'});
 page.setDefaultTimeout(15000);
 await page.route('https://cdn.jsdelivr.net/**',r=>r.abort());
 await page.goto('http://127.0.0.1:'+port);
 await page.locator('#prompt').fill('96 BPM E minor dark Southern country hiphop');
 const saved=page.waitForResponse(r=>r.url().endsWith('/api/projects/commit'));
 const rendered=page.waitForResponse(r=>r.url().endsWith('/api/projects/render'));
 await page.locator('#btnCompile').click();
 assert.equal((await saved).status(),200);
 assert.equal((await rendered).status(),200);
 await page.waitForFunction(()=>document.querySelector('#projectRevision')?.textContent.includes('Saved revision:'));
 await page.locator('#m045Provider').selectOption('ace');
 await page.locator('#m045BatchCount').selectOption('3');
 await page.locator('#m045Duration').fill('12');
 const generated=page.waitForResponse(r=>r.url().endsWith('/api/m045/attempts'));
 await page.locator('#btnM045Generate').click();
 const posted=await generated;
 assert.equal(posted.status(),200,JSON.stringify(await posted.json()));
 await page.locator('#m045Proof').getByText(/AWAITING_TAKE_SELECTION/).waitFor();
 assert.equal(await page.locator('[data-m045-audition]').count(),3);
 assert.equal(await page.locator('[data-m045-select]').count(),3);
 const original=await page.locator('#projectRevision').textContent();
 await page.route('**/api/m045/attempts/take-audio',async route=>{
  const input=route.request().postDataJSON();
  const response=await route.fetch();
  if(input.take_index===0)await new Promise(ok=>setTimeout(ok,250));
  await route.fulfill({response});
 });
 await page.locator('[data-m045-audition="0"]').click();
 await page.locator('[data-m045-audition="1"]').click();
 await page.waitForFunction(()=>document.querySelector('#m045TakeStatus').textContent.includes('Take 2'));
 assert.match(await page.locator('#m045TakeStatus').innerText(),/Take 2/);
 await page.waitForFunction(() => document.querySelector('#m045TakePreview').currentTime > 0.2);
 await page.locator('[data-m045-audition="2"]').click();
 await page.waitForFunction(() => document.querySelector('#m045TakeStatus').textContent.includes('Take 3'));
 assert.ok(await page.locator('#m045TakePreview').evaluate(media => media.currentTime > 0.15));
 assert.equal(await page.locator('#projectRevision').textContent(),original);
 await page.locator('[data-m045-select="1"]').click();
 await page.waitForFunction(prev=>document.querySelector('#projectRevision').textContent!==prev, original);
 const selected1=await page.locator('#projectRevision').textContent();
 await page.locator('[data-m045-select="2"]').click();
 await page.waitForFunction(prev=>document.querySelector('#projectRevision').textContent!==prev, selected1);
 const selected2=await page.locator('#projectRevision').textContent();
 assert.notEqual(selected1,selected2);
 await page.reload();
 await page.locator('#btnOpenProject').click();
 await page.waitForFunction(()=>!document.querySelector('#m045TakePanel').hidden);
 assert.equal(await page.locator('[data-m045-audition]').count(),3);
 assert.match(await page.locator('#projectRevision').innerText(),/Saved revision:/);
});

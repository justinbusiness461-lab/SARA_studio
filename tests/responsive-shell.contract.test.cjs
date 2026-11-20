'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const css=fs.existsSync(path.join(root,'studio-shell.css'))?fs.readFileSync(path.join(root,'studio-shell.css'),'utf8'):'';
const ui=fs.readFileSync(path.join(root,'app-ui.js'),'utf8');

test('responsive shell loads external stylesheet and allows accessible zoom',()=>{
 assert.match(html,/<link[^>]*href="studio-shell\.css"/);
 assert.doesNotMatch(html,/user-scalable=no|maximum-scale=1/);
});
test('project bar, unified thumb transport, navigation and live proof retain source controls',()=>{
 for(const id of ['studioProjectBar','studioHeaderProjectId','studioHeaderRevision',
   'studioThumbDock','dockPlay','dockStop','dockGenerate','dockChangeOnly',
   'studioModeTabs','studioModeChat','studioModeCanvas','studioModeDj','studioModeProof',
   'm045Proof','projectId','projectRevision','btnM045Generate','btnPlay','btnStop']){
   assert.match(html,new RegExp('id="'+id+'"'),id+' absent');
 }
 assert.match(ui,/function\s+initStudioResponsiveShell\s*\(/);
 assert.match(ui,/btnM045Generate/);
});
test('thumb and step grid minimum 48 px and safe-area composition are styled',()=>{
 assert.match(css,/min-height:\s*48px/);
 assert.match(css,/min-width:\s*48px/);
 assert.match(css,/safe-area-inset-bottom/);
 assert.match(css,/overflow-x:\s*auto/);
 assert.match(css,/@media/);
});
test('responsive shell does not duplicate the canonical production control ids',()=>{
 const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);
 const duplicates=ids.filter((id,i)=>ids.indexOf(id)!==i);
 assert.deepEqual(duplicates,[]);
});

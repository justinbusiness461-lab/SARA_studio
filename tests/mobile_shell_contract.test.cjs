'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const root=join(__dirname,'..');
test('mobile 2x8 DJ pads explicit while desktop keeps canonical matrix',()=>{
 const css=readFileSync(join(root,'studio-shell.css'),'utf8');
 assert.match(css,/@media\s*\(max-width:\s*600px\)\s*\{[\s\S]*?#djGrid\s*\{\s*grid-template-columns:\s*repeat\(8,\s*48px\)/);
});
test('viewport contract covers exact required six',()=>{
 const src=readFileSync(join(root,'tests','responsive-shell.browser.cjs'),'utf8');
 for(const vp of ['360,800','390,844','412,915','768,1024','1024,768','1440,900'])
   assert.ok(src.includes('['+vp+']'),'missing viewport '+vp);
});

'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {propose,preview,commit}=require('../tools/m045_conversational_edit.cjs');
function fixture(){return {
 manifest:{projectId:'p-id',currentRevisionId:'R1'},
 revision:{revisionId:'R1',sourceAssetDigests:['asset-A']},
 songSpec:{structure:{sections:[{id:'verse1',name:'Verse 1',start_tick:0,end_tick:3840},{id:'chorus1',name:'Chorus',start_tick:3840,end_tick:7680}]},
 tracks:[{track_id:'bass',name:'Bass',type:'BASS',events:[{type:'NOTE_ON',tick:100,duration_ticks:400,note_number:40,event_id:'b1'},{type:'NOTE_ON',tick:4000,duration_ticks:400,note_number:44,event_id:'b2'}]},
 {track_id:'guitar',name:'Guitar',type:'LEAD',events:[{type:'NOTE_ON',tick:4000,duration_ticks:200,note_number:67,event_id:'g1'}]}]}}
}
test('propose/validate/preview is immutable P0 event-local, no commit',()=>{
 const snap=fixture(), before=JSON.stringify(snap);
 const p=propose('Lower the chorus bass by one octave; keep everything else.',snap,{operationId:'edit-1'});
 const result=preview(p,snap);
 assert.equal(JSON.stringify(snap),before);
 assert.equal(result.preservationTier,'P0_EVENT_CANDIDATE');
 assert.equal(result.diff.length,1);assert.equal(result.diff[0].eventId,'b2');
 assert.equal(result.diff[0].beforePitch,44);assert.equal(result.diff[0].afterPitch,32);
 assert.equal(result.songSpec.tracks[1].events[0].note_number,67);
 assert.equal(result.songSpec.tracks[0].events[0].note_number,40);
});
test('ambiguous command is blocked, not inventing an edit',()=>{
 assert.throws(()=>propose('Change the chorus bass, keep everything else',fixture(),{operationId:'edit-1'}),/AMBIGUOUS|UNSUPPORTED/);
 assert.throws(()=>propose('Improve song',fixture(),{operationId:'edit-1'}),/AMBIGUOUS|UNSUPPORTED/);
});
test('duplicate semantic name and stale snapshot fail closed',()=>{
 const snap=fixture();snap.songSpec.structure.sections[0].name='Chorus';
 assert.throws(()=>propose('Lower the chorus bass by one octave',snap,{operationId:'edit-1'}),/AMBIGUOUS/);
 const stale=fixture();stale.manifest.currentRevisionId='R2';
 assert.throws(()=>propose('Lower the chorus bass by one octave',stale,{operationId:'edit-1'}),/REVISION/);
});
test('sonic lock denies target mutation',()=>{
 const snap=fixture();snap.songSpec.tracks[0].sonic_lock=true;
 assert.throws(()=>propose('Lower the chorus bass by one octave',snap,{operationId:'edit-1'}),/SONIC_LOCK/);
});
test('commit requires approval; canonical API receives pinned R1 and no audio claims',async()=>{
 const snap=fixture(),p=propose('Lower the chorus bass by one octave',snap,{operationId:'edit-9'});
 const proof=preview(p,snap);let count=0,captured;
 const io={commit:async data=>{count++;captured=data;return {manifest:{currentRevisionId:'R2'},revision:{revisionId:'R2',parentRevisionId:'R1'}};}};
 await assert.rejects(()=>commit(proof,{approved:false,io}),/APPROVAL/);
 assert.equal(count,0);
 const res=await commit(proof,{approved:true,io});
 assert.equal(count,1);assert.equal(captured.projectId,'p-id');
 assert.equal(captured.expectedCurrentRevisionId,'R1');
 assert.equal(captured.operationId,'edit-9');
 assert.deepEqual(captured.outputArtifactIds,[]);
 assert.deepEqual(captured.sourceAssetDigests,['asset-A']);
 assert.equal(captured.songSpec.tracks[0].events[1].note_number,32);
 assert.equal(res.revision.revisionId,'R2');
 assert.equal(res.audioStatus,'UNRENDERED');
});
test('stale canonical revision conflict is never retried optimistically',async()=>{
 const p=propose('Lower the chorus bass by one octave',fixture(),{operationId:'edit-11'});
 let calls=0;
 await assert.rejects(()=>commit(preview(p,fixture()),{approved:true,io:{commit:async()=>{calls++;throw Error('409 CONFLICT')}}}),/409/);
 assert.equal(calls,1);
});

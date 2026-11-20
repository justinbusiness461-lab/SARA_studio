'use strict';
/**
 * SJ3 Wave 002, independently written bounded command interpreter.
 * Interpretation is non-authoritative. SongSpec, ProjectRevision, rendering,
 * sample assets and accepted audio remain owned by the existing Studio service.
 * Explicitly unsupported requests fail closed; no speculative model fallback.
 */
const { createHash } = require('node:crypto');
const { transposeSection } = require('./scorecore.cjs');
const clone = value => JSON.parse(JSON.stringify(value));
const normalized = x => String(x).trim().toLowerCase().replace(/\s+/g,' ');
const fingerprint = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');

function requireSnapshot(snapshot) {
  if (!snapshot || !snapshot.manifest || !snapshot.revision || !snapshot.songSpec ||
      typeof snapshot.manifest.projectId!=='string' || !snapshot.manifest.projectId ||
      typeof snapshot.revision.revisionId!=='string' || !snapshot.revision.revisionId ||
      snapshot.manifest.currentRevisionId!==snapshot.revision.revisionId ||
      !Array.isArray(snapshot.songSpec.structure?.sections) ||
      !Array.isArray(snapshot.songSpec.tracks)) throw Error('SOURCE_REVISION_INVALID');
}
function unique(source, label, predicate) {
  const hits=source.filter(predicate);
  if(hits.length!==1) throw Error('AMBIGUOUS_OR_MISSING_'+label);
  return hits[0];
}
function propose(command,snapshot,{operationId}={}) {
  requireSnapshot(snapshot);
  if(typeof operationId!=='string'|| !/^[a-z0-9._:-]{1,80}$/i.test(operationId))
    throw Error('OPERATION_ID_INVALID');
  if(typeof command!=='string' || command.length>300) throw Error('UNSUPPORTED_COMMAND');
  const parsed=/^\s*(lower|raise)\s+(?:the\s+)?(.+?)\s+(bass|guitar|lead|pad|strings)\s+by\s+(one octave|12 semitones)(?:\s*[;,]\s*keep everything else)?\s*\.?\s*$/i.exec(command);
  if(!parsed) throw Error('AMBIGUOUS_OR_UNSUPPORTED_COMMAND');
  const [,verb,sectionText,trackText]=parsed;
  const section=unique(snapshot.songSpec.structure.sections,'SECTION',s=>
    normalized(s.name||'')===normalized(sectionText)||normalized(s.id)===normalized(sectionText));
  const track=unique(snapshot.songSpec.tracks,'TRACK',t=>
    normalized(t.name||'')===normalized(trackText)||normalized(t.track_id)===normalized(trackText));
  if(section.sonic_lock===true||track.sonic_lock===true) throw Error('SONIC_LOCK_BLOCKS_EDIT');
  const edit={sectionId:section.id,trackId:track.track_id,semitones:verb.toLowerCase()==='lower'?-12:12};
  return Object.freeze({schemaVersion:'sara.conversational-edit-proposal.v1',operationId,
    projectId:snapshot.manifest.projectId,
    expectedCurrentRevisionId:snapshot.revision.revisionId,
    sourceFingerprint:fingerprint(snapshot.songSpec),edit:Object.freeze(edit)});
}
function preview(proposal,snapshot) {
  requireSnapshot(snapshot);
  if(proposal?.schemaVersion!=='sara.conversational-edit-proposal.v1'||
     proposal.projectId!==snapshot.manifest.projectId ||
     proposal.expectedCurrentRevisionId!==snapshot.revision.revisionId ||
     proposal.sourceFingerprint!==fingerprint(snapshot.songSpec)) throw Error('SOURCE_REVISION_OR_CONTENT_MISMATCH');
  const original=snapshot.songSpec;
  const candidate=transposeSection(original,proposal.edit);
  const origTrack=unique(original.tracks,'TRACK',x=>x.track_id===proposal.edit.trackId);
  const nextTrack=unique(candidate.tracks,'TRACK',x=>x.track_id===proposal.edit.trackId);
  if(origTrack.events.length!==nextTrack.events.length) throw Error('PRESERVATION_EVENT_COUNT_CHANGED');
  const diff=[];
  for(let i=0;i<origTrack.events.length;i++) {
    const before=origTrack.events[i],after=nextTrack.events[i];
    if(fingerprint(before)===fingerprint(after)) continue;
    if(before.type!=='NOTE_ON'||after.type!=='NOTE_ON'||before.event_id!==after.event_id ||
       before.tick!==after.tick ||before.duration_ticks!==after.duration_ticks ||
       after.note_number-before.note_number!==proposal.edit.semitones)
       throw Error('PRESERVATION_EVENT_MISMATCH');
    const expected={...before,note_number:before.note_number+proposal.edit.semitones};
    if(fingerprint(expected)!==fingerprint(after)) throw Error('PRESERVATION_EVENT_MISMATCH');
    diff.push({eventId:before.event_id??null,eventIndex:i,trackId:proposal.edit.trackId,
      tick:before.tick,beforePitch:before.note_number,afterPitch:after.note_number});
  }
  if(!diff.length) throw Error('NO_VERIFIABLE_TARGET_EVENTS');
  const rest=clone(original);
  rest.tracks=rest.tracks.filter(t=>t.track_id!==proposal.edit.trackId);
  const untouched=clone(candidate);
  untouched.tracks=untouched.tracks.filter(t=>t.track_id!==proposal.edit.trackId);
  if(fingerprint(rest)!==fingerprint(untouched)) throw Error('PRESERVATION_NON_TARGET_CHANGED');
  return Object.freeze({...proposal,preservationTier:'P0_EVENT_CANDIDATE',
    audioStatus:'UNRENDERED',sourceAssetDigests:clone(snapshot.revision.sourceAssetDigests||[]),
    diff:Object.freeze(diff),songSpec:candidate});
}
async function commit(proof,{approved,io}={}) {
  if(approved!==true) throw Error('EXPLICIT_APPROVAL_REQUIRED');
  if(!proof || proof.preservationTier!=='P0_EVENT_CANDIDATE'||
     proof.audioStatus!=='UNRENDERED'||typeof io?.commit!=='function')
    throw Error('CANONICAL_COMMIT_REQUIRED');
  // Backend owns idempotency, expectedCurrentRevisionId fencing and durability.
  // Never retry a 409 or an ambiguous lost response without authoritative readback.
  const result=await io.commit({
    projectId:proof.projectId,expectedCurrentRevisionId:proof.expectedCurrentRevisionId,
    operationId:proof.operationId,songSpec:clone(proof.songSpec),
    sourceAssetDigests:clone(proof.sourceAssetDigests),outputArtifactIds:[],
    operationContext:{kind:'transpose-section',edit:clone(proof.edit)}
  });
  if(!result?.revision?.revisionId || !result?.manifest?.currentRevisionId)
    throw Error('COMMIT_RECEIPT_INCOMPLETE_RECHECK_AUTHORITY');
  return {revision:result.revision,manifest:result.manifest,audioStatus:'UNRENDERED'};
}
module.exports={propose,preview,commit};

"""Durable single-use approval challenges for existing Studio/Platform owners.

This is control-plane intent custody, NOT an alternative music, CAS, billing or
publication authority. A claimed challenge never triggers blind retry.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from platform_identity import PlatformStore,PlatformDenied,PlatformConflict,_SCHEMA_INIT_LOCK

class PlatformServiceUnavailable(RuntimeError):
 pass

_TTL_SECONDS=300
_APPROVABLE=frozenset({"MASTER","TRANSCRIBE_MIDI","REPAINT","ADD_SCRATCH",
                       "TOGGLE_LOCK","CREATE_MUSIC_VIDEO_GRANT","PUBLISH"})
_EXECUTABLE=frozenset({"MASTER","TRANSCRIBE_MIDI","PUBLISH",
                       "TOGGLE_LOCK","CREATE_MUSIC_VIDEO_GRANT","ADD_SCRATCH","REPAINT"})

def _canonical(data):
 return json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)

def _digest(action,project,revision,proposal):
 return hashlib.sha256(_canonical({
    'action':action,'projectId':project,'expectedCurrentRevisionId':revision,
    'proposal':proposal}).encode()).hexdigest()

class ApprovalStore:
 def __init__(self,root):
  self.root=root
  self.store=PlatformStore(root)
  with _SCHEMA_INIT_LOCK:
   with self.store._db() as db:
    db.execute("""CREATE TABLE IF NOT EXISTS chat_approvals (
      challenge_id TEXT PRIMARY KEY,
      principal TEXT NOT NULL,
      project_id TEXT NOT NULL,
      expected_revision_id TEXT NOT NULL,
      action TEXT NOT NULL,
      operation_digest TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      issued_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'PENDING',
      result_digest TEXT,
      FOREIGN KEY(principal) REFERENCES accounts(principal)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_chat_approvals_owner ON chat_approvals(principal,expires_at,status)")
 def issue(self,principal,proposal,instruction):
  from studio_server import project_operation,ProjectConflict
  if proposal.get('state')!='APPROVAL_REQUIRED' or proposal.get('action') not in _APPROVABLE:
   return proposal
  pid=proposal.get('projectId')
  rid=proposal.get('sourceRevisionId')
  if not isinstance(pid,str) or not isinstance(rid,str):
   return proposal
  # Do not mint a transferable challenge for a source the requester cannot own.
  current=project_operation(self.root,{'projectId':pid},principal_id=principal)
  if current['manifest']['currentRevisionId']!=rid:
   raise PlatformConflict('STALE_REVISION_CHALLENGE')
  action=proposal['action']
  op=proposal.get('proposedRequest')
  if op is None:
   op={'projectId':pid,'revisionId':rid,
       'artifactId':proposal.get('sourceArtifactId'),
       'selectedTrackId':proposal.get('selectedTrackId'),
       'selectedBars':proposal.get('selectedBars'),
       'instruction':proposal.get('instruction')}
  if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>350:
   raise ValueError("INVALID_APPROVED_INSTRUCTION")
  # Persist the exact artist instruction separately from the owner endpoint
  # payload. Never pass prose into master/transcribe/publication owner schemas.
  envelope={"instruction":instruction.strip(),"request":op}
  dig=_digest(action,pid,rid,envelope)
  challenge='appr-'+secrets.token_hex(32)
  now=int(time.time())
  with self.store._db() as db:
   db.execute('BEGIN IMMEDIATE')
   db.execute("""INSERT INTO chat_approvals(
     challenge_id,principal,project_id,expected_revision_id,action,
     operation_digest,payload_json,issued_at,expires_at)
     VALUES(?,?,?,?,?,?,?,?,?)""",
     (challenge,principal,pid,rid,action,dig,_canonical(envelope),now,now+_TTL_SECONDS))
   db.commit()
  return {**proposal,'approval_challenge_id':challenge,
    'operation_digest':dig,'expiresAtUnix':now+_TTL_SECONDS,
    'expiresInSeconds':_TTL_SECONDS,'revisionCommitted':False}
 def claim(self,principal,challenge,expected):
  from studio_server import project_operation
  if not isinstance(challenge,str) or len(challenge)!=69 or not challenge.startswith('appr-'):
   raise PlatformDenied('APPROVAL_CHALLENGE_INVALID')
  try:bytes.fromhex(challenge[5:])
  except ValueError:raise PlatformDenied('APPROVAL_CHALLENGE_INVALID')
  if not isinstance(expected,str) or len(expected)!=64:
   raise PlatformConflict('EXPECTED_CURRENT_REVISION_REQUIRED')
  with self.store._db() as db:
   db.execute('BEGIN IMMEDIATE')
   row=db.execute("""SELECT principal,project_id,expected_revision_id,action,
      operation_digest,payload_json,expires_at,status FROM chat_approvals WHERE challenge_id=?""",
      (challenge,)).fetchone()
   if not row or not hmac.compare_digest(row['principal'],principal):
    raise PlatformDenied('APPROVAL_CHALLENGE_DENIED')
   if row['status']!='PENDING' or row['expires_at']<=int(time.time()):
    raise PlatformDenied('APPROVAL_EXPIRED_OR_ALREADY_USED')
   if expected!=row['expected_revision_id']:
    raise PlatformConflict('STALE_APPROVAL_EXPECTED_REVISION')
   op=json.loads(row['payload_json'])
   if _digest(row['action'],row['project_id'],expected,op)!=row['operation_digest']:
    raise PlatformDenied('APPROVAL_OPERATION_DIGEST_INVALID')
   current=project_operation(self.root,{'projectId':row['project_id']},principal_id=principal)
   if current['manifest']['currentRevisionId']!=expected:
    raise PlatformConflict('STALE_APPROVAL_SOURCE_REVISION')
   updated=db.execute("""UPDATE chat_approvals SET status='CLAIMED'
     WHERE challenge_id=? AND status='PENDING'""",(challenge,))
   if updated.rowcount!=1:raise PlatformDenied('APPROVAL_ALREADY_USED')
   db.commit()
  if not isinstance(op,dict) or not isinstance(op.get("request"),dict):
   raise PlatformDenied("APPROVAL_OPERATION_ENVELOPE_INVALID")
  return dict(row)|{'operation':op["request"],'instruction':op["instruction"]}
 def settle(self,challenge,principal,state,result=None):
  digest=hashlib.sha256(_canonical(result or {}).encode()).hexdigest()
  with self.store._db() as db:
   db.execute('BEGIN IMMEDIATE')
   db.execute("""UPDATE chat_approvals SET status=?,result_digest=?
       WHERE challenge_id=? AND principal=? AND status='CLAIMED'""",
       (state,digest,challenge,principal))
   db.commit()

def approved_operation(root,principal,challenge,expected,rights_policy=None):
 from studio_server import project_operation,project_audio_bytes
 store=ApprovalStore(root)
 row=store.claim(principal,challenge,expected)
 action=row['action'];op=row['operation']
 if action not in _EXECUTABLE:
  store.settle(challenge,principal,'OWNER_UNQUALIFIED',{'action':action})
  raise PlatformConflict('CANONICAL_OWNER_EXECUTOR_UNQUALIFIED')
 try:
  if action=='MASTER':
   from m045_wave4_service import authorized_master
   result=authorized_master(root,op,principal_id=principal)
   revision=result['revisionId']
   check=project_audio_bytes(root,{'projectId':row['project_id'],
      'revisionId':revision,'artifactId':result['artifactId']},principal_id=principal)
   if hashlib.sha256(check).hexdigest()!=result['artifactId']:
    raise ValueError('APPROVED_MASTER_READBACK_FAILED')
   committed=True
  elif action=='TRANSCRIBE_MIDI':
   from m045_wave3_service import authorized_transcribe
   result=authorized_transcribe(root,op,principal_id=principal)
   committed=False
  elif action=='TOGGLE_LOCK':
   from m045_chat_owner_operations import authorized_toggle_lock
   result=authorized_toggle_lock(root,op,principal_id=principal)
   committed=True
  elif action=='REPAINT':
   from m045_chat_repaint_owner import authorized_repaint
   result=authorized_repaint(root,op,principal,row["instruction"],challenge)
   committed=True
  elif action=='ADD_SCRATCH':
   from m045_chat_owner_operations import authorized_add_scratch
   result=authorized_add_scratch(root,op,principal_id=principal)
   committed=True
  elif action=='CREATE_MUSIC_VIDEO_GRANT':
   from studio_server import M045_GRANT_SIGNING_RING,M045_GRANT_RIGHTS_POLICY
   if M045_GRANT_SIGNING_RING is None or M045_GRANT_RIGHTS_POLICY is None:
    store.settle(challenge,principal,'HOST_GRANT_ISSUER_UNCONFIGURED')
    raise PlatformServiceUnavailable('HOST_SOUNDTRACK_ISSUER_UNCONFIGURED')
   from m045_soundtrack_grant import issue_authorized_grant
   result=issue_authorized_grant(root=root,request=op,principal_id=principal,
     ring=M045_GRANT_SIGNING_RING,read_project=project_operation,
     read_audio=project_audio_bytes,rights_policy=M045_GRANT_RIGHTS_POLICY)
   committed=False
  elif action=='PUBLISH':
   from platform_catalog import authorized_publish
   if rights_policy is None:
    store.settle(challenge,principal,'RIGHTS_POLICY_UNQUALIFIED')
    raise PlatformDenied('PUBLICATION_RIGHTS_POLICY_NOT_CONFIGURED')
   result=authorized_publish(root,op,principal,rights_policy)
   committed=False
  store.settle(challenge,principal,'SUCCEEDED',{'action':action,'revision':result.get('revisionId')})
  return {'status':'SUCCESS','state':'EXECUTED','action':action,
          'revisionCommitted':committed,'approvalChallengeConsumed':True,
          'sourceRevisionId':row['expected_revision_id'],'operationDigest':row['operation_digest'],
          'operationResult':result}
 except ValueError as error:
  if action=="MASTER" and str(error) in {
      "INDEPENDENT_TRUE_PEAK_CEILING_FAILED",
      "MASTER_REFERENCE_TRUE_PEAK_CEILING_FAILED"}:
   store.settle(challenge,principal,'MASTER_REJECTED_BY_INDEPENDENT_METER')
   raise PlatformConflict("MASTER_TRUE_PEAK_CEILING_NOT_VERIFIED") from error
  # An unexpected error may follow an effect; never blindly retry.
  store.settle(challenge,principal,'RECONCILIATION_REQUIRED')
  raise
 except Exception:
  # Effect may be ambiguous. Never return challenge to PENDING or auto-retry.
  store.settle(challenge,principal,'RECONCILIATION_REQUIRED')
  raise
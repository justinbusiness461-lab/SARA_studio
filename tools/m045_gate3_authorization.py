"""R11-A host-only Gate3 approval custody; NEVER dispatches paid GPU work.

Artist creates a pending *request*, which cannot self-approve. Only trusted
host code with a private signer and independent attest callback may admit it.
Redemption atomically consumes once while retaining DRY_RUN_ONLY semantics.
"""
from __future__ import annotations
import hashlib,hmac,json,math,re,secrets,time
from platform_identity import PlatformStore,PlatformDenied,PlatformConflict,_SCHEMA_INIT_LOCK

FIELDS=frozenset({'projectId','baseRevisionId','modelId','checkpointManifestSha256',
    'maxUsdCents','maxAudioDurationSec','maxContainerRuntimeSec','ttlSeconds'})
HEX64=re.compile('[0-9a-f]{64}\\Z')

def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

def validate(scope):
 if not isinstance(scope,dict) or set(scope)!=FIELDS:raise ValueError('GATE3_SCOPE_FIELDS_INVALID')
 if not isinstance(scope['projectId'],str) or not scope['projectId'] or not isinstance(scope['baseRevisionId'],str) or not HEX64.fullmatch(scope['baseRevisionId']):
  raise ValueError('GATE3_SOURCE_REVISION_INVALID')
 if scope['modelId']!='acestep-v15-turbo' or not isinstance(scope['checkpointManifestSha256'],str) or not HEX64.fullmatch(scope['checkpointManifestSha256']):
  raise ValueError('GATE3_MODEL_UNQUALIFIED')
 if (type(scope['maxUsdCents']) is not int or not 1<=scope['maxUsdCents']<=100
     or type(scope['ttlSeconds']) is not int or not 1<=scope['ttlSeconds']<=900
     or type(scope['maxContainerRuntimeSec']) is not int or not 1<=scope['maxContainerRuntimeSec']<=180
     or type(scope['maxAudioDurationSec']) not in (int,float) or not math.isfinite(scope['maxAudioDurationSec'])
     or not 0<scope['maxAudioDurationSec']<=20):
  raise ValueError('GATE3_SPEND_AND_RUNTIME_BOUNDS_INVALID')
 return scope

class Gate3AuthorizationStore:
 def __init__(self,root,host_signing_key):
  if not isinstance(host_signing_key,bytes) or len(host_signing_key)<32:
   raise PlatformDenied('GATE3_HOST_SIGNER_NOT_CONFIGURED')
  self.key=host_signing_key
  self.db=PlatformStore(root)
  self.root=root
  with _SCHEMA_INIT_LOCK:
   with self.db._db() as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS gate3_spend_requests(
        request_id TEXT PRIMARY KEY,principal TEXT NOT NULL,project_id TEXT NOT NULL,
        revision_id TEXT NOT NULL,scope_json TEXT NOT NULL,scope_digest TEXT NOT NULL,
        requested_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,
        state TEXT NOT NULL,token_digest TEXT,
        FOREIGN KEY(principal) REFERENCES accounts(principal))''')
 def _current(self,principal,scope):
  from studio_server import project_operation
  chosen=project_operation(self.root,{'projectId':scope['projectId']},principal_id=principal)
  if chosen['manifest']['currentRevisionId']!=scope['baseRevisionId']:
   raise PlatformConflict('GATE3_STALE_PROJECT_REVISION')
 def request(self,principal,scope):
  scope=validate(scope);self.db.profile(principal);self._current(principal,scope)
  rid='g3req-'+secrets.token_hex(32);now=int(time.time());digest=hashlib.sha256(canonical(scope).encode()).hexdigest()
  with self.db._db() as conn:
   conn.execute('BEGIN IMMEDIATE')
   conn.execute('''INSERT INTO gate3_spend_requests VALUES(?,?,?,?,?,?,?,?,?,?)''',
    (rid,principal,scope['projectId'],scope['baseRevisionId'],canonical(scope),digest,now,
     now+scope['ttlSeconds'],'PENDING_HOST_APPROVAL',None));conn.commit()
  return {'state':'PENDING_HOST_APPROVAL','requestId':rid,'scopeDigest':digest,
    'expiresAtUnix':now+scope['ttlSeconds'],'trialAuthorized':False,'chargesIncurredUsd':0}
 def _signature(self,request_id,scope_digest,expires):
  return hmac.new(self.key,f'{request_id}|{scope_digest}|{expires}'.encode(),'sha256').hexdigest()
 def admit_host(self,request_id,host_attestor):
  if not callable(host_attestor):raise PlatformDenied('GATE3_TRUSTED_HOST_ATTESTOR_REQUIRED')
  with self.db._db() as conn:
   conn.execute('BEGIN IMMEDIATE')
   row=conn.execute('SELECT * FROM gate3_spend_requests WHERE request_id=?',(request_id,)).fetchone()
   if row is None or row['state']!='PENDING_HOST_APPROVAL' or row['expires_at']<=int(time.time()):
    raise PlatformDenied('GATE3_REQUEST_EXPIRED_OR_USED')
   scope=json.loads(row['scope_json']);validate(scope)
   self.db.profile(row['principal']);self._current(row['principal'],scope)
   # Callback is a host-only, independently authorized function, never a client
   # or HTTP-supplied boolean. No paid dispatch even if it returns True.
   if host_attestor({**scope,'principalId':row['principal']}) is not True:
    raise PlatformDenied('GATE3_INDEPENDENT_HOST_APPROVAL_REQUIRED')
   nonce=secrets.token_hex(32)
   signature=self._signature(request_id,row['scope_digest'],row['expires_at'])
   token='g3-'+nonce+signature
   conn.execute('''UPDATE gate3_spend_requests SET state='ADMITTED_OFFLINE',token_digest=?
                 WHERE request_id=? AND state='PENDING_HOST_APPROVAL' ''',
                (hashlib.sha256(token.encode()).hexdigest(),request_id))
   conn.commit();return token
 def redeem(self,principal,token,scope):
  validate(scope)
  if not isinstance(token,str) or not re.fullmatch('g3-[0-9a-f]{128}',token):
   raise PlatformDenied('GATE3_TOKEN_MALFORMED')
  with self.db._db() as conn:
   conn.execute('BEGIN IMMEDIATE')
   row=conn.execute('SELECT * FROM gate3_spend_requests WHERE token_digest=?',
                    (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
   if row is None or not hmac.compare_digest(row['principal'],principal):
    raise PlatformDenied('GATE3_TOKEN_DENIED')
   if row['state']!='ADMITTED_OFFLINE' or row['expires_at']<=int(time.time()):
    raise PlatformDenied('GATE3_TOKEN_ALREADY_USED_OR_EXPIRED')
   if not hmac.compare_digest(row['scope_digest'],hashlib.sha256(canonical(scope).encode()).hexdigest()):
    raise PlatformConflict('GATE3_TOKEN_SCOPE_MISMATCH')
   if not hmac.compare_digest(token[-64:],self._signature(row['request_id'],row['scope_digest'],row['expires_at'])):
    raise PlatformDenied('GATE3_HOST_SIGNATURE_INVALID')
   self.db.profile(principal);self._current(principal,scope)
   updated=conn.execute('''UPDATE gate3_spend_requests SET state='CONSUMED_OFFLINE'
                     WHERE request_id=? AND state='ADMITTED_OFFLINE' ''',(row['request_id'],))
   if updated.rowcount!=1:raise PlatformDenied('GATE3_TOKEN_RACE_LOST')
   conn.commit()
  return {'schema':'sara.gate3.spend.challenge.receipt.v1','state':'DRY_RUN_ONLY',
          'scopeDigest':row['scope_digest'],'maxUsdCents':scope['maxUsdCents'],
          'modelId':scope['modelId'],'checkpointManifestSha256':scope['checkpointManifestSha256'],
          'tokenConsumed':True,'trialAuthorized':False,'remoteExecutionEnabled':False,
          'providerCallsMade':0,'chargesIncurredUsd':0,
          'gateHolds':['NO_LIVE_PROVIDER_ADAPTER','INDEPENDENT_PROVIDER_COST_CAP_UNVERIFIED',
                       'MODEL_LICENSE_AND_CHECKPOINT_UNQUALIFIED','LIVE_OWNER_SPEND_AUTH_NOT_ISSUED']}

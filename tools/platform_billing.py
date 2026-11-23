"""Local S.A.R.A. credit ledger. Never trusts a browser-supplied payment success.

The production provider webhook verifier must be installed by the host; there
is no client-accessible mint-credits endpoint. In-flight ambiguous jobs remain
RESERVED until authoritative reconciliation. SQLite IMMEDIATE serializes spends.
"""
from __future__ import annotations
import hashlib,hmac,re,time
from platform_identity import PlatformStore,PlatformDenied,PlatformConflict

_KEY=re.compile(r"[A-Za-z0-9][A-Za-z0-9_:.@/-]{0,126}\Z")
def _key(value):
 if not isinstance(value,str) or not _KEY.fullmatch(value):
  raise ValueError("INVALID_IDEMPOTENCY_ID")
 return value
def _count(value,max_value=1000000):
 if type(value)!=int or not 1<=value<=max_value:raise ValueError("INVALID_CREDIT_COUNT")
 return value

class CreditLedger:
 def __init__(self,root):
  self.identity=PlatformStore(root)
  with self.identity._db() as db:
   db.executescript("""
CREATE TABLE IF NOT EXISTS platform_credit_grants(
 provider_event TEXT PRIMARY KEY,principal TEXT NOT NULL,credits INTEGER NOT NULL,
 issued_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS platform_credit_jobs(
 principal TEXT NOT NULL,job_key TEXT NOT NULL,credits INTEGER NOT NULL,
 state TEXT NOT NULL,created_at INTEGER NOT NULL,
 PRIMARY KEY(principal,job_key));
""")
 def grant_host_verified(self,principal,event_id,credits,verifier):
  """Host-only payment reconciliation; require independent verifier callback."""
  self.identity.profile(principal)
  _key(event_id);_count(credits)
  if not callable(verifier) or verifier(event_id,credits) is not True:
   raise PlatformDenied("PAYMENT_PROVIDER_ATTESTATION_REQUIRED")
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   prior=db.execute("SELECT principal,credits FROM platform_credit_grants WHERE provider_event=?",(event_id,)).fetchone()
   if prior:
    if prior["principal"]!=principal or prior["credits"]!=credits:
     raise PlatformConflict("WEBHOOK_REPLAY_CONTENT_CHANGED")
    db.commit();return False
   db.execute("INSERT INTO platform_credit_grants VALUES(?,?,?,?)",
      (event_id,principal,credits,int(time.time())))
   db.commit();return True
 def _balance(self,db,principal):
  granted=db.execute("SELECT COALESCE(SUM(credits),0) FROM platform_credit_grants WHERE principal=?",(principal,)).fetchone()[0]
  reserved=db.execute("SELECT COALESCE(SUM(credits),0) FROM platform_credit_jobs"
    " WHERE principal=? AND state='RESERVED'",(principal,)).fetchone()[0]
  settled=db.execute("SELECT COALESCE(SUM(credits),0) FROM platform_credit_jobs"
    " WHERE principal=? AND state='SETTLED'",(principal,)).fetchone()[0]
  return {"available":granted-reserved-settled,"reserved":reserved,"spent":settled,"granted":granted}
 def balance(self,principal):
  self.identity.profile(principal)
  with self.identity._db() as db:summary=self._balance(db,principal)
  return {"status":"SUCCESS",**summary}
 def quote(self,principal,units,unit_cost=1):
  self.identity.profile(principal)
  units=_count(units,1000);cost=_count(unit_cost,1000)
  required=units*cost
  return {"status":"QUOTED","units":units,"credits":required,"balance":self.balance(principal)}
 def reserve(self,principal,job_key,credits):
  self.identity.profile(principal);_key(job_key);_count(credits)
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   prior=db.execute("SELECT credits,state FROM platform_credit_jobs WHERE principal=? AND job_key=?",
     (principal,job_key)).fetchone()
   if prior:
    if prior["credits"]!=credits:raise PlatformConflict("JOB_KEY_USED_WITH_DIFFERENT_COST")
    result={"jobKey":job_key,"state":prior["state"],"credits":credits};db.commit();return result
   if self._balance(db,principal)["available"]<credits:raise PlatformDenied("INSUFFICIENT_CREDITS")
   db.execute("INSERT INTO platform_credit_jobs VALUES(?,?,?,?,?)",
    (principal,job_key,credits,"RESERVED",int(time.time())))
   db.commit()
  return {"jobKey":job_key,"state":"RESERVED","credits":credits}
 def finalize(self,principal,job_key,outcome):
  self.identity.profile(principal);_key(job_key)
  if outcome not in {"COMMITTED","FAILED_PRE_COMMIT"}:
   raise PlatformDenied("AUTHORITATIVE_OUTCOME_REQUIRED")
  goal="SETTLED" if outcome=="COMMITTED" else "REFUNDED"
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   row=db.execute("SELECT state,credits FROM platform_credit_jobs WHERE principal=? AND job_key=?",
     (principal,job_key)).fetchone()
   if row is None:raise PlatformDenied("JOB_NOT_FOUND")
   if row["state"]==goal:db.commit();return {"jobKey":job_key,"state":goal,"credits":row["credits"]}
   if row["state"]!="RESERVED":raise PlatformConflict("JOB_ALREADY_FINALIZED")
   db.execute("UPDATE platform_credit_jobs SET state=? WHERE principal=? AND job_key=? AND state='RESERVED'",
      (goal,principal,job_key))
   db.commit()
  return {"jobKey":job_key,"state":goal,"credits":row["credits"]}
 def job(self,principal,job_key):
  self.identity.profile(principal);_key(job_key)
  with self.identity._db() as db:
   row=db.execute("SELECT state,credits FROM platform_credit_jobs WHERE principal=? AND job_key=?",
    (principal,job_key)).fetchone()
  if not row:raise PlatformDenied("JOB_NOT_FOUND")
  return {"jobKey":job_key,"state":row["state"],"credits":row["credits"]}

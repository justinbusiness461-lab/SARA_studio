"""Workspace collaboration overlay subordinate to Studio project/revision authority.

Permission for audio is derived from an explicit owner-bound project mapping plus
a *currently active* workspace member. Revocation is checked on every read.
There is deliberately no delegated write route pending exact change-isolation proof.
"""
from __future__ import annotations
import re,secrets,time
from platform_identity import PlatformStore,PlatformDenied,PlatformConflict

_WSID=re.compile(r"ws-[0-9a-f]{32}\Z")
_PROJECT=re.compile(r"[0-9a-f]{32}\Z")
def _ws(value):
 if not isinstance(value,str) or not _WSID.fullmatch(value):raise PlatformDenied("WORKSPACE_DENIED")
 return value

class WorkspaceStore:
 def __init__(self,root):
  self.root=root;self.identity=PlatformStore(root)
  with self.identity._db() as db:
   db.executescript("""
CREATE TABLE IF NOT EXISTS platform_workspaces(
 id TEXT PRIMARY KEY,owner TEXT NOT NULL,name TEXT NOT NULL,created INTEGER NOT NULL,
 FOREIGN KEY(owner) REFERENCES accounts(principal));
CREATE TABLE IF NOT EXISTS platform_workspace_members(
 workspace TEXT NOT NULL,principal TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL,
 PRIMARY KEY(workspace,principal));
CREATE TABLE IF NOT EXISTS platform_workspace_projects(
 workspace TEXT NOT NULL,project TEXT NOT NULL,owner TEXT NOT NULL,
 PRIMARY KEY(workspace,project));
""")
 def create(self,owner,name):
  self.identity.profile(owner)
  if not isinstance(name,str) or not 1<=len(name.strip())<=120:raise ValueError("INVALID_WORKSPACE_NAME")
  ws="ws-"+secrets.token_hex(16)
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   db.execute("INSERT INTO platform_workspaces VALUES(?,?,?,?)",(ws,owner,name.strip(),int(time.time())))
   db.execute("INSERT INTO platform_workspace_members VALUES(?,?,?,1)",(ws,owner,"owner"))
   db.commit()
  return {"workspaceId":ws,"ownerPrincipalId":owner,"name":name.strip()}
 def _owner(self,db,actor,workspace):
  row=db.execute("SELECT owner FROM platform_workspaces WHERE id=?",(workspace,)).fetchone()
  if not row or row["owner"]!=actor:raise PlatformDenied("WORKSPACE_OWNER_REQUIRED")
  return row["owner"]
 def member_role(self,actor,workspace):
  _ws(workspace)
  with self.identity._db() as db:
   row=db.execute("SELECT role FROM platform_workspace_members WHERE workspace=? AND principal=? AND active=1",
      (workspace,actor)).fetchone()
  return row["role"] if row else None
 def my_workspaces(self,actor):
  self.identity.profile(actor)
  with self.identity._db() as db:
   rows=db.execute("""SELECT w.id,w.name,w.owner,m.role FROM platform_workspaces w
JOIN platform_workspace_members m ON m.workspace=w.id AND m.principal=?
WHERE m.active=1 ORDER BY w.created DESC,w.id DESC LIMIT 200""",(actor,)).fetchall()
  return [{"workspaceId":r["id"],"name":r["name"],"role":r["role"],
     "ownerPrincipalId":r["owner"]} for r in rows]
 def invite(self,actor,workspace,handle,role):
  _ws(workspace)
  if role not in {"viewer","editor"}:raise ValueError("INVALID_WORKSPACE_ROLE")
  if not isinstance(handle,str):raise ValueError("INVALID_HANDLE")
  profile=self.identity.public_profile(handle)
  if profile is None:raise PlatformDenied("INVITEE_NOT_FOUND")
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE");self._owner(db,actor,workspace)
   target=db.execute("SELECT principal FROM accounts WHERE handle=?",(profile["handle"],)).fetchone()["principal"]
   if target==actor:raise PlatformDenied("OWNER_ROLE_IMMUTABLE")
   db.execute("INSERT INTO platform_workspace_members VALUES(?,?,?,1)"
     " ON CONFLICT(workspace,principal) DO UPDATE SET role=excluded.role,active=1",
      (workspace,target,role))
   db.commit()
  return {"workspaceId":workspace,"role":role,"invitee":profile["handle"]}
 def revoke(self,actor,workspace,handle):
  _ws(workspace)
  profile=self.identity.public_profile(handle)
  if profile is None:raise PlatformDenied("MEMBER_NOT_FOUND")
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE");self._owner(db,actor,workspace)
   target=db.execute("SELECT principal FROM accounts WHERE handle=?",(profile["handle"],)).fetchone()["principal"]
   if target==actor:raise PlatformDenied("OWNER_CANNOT_BE_REVOKED")
   db.execute("UPDATE platform_workspace_members SET active=0 WHERE workspace=? AND principal=?",
              (workspace,target))
   db.commit()
  return {"status":"SUCCESS","revoked":True}
 def bind_project(self,actor,workspace,project_id):
  from studio_server import project_operation
  _ws(workspace)
  if not isinstance(project_id,str) or not _PROJECT.fullmatch(project_id):
   raise PlatformDenied("PROJECT_DENIED")
  with self.identity._db() as db:self._owner(db,actor,workspace)
  # The canonical music owner must authenticate *the project owner*, not a
  # collaborator-provided CAS digest. No workspace record creates project ownership.
  try:project_operation(self.root,{"projectId":project_id},principal_id=actor)
  except (PermissionError,ValueError,OSError) as exc:
   raise PlatformDenied("PROJECT_NOT_OWNED") from exc
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE");self._owner(db,actor,workspace)
   db.execute("INSERT OR IGNORE INTO platform_workspace_projects VALUES(?,?,?)",(workspace,project_id,actor))
   db.commit()
  return {"workspaceId":workspace,"projectId":project_id}
 def _grant(self,db,actor,workspace,project_id):
  row=db.execute("""SELECT w.owner,m.role FROM platform_workspaces w
JOIN platform_workspace_members m ON m.workspace=w.id AND m.principal=?
JOIN platform_workspace_projects p ON p.workspace=w.id AND p.project=?
WHERE w.id=? AND m.active=1 AND p.owner=w.owner""",(actor,project_id,workspace)).fetchone()
  if not row:raise PlatformDenied("WORKSPACE_OR_PROJECT_GRANT_DENIED")
  return row["owner"],row["role"]
 def read_member_audio(self,root,actor,workspace,project_id,artifact_id,revision_id=None):
  from studio_server import project_audio_bytes
  _ws(workspace)
  if revision_id is None:raise PlatformDenied("EXACT_SOURCE_REVISION_REQUIRED")
  with self.identity._db() as db:owner,role=self._grant(db,actor,workspace,project_id)
  # Selection is scoped by project+revision; lawful artifact membership
  # and digest are *always* checked by the original project audio owner.
  try:
   data=project_audio_bytes(root,{"projectId":project_id,
     "revisionId":revision_id,"artifactId":artifact_id},principal_id=owner)
  except (PermissionError,ValueError,OSError) as exc:
   raise PlatformDenied("AUTHORIZED_AUDIO_NOT_AVAILABLE") from exc
  # Recheck after I/O to avoid returning a read initiated before revocation.
  with self.identity._db() as db:self._grant(db,actor,workspace,project_id)
  return data
 def read_member_project(self,root,actor,workspace,project_id,revision_id=None):
  from studio_server import project_operation
  _ws(workspace)
  with self.identity._db() as db:owner,role=self._grant(db,actor,workspace,project_id)
  body={"projectId":project_id}
  if revision_id:body["revisionId"]=revision_id
  try:result=project_operation(root,body,principal_id=owner)
  except (PermissionError,ValueError,OSError) as exc:
   raise PlatformDenied("AUTHORIZED_PROJECT_NOT_AVAILABLE") from exc
  with self.identity._db() as db:self._grant(db,actor,workspace,project_id)
  return result

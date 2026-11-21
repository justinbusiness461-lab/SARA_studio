"""S.A.R.A. PLATFORM-01: local-account identity, durable sessions, artist profiles.

An opt-in localhost development substrate; not a replacement for an audited
production OIDC/OTP identity provider. Account/session/project principal IDs
are separate from public artist handles. Session hashes, never bearer tokens,
cross the SQLite durability boundary. Studio remains the owner of projects.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import os
import json
import re
import secrets
import sqlite3
import time
import threading
from pathlib import Path

class PlatformDenied(PermissionError): pass
class PlatformConflict(ValueError): pass

_HANDLE = re.compile(r"[a-z][a-z0-9_]{2,29}\Z")
_PRINCIPAL = re.compile(r"acct-[0-9a-f]{32}\Z")
_SESSION = re.compile(r"[-_A-Za-z0-9]{38,128}\Z")
_MAX_BIO = 1200
_TTL_SECONDS = 60*60*24*7
_SCHEMA_INIT_LOCK = threading.RLock()

class PlatformStore:
    def __init__(self, root):
        base=Path(root).resolve()
        folder=base/"platform"
        if folder.is_symlink():raise ValueError("unsafe platform directory")
        folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        if folder.is_symlink():raise ValueError("unsafe platform directory")
        self.path=folder/"platform.sqlite3"
        if self.path.is_symlink():raise ValueError("unsafe platform database")
        with _SCHEMA_INIT_LOCK:
            with self._db() as db:
                # Only one local process thread transitions the database to WAL.
                # Never issue PRAGMA journal_mode=WAL on every HTTP read; that
                # can require an exclusive lock and crash concurrent signups.
                if db.execute("PRAGMA journal_mode").fetchone()[0].lower()!="wal":
                    db.execute("PRAGMA journal_mode=WAL")
                db.executescript("""
    CREATE TABLE IF NOT EXISTS accounts (
     principal TEXT PRIMARY KEY, handle TEXT NOT NULL UNIQUE COLLATE NOCASE,
     password_salt BLOB NOT NULL, password_hash BLOB NOT NULL,
     display_name TEXT NOT NULL, bio TEXT NOT NULL DEFAULT '',
     created_at INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active');
    CREATE TABLE IF NOT EXISTS sessions (
     session_id TEXT PRIMARY KEY, principal TEXT NOT NULL,
     token_digest TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL,
     expires_at INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0,
     FOREIGN KEY(principal) REFERENCES accounts(principal));
    CREATE INDEX IF NOT EXISTS idx_session_principal ON sessions(principal, revoked);
    CREATE TABLE IF NOT EXISTS publications (
     publication_id TEXT PRIMARY KEY, principal TEXT NOT NULL, project_id TEXT NOT NULL,
     revision_id TEXT NOT NULL, artifact_id TEXT NOT NULL,
     title TEXT NOT NULL, rights_evidence TEXT NOT NULL,
     published_at INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1,
     UNIQUE(principal, project_id, revision_id, artifact_id),
     FOREIGN KEY(principal) REFERENCES accounts(principal));
    CREATE INDEX IF NOT EXISTS idx_publications_active ON publications(active,published_at);
    CREATE TABLE IF NOT EXISTS account_erasure_requests(
     principal TEXT PRIMARY KEY,
     requested_at INTEGER NOT NULL,
     state TEXT NOT NULL,
     entrypoint TEXT NOT NULL,
     FOREIGN KEY(principal) REFERENCES accounts(principal));
    CREATE TABLE IF NOT EXISTS account_erasure_completion_receipts(
     principal TEXT PRIMARY KEY,
     receipt_json TEXT NOT NULL,
     receipt_sha256 TEXT NOT NULL,
     completed_at INTEGER NOT NULL,
     FOREIGN KEY(principal) REFERENCES accounts(principal));

                """)
        try:os.chmod(self.path,0o600)
        except OSError:pass

    def _db(self):
        db=sqlite3.connect(str(self.path),timeout=10,isolation_level=None)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _handle(value):
        if not isinstance(value,str):raise ValueError("INVALID_HANDLE")
        value=value.strip().lower().removeprefix("@")
        if not _HANDLE.fullmatch(value):raise ValueError("INVALID_HANDLE")
        return value

    @staticmethod
    def _name(value):
        if not isinstance(value,str) or not 1<=len(value.strip())<=80:
            raise ValueError("INVALID_DISPLAY_NAME")
        return html.escape(value.strip(),quote=True)

    @staticmethod
    def _bio(value):
        if not isinstance(value,str) or len(value)>_MAX_BIO:
            raise ValueError("INVALID_BIO")
        return html.escape(value.strip(),quote=True)

    @staticmethod
    def _password(value):
        if not isinstance(value,str) or not 12<=len(value)<=128 or "\x00" in value:
            raise ValueError("PASSWORD_LENGTH_OR_FORMAT_INVALID")
        return value.encode("utf-8")

    @staticmethod
    def _hash(secret, salt):
        return hashlib.scrypt(secret, salt=salt, n=2**14, r=8, p=1, dklen=32)

    def register(self,handle,password,display_name):
        handle=self._handle(handle)
        secret=self._password(password)
        name=self._name(display_name)
        principal="acct-"+secrets.token_hex(16)
        salt=secrets.token_bytes(16)
        digest=self._hash(secret,salt)
        try:
            with self._db() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("INSERT INTO accounts(principal,handle,password_salt,password_hash,display_name,created_at)"
                           " VALUES(?,?,?,?,?,?)",(principal,handle,salt,digest,name,int(time.time())))
                db.commit()
        except sqlite3.IntegrityError as ex:
            raise PlatformConflict("HANDLE_ALREADY_TAKEN") from ex
        return {"principalId":principal,"handle":handle,"displayName":name}

    def login(self,handle,password):
        handle=self._handle(handle)
        try:secret=self._password(password)
        except ValueError as error:
            raise PlatformDenied("BAD_CREDENTIALS") from error
        with self._db() as db:
            row=db.execute("SELECT principal,password_salt,password_hash,status FROM accounts WHERE handle=?",
                           (handle,)).fetchone()
            salt=row["password_salt"] if row else b"no-user-salt0001"
            expected=row["password_hash"] if row else b"\x00"*32
            digest=self._hash(secret,salt)
            if not row or row["status"]!="active" or not hmac.compare_digest(expected,digest):
                raise PlatformDenied("BAD_CREDENTIALS")
            token=secrets.token_urlsafe(48)
            sess_id="sess-"+secrets.token_hex(16)
            now=int(time.time())
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO sessions(session_id,principal,token_digest,created_at,expires_at)"
                       " VALUES(?,?,?,?,?)",(sess_id,row["principal"],hashlib.sha256(token.encode()).hexdigest(),
                                                 now,now+_TTL_SECONDS))
            db.commit()
        return token,{"sessionId":sess_id,"expiresAt":now+_TTL_SECONDS}

    def session_principal(self,token):
        if not isinstance(token,str) or not _SESSION.fullmatch(token):
            raise PlatformDenied("SESSION_DENIED")
        digest=hashlib.sha256(token.encode()).hexdigest()
        with self._db() as db:
            row=db.execute("SELECT s.principal FROM sessions s JOIN accounts a ON a.principal=s.principal"
              " WHERE s.token_digest=? AND s.revoked=0 AND s.expires_at>? AND a.status='active'",
              (digest,int(time.time()))).fetchone()
        if row is None:raise PlatformDenied("SESSION_DENIED")
        return row["principal"]

    def request_account_erasure(self,principal,entrypoint):
        """Durably request erasure and immediately revoke sessions/publication.

        Account erasure is NOT complete until a separately authorized purge
        owner physically removes eligible data and records retention exceptions.
        """
        if entrypoint not in {"in_app","external_web"}:
            raise ValueError("INVALID_ERASURE_ENTRYPOINT")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            account=db.execute("SELECT status FROM accounts WHERE principal=?",(principal,)).fetchone()
            if account is None or account["status"]!="active":
                raise PlatformDenied("ACCOUNT_ERASURE_DENIED")
            now=int(time.time())
            db.execute("INSERT INTO account_erasure_requests VALUES(?,?,?,?)",
                (principal,now,"PENDING",entrypoint))
            db.execute("UPDATE accounts SET status='deletion_pending' WHERE principal=? AND status='active'",
                (principal,))
            db.execute("UPDATE sessions SET revoked=1 WHERE principal=?",(principal,))
            db.execute("UPDATE publications SET active=0 WHERE principal=?",(principal,))
            db.commit()
        return {"status":"ACCEPTED","state":"ERASURE_PENDING","erasureComplete":False,
                "sessionsRevoked":True,"catalogUnpublished":True}

    def process_pending_account_erasures(self, limit=50):
        """Deterministic, atomic mutable-data purge; NOT physical Studio media erasure.

        Keeps a non-loginable principal tombstone to preserve rights/financial
        referential integrity and project provenance. A separate authorized,
        retention-reviewed Studio operation must handle immutable audio and
        revisions. The result must NEVER claim full erasure.
        """
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("INVALID_ERASURE_BATCH_LIMIT")
        retained=("immutable_project_revisions","source_and_render_artifacts",
                  "financial_ledger_tombstones","rights_and_publication_audit")
        processed=0
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            rows=db.execute("""SELECT r.principal FROM account_erasure_requests r
                JOIN accounts a ON a.principal=r.principal
                WHERE r.state='PENDING' AND a.status='deletion_pending'
                ORDER BY r.requested_at,r.principal LIMIT ?""",(limit,)).fetchall()
            for row in rows:
                principal=row["principal"]
                def run(table,query,*params):
                    if table in tables:db.execute(query,(principal,*params))
                # Artist-authored mutable social drafts and engagement.
                for child,parent,parent_id in (
                    ("social_playlist_items","social_playlists","playlist"),
                    ("social_album_items","social_albums","album")):
                    if child in tables and parent in tables:
                        db.execute(f"""DELETE FROM {child} WHERE {parent_id} IN
                            (SELECT id FROM {parent} WHERE principal=?)""",(principal,))
                run("social_playlists","DELETE FROM social_playlists WHERE principal=?")
                run("social_albums","DELETE FROM social_albums WHERE principal=?")
                run("social_follows","DELETE FROM social_follows WHERE follower=? OR followed=?",principal)
                run("social_blocks","DELETE FROM social_blocks WHERE blocker=? OR blocked=?",principal)
                run("social_likes","DELETE FROM social_likes WHERE principal=?")
                run("social_comments_enabled","DELETE FROM social_comments_enabled WHERE principal=?")
                run("social_comments","DELETE FROM social_comments WHERE author=?")
                run("social_notifications","DELETE FROM social_notifications WHERE target=? OR actor=?",principal)
                # Workspace grants and privately named collaboration drafts.
                if "platform_workspaces" in tables:
                    for table in ("platform_workspace_projects","platform_workspace_members"):
                        if table in tables: db.execute(
                            f"DELETE FROM {table} WHERE workspace IN "
                            "(SELECT id FROM platform_workspaces WHERE owner=?)",(principal,))
                    db.execute("DELETE FROM platform_workspaces WHERE owner=?",(principal,))
                run("platform_workspace_members","DELETE FROM platform_workspace_members WHERE principal=?")
                run("platform_workspace_projects","DELETE FROM platform_workspace_projects WHERE owner=?")
                # Unexecuted command proposals can include personal creative prose.
                run("chat_approvals","DELETE FROM chat_approvals WHERE principal=?")
                run("sessions","DELETE FROM sessions WHERE principal=?")
                # Rights/financial audit binds remain, but titles cannot leak.
                run("publications","UPDATE publications SET title='Deleted account publication',active=0 WHERE principal=?")
                # Maintain non-loginable stable principal for provenance/ledger
                # and erase live handle, profile, credential material.
                tombstone="erased_"+hashlib.sha256(principal.encode()).hexdigest()[:22]
                db.execute("""UPDATE accounts
                   SET handle=?,display_name='Deleted account',bio='',
                       password_salt=?,password_hash=?,status='erased_partial'
                   WHERE principal=? AND status='deletion_pending'""",
                   (tombstone,secrets.token_bytes(16),secrets.token_bytes(32),principal))
                db.execute("UPDATE account_erasure_requests SET state='PURGED_MUTABLE' WHERE principal=? AND state='PENDING'",(principal,))
                processed+=1
            db.commit()
        return {"state":"PURGED_MUTABLE" if processed else "NO_PENDING_MUTABLE_ERASURES",
                "processed":processed,"erasureComplete":False,
                "retainedDataClasses":list(retained),
                "requiresOwnerRetentionReview":True}

    def account_erasure_completion_receipt(self,principal):
        """Verify a durable completion receipt; not authorization for retained media."""
        if not isinstance(principal,str) or not _PRINCIPAL.fullmatch(principal):
            raise PlatformDenied("ERASURE_RECEIPT_PRINCIPAL_INVALID")
        with self._db() as db:
            row=db.execute("""SELECT c.receipt_json,c.receipt_sha256,r.state,a.status
                FROM account_erasure_completion_receipts c
                JOIN account_erasure_requests r ON r.principal=c.principal
                JOIN accounts a ON a.principal=c.principal
                WHERE c.principal=?""",(principal,)).fetchone()
        if row is None:return None
        receipt=json.loads(row["receipt_json"])
        unsigned=dict(receipt)
        declared=unsigned.pop("receiptSha256",None)
        encoded=json.dumps(unsigned,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
        if (hashlib.sha256(encoded).hexdigest()!=row["receipt_sha256"]
                or declared!=row["receipt_sha256"]
                or row["state"]!="COMPLETED" or row["status"]!="erasure_completed"):
            raise PlatformDenied("ERASURE_RECEIPT_INTEGRITY_INVALID")
        return receipt

    def complete_account_erasure(self,principal,*,studio_root):
        """Finish *eligible* account-data erasure only with no retained project.

        NEVER marks an account with immutable music or undecidable ownership
        as fully erased. Financial/rights tombstones remain explicitly retained.
        Designed for a host-owned worker; never directly exposed as a public
        HTTP mutation. Atomic state and receipt; reread proof on completion.
        """
        if not isinstance(principal,str) or not _PRINCIPAL.fullmatch(principal):
            raise PlatformDenied("ERASURE_PRINCIPAL_INVALID")
        base=Path(studio_root).resolve()
        if base != self.path.parent.parent.resolve():
            raise PlatformDenied("ERASURE_STUDIO_ROOT_MISMATCH")
        existing=self.account_erasure_completion_receipt(principal)
        if existing is not None:return existing
        # R9 new host-private licensing ledger is a separate principal-bearing
        # store. Its lawful retention must be resolved by the rights owner;
        # never complete eligible erasure while a plaintext principal remains.
        rights_store=base/'.host-rights'/'rights.sqlite3'
        if rights_store.exists() or rights_store.is_symlink():
            if rights_store.is_symlink():
                raise PlatformDenied('ERASURE_HOST_RIGHTS_INVENTORY_UNVERIFIED')
            try:
                from m045_host_authorities import HostRightsRegistry
                has_rights=HostRightsRegistry(base).has_retained_principal(principal)
            except (OSError,ValueError) as error:
                raise PlatformDenied('ERASURE_HOST_RIGHTS_INVENTORY_UNVERIFIED') from error
            if has_rights:
                raise PlatformDenied('ERASURE_HOST_RIGHTS_PERSONAL_IDENTITY_HELD')
        projects=base/"projects"
        if projects.exists():
            for folder in projects.iterdir():
                if folder.name.startswith("."):continue
                if not folder.is_dir() or folder.is_symlink():
                    raise PlatformDenied("ERASURE_PROJECT_OWNER_INVENTORY_UNVERIFIED")
                owner_path=folder/"ProjectOwner.json"
                if not owner_path.is_file() or owner_path.is_symlink():
                    raise PlatformDenied("ERASURE_PROJECT_OWNER_INVENTORY_UNVERIFIED")
                try:
                    owner=json.loads(owner_path.read_text(encoding="utf-8"))
                except (OSError,UnicodeError,json.JSONDecodeError) as error:
                    raise PlatformDenied("ERASURE_PROJECT_OWNER_INVENTORY_UNVERIFIED") from error
                if owner.get("principalId")==principal:
                    raise PlatformDenied("ERASURE_HELD_IMMUTABLE_PROJECT_DATA")
        # Only checked account data qualifies: other external stores and
        # remotes remain unverified, never silently declared physically wiped.
        retained=["legal_financial_ledger_tombstones",
                  "rights_publication_audit_tombstones"]
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("""SELECT a.status,r.state,r.requested_at,r.entrypoint
               FROM accounts a JOIN account_erasure_requests r
                 ON a.principal=r.principal WHERE a.principal=?""",(principal,)).fetchone()
            if row is None or row["status"]!="erased_partial" or row["state"]!="PURGED_MUTABLE":
                raise PlatformDenied("ERASURE_MUTABLE_PURGE_NOT_PROVEN")
            names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            # An unreviewed future table can hold personal data in *any*
            # schema shape. Never certify completion if storage evolved
            # without a corresponding erasure-policy owner decision.
            reviewed={
              "accounts","sessions","publications",
              "account_erasure_requests","account_erasure_completion_receipts",
              "platform_credit_grants","platform_credit_jobs",
              "social_playlists","social_playlist_items",
              "social_albums","social_album_items","social_follows",
              "social_blocks","social_likes","social_comments_enabled",
              "social_comments","social_notifications",
              "platform_workspaces","platform_workspace_members",
              "platform_workspace_projects"}
            unknown=names-reviewed-{"sqlite_sequence"}
            if unknown:
                raise PlatformDenied("ERASURE_SCHEMA_UNREVIEWED")
            refs={"sessions":("principal",),"social_playlists":("principal",),
                  "social_albums":("principal",),"social_comments":("author",),
                  "platform_workspaces":("owner",),"platform_workspace_members":("principal",),
                  "social_likes":("principal",),"social_follows":("follower","followed"),
                  "social_notifications":("target","actor"),"chat_approvals":("principal",)}
            for table,keys in refs.items():
                if table not in names:continue
                columns={x["name"] for x in db.execute(f"PRAGMA table_info({table})")}
                for key in keys:
                    if key in columns and db.execute(
                            f"SELECT 1 FROM {table} WHERE {key}=? LIMIT 1",
                            (principal,)).fetchone():
                        raise PlatformDenied("ERASURE_MUTABLE_RESIDUAL_"+table)
            if "publications" in names:
                if db.execute("""SELECT 1 FROM publications
                  WHERE principal=? AND (active!=0 OR title!='Deleted account publication')
                  LIMIT 1""",(principal,)).fetchone():
                    raise PlatformDenied("ERASURE_PUBLICATION_TOMBSTONE_INVALID")
            # Financial/rights auditing remains pseudonymous; do not claim
            # all account-related bytes in every external system are erased.
            now=int(time.time())
            unsigned={
              "schemaVersion":"sara.account.erasure.completion.v1",
              "state":"ERASURE_COMPLETED",
              "principalDigest":hashlib.sha256(principal.encode()).hexdigest(),
              "requestedAt":row["requested_at"],
              "completedAt":now,
              "entrypoint":row["entrypoint"],
              "eligibleDataErasureComplete":True,
              "allHistoricalRecordsDestroyed":False,
              "retainedDataClasses":retained,
              "projectOwnerInventory":"NO_OWNED_PROJECTS",
              "externalProviderErasure":"NOT_VERIFIED",
              "method":"TRANSACTIONAL_SQL_PURGE_WITH_OWNER_INVENTORY"}
            canonical=json.dumps(unsigned,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
            digest=hashlib.sha256(canonical).hexdigest()
            receipt={**unsigned,"receiptSha256":digest}
            encoded=json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False)
            db.execute("INSERT INTO account_erasure_completion_receipts VALUES(?,?,?,?)",
                       (principal,encoded,digest,now))
            db.execute("UPDATE accounts SET status='erasure_completed' WHERE principal=? AND status='erased_partial'",(principal,))
            db.execute("UPDATE account_erasure_requests SET state='COMPLETED' WHERE principal=? AND state='PURGED_MUTABLE'",(principal,))
            db.commit()
        readback=self.account_erasure_completion_receipt(principal)
        if readback!=receipt:
            raise PlatformDenied("ERASURE_COMPLETION_DURABLE_READBACK_FAILED")
        return readback

    def process_account_erasure_lifecycle(self, *, studio_root, limit=50):
        """Host worker: advance mutable purge, then independently certify scope.

        No timer/queue/cron is implied. Reentrant: each durable transition is
        atomic and already-committed completion receipts remain unchanged.
        """
        mutable=self.process_pending_account_erasures(limit=limit)
        if Path(studio_root).resolve()!=self.path.parent.parent.resolve():
            raise PlatformDenied("ERASURE_STUDIO_ROOT_MISMATCH")
        with self._db() as db:
            rows=db.execute("""SELECT principal FROM account_erasure_requests
                WHERE state='PURGED_MUTABLE' ORDER BY requested_at,principal LIMIT ?""",
                (limit,)).fetchall()
        receipts=[];holds=[]
        for row in rows:
            principal=row["principal"]
            try:
                receipt=self.complete_account_erasure(principal,studio_root=studio_root)
                receipts.append(receipt)
            except PlatformDenied as error:
                # Do not retry/force an ambiguous owner state; retain the
                # PURGED_MUTABLE staging for review and deterministic wake.
                holds.append({"principalDigest":hashlib.sha256(principal.encode()).hexdigest(),
                              "reason":str(error)})
        return {"state":"ERASURE_WORKER_RECONCILED",
                "mutableProcessed":mutable["processed"],
                "completed":len(receipts),"held":len(holds),
                "receipts":receipts,"holds":holds,
                "workerScheduler":"NOT_CONFIGURED"}

    def request_external_erasure(self,handle,password,confirmation):
        if confirmation!="DELETE_MY_ACCOUNT":
            raise ValueError("EXPLICIT_ERASURE_CONFIRMATION_REQUIRED")
        # Credential verification reuses the existing hardened password owner.
        # Any temporary login session created here is revoked atomically by
        # request_account_erasure; no credentials leave the host.
        handle=self._handle(handle)
        token,_=self.login(handle,password)
        principal=self.session_principal(token)
        return self.request_account_erasure(principal,"external_web")

    def revoke_session(self,principal,session_id):
        if not isinstance(session_id,str) or not re.fullmatch(r"sess-[0-9a-f]{32}",session_id):
            raise PlatformDenied("SESSION_DENIED")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor=db.execute("UPDATE sessions SET revoked=1 WHERE principal=? AND session_id=? AND revoked=0",
                              (principal,session_id))
            db.commit()
        if not cursor.rowcount:raise PlatformDenied("SESSION_DENIED")
        return {"status":"SUCCESS","revoked":True}

    def list_sessions(self,principal):
        with self._db() as db:
            rows=db.execute("SELECT session_id,created_at,expires_at FROM sessions"
             " WHERE principal=? AND revoked=0 AND expires_at>? ORDER BY created_at DESC",
             (principal,int(time.time()))).fetchall()
        return [{"sessionId":row["session_id"],"createdAt":row["created_at"],
                 "expiresAt":row["expires_at"]} for row in rows]

    def profile(self,principal):
        with self._db() as db:
            row=db.execute("SELECT principal,handle,display_name,bio FROM accounts"
             " WHERE principal=? AND status='active'",(principal,)).fetchone()
        if row is None:raise PlatformDenied("ACCOUNT_NOT_FOUND")
        return {"principalId":row["principal"],"handle":row["handle"],
          "displayName":row["display_name"],"bio":row["bio"]}

    def update_profile(self,principal,body):
        if not isinstance(body,dict) or set(body)-{"handle","displayName","bio"}:
            raise ValueError("PROFILE_FIELDS_DENIED")
        old=self.profile(principal)
        handle=self._handle(body.get("handle",old["handle"]))
        name=self._name(body.get("displayName",old["displayName"]))
        bio=self._bio(body.get("bio",old["bio"]))
        try:
            with self._db() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("UPDATE accounts SET handle=?,display_name=?,bio=? WHERE principal=?",
                           (handle,name,bio,principal))
                db.commit()
        except sqlite3.IntegrityError as ex:
            raise PlatformConflict("HANDLE_ALREADY_TAKEN") from ex
        return self.profile(principal)

    def public_profile(self,handle):
        try:handle=self._handle(handle)
        except ValueError:return None
        with self._db() as db:
            row=db.execute("SELECT handle,display_name,bio FROM accounts"
             " WHERE handle=? AND status='active'",(handle,)).fetchone()
        return {"handle":row["handle"],"displayName":row["display_name"],
                "bio":row["bio"]} if row else None

    def add_publication(self,principal,project_id,revision_id,artifact_id,title,rights_evidence):
        title=self._name(title[:80] if isinstance(title,str) else "")
        if rights_evidence not in {"ARTIST_OWNED","LICENSE_CLEARED"}:
            raise PlatformDenied("RIGHTS_NOT_VERIFIED")
        now=int(time.time())
        public_id="pub-"+secrets.token_hex(16)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT publication_id FROM publications"
               " WHERE principal=? AND project_id=? AND revision_id=? AND artifact_id=?",
               (principal,project_id,revision_id,artifact_id)).fetchone():
                raise PlatformConflict("ALREADY_PUBLISHED_OR_REVOKED")
            db.execute("INSERT INTO publications(publication_id,principal,project_id,revision_id,"
              "artifact_id,title,rights_evidence,published_at) VALUES(?,?,?,?,?,?,?,?)",
              (public_id,principal,project_id,revision_id,artifact_id,title,rights_evidence,now))
            db.commit()
        return self.publication(public_id)

    def publication(self,pub_id):
        if not isinstance(pub_id,str) or not re.fullmatch(r"pub-[0-9a-f]{32}",pub_id):
            return None
        with self._db() as db:
            row=db.execute("SELECT p.*,a.handle,a.display_name FROM publications p"
              " JOIN accounts a ON a.principal=p.principal"
              " WHERE p.publication_id=? AND p.active=1 AND a.status='active'",(pub_id,)).fetchone()
        return dict(row) if row else None

    def revoke_publication(self,principal,pub_id):
        if not isinstance(pub_id,str) or not re.fullmatch(r"pub-[0-9a-f]{32}",pub_id):
            raise PlatformDenied("PUBLICATION_DENIED")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor=db.execute("UPDATE publications SET active=0 WHERE publication_id=?"
              " AND principal=? AND active=1",(pub_id,principal))
            db.commit()
        if cursor.rowcount!=1:raise PlatformDenied("PUBLICATION_DENIED")
        return {"status":"SUCCESS","unpublished":True}

    def list_publications(self,query="",handle=None,limit=40):
        query=query[:100].strip().lower()
        with self._db() as db:
            sql=("SELECT p.*,a.handle,a.display_name FROM publications p"
              " JOIN accounts a ON a.principal=p.principal"
              " WHERE p.active=1 AND a.status='active'")
            args=[]
            if handle is not None:
                sql+=" AND a.handle=?";args.append(handle)
            if query:
                sql+=" AND (lower(p.title) LIKE ? ESCAPE '\\' OR lower(a.handle) LIKE ? ESCAPE '\\')"
                safe=query.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
                args.extend(["%"+safe+"%","%"+safe+"%"])
            sql+=" ORDER BY p.published_at DESC,p.publication_id DESC LIMIT ?"
            args.append(limit)
            rows=db.execute(sql,args).fetchall()
        return [dict(row) for row in rows]
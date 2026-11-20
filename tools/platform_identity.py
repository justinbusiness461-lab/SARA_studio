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

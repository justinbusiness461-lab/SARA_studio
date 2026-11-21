"""Revision-bound waveform annotations subordinate to canonical Studio audio.

Social feedback is non-authoritative. No comment can select a revision, grant
media access, publish an artifact, or change a music event.
"""
from __future__ import annotations
import io
import hashlib
import hmac
import re
import secrets
import time
import wave
from platform_identity import PlatformDenied, PlatformStore

_PROJECT = re.compile(r'[0-9a-f]{32}\Z')
_REVISION = re.compile(r'[0-9a-f]{64}\Z')

class FeedbackStore:
    def __init__(self, root):
        self.root = root
        self.identity = PlatformStore(root)
        with self.identity._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS revision_timeline_comments(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT NOT NULL UNIQUE,
                    project TEXT NOT NULL,
                    revision TEXT NOT NULL,
                    artifact TEXT NOT NULL,
                    sample_position INTEGER NOT NULL,
                    sample_rate INTEGER NOT NULL,
                    bar_beat_label TEXT NOT NULL,
                    author TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_timeline_comments_anchor
                    ON revision_timeline_comments(project,revision,artifact,sample_position,id);
                CREATE TABLE IF NOT EXISTS private_preview_grants(
                    id TEXT PRIMARY KEY, token_digest TEXT NOT NULL UNIQUE,
                    project TEXT NOT NULL, revision TEXT NOT NULL,
                    artifact TEXT NOT NULL, creator TEXT NOT NULL,
                    created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                    revoked_at INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_private_preview_creator
                    ON private_preview_grants(creator,expires_at);
            """)

    def _source(self, principal, pid, rid, aid):
        from studio_server import project_operation, project_audio_bytes
        if not isinstance(pid,str) or not _PROJECT.fullmatch(pid):
            raise PlatformDenied('FEEDBACK_PROJECT_DENIED')
        if not isinstance(rid,str) or not _REVISION.fullmatch(rid):
            raise PlatformDenied('FEEDBACK_REVISION_DENIED')
        if not isinstance(aid,str) or not _REVISION.fullmatch(aid):
            raise PlatformDenied('FEEDBACK_ARTIFACT_DENIED')
        self.identity.profile(principal)
        try:
            revision = project_operation(self.root, {'projectId':pid,'revisionId':rid},principal_id=principal)['revision']
            if aid not in revision.get('outputArtifactIds', []):
                raise PlatformDenied('FEEDBACK_ARTIFACT_NOT_BOUND')
            pcm = project_audio_bytes(self.root, {'projectId':pid,'revisionId':rid,'artifactId':aid},principal_id=principal)
            with wave.open(io.BytesIO(pcm),'rb') as w:
                if w.getnchannels()!=2 or w.getsampwidth()!=2:
                    raise ValueError('FEEDBACK_WAV_FORMAT_UNSUPPORTED')
                return w.getnframes(), w.getframerate()
        except (ValueError, OSError, PermissionError, EOFError, wave.Error) as error:
            raise PlatformDenied('FEEDBACK_SOURCE_DENIED') from error

    def create_comment(self, principal, payload):
        if not isinstance(payload,dict) or set(payload)!={'projectId','revisionId','artifactId','samplePosition','barBeatLabel','body'}:
            raise ValueError('FEEDBACK_FIELDS_DENIED')
        position=payload['samplePosition']
        label=payload['barBeatLabel']
        body=payload['body']
        if type(position) is not int or position<0 or position>=2**63:
            raise ValueError('FEEDBACK_POSITION_DENIED')
        if not isinstance(label,str) or len(label)>80 or not label.strip() or '\x00' in label:
            raise ValueError('FEEDBACK_LABEL_DENIED')
        if not isinstance(body,str) or not 1<=len(body.strip())<=2000 or '\x00' in body:
            raise ValueError('FEEDBACK_BODY_DENIED')
        pid,rid,aid=payload['projectId'],payload['revisionId'],payload['artifactId']
        frames,rate=self._source(principal,pid,rid,aid)
        if position>=frames:
            raise ValueError('FEEDBACK_POSITION_OUTSIDE_AUDIO')
        cid='fc-'+secrets.token_hex(16)
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE')
            # Account erasure revokes publication of comments.
            actor=db.execute("SELECT status FROM accounts WHERE principal=?",(principal,)).fetchone()
            if actor is None or actor['status']!='active':
                raise PlatformDenied('FEEDBACK_ACCOUNT_DENIED')
            db.execute('''INSERT INTO revision_timeline_comments
                (id,project,revision,artifact,sample_position,sample_rate,bar_beat_label,author,body,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)''',
                (cid,pid,rid,aid,position,rate,label.strip(),principal,body.strip(),int(time.time())))
            db.commit()
        return {'status':'CREATED','commentId':cid,'projectId':pid,'revisionId':rid,
                'artifactId':aid,'samplePosition':position,'sampleRate':rate,
                'barBeatLabel':label.strip(),'body':body.strip()}

    def list_comments(self, principal, pid, rid, aid):
        frame_count,source_rate=self._source(principal,pid,rid,aid)
        with self.identity._db() as db:
            recent=db.execute('''SELECT sequence,id,sample_position,sample_rate,bar_beat_label,body,created_at
                FROM revision_timeline_comments WHERE project=? AND revision=? AND artifact=?
                ORDER BY sequence DESC LIMIT 300''',(pid,rid,aid)).fetchall()
            rows=sorted(recent,key=lambda r:(r['sample_position'],r['sequence']))
            actor=db.execute("SELECT status FROM accounts WHERE principal=?",(principal,)).fetchone()
            if actor is None or actor['status']!='active':
                raise PlatformDenied('FEEDBACK_ACCOUNT_DENIED')
        return {'status':'SUCCESS','projectId':pid,'revisionId':rid,'artifactId':aid,
                'totalSamples':frame_count,'sampleRate':source_rate,
                'comments':[{'commentId':r['id'],'samplePosition':r['sample_position'],
                 'sampleRate':r['sample_rate'],'barBeatLabel':r['bar_beat_label'],
                 'body':r['body'],'createdAt':r['created_at']} for r in rows]}


    def create_grant(self, principal, payload):
        if not isinstance(payload,dict) or set(payload)!={'projectId','revisionId','artifactId','expiresInSeconds'}:
            raise ValueError('PREVIEW_FIELDS_DENIED')
        ttl=payload['expiresInSeconds']
        if type(ttl) is not int or not 1 <= ttl <= 604800:
            raise ValueError('PREVIEW_TTL_DENIED')
        pid,rid,aid=payload['projectId'],payload['revisionId'],payload['artifactId']
        self._source(principal,pid,rid,aid)
        grant_id='pg-'+secrets.token_hex(16)
        token=secrets.token_urlsafe(32)
        digest=hashlib.sha256(token.encode('ascii')).hexdigest()
        now=int(time.time())
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE')
            active=db.execute("SELECT status FROM accounts WHERE principal=?",(principal,)).fetchone()
            if not active or active['status']!='active':
                raise PlatformDenied('PREVIEW_OWNER_INACTIVE')
            db.execute("""INSERT INTO private_preview_grants
                (id,token_digest,project,revision,artifact,creator,created_at,expires_at)
                VALUES(?,?,?,?,?,?,?,?)""",(grant_id,digest,pid,rid,aid,principal,now,now+ttl))
            db.commit()
        base='/api/previews/'+grant_id
        return {'status':'CREATED','grantId':grant_id,'projectId':pid,
                'revisionId':rid,'artifactId':aid,'expiresAt':now+ttl,
                'metadataUrl':base+'/metadata?token='+token,
                'audioUrl':base+'/audio?token='+token}

    def revoke_grant(self, principal, grant_id):
        if not isinstance(grant_id,str) or not re.fullmatch(r'pg-[0-9a-f]{32}',grant_id):
            raise PlatformDenied('PREVIEW_REVOKE_DENIED')
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("""SELECT g.creator,a.status FROM private_preview_grants g
                JOIN accounts a ON a.principal=g.creator WHERE g.id=?""",(grant_id,)).fetchone()
            if row is None or row['creator']!=principal or row['status']!='active':
                raise PlatformDenied('PREVIEW_REVOKE_DENIED')
            db.execute('UPDATE private_preview_grants SET revoked_at=COALESCE(revoked_at,?) WHERE id=?',
                       (int(time.time()),grant_id))
            db.commit()
        return {'status':'REVOKED','grantId':grant_id}

    def read_grant(self, grant_id, token, *, audio=False):
        if (not isinstance(grant_id,str) or not re.fullmatch(r'pg-[0-9a-f]{32}',grant_id)
            or not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}',token)):
            raise PlatformDenied('PREVIEW_GRANT_DENIED')
        token_digest=hashlib.sha256(token.encode('ascii')).hexdigest()
        with self.identity._db() as db:
            row=db.execute("""SELECT g.*,a.status FROM private_preview_grants g
                JOIN accounts a ON a.principal=g.creator WHERE g.id=?""",(grant_id,)).fetchone()
        if (row is None or row['status']!='active' or row['revoked_at'] is not None
             or row['expires_at']<=int(time.time())
             or not hmac.compare_digest(row['token_digest'],token_digest)):
            raise PlatformDenied('PREVIEW_GRANT_DENIED')
        principal,pid,rid,aid=(row[k] for k in ('creator','project','revision','artifact'))
        self._source(principal,pid,rid,aid)
        info={'status':'SUCCESS','grantId':grant_id,'projectId':pid,
              'revisionId':rid,'artifactId':aid,'expiresAt':row['expires_at']}
        if not audio:return info
        from studio_server import project_audio_bytes
        return info,project_audio_bytes(self.root,
            {'projectId':pid,'revisionId':rid,'artifactId':aid},principal_id=principal)

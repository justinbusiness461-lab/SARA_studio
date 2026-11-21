"""Revision-bound waveform annotations subordinate to canonical Studio audio.

Social feedback is non-authoritative. No comment can select a revision, grant
media access, publish an artifact, or change a music event.
"""
from __future__ import annotations
import io
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
        self._source(principal,pid,rid,aid)
        with self.identity._db() as db:
            recent=db.execute('''SELECT sequence,id,sample_position,sample_rate,bar_beat_label,body,created_at
                FROM revision_timeline_comments WHERE project=? AND revision=? AND artifact=?
                ORDER BY sequence DESC LIMIT 300''',(pid,rid,aid)).fetchall()
            rows=sorted(recent,key=lambda r:(r['sample_position'],r['sequence']))
            actor=db.execute("SELECT status FROM accounts WHERE principal=?",(principal,)).fetchone()
            if actor is None or actor['status']!='active':
                raise PlatformDenied('FEEDBACK_ACCOUNT_DENIED')
        return {'status':'SUCCESS','projectId':pid,'revisionId':rid,'artifactId':aid,
                'comments':[{'commentId':r['id'],'samplePosition':r['sample_position'],
                 'sampleRate':r['sample_rate'],'barBeatLabel':r['bar_beat_label'],
                 'body':r['body'],'createdAt':r['created_at']} for r in rows]}

"""SARA-EXPLORE-ROOMS-001: bounded artist rooms; never music or revision authority.

Membership, room identity and transcript are durable in the existing platform
SQLite. All published playback is reauthorized by platform_catalog on EACH
read. A proposal is a message to the Studio owner, never a revision commit.
"""
from __future__ import annotations
import html
import re
import secrets
import sqlite3
import time
from platform_identity import PlatformStore,PlatformDenied,PlatformConflict
from platform_catalog import public_song
from platform_workspaces import WorkspaceStore

ROOM_ID=re.compile(r'room-[0-9a-f]{32}\Z')
PROJECT=re.compile(r'[0-9a-f]{32}\Z')
REVISION=re.compile(r'[0-9a-f]{64}\Z')
CATEGORY={'Country-Hop','Beat Lab','Songwriters','DJ Scratch Lounge','Mix & Master','Open Collaboration','Experimental'}

def room_id(value):
    if not isinstance(value,str) or not ROOM_ID.fullmatch(value):
        raise PlatformDenied('ROOM_DENIED')
    return value

def cleaned(value,limit,what):
    if not isinstance(value,str) or not 1<=len(value.strip())<=limit or '\x00' in value:
        raise ValueError('INVALID_'+what)
    return html.escape(value.strip(),quote=True)

class RoomStore:
    def __init__(self,root):
        from platform_social import SocialStore
        SocialStore(root)  # Reuse the canonical block graph; no new ignore authority.
        self.root=root;self.identity=PlatformStore(root)
        with self.identity._db() as db:
            db.executescript('''
CREATE TABLE IF NOT EXISTS music_rooms(
 id TEXT PRIMARY KEY,slug TEXT NOT NULL UNIQUE,name TEXT NOT NULL,
 category TEXT NOT NULL,visibility TEXT NOT NULL,host TEXT NOT NULL,
 capacity INTEGER NOT NULL,created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS music_room_members(
 room TEXT NOT NULL,principal TEXT NOT NULL,role TEXT NOT NULL,
 active INTEGER NOT NULL,seen_at INTEGER NOT NULL,
 PRIMARY KEY(room,principal));
CREATE TABLE IF NOT EXISTS music_room_invites(
 room TEXT NOT NULL,principal TEXT NOT NULL,active INTEGER NOT NULL,
 PRIMARY KEY(room,principal));
CREATE TABLE IF NOT EXISTS music_room_messages(
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,room TEXT NOT NULL,
 author TEXT NOT NULL,body TEXT NOT NULL,created INTEGER NOT NULL,
 is_bot INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_room_message_sequence ON music_room_messages(room,sequence);
CREATE TABLE IF NOT EXISTS music_room_pins(
 room TEXT NOT NULL,publication TEXT NOT NULL,created INTEGER NOT NULL,
 PRIMARY KEY(room,publication));
CREATE TABLE IF NOT EXISTS music_room_proposals(
 id TEXT PRIMARY KEY,room TEXT NOT NULL,author TEXT NOT NULL,
 workspace TEXT NOT NULL,project TEXT NOT NULL,base_revision TEXT NOT NULL,
 instruction TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS music_room_blocks(
 room TEXT NOT NULL,principal TEXT NOT NULL,created INTEGER NOT NULL,
 PRIMARY KEY(room,principal));
''')
    def _active(self,db,actor):
        row=db.execute("SELECT status FROM accounts WHERE principal=?",(actor,)).fetchone()
        if row is None or row['status']!='active':raise PlatformDenied('ROOM_ACCOUNT_DENIED')
    def _room(self,db,rid):
        room_id(rid)
        row=db.execute('SELECT * FROM music_rooms WHERE id=?',(rid,)).fetchone()
        if row is None:raise PlatformDenied('ROOM_DENIED')
        return row
    def _admit(self,db,actor,rid,host=False):
        self._active(db,actor);row=self._room(db,rid)
        member=db.execute('SELECT role FROM music_room_members WHERE room=? AND principal=? AND active=1',(rid,actor)).fetchone()
        if not member:raise PlatformDenied('ROOM_MEMBERSHIP_REQUIRED')
        if host and row['host']!=actor:raise PlatformDenied('ROOM_HOST_REQUIRED')
        if db.execute('SELECT 1 FROM music_room_blocks WHERE room=? AND principal=?',(rid,actor)).fetchone():
            raise PlatformDenied('ROOM_BLOCKED')
        if actor!=row['host'] and db.execute('''SELECT 1 FROM social_blocks WHERE (blocker=? AND blocked=?) OR (blocker=? AND blocked=?)''',(actor,row['host'],row['host'],actor)).fetchone():
            raise PlatformDenied('SOCIAL_BLOCKED')
        return row
    def _target(self,db,handle):
        handle=self.identity._handle(handle)
        row=db.execute("SELECT principal FROM accounts WHERE handle=? AND status='active'",(handle,)).fetchone()
        if not row:raise PlatformDenied('ROOM_TARGET_NOT_FOUND')
        return row['principal']
    def create(self,actor,payload):
        if not isinstance(payload,dict) or set(payload)!={'name','category','visibility','maxOccupancy'}:
            raise ValueError('ROOM_CREATE_FIELDS')
        name=cleaned(payload['name'],80,'ROOM_NAME')
        category=payload['category'];visibility=payload['visibility'];capacity=payload['maxOccupancy']
        if category not in CATEGORY:raise ValueError('ROOM_CATEGORY_DENIED')
        if visibility not in ('public','private'):raise ValueError('ROOM_VISIBILITY_DENIED')
        if type(capacity) is not int or not 2<=capacity<=30:raise ValueError('ROOM_CAPACITY_DENIED')
        rid='room-'+secrets.token_hex(16);now=int(time.time())
        slug=re.sub('[^a-z0-9]+','-',name.lower()).strip('-')[:40]+'-'+rid[-8:]
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE');self._active(db,actor)
            db.execute('INSERT INTO music_rooms VALUES(?,?,?,?,?,?,?,?)',(rid,slug,name,category,visibility,actor,capacity,now))
            db.execute('INSERT INTO music_room_members VALUES(?,?,?,?,?)',(rid,actor,'host',1,now));db.commit()
        return {'status':'SUCCESS','roomId':rid,'slug':slug,'visibility':visibility,'category':category}
    def directory(self,actor,category='',query=''):
        if not isinstance(query,str) or len(query)>80 or not isinstance(category,str) or len(category)>80:
            raise ValueError('INVALID_ROOM_SEARCH')
        with self.identity._db() as db:
            self._active(db,actor)
            rows=db.execute('''SELECT r.*,COUNT(m.principal) as members FROM music_rooms r
            LEFT JOIN music_room_members m ON m.room=r.id AND m.active=1
            WHERE (r.visibility='public' OR EXISTS(SELECT 1 FROM music_room_members mine WHERE mine.room=r.id AND mine.principal=? AND mine.active=1))
            AND (?='' OR r.category=?) AND (?='' OR lower(r.name) LIKE ?)
            GROUP BY r.id ORDER BY r.created DESC,r.id DESC LIMIT 100''',
             (actor,category,category,query,'%'+query.lower()+'%')).fetchall()
        return {'status':'SUCCESS','rooms':[{'roomId':r['id'],'name':r['name'],'category':r['category'],
             'visibility':r['visibility'],'memberCount':r['members'],'maxOccupancy':r['capacity']} for r in rows]}
    def join(self,actor,rid):
        now=int(time.time())
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE');self._active(db,actor);r=self._room(db,rid)
            if db.execute('SELECT 1 FROM music_room_blocks WHERE room=? AND principal=?',(rid,actor)).fetchone():raise PlatformDenied('ROOM_BLOCKED')
            if r['host']!=actor and db.execute('SELECT 1 FROM social_blocks WHERE (blocker=? AND blocked=?) OR (blocker=? AND blocked=?)',(actor,r['host'],r['host'],actor)).fetchone():raise PlatformDenied('SOCIAL_BLOCKED')
            if r['visibility']=='private' and r['host']!=actor and not db.execute('SELECT 1 FROM music_room_invites WHERE room=? AND principal=? AND active=1',(rid,actor)).fetchone():raise PlatformDenied('ROOM_INVITE_REQUIRED')
            prior=db.execute('SELECT active FROM music_room_members WHERE room=? AND principal=?',(rid,actor)).fetchone()
            if not prior or not prior['active']:
                count=db.execute('SELECT COUNT(*) FROM music_room_members WHERE room=? AND active=1',(rid,)).fetchone()[0]
                if count>=r['capacity']:raise PlatformConflict('ROOM_AT_CAPACITY')
            db.execute("INSERT INTO music_room_members VALUES(?,?,'member',1,?) ON CONFLICT(room,principal) DO UPDATE SET active=1,seen_at=excluded.seen_at",(rid,actor,now))
            db.commit()
        return {'status':'JOINED','roomId':rid}
    def leave(self,actor,rid):
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE');r=self._admit(db,actor,rid)
            if r['host']==actor:raise PlatformDenied('ROOM_HOST_CANNOT_LEAVE')
            db.execute('UPDATE music_room_members SET active=0 WHERE room=? AND principal=?',(rid,actor));db.commit()
        return {'status':'LEFT','roomId':rid}
    def invite(self,actor,rid,handle):
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE');self._admit(db,actor,rid,host=True)
            target=self._target(db,handle)
            if target==actor:raise PlatformDenied('HOST_ALREADY_MEMBER')
            db.execute('INSERT INTO music_room_invites VALUES(?,?,1) ON CONFLICT(room,principal) DO UPDATE SET active=1',(rid,target));db.commit()
        return {'status':'INVITED','roomId':rid}
    def kick(self,actor,rid,handle,block=False):
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE');self._admit(db,actor,rid,host=True)
            target=self._target(db,handle)
            if target==actor:raise PlatformDenied('ROOM_HOST_IMMUTABLE')
            db.execute('UPDATE music_room_members SET active=0 WHERE room=? AND principal=?',(rid,target))
            db.execute('UPDATE music_room_invites SET active=0 WHERE room=? AND principal=?',(rid,target))
            if block:db.execute('INSERT OR REPLACE INTO music_room_blocks VALUES(?,?,?)',(rid,target,int(time.time())))
            db.commit()
        return {'status':'BLOCKED' if block else 'REMOVED','roomId':rid}
    def messages(self,actor,rid):
        from platform_catalog import public_song
        with self.identity._db() as db:
            self._admit(db,actor,rid)
            msgs=db.execute('''SELECT m.sequence,m.body,m.created,m.is_bot,a.handle FROM music_room_messages m
               JOIN accounts a ON a.principal=m.author WHERE m.room=? ORDER BY m.sequence DESC LIMIT 300''',(rid,)).fetchall()
            participants=db.execute('''SELECT a.handle,m.role,m.seen_at FROM music_room_members m JOIN accounts a ON a.principal=m.principal
               WHERE m.room=? AND m.active=1 AND a.status='active' ORDER BY a.handle LIMIT 30''',(rid,)).fetchall()
            pubs=[x[0] for x in db.execute('SELECT publication FROM music_room_pins WHERE room=? ORDER BY created DESC LIMIT 20',(rid,))]
        listening=[song['song'] for pub in pubs if (song:=public_song(self.root,pub,self.rights_policy)) is not None]
        # Late room revocation must prevent publication of already-read text.
        with self.identity._db() as db:self._admit(db,actor,rid)
        now=int(time.time())
        return {'status':'SUCCESS','messages':[{'sequence':m['sequence'],'body':m['body'],'createdAt':m['created'],'handle':m['handle'],'isBot':bool(m['is_bot'])} for m in reversed(msgs)],
           'participants':[{'handle':p['handle'],'role':p['role'],'observedRecently':bool(p['seen_at']>=now-60)} for p in participants],
           'listeningStation':listening}
    rights_policy=None
    def post_message(self,actor,rid,body):
        message=cleaned(body,1200,'ROOM_MESSAGE')
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE');self._admit(db,actor,rid)
            now=int(time.time())
            recent=db.execute('SELECT COUNT(*) FROM music_room_messages WHERE room=? AND author=? AND created>?',(rid,actor,now-60)).fetchone()[0]
            if recent>=20:raise PlatformConflict('ROOM_RATE_LIMIT')
            row=db.execute('INSERT INTO music_room_messages(room,author,body,created,is_bot) VALUES(?,?,?,?,0)',(rid,actor,message,now))
            db.execute('UPDATE music_room_members SET seen_at=? WHERE room=? AND principal=?',(now,rid,actor))
            db.commit()
        return {'status':'MESSAGE_COMMITTED','sequence':row.lastrowid,'isBot':False}
    def pin(self,actor,rid,publication,rights_policy):
        from platform_catalog import public_song
        if not isinstance(publication,str) or not re.fullmatch(r'pub-[0-9a-f]{32}',publication):raise PlatformDenied('PUBLICATION_DENIED')
        if public_song(self.root,publication,rights_policy) is None:raise PlatformDenied('PUBLICATION_NOT_PLAYABLE')
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE');self._admit(db,actor,rid,host=True)
            db.execute('INSERT OR IGNORE INTO music_room_pins VALUES(?,?,?)',(rid,publication,int(time.time())))
            db.commit()
        return {'status':'PINNED','publicationId':publication,'audioUrl':'/api/songs/'+publication+'/audio'}
    def proposals_for_owner(self,actor,rid):
        """Only the original workspace/project owner reviews social proposals.

        The Room host role cannot mint Studio project grants. Do not expose
        creative intent to other members or invent a delegated edit grant.
        """
        ws=WorkspaceStore(self.root)  # Materialize the rightful owner schema for empty/new rooms.
        with self.identity._db() as db:
            self._admit(db,actor,rid)
            rows=db.execute('''SELECT p.*,a.handle FROM music_room_proposals p
                JOIN accounts a ON a.principal=p.author
                JOIN platform_workspaces w ON w.id=p.workspace AND w.owner=?
                JOIN platform_workspace_projects wp ON wp.workspace=w.id
                    AND wp.project=p.project AND wp.owner=?
                WHERE p.room=? ORDER BY p.created DESC,p.id DESC LIMIT 100''',
                (actor,actor,rid)).fetchall()
        from studio_server import project_operation
        result=[]
        for proposal in rows:
            try:
                with self.identity._db() as db:
                    self._admit(db,actor,rid)
                    ws._grant(db,actor,proposal['workspace'],proposal['project'])
                project=project_operation(self.root,{'projectId':proposal['project']},principal_id=actor)
                # Historical source is read-only; a stale proposal cannot
                # silently become an instruction for a newer revision.
                state=(proposal['state'] if project['manifest']['currentRevisionId']==proposal['base_revision']
                    else 'STALE_SOURCE_REVISION')
                with self.identity._db() as db:
                    self._admit(db,actor,rid)
                    ws._grant(db,actor,proposal['workspace'],proposal['project'])
                result.append({'proposalId':proposal['id'],'authorHandle':proposal['handle'],
                   'workspaceId':proposal['workspace'],'projectId':proposal['project'],
                   'baseRevisionId':proposal['base_revision'],'instruction':proposal['instruction'],
                   'state':state,'revisionCommitted':False,'audioRendered':False})
            except (PermissionError,ValueError,OSError):continue
        return {'status':'SUCCESS','proposals':result}

    def proposal(self,actor,rid,payload):
        if set(payload)!={'workspaceId','projectId','baseRevisionId','instruction'}:
            raise ValueError('ROOM_PROPOSAL_FIELDS')
        wid,pid,rev=payload['workspaceId'],payload['projectId'],payload['baseRevisionId']
        if not isinstance(pid,str) or not PROJECT.fullmatch(pid) or not isinstance(rev,str) or not REVISION.fullmatch(rev):
            raise PlatformDenied('ROOM_PROPOSAL_REVISION_REQUIRED')
        instruction=cleaned(payload['instruction'],2000,'ROOM_PROPOSAL')
        ws=WorkspaceStore(self.root)
        with self.identity._db() as db:
            self._admit(db,actor,rid)
            owner,role=ws._grant(db,actor,wid,pid)
        from studio_server import project_operation
        try:
            source=project_operation(self.root,{'projectId':pid,'revisionId':rev},principal_id=owner)
            live=project_operation(self.root,{'projectId':pid},principal_id=owner)
        except (PermissionError,ValueError,OSError) as exc:raise PlatformDenied('ROOM_PROPOSAL_SOURCE_DENIED') from exc
        if live['manifest']['currentRevisionId']!=rev:raise PlatformConflict('ROOM_PROPOSAL_STALE_REVISION')
        prop='rp-'+secrets.token_hex(16)
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE');self._admit(db,actor,rid)
            ws._grant(db,actor,wid,pid)
            db.execute('INSERT INTO music_room_proposals VALUES(?,?,?,?,?,?,?,?,?)',
               (prop,rid,actor,wid,pid,rev,instruction,'AWAITING_OWNER_REVIEW',int(time.time())))
            db.commit()
        return {'status':'SUCCESS','proposalId':prop,'state':'AWAITING_OWNER_REVIEW',
                'sourceRevisionId':rev,'revisionCommitted':False,'audioRendered':False}

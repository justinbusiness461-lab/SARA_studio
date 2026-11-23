"""S.A.R.A. Wave2 social projections; Studio remains source of sound truth.

All playlist/album IDs reference *qualified SongPublications*, never private
ProjectRevision or CAS identity. Public reads recheck the host rights gate.
"""
from __future__ import annotations
import html,re,secrets,sqlite3,time
from platform_identity import PlatformStore,PlatformDenied,PlatformConflict
from platform_catalog import public_song

_ID=re.compile(r"(?:pl|alb)-[0-9a-f]{32}\Z")
def _id(value,kind):
 if not isinstance(value,str) or not re.fullmatch(kind+r"-[0-9a-f]{32}",value):
  raise PlatformDenied("RESOURCE_DENIED")
 return value
def _title(value):
 if not isinstance(value,str) or not 1<=len(value.strip())<=100:raise ValueError("INVALID_TITLE")
 return html.escape(value.strip(),quote=True)
def _pub(value):
 if not isinstance(value,str) or not re.fullmatch(r"pub-[0-9a-f]{32}",value):
  raise PlatformDenied("PUBLICATION_DENIED")
 return value

class SocialStore:
 def __init__(self,root):
  self.root=root;self.identity=PlatformStore(root)
  with self.identity._db() as db:
   db.executescript("""
CREATE TABLE IF NOT EXISTS social_playlists (
 id TEXT PRIMARY KEY,principal TEXT NOT NULL,title TEXT NOT NULL,
 visibility TEXT NOT NULL DEFAULT 'private',created INTEGER NOT NULL,
 FOREIGN KEY(principal) REFERENCES accounts(principal));
CREATE TABLE IF NOT EXISTS social_playlist_items(
 playlist TEXT NOT NULL,publication TEXT NOT NULL,position INTEGER NOT NULL,
 PRIMARY KEY(playlist,publication),FOREIGN KEY(playlist) REFERENCES social_playlists(id));
CREATE TABLE IF NOT EXISTS social_albums(
 id TEXT PRIMARY KEY,principal TEXT NOT NULL,title TEXT NOT NULL,
 released INTEGER NOT NULL DEFAULT 0,created INTEGER NOT NULL,
 FOREIGN KEY(principal) REFERENCES accounts(principal));
CREATE TABLE IF NOT EXISTS social_album_items(
 album TEXT NOT NULL,publication TEXT NOT NULL,position INTEGER NOT NULL,
 PRIMARY KEY(album,publication),FOREIGN KEY(album) REFERENCES social_albums(id));
CREATE TABLE IF NOT EXISTS social_follows(
 follower TEXT NOT NULL,followed TEXT NOT NULL,PRIMARY KEY(follower,followed));
CREATE TABLE IF NOT EXISTS social_blocks(
 blocker TEXT NOT NULL,blocked TEXT NOT NULL,PRIMARY KEY(blocker,blocked));
CREATE TABLE IF NOT EXISTS social_likes(
 principal TEXT NOT NULL,publication TEXT NOT NULL,PRIMARY KEY(principal,publication));
CREATE TABLE IF NOT EXISTS social_comments_enabled(
 principal TEXT PRIMARY KEY,enabled INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS social_comments(
 id TEXT PRIMARY KEY,author TEXT NOT NULL,publication TEXT NOT NULL,
 body TEXT NOT NULL,created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS social_notifications(
 target TEXT NOT NULL,event_id TEXT NOT NULL,kind TEXT NOT NULL,
 actor TEXT NOT NULL,created INTEGER NOT NULL,PRIMARY KEY(target,event_id));
""")
 def _owns(self,db,table,resource,principal):
  row=db.execute("SELECT principal FROM "+table+" WHERE id=?",(resource,)).fetchone()
  if row is None or row["principal"]!=principal:raise PlatformDenied("RESOURCE_OWNER_DENIED")
  return row
 def _published(self,public_id,policy):
  public_id=_pub(public_id)
  result=public_song(self.root,public_id,policy)
  if result is None:raise PlatformDenied("SONG_NOT_PUBLIC_OR_RIGHTS_HELD")
  return result["song"]
 def create_playlist(self,principal,title,visibility="private"):
  self.identity.profile(principal)
  if visibility not in {"private","public"}:raise ValueError("INVALID_VISIBILITY")
  pl="pl-"+secrets.token_hex(16)
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   db.execute("INSERT INTO social_playlists VALUES(?,?,?,?,?)",
    (pl,principal,_title(title),visibility,int(time.time())))
   db.commit()
  return {"playlistId":pl,"title":_title(title),"visibility":visibility}
 def my_playlists(self,principal):
  self.identity.profile(principal)
  with self.identity._db() as db:
   rows=db.execute("SELECT id,title,visibility FROM social_playlists WHERE principal=?"
     " ORDER BY created DESC,id DESC LIMIT 200",(principal,)).fetchall()
  return [{"playlistId":r["id"],"title":r["title"],"visibility":r["visibility"]} for r in rows]
 def set_playlist_visibility(self,principal,playlist,visibility):
  _id(playlist,"pl")
  if visibility not in {"private","public"}:raise ValueError("INVALID_VISIBILITY")
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE");self._owns(db,"social_playlists",playlist,principal)
   db.execute("UPDATE social_playlists SET visibility=? WHERE id=?",(visibility,playlist));db.commit()
  return {"playlistId":playlist,"visibility":visibility}
 def add_playlist_song(self,principal,playlist,publication,rights_policy=None):
  _id(playlist,"pl")
  self._published(publication,rights_policy)
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   self._owns(db,"social_playlists",playlist,principal)
   pos=db.execute("SELECT COALESCE(MAX(position),-1)+1 FROM social_playlist_items WHERE playlist=?",(playlist,)).fetchone()[0]
   db.execute("INSERT OR IGNORE INTO social_playlist_items VALUES(?,?,?)",
    (playlist,_pub(publication),pos));db.commit()
  return {"playlistId":playlist,"publicationId":publication}
 def remove_playlist_song(self,principal,playlist,publication):
  _id(playlist,"pl");_pub(publication)
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   self._owns(db,"social_playlists",playlist,principal)
   db.execute("DELETE FROM social_playlist_items WHERE playlist=? AND publication=?",
     (playlist,publication))
   db.commit()
  return {"status":"SUCCESS"}
 def reorder_playlist(self,principal,playlist,publication_ids):
  _id(playlist,"pl")
  if not isinstance(publication_ids,list) or len(publication_ids)>300 or len(set(publication_ids))!=len(publication_ids):
   raise ValueError("INVALID_REORDER")
  for item in publication_ids:_pub(item)
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   self._owns(db,"social_playlists",playlist,principal)
   current={x[0] for x in db.execute("SELECT publication FROM social_playlist_items WHERE playlist=?",(playlist,)).fetchall()}
   if current!=set(publication_ids):raise PlatformDenied("REORDER_MEMBERSHIP_MISMATCH")
   for i,item in enumerate(publication_ids):
    db.execute("UPDATE social_playlist_items SET position=? WHERE playlist=? AND publication=?",(i,playlist,item))
   db.commit()
  return {"status":"SUCCESS","order":publication_ids}
 def read_playlist(self,playlist,viewer=None,rights_policy=None):
  _id(playlist,"pl")
  with self.identity._db() as db:
   row=db.execute("SELECT * FROM social_playlists WHERE id=?",(playlist,)).fetchone()
   if row is None or (row["visibility"]!="public" and row["principal"]!=viewer):return None
   ids=[r[0] for r in db.execute("SELECT publication FROM social_playlist_items WHERE playlist=? ORDER BY position",(playlist,))]
  songs=[]
  for pub in ids:
   try:songs.append(self._published(pub,rights_policy))
   except PlatformDenied:continue
  return {"playlistId":playlist,"title":row["title"],"visibility":row["visibility"],"songs":songs}
 def create_album(self,principal,title):
  self.identity.profile(principal)
  alb="alb-"+secrets.token_hex(16)
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   db.execute("INSERT INTO social_albums VALUES(?,?,?,?,?)",(alb,principal,_title(title),0,int(time.time())))
   db.commit()
  return {"albumId":alb,"title":_title(title),"released":False}
 def album(self,album,viewer=None,rights_policy=None):
  _id(album,"alb")
  with self.identity._db() as db:
   row=db.execute("SELECT * FROM social_albums WHERE id=?",(album,)).fetchone()
   if not row or (not row["released"] and row["principal"]!=viewer):return None
   pubs=[r[0] for r in db.execute("SELECT publication FROM social_album_items WHERE album=? ORDER BY position",(album,))]
  return {"albumId":album,"title":row["title"],"released":bool(row["released"]),
    "songs":[song for pub in pubs if (song:=public_song(self.root,pub,rights_policy)) is not None]}
 def release_album(self,principal,album,publications,confirm_disclosure=False,rights_policy=None):
  _id(album,"alb")
  if confirm_disclosure is not True:raise PlatformDenied("ALBUM_PUBLICATION_REQUIRES_CONFIRMATION")
  if not isinstance(publications,list) or not 1<=len(publications)<=100 or len(set(publications))!=len(publications):
   raise ValueError("INVALID_ALBUM_TRACKS")
  for p in publications:self._published(p,rights_policy)
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   self._owns(db,"social_albums",album,principal)
   if db.execute("SELECT released FROM social_albums WHERE id=?",(album,)).fetchone()[0]:
    raise PlatformConflict("ALBUM_ALREADY_RELEASED")
   for i,p in enumerate(publications):
    db.execute("INSERT INTO social_album_items VALUES(?,?,?)",(album,p,i))
   db.execute("UPDATE social_albums SET released=1 WHERE id=?",(album,));db.commit()
  return {"albumId":album,"released":True}
 def _blocked(self,db,a,b):
  return db.execute("SELECT 1 FROM social_blocks WHERE (blocker=? AND blocked=?) OR (blocker=? AND blocked=?)",
   (a,b,b,a)).fetchone() is not None
 def follow(self,principal,target):
  self.identity.profile(principal);self.identity.profile(target)
  if principal==target:raise PlatformDenied("SELF_FOLLOW_DENIED")
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   if self._blocked(db,principal,target):raise PlatformDenied("BLOCKED")
   cursor=db.execute("INSERT OR IGNORE INTO social_follows VALUES(?,?)",(principal,target))
   db.commit()
  if cursor.rowcount:self.notify(target,"follow:"+principal,"follow",principal)
  return bool(cursor.rowcount)
 def unfollow(self,principal,target):
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   cursor=db.execute("DELETE FROM social_follows WHERE follower=? AND followed=?",(principal,target))
   db.commit()
  return bool(cursor.rowcount)
 def block(self,principal,target):
  self.identity.profile(principal);self.identity.profile(target)
  if principal==target:raise PlatformDenied("SELF_BLOCK_DENIED")
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   db.execute("INSERT OR IGNORE INTO social_blocks VALUES(?,?)",(principal,target))
   db.execute("DELETE FROM social_follows WHERE (follower=? AND followed=?) OR (follower=? AND followed=?)",
    (principal,target,target,principal))
   db.commit()
  return {"status":"SUCCESS"}
 def like(self,principal,publication,rights_policy=None):
  song=self._published(publication,rights_policy)
  owner=self.identity.public_profile(song["artist"]["handle"])
  if not owner:raise PlatformDenied("ARTIST_MISSING")
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   target=db.execute("SELECT principal FROM accounts WHERE handle=?",(owner["handle"],)).fetchone()["principal"]
   if self._blocked(db,principal,target):raise PlatformDenied("BLOCKED")
   cursor=db.execute("INSERT OR IGNORE INTO social_likes VALUES(?,?)",(principal,publication));db.commit()
  if cursor.rowcount and target!=principal:self.notify(target,"like:"+publication+":"+principal,"like",principal)
  return bool(cursor.rowcount)
 def unlike(self,principal,publication):
  _pub(publication)
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   cursor=db.execute("DELETE FROM social_likes WHERE principal=? AND publication=?",(principal,publication))
   db.commit()
  return bool(cursor.rowcount)
 def set_comments_enabled(self,principal,enabled):
  self.identity.profile(principal)
  if type(enabled)!=bool:raise ValueError("INVALID_COMMENT_SETTING")
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   db.execute("INSERT INTO social_comments_enabled VALUES(?,?) ON CONFLICT(principal) DO UPDATE SET enabled=excluded.enabled",
     (principal,int(enabled)));db.commit()
  return {"commentsEnabled":enabled}
 def comment(self,principal,publication,body,rights_policy=None):
  self.identity.profile(principal)
  if not isinstance(body,str) or not 1<=len(body.strip())<=1000:raise ValueError("INVALID_COMMENT")
  song=self._published(publication,rights_policy)
  owner_handle=song["artist"]["handle"]
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   target=db.execute("SELECT principal FROM accounts WHERE handle=?",(owner_handle,)).fetchone()["principal"]
   if self._blocked(db,principal,target):raise PlatformDenied("BLOCKED")
   row=db.execute("SELECT enabled FROM social_comments_enabled WHERE principal=?",(target,)).fetchone()
   if row and not row["enabled"]:raise PlatformDenied("COMMENTS_DISABLED")
   cid="comment-"+secrets.token_hex(16)
   db.execute("INSERT INTO social_comments VALUES(?,?,?,?,?)",
     (cid,principal,publication,html.escape(body.strip(),quote=True),int(time.time())));db.commit()
  if target!=principal:self.notify(target,"comment:"+cid,"comment",principal)
  return {"commentId":cid}
 def notify(self,target,event_id,kind,actor):
  self.identity.profile(target);self.identity.profile(actor)
  if not isinstance(event_id,str) or not 1<=len(event_id)<=128 or not re.fullmatch(r"[\w:.\-]+",event_id):
   raise ValueError("INVALID_EVENT_ID")
  if kind not in {"follow","like","comment","workspace_invite"}:raise ValueError("INVALID_NOTIFICATION")
  with self.identity._db() as db:
   db.execute("BEGIN IMMEDIATE")
   cursor=db.execute("INSERT OR IGNORE INTO social_notifications VALUES(?,?,?,?,?)",
       (target,event_id,kind,actor,int(time.time())))
   db.commit()
  return bool(cursor.rowcount)
 def notifications(self,target):
  self.identity.profile(target)
  with self.identity._db() as db:
   rows=db.execute("SELECT event_id,kind,actor,created FROM social_notifications WHERE target=? ORDER BY created DESC,event_id DESC LIMIT 100",
    (target,)).fetchall()
  return [{"eventId":r["event_id"],"kind":r["kind"],"actor":r["actor"],"created":r["created"]} for r in rows]

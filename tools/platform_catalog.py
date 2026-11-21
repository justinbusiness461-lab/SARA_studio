"""S.A.R.A. PLATFORM-02: public listings subordinate to immutable music authority.

No digest, path, publication row or public handle independently authorizes media.
All playable reads cross the existing project_audio_bytes authorization barrier
and a host-held rights policy on each read. Never infer ownership from CAS.
"""
from __future__ import annotations
import re
from platform_identity import PlatformStore,PlatformDenied,PlatformConflict

def _song_public(row):
 return {"publicationId":row["publication_id"],"title":row["title"],
   "artist":{"handle":row["handle"],"displayName":row["display_name"]},
   "publishedAt":row["published_at"],
   "audioUrl":"/api/songs/"+row["publication_id"]+"/audio"}

def _rights_or_deny(policy,pid,rid,aid,principal):
 if not callable(policy):raise PlatformDenied("RIGHTS_POLICY_NOT_CONFIGURED")
 result=policy(pid,rid,aid,principal)
 if result not in {"ARTIST_OWNED","LICENSE_CLEARED"}:
  raise PlatformDenied("RIGHTS_NOT_VERIFIED")
 return result

def authorized_publish(root,payload,principal,policy):
 from studio_server import project_operation,project_audio_bytes,ProjectConflict
 if not isinstance(payload,dict) or set(payload)!={"projectId","revisionId","artifactId","confirmPublic"}:
  raise ValueError("INVALID_PUBLICATION_REQUEST")
 if payload.get("confirmPublic") is not True:
  raise PlatformDenied("PUBLICATION_REQUIRES_EXPLICIT_CONFIRMATION")
 pid,rid,aid=payload["projectId"],payload["revisionId"],payload["artifactId"]
 store=PlatformStore(root)
 store.profile(principal)
 source=project_operation(root,{"projectId":pid,"revisionId":rid},principal_id=principal)
 live=project_operation(root,{"projectId":pid},principal_id=principal)
 if live["manifest"]["currentRevisionId"]!=rid:
  raise PlatformDenied("HISTORICAL_REVISION_PUBLICATION_DENIED")
 if aid not in source["revision"].get("outputArtifactIds",[]):
  # If a render produced an immutable historical-renders association instead,
  # the media read still validates it, but the present publication contract
  # requires explicit accepted output on selected revision.
  raise PlatformDenied("SOURCE_ARTIFACT_NOT_EXPLICITLY_ACCEPTED")
 project_audio_bytes(root,{"projectId":pid,"revisionId":rid,"artifactId":aid},principal_id=principal)
 evidence=_rights_or_deny(policy,pid,rid,aid,principal)
 title=source["songSpec"].get("title") or "Untitled"
 pub=store.add_publication(principal,pid,rid,aid,title,evidence)
 return _song_public(pub)

def _still_qualified(root,row,policy):
 from studio_server import project_audio_bytes
 try:
  _rights_or_deny(policy,row["project_id"],row["revision_id"],row["artifact_id"],row["principal"])
  # Verify *lawful* historical membership, not currentness. Published immutable
  # R1 remains valid when new private R2 is made, unless explicitly unpublished.
  project_audio_bytes(root,{"projectId":row["project_id"],"revisionId":row["revision_id"],
     "artifactId":row["artifact_id"]},principal_id=row["principal"])
  return True
 except (ValueError,KeyError,OSError,PermissionError):
  return False

def discover(root,policy,query="",handle=None):
 store=PlatformStore(root)
 if not isinstance(query,str) or len(query)>100:raise ValueError("INVALID_SEARCH_QUERY")
 visible=[_song_public(row) for row in store.list_publications(query=query,handle=handle)
          if _still_qualified(root,row,policy)]
 return {"status":"SUCCESS","songs":visible,"total":len(visible)}

def public_song(root,public_id,policy):
 row=PlatformStore(root).publication(public_id)
 if row is None or not _still_qualified(root,row,policy):return None
 return {"status":"SUCCESS","song":_song_public(row)}

def public_profile(root,handle,policy):
 store=PlatformStore(root)
 profile=store.public_profile(handle)
 if not profile:return None
 return {"status":"SUCCESS","profile":profile,
   "songs":discover(root,policy,handle=profile["handle"])["songs"]}

def playable_public_audio(root,public_id,policy):
 from studio_server import project_audio_bytes
 row=PlatformStore(root).publication(public_id)
 if row is None or not _still_qualified(root,row,policy):return None
 return project_audio_bytes(root,{"projectId":row["project_id"],
      "revisionId":row["revision_id"],"artifactId":row["artifact_id"]},
      principal_id=row["principal"])

def owned_library(root,principal):
 # ProjectManifest is authoritative; never derive project ownership from CAS.
 from studio_server import project_operation
 from pathlib import Path
 result=[]
 root=Path(root)
 projects=root/"projects"
 if not projects.exists():return {"status":"SUCCESS","projects":[]}
 for folder in sorted(projects.iterdir()):
  if not folder.is_dir() or not re.fullmatch(r"[a-f0-9]{32}",folder.name):continue
  try:
   selection=project_operation(root,{"projectId":folder.name},principal_id=principal)
  except (ValueError,PermissionError,OSError):
   continue
  result.append({"projectId":folder.name,"currentRevisionId":selection["manifest"]["currentRevisionId"],
    "title":selection["songSpec"].get("title","Untitled")})
 return {"status":"SUCCESS","projects":result[:200]}

def publication_unpublish(root,public_id,principal):
 return PlatformStore(root).revoke_publication(principal,public_id)

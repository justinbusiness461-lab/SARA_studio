"""Bounded, auditable platform chat adapter. No LLM-generated arbitrary actions.

Every action calls the same SocialStore/CreditLedger/Catalog owner service as the
HTTP/UI endpoints. Public publishing is always a proposal requiring an exact
revision, artifact, rights policy and explicit acceptance on the normal route.
"""
from __future__ import annotations
import re
from platform_identity import PlatformStore,PlatformDenied
from platform_social import SocialStore
from platform_billing import CreditLedger
from platform_catalog import discover

def run_platform_chat(root,principal,instruction,rights_policy,context=None):
 PlatformStore(root).profile(principal)
 if not isinstance(instruction,str) or not 1<=len(instruction.strip())<=350:
  raise ValueError("INVALID_CHAT_INTENT")
 instruction=instruction.strip()
 normalized=" ".join(instruction.lower().split())
 if re.fullmatch(r"(?:check|show|what is|what's) (?:my )?credit balance[?.]?",normalized):
  return {"state":"EXECUTED","action":"CREDIT_BALANCE",
    "result":CreditLedger(root).balance(principal),"revisionCommitted":False}
 matched=re.fullmatch(r"(?:search|find)(?: for)? (.+?)(?: songs)?[?.]?",normalized)
 if matched:
  term=matched.group(1).strip()
  if not term or len(term)>100:raise ValueError("UNSUPPORTED_CHAT_SEARCH")
  return {"state":"EXECUTED","action":"SEARCH_PUBLIC_CATALOG",
    "result":discover(root,rights_policy,query=term),"revisionCommitted":False}
 matched=re.fullmatch(r"create (?:a )?(?:new )?playlist (?:called|named) ([a-zA-Z0-9 _'!-]{1,80})",instruction,re.I)
 if matched:
  return {"state":"EXECUTED","action":"CREATE_PRIVATE_PLAYLIST",
   "result":SocialStore(root).create_playlist(principal,matched.group(1).strip()),"revisionCommitted":False}
 if normalized in {"publish r2","publish this track","publish this song","publish current song"}:
  if isinstance(context,dict) and set(context)>= {"projectId","revisionId","artifactId"}:
   from studio_server import project_operation,project_audio_bytes
   if set(context)-{"projectId","revisionId","artifactId","selectedTrackId","selectedBars"}:
    raise ValueError("INVALID_PUBLICATION_CHAT_CONTEXT")
   project=project_operation(root,{"projectId":context["projectId"]},principal_id=principal)
   if project["manifest"]["currentRevisionId"]!=context["revisionId"]:
    raise PlatformDenied("PUBLICATION_SOURCE_NOT_CURRENT")
   project_audio_bytes(root,{"projectId":context["projectId"],
      "revisionId":context["revisionId"],"artifactId":context["artifactId"]},
      principal_id=principal)
   return {"state":"APPROVAL_REQUIRED","action":"PUBLISH",
    "projectId":context["projectId"],"sourceRevisionId":context["revisionId"],
    "sourceArtifactId":context["artifactId"],"route":"/api/publications",
    "proposedRequest":{"projectId":context["projectId"],"revisionId":context["revisionId"],
      "artifactId":context["artifactId"],"confirmPublic":True},
    "message":"Public disclosure requires explicit approval and independent host rights clearance.",
    "revisionCommitted":False}
  return {"state":"AWAITING_CONFIRMATION","action":"PUBLISH_VERIFIED_REVISION",
   "message":"Choose a specific current project/revision/accepted audio, verify rights and confirm publication. No song changed.",
   "revisionCommitted":False}
 # Compound find→queue→playlist is bounded: playlist contains only independently
 # lawful publication IDs, and UI performs playback of queue, never server magic.
 found=re.fullmatch(r"(?:find|search) (.{1,120}) songs,? play (?:the )?top ([1-9]) and save (?:them )?to (?:a )?(?:new )?playlist",normalized)
 if found:
  term=found.group(1);count=int(found.group(2))
  catalog=discover(root,rights_policy,query=term)
  chosen=catalog["songs"][:count]
  if not chosen:
   return {"state":"EXECUTED","action":"SEARCH_QUEUE_PRIVATE_PLAYLIST",
    "result":{"songs":[],"playlist":None,"queue":[]},"revisionCommitted":False}
  social=SocialStore(root)
  playlist=social.create_playlist(principal,"Found: "+term[:60])
  for song in chosen:social.add_playlist_song(principal,playlist["playlistId"],song["publicationId"],rights_policy)
  return {"state":"EXECUTED","action":"SEARCH_QUEUE_PRIVATE_PLAYLIST",
   "result":{"songs":chosen,"playlist":playlist,
     "queue":[song["audioUrl"] for song in chosen]},"revisionCommitted":False}
 # Source-bound Studio bridge: interpretation remains subordinate and
 # independently authorizes project/revision/artifact before any proposal.
 from m045_studio_chat_orchestrator import orchestrate_studio_chat
 return orchestrate_studio_chat(root,principal,instruction,context,rights_policy)

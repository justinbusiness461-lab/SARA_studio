"""Source-bound Studio commands for platform Chat, subordinate to canonical music owners.

Intent interpretation and preview plans NEVER originate SongSpec/ProjectRevision,
SampleAsset rights, CAS publication or audio certification. Only existing owner
operations can effect changes. This module fails closed for ambiguous targets.
"""
from __future__ import annotations
import re
from platform_identity import PlatformDenied

_ALLOWED_FIELDS=frozenset({"projectId","revisionId","artifactId",
 "selectedTrackId","selectedBars","playlistId","publicationId"})
_PROTECTED=frozenset({"REPAINT","ADD_SCRATCH","TRANSCRIBE_MIDI","MASTER",
 "TOGGLE_LOCK","CREATE_MUSIC_VIDEO_GRANT"})

def _result(state,action,**payload):
 return {"state":state,"action":action,"revisionCommitted":False,**payload}

def _need(action,**kwargs):
 return _result("CLARIFICATION_REQUIRED",action,**kwargs)

def _recognize(raw):
 text=" ".join(raw.casefold().split())
 if re.fullmatch(r"(?:generate|create (?:a |an )?(?:new )?song)(?:\s+.+)?",text):
  return "GENERATE"
 if re.search(r"\b(?:repaint|change only this|change this part)\b",text):
  return "REPAINT"
 if re.search(r"\b(?:add scratch|scratch chirp|add a scratch)\b",text):
  return "ADD_SCRATCH"
 if re.search(r"\b(?:sample preview|preview a .+sample|preview .+sample)\b",text):
  return "SAMPLE_PREVIEW"
 if re.search(r"\b(?:audio to midi|audio-to-midi|transcribe .+ midi)\b",text):
  return "TRANSCRIBE_MIDI"
 if re.search(r"\bmaster\b",text):
  return "MASTER"
 if re.search(r"\b(?:sonic lock|toggle lock|lock this track)\b",text):
  return "TOGGLE_LOCK"
 if re.search(r"\b(?:music video grant|soundtrack grant|cinema grant)\b",text):
  return "CREATE_MUSIC_VIDEO_GRANT"
 if re.search(r"\badd (?:this )?(?:song|track) to playlist\b",text):
  return "ADD_TO_PLAYLIST"
 return None

def orchestrate_studio_chat(root,principal,instruction,context=None,rights_policy=None):
 if not isinstance(instruction,str) or not 1<=len(instruction.strip())<=350:
  raise ValueError("INVALID_CHAT_INTENT")
 if context is None:context={}
 if not isinstance(context,dict) or set(context)-_ALLOWED_FIELDS:
  raise ValueError("INVALID_STUDIO_CHAT_CONTEXT")
 action=_recognize(instruction)
 if action is None:raise ValueError("UNSUPPORTED_STUDIO_CHAT_COMMAND")
 if action=="ADD_TO_PLAYLIST":
  from platform_social import SocialStore
  if not context.get("playlistId") or not context.get("publicationId"):
   return _need(action,missing=[x for x in ("playlistId","publicationId") if not context.get(x)],
      message="Select an existing private/owned playlist and a verified public publication.")
  result=SocialStore(root).add_playlist_song(principal,context["playlistId"],
       context["publicationId"],rights_policy=rights_policy)
  return _result("EXECUTED",action,result=result)
 if action=="GENERATE" and not context.get("projectId"):
  match=re.match(r"(?is)^\s*(?:generate|create (?:a |an )?(?:new )?song)\s*(.*)$",instruction)
  prompt=(match.group(1) if match else "").strip()
  if not prompt:return _need(action,missing=["prompt"],message="Describe what to generate.")
  # No server-side fake source or revision. Client submits through its current
  # ScoreCore Generate owner and awaits physical audio + authoritative readback.
  return _result("STUDIO_ACTION_READY",action,
       clientOwner="EXISTING_SCORECORE_GENERATE",prompt=prompt,
       message="Prepared a prompt for the existing Studio Generate action. No revision committed yet.")
 missing=[key for key in ("projectId","revisionId") if not context.get(key)]
 if missing:return _need(action,missing=missing,
   message="Select and open an authorized saved Studio project/revision first.")
 from studio_server import project_operation,project_audio_bytes,ProjectConflict
 pid,rid=context["projectId"],context["revisionId"]
 # Verify ownership/session/membership before compiling target details.
 try:
  chosen=project_operation(root,{"projectId":pid,"revisionId":rid},principal_id=principal)
  current=project_operation(root,{"projectId":pid},principal_id=principal)
 except (ProjectConflict,PermissionError,ValueError,OSError) as exc:
  raise PlatformDenied("STUDIO_PROJECT_OR_REVISION_NOT_AUTHORIZED") from exc
 if chosen["revision"]["revisionId"]!=rid or chosen["manifest"]["projectId"]!=pid:
  raise PlatformDenied("STUDIO_SOURCE_ASSOCIATION_MISMATCH")
 artifact=context.get("artifactId")
 if artifact is not None:
  # The CAS digest is never ownership. Read through the canonical graph.
  try:project_audio_bytes(root,{"projectId":pid,"revisionId":rid,
           "artifactId":artifact},principal_id=principal)
  except (ProjectConflict,PermissionError,ValueError,OSError) as exc:
   raise PlatformDenied("STUDIO_SOURCE_AUDIO_NOT_AUTHORIZED") from exc
 current_id=current["manifest"]["currentRevisionId"]
 if rid!=current_id:
  return _need(action,missing=["currentRevisionSelection"],sourceRevisionId=rid,
     currentRevisionId=current_id,
     message="Selected historical revision; select current or explicitly open history in Studio. Chat will not promote it.")
 target_track=context.get("selectedTrackId")
 bars=context.get("selectedBars")
 if target_track is not None and (not isinstance(target_track,str) or len(target_track)>120 or
      target_track not in {t.get("track_id") for t in chosen["songSpec"]["tracks"]}):
  raise PlatformDenied("TRACK_NOT_IN_SELECTED_SONGSPEC")
 if bars is not None and (not isinstance(bars,list) or not 1<=len(bars)<=64 or
      any(type(b)!=int or b<1 or b>1024 for b in bars) or len(set(bars))!=len(bars)):
  raise ValueError("INVALID_BAR_SELECTION")
 missing=[]
 if action in {"REPAINT","ADD_SCRATCH","TOGGLE_LOCK"} and not target_track:missing.append("selectedTrackId")
 if action in {"REPAINT","ADD_SCRATCH"} and not bars:missing.append("selectedBars")
 if action in {"MASTER","TRANSCRIBE_MIDI","SAMPLE_PREVIEW","CREATE_MUSIC_VIDEO_GRANT"} and not artifact:
  missing.append("artifactId")
 if missing:
  return _need(action,missing=missing,projectId=pid,sourceRevisionId=rid,
    message="Choose exactly which track, bars or accepted audio to operate on.")
 if action=="MASTER":
  matches=re.findall(r"(?<!\d)-(?:14|9)(?:\.0)?\s*LUFS\b",instruction,re.I)
  if len(matches)!=1:return _need(action,missing=["targetLufs"],
     message="Select explicit -14 LUFS streaming or -9 LUFS club preset.")
  target=float(matches[0].split()[0])
  return _result("APPROVAL_REQUIRED",action,projectId=pid,sourceRevisionId=rid,
    sourceArtifactId=artifact,route="/api/m045/master",
    proposedRequest={"projectId":pid,"revisionId":rid,"artifactId":artifact,
       "expectedCurrentRevisionId":rid,"targetLufs":target,"truePeakCeilingDbtp":-1.0},
    message="Mastering commits a new immutable output. Approve exact current revision, loudness, cost and rights separately.")
 if action=="GENERATE":
  return _result("APPROVAL_REQUIRED",action,projectId=pid,sourceRevisionId=rid,
     message="Existing project selected; choose create-new or an explicit non-destructive revised generation before submitting.")
 if action=="SAMPLE_PREVIEW":
  return _need(action,missing=["transform","parameters"],projectId=pid,sourceRevisionId=rid,
     route="/api/m045/sample-preview",
     message="Choose exact bounded sample transform and parameters; preview is P3, unpublished and rights held.")
 route={"REPAINT":"/api/m045/compound-plan","TRANSCRIBE_MIDI":"/api/m045/transcribe-midi",
   "CREATE_MUSIC_VIDEO_GRANT":"/api/m045/soundtrack-grant"}.get(action)
 proposed={"projectId":pid,"revisionId":rid,"artifactId":artifact} if action=="TRANSCRIBE_MIDI" else None
 response=_result("APPROVAL_REQUIRED",action,projectId=pid,sourceRevisionId=rid,
   sourceArtifactId=artifact,selectedTrackId=target_track,
   selectedBars=bars,route=route,
   preservationTier="UNQUALIFIED_UNTIL_EXISTING_OWNER_PROOF",
   message="Review exact source, scope, locks, rights and impact. Commit only through the existing Studio owner.")
 if proposed:response["proposedRequest"]=proposed
 return response


"""M044 Chat D presentation publication fence. Observation-contract checker only."""
import json,sys

def assess(events):
    defects=[]
    if not isinstance(events,list) or not events: return ["missing observations"]
    for i,e in enumerate(events):
        tag=e.get("case","?")
        gen=e.get("latestRequestGeneration")
        selected=e.get("selectedRevisionId")
        current=e.get("currentRevisionId")
        history=e.get("history",[])
        if not isinstance(gen,int) or gen<0: defects.append(f"{i}:{tag}: missing latest request generation")
        if not isinstance(history,list): history=[]
        ids=[h.get("revisionId") for h in history]
        if len(ids)!=len(set(ids)): defects.append(f"{i}:{tag}: duplicate history revision")
        if current not in ids: defects.append(f"{i}:{tag}: current revision missing")
        for h in history:
            if h.get("current") != (h.get("revisionId")==current): defects.append(f"{i}:{tag}: false current badge")
            if h.get("playable") and (h.get("audioValidation")!="PASS" or h.get("sourceRevisionId")!=h.get("revisionId")):
                defects.append(f"{i}:{tag}: invalid historical audio shown playable")
        for completed in e.get("networkCompletions",[]):
            if completed.get("published"):
                if completed.get("requestGeneration")!=gen: defects.append(f"{i}:{tag}: stale network completion published")
                if completed.get("revisionId")!=selected: defects.append(f"{i}:{tag}: wrong revision published")
                match=[h for h in history if h.get("revisionId")==selected]
                if not match or match[0].get("artifactId")!=completed.get("artifactId"):
                    defects.append(f"{i}:{tag}: wrong artifact published")
        playback=e.get("playback")
        if playback and playback.get("started"):
            pg=playback.get("requestGeneration")
            if not isinstance(pg,int): defects.append(f"{i}:{tag}: missing playback generation")
            elif pg!=gen: defects.append(f"{i}:{tag}: stale playback generation")
            match=[h for h in history if h.get("revisionId")==selected]
            if not match or not match[0].get("playable") or any(playback.get(k)!=match[0].get(k) for k in ("artifactId","decodedPcmSha256")) or playback.get("revisionId")!=selected:
                defects.append(f"{i}:{tag}: audio provenance mismatch")
    return defects

if __name__=="__main__":
    events=json.load(open(sys.argv[1],encoding="utf-8"))
    failures=assess(events)
    print(json.dumps({"verdict":"FAIL" if failures else "PASS","scope":"observation contract ONLY; external evidence required","defects":failures},indent=2))
    sys.exit(bool(failures))

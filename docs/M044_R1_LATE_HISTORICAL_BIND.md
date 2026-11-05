# M044-R1 Repair — Late R1 historical artifact binding

**Local repair HEAD:** `602dfcf6b691f59039e8c9a7b9d55ca5e6778b46`
**Base:** `220010f44c7cf2f280afdacc1eae73bfdf9f365a`

## Defect

Late R1 render was blocked from promoting R2 (correct) but completed artifact was orphaned (incorrect).

## Fix

- `operationContext.kind == "render"` + expected revision is historical ancestor of current
- Persist under `projects/<pid>/historical_outputs/<r1>.json`
- `open(project, r1)` merges historical outputs into revision view
- **Does not** change `ProjectManifest.currentRevisionId`
- Stale non-render edits still 409
- Idempotent same-op replay; conflicting digest under same op → ProjectConflict

## Tests

```
python3 -m unittest discover -s tests  → 44/44 PASS
includes test_late_render_binds_historical_artifact_to_r1
includes test_stale_non_render_still_rejects
node --test tests/*.cjs → 8/8 PASS
```

## READY_FOR_B

YES after code files land on branch (studio_server.py + tests + probe).

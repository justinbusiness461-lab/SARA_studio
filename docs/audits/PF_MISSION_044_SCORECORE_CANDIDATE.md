# Mission 044 — Work B candidate qualification

**Target:** `bobby/m044-scorecore-foundation` @ `caeac41b9c88949739c31239a3096661fb0dda7e`

## Authentication

| Path | Role | Remote |
|------|------|--------|
| `tools/scorecore.cjs` | MusicIntent + section transpose (non-authoritative adapter) | present |
| `tests/scorecore.test.cjs` | 6 symbolic tests | present |
| `docs/M044_BOBBY_REUSE_MAP.md` | REUSE map | present |

Independent run on candidate tree:

- `node tests/scorecore.test.cjs` → **6/6 PASS**
- `python3 -m unittest discover -s tests` → **35/35 PASS** (no lyric/project regression)

## Architecture answers

| Question | Answer |
|----------|--------|
| MusicIntent non-authoritative? | **YES** — freezes prompt/bpm/key/meter/seed only; no persist/render |
| Compiles via existing `parsePrompt`? | **YES** — `compileIntent(intent, parsePrompt)` requires owner function |
| One stable section + track? | **YES** — `sectionId` + `trackId` required; ambiguous/missing **fail closed** |
| Pitch out of range? | **YES** — atomic fail, no partial mutation |
| Non-target events preserved? | **YES** — only NOTE_ON fully inside `[start,end)` |
| Second save path? | **NO** — no ProjectRevision/render in this commit |

## Result

```
M044_SCORECORE_CANDIDATE = QUALIFIED_FOR_INTEGRATION
```

**Not** an M044 PASS. Still missing: ProjectRevision R1/R2, real render A/B, cold reopen, physical audio, listening ≥7/10.

## Authorized next (Bobby only)

Narrow vertical slice on this foundation:

```
MusicIntent → SongSpec → ProjectRevision R1 → render A
→ transposeSection bass (scoped) → R2 → render B
→ kill → reopen → R2 current, R1 retained, non-target conserved
```

No neural vocals, no new scheduler, no UI redesign, no cinema, no GRAVEYARD full 3:20 until mechanism proven on small fixture.

Product freeze remains M043 `076aed8…` until an M044 integration successor is frozen by B after the vertical slice.

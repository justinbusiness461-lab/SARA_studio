# M044 Studio callable map

Work A preflight for Sound Forge main `14e2fb9cc55c8ce2909803a66d509915a18eb625` and the PR #11 Generate change `cb80d4fe06cc1148651787872ad89216c20328f3`.

| Studio step | Current call and request | Result and authority | Failure boundary |
|---|---|---|---|
| New Project | `#btnNewProject` clears the browser project reference and source selection | Local draft. The server assigns a project ID on first commit | Entering an existing ID requires opening that project before saving |
| Prompt → Generate | `#btnCompile → generateProject() → compile()` passes the prompt and explicit overrides to `ScoreCore.musicIntent()` and `compileIntent(intent, parsePrompt)` | Shared ScoreCore validates intent. App core produces SongSpec. `saveJSON()` then commits the snapshot | Admission failure skips save. Failed save is surfaced as an unconfirmed draft |
| Save | `POST /api/projects/commit` with `projectId`, `expectedCurrentRevisionId`, `songSpec`, `sourceAssetDigests`, `outputArtifactIds` | Server returns `manifest`, immutable `revision`, `songSpec`, `productionTimeline`, and lyric data where present | 403 for origin/capability denial, 409 for stale base or operation conflict, 400 for invalid authority, 413 for request size |
| Sections and tracks | `render()` reads `skeleton.structure.sections` and `skeleton.tracks`. Section badges set `activeSectionIdx`. Track selector uses `track_id` | Browser draft and selection. Reopen hydrates the draft from server SongSpec | Selection itself writes no revision |
| Play | `#btnPlay → playScore()` schedules SongSpec events through Web Audio | Live browser synthesis from the loaded draft | Revision-bound WAV read is absent. Local synthesis gives no evidence of artifact playback |
| Scoped bass edit | Headless `session.edit(projectId, expectedCurrentRevisionId, operationId, edit)` opens the exact base, calls `transposeSection`, and commits the resulting SongSpec with operation context | Existing ScoreCore edit and ProjectRevision owners. No chat or section/track octave-edit control is wired to this operation | Invalid target, crossing note or pitch range fails before commit. Stale and conflicting writes reject |
| Render | Browser `exportWav()` renders and encodes a mix, POSTs `filename`, `subdirectory`, `data_bytes` to `/api/write_production_file`, then commits the returned `sha256` as output | Server stores the bytes. Browser downloads its in-memory Blob. Headless `renderCaptured` additionally sends `operationId` and `operationContext: {kind: "render", sourceRevisionId}` | Browser blocks a silent mix and surfaces write/commit failure. Headless render validates the WAV and fences the captured revision. Early process death before pending ownership remains an open defect |
| History | `POST /api/projects/open` with `projectId` and optional `revisionId` | Server verifies committed ancestry, returns that revision and any verified `historicalOutputBindings`. Omitting the revision opens current | Unknown or out-of-history revision fails closed. Current browser Open requests only the current revision |
| A/B | No revision-bound transport operation in inspected code | Requires the existing project and artifact owners plus exact musical-position alignment for matching timelines | Missing R2 or a late R1 response must never produce R1 playback labeled R2 |
| Close → reopen | Close has no commit. `#btnOpenProject → restoreProjectFromStorage()` sends the entered or cached project ID to `POST /api/projects/open` | Server supplies the authoritative current revision. The browser cache supplies an address | Missing ID, request failure or invalid SongSpec prevents opening |

## First missing browser-to-audio call

`StudioHandler.do_GET()` serves the shell and public assets. It has no callable revision-bound WAV read. The existing local process capability gates POST and provides no evidence of hosted two-user authorization. Bobby owns the private read that checks caller access, committed revision ancestry, exact artifact binding, immutable bytes and admitted WAV before responding. The transport must separate current revision from historical selection and suppress late completions. See PR #16 for the read contract and PR #17 for the separate early-crash failure.

## Generate startup fix

The PR #11 shell references `scorecore.js` before `app-ui.js`. The Studio server allowlist omitted that script. Admit that exact public path and include it in the versioned PWA asset list so existing caches refresh with the matching UI. The Playwright smoke test drives the real Studio handler and Generate/Open UI. It uses temporary local project storage, blocks the unrelated Cinema CDN, and bypasses the service worker to exercise the server directly.

With Playwright and its Chromium browser available, run `node --test tests/prompt-generate.browser.cjs`. Set `CHROMIUM_PATH` to use a separately installed Chromium executable. The test checks project persistence and page reload. Authenticated WAV playback and offline-cache behavior have separate qualification gates.

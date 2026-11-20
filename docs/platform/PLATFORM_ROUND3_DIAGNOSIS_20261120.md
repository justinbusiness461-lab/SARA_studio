# Round 3: verified browser investigation — held, not 28/28

Canonical owner: `justinbusiness461-lab/SARA_studio` repo ID `1427534706`.
Branch `feat/platform-identity-and-catalog`, intake SHA `d35da48c44894109468b3a1e7d56d09c7a375246`; main unchanged.
Status: **INDEPENDENT DIAGNOSTIC EVIDENCE; NO ENGINE OR TEST REPAIR COMMITTED**.

## What changed because this investigation existed

1. The interpretation of the former `# AB_DEBUG` is corrected. In `docs/platform/evidence/kernel_20261120_round2/chromium-full-28.log`, `AB_DEBUG` was collected **after** the 15-second Playwright timeout, not at the failed deadline. Its `switch.state=COMPLETE`, R1 selected revision, lawful output artifact, digest, and exact position `3.84706` do not establish an unloaded active player. The four queried `document.querySelectorAll('audio')` elements exclude Studio's detached `new Audio()` verified playback object. No authority change or speculative `src` reattachment was made.
2. DJ overlay hypothesis independently challenged: on the exact current feature branch, `document.elementFromPoint` at the `#studioModeDj` center returns `#studioModeDj` itself, at viewport point ~640x687 in a 1280x720 Chromium viewport. The platform mini-player/navigation have zero-area rectangles, hidden by their parent in legacy Studio mode. There is no captured evidence of a dock/mini-player covering this button.
3. **Reproduced actual timing fault**: in `dj-network.log`, commit POST requested at +4742 ms and completed +5553 ms; render POST began +6102 ms and completed +15730 ms (9,628 ms render). The original Playwright render-response waiter was created before pressing Generate, so its default 12-second deadline spans commit + render rather than solely the render response. It can time out even though the render itself completed within 12 seconds. This timing anchor is an observable **test-harness boundary**, not proof of a failed render/CAS publication.
4. The **diagnostic-only** request-anchored waiter in `dj-request-anchored.log` preserved the original 12-second per-render threshold: commit at +3824–4333 ms; render at +4821–13697 ms (~8,876 ms). The render assertion cleared, exposing a later `#djDeck` actionability timeout. **No test timeout extension or source commit** followed.
5. After the render response, the DJ card and controls existed and were visible/enabled but located ~4,000 CSS pixels below the viewport while Studio's status still read `Revision saved. Rendering audio…` (see `dj-dom-pre.log`). Waiting for verified WAV before attempting mode navigation moved the failure to a `#studioModeDj` click timeout, **not a render-failure proof**. The center hit test still returned the actual DJ button (see `dj-hit-test.log`). This supports investigating Chromium responsiveness, phase boundaries and long tasks before changing CSS.
6. The same 1-GiB CPU-only KERNEL environment was used for these diagnostic replays. Memory contention/main-thread stalls remain hypotheses until independent renderer traces and a full repeat confirm them.

## Security and architecture hold

- Studio remains source, revision, render and audio authorization owner. Do not manufacture audio truth from DOM tags or browser cache.
- A `confirmed:true` field is not authorization for repaint, mastering, lock mutation, public publication, billed generation, or cinema grants. A true direct Chat executor requires canonical session/principal, exact current revision + expectedRevision CAS, protected lock/rights checks, durable operation IDs and fresh readback; approval is a separate authenticated operation, not a browser-supplied boolean.
- `AI Software Architect` guidance is review-only; `Superpowers` TDD / source-first red-green discipline is applicable. NVIDIA GPU spending is not pertinent to this 0-GPU source/Chromium defect. Android-device QA requires an actual runnable app/build; browser emulation alone is not Android device certification. Sentry production queries require a configured read-only token/connection and were not performed.

## Wake conditions / next owner work

**Studio browser/transport owner**: instrument A/B active detached `verifiedPlayback.media`, media readiness and position at the timed-out assertion; record Chromium main-thread long tasks and render/decoder time; distinguish test-clock misalignment from UI actionability and transport failure.

**Studio mobile QA**: use representative actual mobile browser and Android app build when available, with explicit 48px bounds and documented source/revision playback.

**Platform Chat owner**: qualify separate authenticated two-stage approval before any effectful protected mutation. Keep cinema grants delegated to `dj_rezrxtion`, not local creation by Chat.

**Certification**: Latest prior complete suite remains **25/28 Chromium**, 267/267 Python and 39/39 Node. This diagnostic **does not claim a new full-suite pass**, Android hardware PASS, direct protected Chat execution, physical listening, release or deployment.

## JUSTIN 101

WHAT CHANGED: exact source-based diagnostic classification and durable request/DOM measurements.
FAILED: candidate audio-tag/dock-overlay root-cause theories are unsupported; legacy render response/actionability timing remains reproduced.
PROVEN: lawful A/B proof was eventually correct in logged switch; render endpoint answered in ~9 sec; DJ mode button center was not occluded in observed frame.
UNPROVEN: all three browser failures eliminated, audio player lifecycle under every race, Android device, Sentry telemetry, production release.
TEAM NEXT: exact renderer performance trace, target-first TDD repair, full 28-case rerun.
JUSTIN ACTION: none for read-only diagnosis; retain draft/hold.

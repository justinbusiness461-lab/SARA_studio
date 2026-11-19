# Flight 001A — A/B completion after opening a project

Studio implementation follow-up, SARA_studio (1427534706), draft PR #31. Both test projects belong to the same authorized local session.

| Identity | SHA |
|---|---|
| Studio main at intake | d6aa889a0def72bb8e1c87009a98d6c29e47067e |
| Previous PR head, tested RED | e3a820ecc651ba915c03c9dc16425a7c0ba2f4ff |
| Repaired product and regression commit | c31db969e46a7c27229791f11b9b1dcffb8426bd |
| Tested Git tree | 57553f584fa3ec4d5b4cf36dbdd153121a634e44 |

## Artist-visible defect

Chromium generated two distinct projects through Studio and made a second revision in one of them. The test held the historical revision's audio request, opened the other project, and confirmed that the browser had verified that project's WAV. Releasing the old request exposed two outcomes on the previous candidate.

| Old request | Before repair | After repair |
|---|---|---|
| Delayed authorized WAV | Project field retained the newly opened ID while the transport and both proofs selected the old project's WAV | Newly opened project, revision, verified WAV, controls and transport preserved |
| Delayed HTTP 503 | The old error cleared the new transport and disabled Play | Newly opened project stayed playable with its verified transport |

Opening a valid project now invokes the same comparison reset used for New Project. The reset cancels the active comparison, discards its retry position, and clears the old controls before the new project's audio and revision history load. Studio verifies the opened project's audio using its existing server path. The installed-client cache key advances with the changed UI script.

## Replay and qualification

Use the prior return's Node 24, Python 3.12 and Playwright 1.57 / Chromium headless shell 153 setup. Run from the repository root with the browser path and module path configured.

    PYTHONPATH="$PWD/tools" python3 -m unittest discover -s tests -v
    node --test tests/*.test.cjs
    node --test --test-concurrency=2 tests/*.browser.cjs

For RED, copy the candidate tests/r2-ab.browser.cjs into a separate checkout of the previous head. Run the focused browser command there and again on the candidate.

    node --test --test-name-pattern='opening a different project supersedes' tests/r2-ab.browser.cjs

Results on the candidate were 66 Python checks, 11 Node checks and 20 Chromium entries passing. The browser total includes two parent tests. The new test contributes two late-response checks and one parent. The previous six failure cases, same-position playback and fresh server/browser reopen also passed. baseline.log records the previous head's two failed checks and IDs. The four logs and source digests are covered by SHA256SUMS.

Proof is bounded to local browser execution, verified project/revision/audio identity and UI state. Independent Night Lead replay of this commit is the next review gate. Hosted playback, physical phone operation and human listening remain open. No creative or release decision. Reverting the product commit removes this follow-up. Use a fresh cache key for an installed-client rollback.

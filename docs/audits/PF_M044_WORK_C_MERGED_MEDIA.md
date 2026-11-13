# M044 — Work C merged-main physical media qualification

Source: `749127ce0ce2cd08cdc5a6354626a078064f4704`.
PR #22 merged at `1ea3909a25a2365862bd6a1106cfb386d933a504`; candidate `91ed45f67f8c0bd432a7f4afb5de7a9ebe1dbdf5`.

## Independent results

- AUDIO VALIDITY: PASS bounded to newly generated server-rendered PCM16 files.
- MUSICAL EDIT CORRECTNESS: PASS at SongSpec and PCM locality level; listening unverified.
- PLAYBACK TRUTH: UNVERIFIED in this executor. Chromium launch fails before page creation with Unix socket `Operation not permitted`. No HTTP/browser result is inferred from direct accessor success.

A fresh deterministic 96 BPM E minor product specification (seed 44044) was generated, persisted, rendered through `render_publish_operation`, edited in Verse 2/Bass by exactly -12 semitones, persisted and rendered again. This is the 50.5-second specification, not the old 10.5-second fixture.

Both artifacts: 44,100 Hz, 2 channels, 2,227,050 frames, 50.5 seconds. FFmpeg independently decoded PCM exactly matches Python wave decoding. Both channels are identical (dual mono). Sample peak is 0.341156005859375 FS; zero clipped samples. Silent-frame totals are descriptive, not dropout or artistic approval. True peak and LUFS-I were not measured.

The edit interval is [1,102,500, 1,543,500) frames with a declared 4,410-frame tail. Zero changed frames outside this region and tail. Non-target SongSpec is exactly conserved. See JSON for target-event count, exact hashes, DC and silence counts.

A fresh Python process reopened R2 as current. R1 historical and R2 current lawful-accessor bytes equal their authoritative CAS artifact digests after reopen. These are direct server API calls, not HTTP requests. Browser same-position switching and actual listening remain unverified here.

## Reproduce

From this checkout: `npm ci --ignore-scripts --no-audit --no-fund`, then `python3 tools/work_c_main_physical.py` (requires NumPy and FFmpeg). The script creates a fresh temporary authority root and writes local WAVs plus the JSON receipt. WAVs are reproducible outputs and are not committed.

## Exact remaining edge

Owner: Work C / runtime-capable executor. Wake condition: executor permits browser/server sockets on this exact merged source. Capture authenticated HTTP R1/R2 responses, compare with the same authoritative artifacts, measure audible same-position A/B and perform listening. This executor limitation does not negate Work B's separately recorded runtime receipt.

No product code changed. No release, hosted deployment or creative approval claimed.

#!/usr/bin/env bash
set -euo pipefail

EXPECTED_MAIN_SHA="${EXPECTED_MAIN_SHA:-749127ce0ce2cd08cdc5a6354626a078064f4704}"
EXPECTED_PRODUCT_SHA="${EXPECTED_PRODUCT_SHA:-1ea3909a25a2365862bd6a1106cfb386d933a504}"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

HEAD="$(git rev-parse HEAD)"
printf 'RUNNABLE_POSTMERGE_HEAD=%s\n' "$HEAD"
printf 'EXPECTED_MAIN_SHA=%s\n' "$EXPECTED_MAIN_SHA"
printf 'EXPECTED_PRODUCT_SHA=%s\n' "$EXPECTED_PRODUCT_SHA"

if [[ "$HEAD" != "$EXPECTED_MAIN_SHA" ]]; then
  printf 'BLOCKED: checkout HEAD does not equal expected post-merge main\n' >&2
  exit 2
fi

if ! git merge-base --is-ancestor "$EXPECTED_PRODUCT_SHA" "$HEAD"; then
  printf 'BLOCKED: qualified PR22 merge SHA is not ancestor of checkout\n' >&2
  exit 3
fi

if [[ -n "$(git status --porcelain)" ]]; then
  printf 'BLOCKED: working tree dirty before reproduction\n' >&2
  git status --short >&2
  exit 4
fi

python3 --version
node --version
npm --version

npm ci

python3 -m unittest discover -s tests -v
node --test tests/scorecore.test.cjs tests/m044-session.test.cjs tests/prompt-ui.test.cjs

: "${CHROMIUM_PATH:?CHROMIUM_PATH must point to a real Chromium executable}"
node --test tests/r1-playback.browser.cjs
node --test tests/prompt-generate.browser.cjs
node --test tests/r2-ab.browser.cjs
node --test tests/r2-cold-reopen.browser.cjs

printf 'RUNNABLE_M044_POSTMERGE_REPRODUCTION=PASS\n'
printf 'SOURCE_MUTATION_BY_RUNNABLE=NONE\n'
printf 'PRODUCT_AUTHORITY_CREATED=NONE\n'
printf 'RELEASE_CERTIFIED=false\n'

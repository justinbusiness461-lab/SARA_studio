#!/usr/bin/env bash
set -euo pipefail

EXPECTED_SHA="${EXPECTED_SHA:-14e2fb9cc55c8ce2909803a66d509915a18eb625}"
REPRO_COMMIT="${REPRO_COMMIT:-c107da1308dcd972676d237d33b8c318f7d34f33}"
REPRO_PATH="evidence/work-b-m044-r2-crash/independent_pre_pending.py"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ACTUAL_SHA="$(git rev-parse HEAD)"
printf 'RUNNABLE_EXPECTED_SHA=%s\n' "$EXPECTED_SHA"
printf 'RUNNABLE_ACTUAL_SHA=%s\n' "$ACTUAL_SHA"
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
  printf 'BLOCKED: exact SHA mismatch\n' >&2
  exit 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  printf 'BLOCKED: working tree is not clean\n' >&2
  git status --short >&2
  exit 3
fi

python3 --version
node --version
npm --version

python3 -m unittest discover -s tests -v
node --test tests/scorecore.test.cjs tests/m044-session.test.cjs

EVIDENCE_DIR="$(mktemp -d)"
trap 'rm -rf "$EVIDENCE_DIR" .runnable_independent_pre_pending.py independent_pre_pending_result.json' EXIT
node tools/m044_probe.cjs "$EVIDENCE_DIR/m044-probe"

PYTHONPATH=tools:tests python3 -m unittest -v \
  test_m044_operations.OperationTests.test_malformed_historical_wav_rejected \
  test_m044_operations.OperationTests.test_crash_before_history_bind_recovers_without_replay

# Reuse the existing independent early-kill reproducer from its verified historical commit.
# This is test evidence only; it does not modify product source or create a second authority.
git show "${REPRO_COMMIT}:${REPRO_PATH}" > .runnable_independent_pre_pending.py
PYTHONPATH=tools:tests python3 .runnable_independent_pre_pending.py | tee "$EVIDENCE_DIR/early-crash.log"
cp independent_pre_pending_result.json "$EVIDENCE_DIR/independent_pre_pending_result.json"

python3 - <<'PY' "$EVIDENCE_DIR/independent_pre_pending_result.json"
import json, sys
p = sys.argv[1]
r = json.load(open(p, 'r', encoding='utf-8'))
print('EARLY_CRASH_VERDICT=' + str(r.get('verdict')))
print('R1_HISTORY_OCCURRENCES=' + str(r.get('historyOccurrences')))
print('R2_STILL_CURRENT=' + str(r.get('R2StillCurrent')))
print('ARTIFACT_HASH_VALID=' + str(r.get('artifactHashValid')))
print('ARTIFACT_DECODE_VALID=' + str(r.get('artifactDecodeValid')))
if r.get('verdict') != 'PASS':
    sys.exit(10)
PY

printf 'RUNNABLE_M044_CLEAN_RUN=PASS\n'
printf 'EVIDENCE_DIR=%s\n' "$EVIDENCE_DIR"

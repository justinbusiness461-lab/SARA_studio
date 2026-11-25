'use strict';
/** Independent test-side observations. Never a revision, rights, or media authority. */
const assert = require('node:assert/strict');

function validMedia(m) {
  if (!m || typeof m !== 'object') throw Error('MEDIA_SNAPSHOT_INVALID');
  if (!Number.isFinite(m.currentTimeSec) || !Number.isFinite(m.durationSec) ||
      m.durationSec <= 0 || m.currentTimeSec < 0 || m.currentTimeSec > m.durationSec + 0.05 ||
      !Number.isInteger(m.readyState) || m.readyState < 2 ||
      m.paused !== false || m.ended !== false) throw Error('MEDIA_CLOCK_INVALID_STATE');
  if (!Number.isFinite(m.observedAtMs)) throw Error('MEDIA_CLOCK_INVALID_OBSERVATION_TIME');
  return m;
}

function assertMediaIdentity(snapshot, expected) {
  validMedia(snapshot);
  if (!expected || typeof expected !== 'object' ||
      typeof expected.revisionId !== 'string' || !expected.revisionId ||
      typeof expected.artifactId !== 'string' || !expected.artifactId ||
      snapshot.revisionId !== expected.revisionId ||
      snapshot.artifactId !== expected.artifactId) throw Error('MEDIA_IDENTITY_MISMATCH');
  return snapshot;
}

function assertClockProgress(before, after, expected) {
  assertMediaIdentity(before, expected);
  assertMediaIdentity(after, expected);
  const observedElapsedMs = after.observedAtMs - before.observedAtMs;
  if (!(observedElapsedMs > 0 && observedElapsedMs <= 10000))
    throw Error('MEDIA_CLOCK_INVALID_OBSERVATION_TIME');
  const advanceSec = after.currentTimeSec - before.currentTimeSec;
  if (!(advanceSec >= 0.10)) throw Error('MEDIA_CLOCK_NOT_ADVANCING');
  // A discontinuous seek can manufacture progress without media clock running.
  if (advanceSec > observedElapsedMs / 1000 + 0.50)
    throw Error('MEDIA_CLOCK_IMPLAUSIBLE_ADVANCE');
  return {advanceSec, observedElapsedMs};
}

function assertABMediaReadback(ui, actual, expected) {
  if (!ui || !Number.isFinite(ui.fromPositionSec) ||
      !Number.isFinite(ui.toPositionSec) || ui.fromPositionSec < 0 ||
      ui.toPositionSec < 0) throw Error('AB_PROOF_INVALID');
  const uiDriftSec = Math.abs(ui.fromPositionSec - ui.toPositionSec);
  if (uiDriftSec > .05) throw Error('AB_POSITION_DRIFT');
  assertMediaIdentity(actual, expected);
  // Independent sample is taken after a browser/Playwright hop; 150 ms is
  // only an observation-lag bound. The stricter <=50ms gate is the verified
  // source-vs-restored UI switch proof, not this delayed sample.
  const sampleDriftSec = Math.abs(actual.currentTimeSec - ui.toPositionSec);
  if (sampleDriftSec > .15) throw Error('AB_MEDIA_READBACK_MISMATCH');
  return {uiDriftSec, sampleDriftSec};
}
module.exports = {assertClockProgress, assertMediaIdentity, assertABMediaReadback};

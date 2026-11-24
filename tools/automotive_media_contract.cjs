'use strict';
/**
 * S.A.R.A. Studio automotive adapter contract (NOT a native Android app).
 * Inputs are provided exclusively by a server-side, principal-authorized catalog
 * and media grant issuer. This module cannot validate server authority itself.
 * No browser state, CAS digest, media URL or car host can select current project truth.
 */
const OPAQUE_ID = /^opaque-[A-Za-z0-9_-]{1,120}$/;
function validOpaqueId(value) { return typeof value === 'string' && OPAQUE_ID.test(value); }
function carDisplayPolicy({ platform, driving, hostSupportsPresets = false,
  hostSupportsParkedScreens = false, parkedExperienceApproved = false } = {}) {
  if (platform !== 'android-auto' && platform !== 'android-automotive') throw new TypeError('Unsupported car platform');
  const parked = driving === false;
  return Object.freeze({
    playback: true, browse: true, voiceSearch: true,
    presetActions: hostSupportsPresets === true,
    // Android Auto phone projection does not grant arbitrary full-screen UI.
    visualizer: platform === 'android-automotive' && parked && hostSupportsParkedScreens === true && parkedExperienceApproved === true,
    fineEqSliders: platform === 'android-automotive' && parked && hostSupportsParkedScreens === true && parkedExperienceApproved === true,
    editor: false
  });
}
function createCarMediaBridge({ listAuthorized, resolveForPlayback } = {}) {
  if (typeof listAuthorized !== 'function' || typeof resolveForPlayback !== 'function') {
    throw new TypeError('Server-authorized catalog and fresh media grant issuer are required');
  }
  return Object.freeze({
    async browse() {
      // No cache: caller must use current principal/session and live revision membership.
      const list = await listAuthorized();
      if (!Array.isArray(list)) throw new TypeError('Invalid authorized catalog');
      return list.filter(x => x && x.isPlayable === true && validOpaqueId(x.mediaId))
        .map(x => Object.freeze({
          mediaId: x.mediaId,
          title: typeof x.title === 'string' ? x.title.slice(0, 200) : 'Untitled',
          artist: typeof x.artist === 'string' ? x.artist.slice(0, 160) : 'Unknown artist',
          durationMs: Number.isSafeInteger(x.durationMs) && x.durationMs >= 0 ? x.durationMs : 0
        }));
    },
    async play(mediaId) {
      if (!validOpaqueId(mediaId)) throw new TypeError('Invalid media id');
      // Each playback request MUST revalidate authorization, committed ancestry,
      // lawful revision->artifact association, digest and actual media decoding.
      // The server must issue a narrowly scoped short-lived HTTPS stream grant.
      const grant = await resolveForPlayback(mediaId);
      if (!grant || grant.mediaId !== mediaId || typeof grant.playableUrl !== 'string' ||
          !/^https:\/\/[^\s/?#]+[^\s]*$/.test(grant.playableUrl) ||
          !Number.isSafeInteger(grant.expiresAtMs) || grant.expiresAtMs <= Date.now() ||
          grant.expiresAtMs - Date.now() > 120000 ||
          typeof grant.sourceRevisionId !== 'string' || !grant.sourceRevisionId ||
          typeof grant.artifactId !== 'string' || !grant.artifactId) {
        throw new Error('Invalid or expired authorized stream grant');
      }
      return Object.freeze({ mediaId, playableUrl: grant.playableUrl,
        expiresAtMs: grant.expiresAtMs, sourceRevisionId: grant.sourceRevisionId, artifactId: grant.artifactId });
    }
  });
}
module.exports = { createCarMediaBridge, carDisplayPolicy };

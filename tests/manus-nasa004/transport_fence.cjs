'use strict';
/**
 * NASA-004 TEST REFERENCE ONLY — ephemeral audio-preview publication fence.
 * NOT a project/revision authority and NOT the Manus production UI implementation.
 * Current revision and accepted artifact MUST come from the authoritative server.
 */
class TransportFence {
  constructor() {
    this.generation = 0;
    this.authority = null;
    this.selected = null;
    this.pending = null;
    this.playback = null;
  }
  acceptServerAuthority({ currentRevisionId, currentArtifactId }) {
    if (!valid(currentRevisionId) || (currentArtifactId !== null && !valid(currentArtifactId)))
      throw Error('invalid authoritative revision/artifact identity');
    const before = this.authority;
    this.authority = { currentRevisionId, currentArtifactId };
    // An external edit/revision swap must invalidate the active current transport.
    if (!before || before.currentRevisionId !== currentRevisionId || before.currentArtifactId !== currentArtifactId) {
      this.generation += 1;
      this.pending = null;
      this.playback = null;
      this.selected = null;
    }
  }
  beginCurrent() {
    if (!this.authority || !this.authority.currentArtifactId)
      return { status: 'UNAVAILABLE', reason: 'current audio not verified', request: null };
    return this._begin(this.authority.currentRevisionId, this.authority.currentArtifactId, 'current');
  }
  beginHistorical(revisionId, artifactId) {
    if (!this.authority || !valid(revisionId) || !valid(artifactId))
      throw Error('verified historical binding required');
    if (revisionId === this.authority.currentRevisionId && artifactId === this.authority.currentArtifactId)
      return this.beginCurrent();
    // Caller still MUST prove this historical artifact binding with the server.
    return this._begin(revisionId, artifactId, 'historical');
  }
  _begin(revisionId, artifactId, kind) {
    const request = Object.freeze({generation: ++this.generation, revisionId, artifactId, kind});
    this.pending = request;
    this.selected = { revisionId, artifactId, kind, state: 'LOADING' };
    this.playback = null;
    return { status: 'LOADING', request };
  }
  complete(request, { digest, decoded, bindingVerified } = {}) {
    if (!request || !this.pending || request.generation !== this.generation || request !== this.pending)
      return {published: false, reason: 'STALE_REQUEST'};
    if (request.kind === 'current' && (!this.authority || request.revisionId !== this.authority.currentRevisionId || request.artifactId !== this.authority.currentArtifactId))
      return { published: false, reason: 'CURRENT_AUTHORITY_CHANGED' };
    if (!decoded || !bindingVerified || digest !== request.artifactId) {
      this.selected = { revisionId: request.revisionId, artifactId: request.artifactId, kind: request.kind, state:'UNAVAILABLE' };
      this.pending = null;
      this.playback = null;
      return { published: false, reason: 'AUDIO_UNAVAILABLE' };
    }
    this.playback = { revisionId: request.revisionId, artifactId: request.artifactId, kind: request.kind };
    this.selected = { ...this.playback, state: 'PLAYABLE' };
    this.pending = null;
    return {published: true, kind: request.kind};
  }
  abort() {
    this.generation++;
    this.pending = null;
    this.playback = null;
    if (this.selected) this.selected = {...this.selected, state:'CANCELLED'};
  }
  snapshot() {
    return JSON.parse(JSON.stringify({authority:this.authority, selected:this.selected, playback:this.playback, generation:this.generation}));
  }
}
function valid(s) { return typeof s === 'string' && /^[0-9a-f]{64}$/.test(s); }
module.exports = {TransportFence};

const test = require('node:test');
const assert = require('node:assert/strict');
const { renderCaptured } = require('../tools/m044-session.cjs');

test('render completion retains captured revision, spec and sources even if caller mutates input', async () => {
  const source = { manifest: { projectId: 'p' }, revision: { revisionId: 'r1', sourceAssetDigests: ['source'] }, songSpec: { title: 'A' } };
  let release, captured, committed;
  const rendering = new Promise(resolve => { release = resolve; });
  const work = renderCaptured(source, 'render-1', {
    render: async spec => { captured = spec; await rendering; return Buffer.from('wav'); },
    write: async () => ({ sha256: 'audio' }),
    commit: async payload => { committed = payload; return payload; }
  });
  source.songSpec.title = 'B'; source.revision.revisionId = 'r2'; source.revision.sourceAssetDigests.push('wrong');
  release(); await work;
  assert.equal(captured.title, 'A');
  assert.equal(committed.expectedCurrentRevisionId, 'r1');
  assert.deepEqual(committed.sourceAssetDigests, ['source']);
  assert.deepEqual(committed.outputArtifactIds, ['audio']);
});
test('stale render rejects once without retrying commit', async () => {
  let calls = 0;
  await assert.rejects(() => renderCaptured({ manifest: { projectId: 'p' }, revision: { revisionId: 'r1', sourceAssetDigests: [] }, songSpec: {} }, 'render-old', {
    render: async () => Buffer.from('orphan'), write: async () => ({ sha256: 'orphan' }),
    commit: async () => { calls++; throw Error('409 stale'); }
  }), /409/);
  assert.equal(calls, 1);
});

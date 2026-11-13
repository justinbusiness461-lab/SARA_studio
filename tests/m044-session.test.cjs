const test = require('node:test');
const assert = require('node:assert/strict');
const { renderCaptured } = require('../tools/m044-session.cjs');

test('render completion retains captured revision and publishes one durable transaction', async () => {
  const source = { manifest: { projectId: 'p' }, revision: { revisionId: 'r1', sourceAssetDigests: ['source'] }, songSpec: { title: 'A' } };
  let release, captured, published;
  const rendering = new Promise(resolve => { release = resolve; });
  const work = renderCaptured(source, 'render-1', {
    render: async spec => { captured = spec; await rendering; return Buffer.from('wav'); },
    publish: async payload => { published = payload; return payload; }
  });
  source.songSpec.title = 'B'; source.revision.revisionId = 'r2'; source.revision.sourceAssetDigests.push('wrong');
  release(); await work;
  assert.equal(captured.title, 'A');
  assert.equal(published.projectId, 'p');
  assert.equal(published.sourceRevisionId, 'r1');
  assert.equal(published.operationId, 'render-1');
  assert.deepEqual(Buffer.from(published.data_bytes), Buffer.from('wav'));
});

test('render path refuses legacy split write/commit publication', async () => {
  let writes = 0, commits = 0;
  await assert.rejects(() => renderCaptured(
    { manifest: { projectId: 'p' }, revision: { revisionId: 'r1', sourceAssetDigests: [] }, songSpec: {} },
    'render-old',
    {
      render: async () => Buffer.from('orphan'),
      write: async () => { writes++; return { sha256: 'orphan' }; },
      commit: async () => { commits++; return {}; }
    }), /durable render publisher required/);
  assert.equal(writes, 0);
  assert.equal(commits, 0);
});

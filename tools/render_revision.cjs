'use strict';
const fs = require('node:fs');
const { render } = require('./m044-session.cjs');

(async () => {
  const input = fs.readFileSync(0, 'utf8');
  const spec = JSON.parse(input);
  const wav = await render(spec);
  process.stdout.write(wav);
})().catch(error => {
  console.error(error && error.stack || String(error));
  process.exit(2);
});
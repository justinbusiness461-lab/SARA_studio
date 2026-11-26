'use strict';
/** Test-harness aggregation only. Not Studio authority, media decoding, or listening proof. */
const SONGS = new Set(['Turn The Noise Back On','If This Is All I Get','Outlaws and Echoes']);
const WIDTHS = [390,1440];
function finiteNonnegative(v){ return typeof v==='number' && Number.isFinite(v) && v>=0; }
function assertThreeSongBrowserCoverage(records){
  if(!Array.isArray(records)) throw Error('R34_BROWSER_COVERAGE_INVALID');
  const clocks=new Set(), ab=new Set();
  for(const row of records){
    if(!row || typeof row!=='object' || !WIDTHS.includes(row.width))
      throw Error('R34_BROWSER_COVERAGE_UNEXPECTED_VIEWPORT');
    if(Object.hasOwn(row,'ab')){
      if(row.ab!=='R1->R2' || ab.has(row.width)) throw Error('R34_AB_COVERAGE_INVALID');
      ab.add(row.width);
      for(const key of ['r1PositionDriftSec','r2PositionDriftSec']){
        if(!finiteNonnegative(row[key]) || row[key]>.05) throw Error('R34_AB_DRIFT_UNVERIFIED');
      }
      for(const key of ['independentR1LagSec','independentR2LagSec']){
        if(!finiteNonnegative(row[key]) || row[key]>.15) throw Error('R34_AB_MEDIA_READBACK_UNVERIFIED');
      }
      continue;
    }
    const key=`${row.width}:${row.title}`;
    if(!SONGS.has(row.title) || clocks.has(key)) throw Error('R34_CLOCK_COVERAGE_INVALID');
    clocks.add(key);
    if(typeof row.revisionId!=='string' || !row.revisionId ||
       typeof row.artifactId!=='string' || !row.artifactId ||
       !finiteNonnegative(row.mediaClockAdvanceSec) || row.mediaClockAdvanceSec<.10 ||
       !finiteNonnegative(row.mediaObservedElapsedMs) || row.mediaObservedElapsedMs<=0 ||
       row.mediaObservedElapsedMs>10000)
      throw Error('R34_CLOCK_NOT_PHYSICALLY_OBSERVED');
  }
  if(clocks.size!==SONGS.size*WIDTHS.length ||
     [...SONGS].some(title=>WIDTHS.some(width=>!clocks.has(`${width}:${title}`))))
    throw Error('R34_CLOCK_COVERAGE_INCOMPLETE');
  if(ab.size!==WIDTHS.length || WIDTHS.some(width=>!ab.has(width)))
    throw Error('R34_AB_COVERAGE_INCOMPLETE');
  return {clockCount:clocks.size,abCount:ab.size,widths:[...WIDTHS]};
}
module.exports={assertThreeSongBrowserCoverage};

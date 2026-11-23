'use strict';
/** Diagnostics are read-only: never revision, artifact or timing authority. */
async function installQaLongtasks(page){
 await page.addInitScript(()=>{
  window.__QA_LONG_TASKS__=[];
  try{
   const observer=new PerformanceObserver(list=>{
    for(const entry of list.getEntries()){
     const target=window.__QA_LONG_TASKS__;
     if(target.length<256)target.push({startMs:Math.round(entry.startTime),
        durationMs:Math.round(entry.duration)});
    }
   });
   observer.observe({entryTypes:['longtask']});
  }catch(_){}
 });
}
async function qaSnapshot(page){
 try{
  return await page.evaluate(()=>{
    const playback=typeof verifiedPlayback!=='undefined'?verifiedPlayback:null;
    const media=playback?.media;
    return {
      status:document.querySelector('#status')?.textContent,
      abStatus:document.querySelector('#abStatus')?.textContent,
      selectedRevision:window.__M044_PLAYBACK_PROOF__?.revisionId||null,
      switch:window.__M044_AB_SWITCH__,abProof:window.__M044_AB_PROOF__,
      activeDetachedMedia:media?{paused:media.paused,readyState:media.readyState,
        networkState:media.networkState,currentTime:media.currentTime,
        duration:media.duration,hasSource:!!media.src}:null,
      longtasks:(window.__QA_LONG_TASKS__||[]).slice(-25)
    };
  });
 }catch(error){return {diagnosticUnavailable:String(error)};}
}
module.exports={installQaLongtasks,qaSnapshot};


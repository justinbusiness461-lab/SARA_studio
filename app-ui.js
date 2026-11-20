/** Tauri IPC bridge — no-op in plain browser */
function hasNativeShell() {
  return !!(window.__TAURI_IPC__ || (window.__TAURI__ && window.__TAURI__.core));
}
function logToNative(eventType, message) {
  console.log("[UI-Log] [" + eventType + "] " + message);
  try {
    if (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) {
      window.__TAURI__.core.invoke("native_log_event", {
        eventType: String(eventType),
        message: String(message)
      }).catch(function (err) { console.warn("[Tauri]", err); });
    } else if (window.__TAURI__ && window.__TAURI__.tauri && window.__TAURI__.tauri.invoke) {
      window.__TAURI__.tauri.invoke("native_log_event", {
        eventType: String(eventType),
        message: String(message)
      }).catch(function (err) { console.warn("[Tauri]", err); });
    }
  } catch (e) { /* browser-only */ }
}

let activeSectionIdx = 0;

function render() {
  if (!skeleton) return;
  const tb = skeleton.timebase;
  const repaintTrack = $("m045TargetTrack");
  if (repaintTrack) {
    const selected = repaintTrack.value;
    repaintTrack.replaceChildren();
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "Select an unlocked track";
    repaintTrack.appendChild(empty);
    skeleton.tracks.forEach(track => {
      const option = document.createElement("option");
      option.value = track.track_id;
      option.textContent = track.track_id + (track.sonic_lock ? " · Sonic Lock ON" : "");
      option.disabled = !!track.sonic_lock;
      repaintTrack.appendChild(option);
    });
    if (skeleton.tracks.some(track => track.track_id === selected && !track.sonic_lock))
      repaintTrack.value = selected;
  }
  $("meta").innerHTML =
    "<strong>" + (skeleton.title || "Song") + "</strong> · " +
    tb.initial_bpm + " BPM · " + tb.key + " · " + tb.genre +
    "<br/><span style='color:var(--m);font-size:0.75rem'>" + skeleton.song_id +
    " · " + skeleton.tracks.length + " tracks · Phase 4 spatial + vocal</span>";

  $("sections").innerHTML = skeleton.structure.sections.map((s, i) =>
    "<span class='badge" + (i === activeSectionIdx ? " role" : "") + (s.muted ? " muted" : "") + "' data-sec='" + i + "' data-sid='" + s.id + "' style='cursor:pointer'>" +
    s.name + (s.role !== "none" ? " · " + s.role : "") + (s.muted ? " · MUTE" : "") + "</span>"
  ).join("") +
  "<div style='margin-top:8px;display:flex;gap:6px;flex-wrap:wrap'>" +
  "<button class='secondary sm' id='btnSecMute'>Mute section</button>" +
  "<button class='secondary sm' id='btnSecDup'>Duplicate section</button>" +
  "<button class='secondary sm' id='btnRestore'>Restore last save</button>" +
  "</div>";
  document.querySelectorAll("[data-sec]").forEach(el => {
    el.onclick = () => {
      activeSectionIdx = +el.dataset.sec;
      syncSectionEditors();
      render();
    };
  });
  syncSectionEditors();

  const btnSecMute = $("btnSecMute");
  if (btnSecMute) btnSecMute.onclick = () => {
    const sec = skeleton.structure.sections[activeSectionIdx];
    if (!sec) return;
    const r = muteSectionEvents(sec.id, !sec.muted);
    if (r.ok) { render(); setStatus((sec.muted ? "Muted" : "Unmuted") + " section " + sec.name, "ok"); }
  };
  const btnSecDup = $("btnSecDup");
  if (btnSecDup) btnSecDup.onclick = () => {
    const sec = skeleton.structure.sections[activeSectionIdx];
    if (!sec) return;
    const r = duplicateSection(sec.id);
    if (r.ok) { activeSectionIdx = skeleton.structure.sections.length - 1; render(); setStatus("Duplicated → " + r.section_id, "ok"); }
  };
  const btnRestore = $("btnRestore");
  if (btnRestore) btnRestore.onclick = () => {
    restoreProjectFromStorage().catch(e => setStatus('Open failed: ' + e.message, 'warn'));
  };


  const mix = $("mixer");
  mix.innerHTML = "";
  const sel = $("editTrack");
  sel.innerHTML = "";
  skeleton.tracks.forEach(tr => {
    const opt = document.createElement("option");
    opt.value = tr.track_id;
    opt.textContent = tr.name + " [" + tr.type + "]";
    sel.appendChild(opt);
    const el = document.createElement("div");
    el.className = "strip";
    el.innerHTML =
      "<div class='strip-name'>" + tr.name + "</div>" +
      "<div class='strip-row'>" +
      "<label>Vol</label><input type='range' min='-24' max='6' step='0.5' value='" + (tr.volume_db || 0) + "' data-vol='" + tr.track_id + "'/>" +
      "<label>Pan</label><input type='range' min='-1' max='1' step='0.05' value='" + (tr.pan || 0) + "' data-pan='" + tr.track_id + "'/>" +
      "<button class='secondary sm' data-mute='" + tr.track_id + "'>" + (tr.muted ? "Unmute" : "Mute") + "</button>" +
      "<button class='secondary sm' data-lock='" + tr.track_id + "' aria-pressed='" + (!!tr.sonic_lock) + "'>" + (tr.sonic_lock ? "Sonic Lock™ ON" : "Sonic Lock™ OFF") + "</button>" +
      "</div>";
    mix.appendChild(el);
  });
  mix.querySelectorAll("[data-vol]").forEach(inp => {
    inp.oninput = () => {
      const t = skeleton.tracks.find(x => x.track_id === inp.dataset.vol);
      if (t) t.volume_db = +inp.value;
    };
  });
  mix.querySelectorAll("[data-pan]").forEach(inp => {
    inp.oninput = () => {
      const t = skeleton.tracks.find(x => x.track_id === inp.dataset.pan);
      if (t) t.pan = +inp.value;
    };
  });
  mix.querySelectorAll("[data-mute]").forEach(btn => {
    btn.onclick = () => {
      const t = skeleton.tracks.find(x => x.track_id === btn.dataset.mute);
      if (!t) return;
      t.muted = !t.muted;
      btn.textContent = t.muted ? "Unmute" : "Mute";
      btn.style.background = t.muted ? "var(--danger)" : "";
      btn.style.color = t.muted ? "#fff" : "";
    };
  });
  mix.querySelectorAll("[data-lock]").forEach(btn => {
    btn.onclick = () => {
      const tr = skeleton.tracks.find(x => x.track_id === btn.dataset.lock);
      if (!tr) return;
      tr.sonic_lock = !tr.sonic_lock;
      m045LocksDirty = true;
      btn.textContent = tr.sonic_lock ? "Sonic Lock™ ON" : "Sonic Lock™ OFF";
      btn.setAttribute("aria-pressed", String(!!tr.sonic_lock));
      setStatus("Sonic Lock changed in draft · Save project before generation", "warn");
    };
  });
  drawMatrix();
  drawScratchGrid();
}

function drawScratchGrid() {
  const box=$("djGrid");
  if (!box) return;
  box.replaceChildren();
  if (!skeleton || !window.ScoreCore) return;
  const section=skeleton.structure.sections[activeSectionIdx];
  if (!section) return;
  const technique=$("djTechnique").value, deck=$("djDeck").value;
  const markers=skeleton.tracks.find(t=>t.track_id==="dj_scratch");
  for (let step=0;step<16;step++) {
    const tick=section.start_tick+step*480;
    const cell=document.createElement("button");
    cell.type="button";
    cell.className="cell";
    cell.dataset.djStep=String(step);
    cell.textContent=String(step+1);
    const found=markers && markers.events.find(e=>e.type==="DJ_SCRATCH_MARKER" &&
       e.tick===tick && e.deck===deck);
    if (found) cell.classList.add("on");
    cell.setAttribute("aria-pressed",String(!!found));
    cell.title=found ? found.technique+" · "+deck+" · sample "+found.sample_index
                     : "Add "+technique+" · Deck "+deck+" · step "+(step+1);
    cell.onclick=()=>{
      try {
        const proposed=window.ScoreCore.toggleScratchMarker(skeleton,{
          sectionId:section.id,stepIndex:step,
          technique:$("djTechnique").value,deck:$("djDeck").value});
        skeleton=proposed;
        window.skeleton=skeleton;
        clearVerifiedPlayback();
        ++m045RequestToken;
        m045ClearTakes();
        m045PublishProof("DECLARED");
        render();
        setStatus("DJ marker changed in draft · Save project before playback/render","warn");
        $("djGridStatus").textContent="Symbolic DJ marker recorded · audio UNRENDERED until a lawful source asset is qualified";
      } catch (error) {
        setStatus("Scratch edit blocked: "+String(error.message||error),"warn");
      }
    };
    box.appendChild(cell);
  }
}

function syncSectionEditors() {
  if (!skeleton) return;
  const sec = skeleton.structure.sections[activeSectionIdx];
  if (!sec) return;
  const lyr = $("lyrics");
  const role = $("vocalRole");
  if (lyr) lyr.value = sec.lyrics || "";
  if (role) role.value = sec.role || "none";
}

function drawMatrix() {
  const box = $("matrix");
  box.innerHTML = "";
  if (!skeleton) return;
  const track = skeleton.tracks.find(t => t.track_id === $("editTrack").value);
  if (!track) return;
  const step = TPQ / 2;
  for (let i = 0; i < 16; i++) {
    const tick = i * step;
    const cell = document.createElement("div");
    cell.className = "cell";
    const hit = track.events.find(e => Math.abs(e.tick - tick) < 20);
    if (hit) {
      cell.classList.add("on");
      if (hit.note_number === 36) cell.classList.add("kick");
    }
    cell.onclick = () => {
      if (hit) track.events = track.events.filter(e => e !== hit);
      else {
        const note = track.type === "DRUMS" ? 36 : track.type === "BASS" ? 36 : track.type === "VOCAL" ? 57 : 60;
        track.events.push({
          type: "NOTE_ON", tick, note_number: note, velocity: 100,
          duration_ticks: step - 40, phoneme: "ah", word: "ah", role: "male"
        });
      }
      drawMatrix();
    };
    box.appendChild(cell);
  }
}

function compile() {
  const text = ($("prompt").value || "").trim() ||
    "dark 102 BPM alt hip-hop, F# minor, guitar plucks, male verse";
  // Admission precedes draft mutation. The shared adapter owns no project state.
  const bpmO = $("bpmOverride");
  const keyO = $("keyOverride");
  let directive = text;
  if (bpmO && bpmO.value) directive += " " + bpmO.value + " BPM";
  if (keyO && keyO.value) directive += " " + keyO.value;
  const intent = window.ScoreCore.musicIntent(directive);
  skeleton = window.ScoreCore.compileIntent(intent, parsePrompt);
  window.skeleton = skeleton;
  const titleEl = $("title");
  skeleton.title = (titleEl && titleEl.value) ? titleEl.value : (text.slice(0, 40) || "Generated");

  activeSectionIdx = 0;
  render();
  setStatus(
    "Compiled · " + skeleton.timebase.initial_bpm + " BPM · " + skeleton.timebase.key +
    " · " + skeleton.tracks.reduce((n, t) => n + t.events.length, 0) + " notes · spatial BBD",
    "ok"
  );
}

async function generateProject() {
  clearVerifiedPlayback();
  try {
    setStatus('Generating…', 'warn');
    compile();
    setStatus('Generating…', 'warn');
    const saved = await saveJSON(false);
    setStatus('Revision saved. Rendering audio…', 'warn');
    const rendered = await renderAndVerifyRevision(saved);
    abRevisions = { r1: revisionRef(rendered), r2: null };
    setABControls();
  } catch (error) {
    clearVerifiedPlayback();
    const message = String(error && error.message || error);
    setStatus(message.startsWith('Audio unavailable') ? message : 'Generate failed: ' + message, 'warn');
  }
}

function audioBufferToWav(buffer) {
  const nCh = buffer.numberOfChannels, sr = buffer.sampleRate, len = buffer.length;
  const ab = new ArrayBuffer(44 + len * nCh * 2), v = new DataView(ab);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, "RIFF"); v.setUint32(4, 36 + len * nCh * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, nCh, true);
  v.setUint32(24, sr, true); v.setUint32(28, sr * nCh * 2, true);
  v.setUint16(32, nCh * 2, true); v.setUint16(34, 16, true);
  w(36, "data"); v.setUint32(40, len * nCh * 2, true);
  let off = 44;
  const ch = [];
  for (let c = 0; c < nCh; c++) ch.push(buffer.getChannelData(c));
  for (let i = 0; i < len; i++) for (let c = 0; c < nCh; c++) {
    let s = Math.max(-1, Math.min(1, ch[c][i]));
    v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true); off += 2;
  }
  return ab;
}


/** Offline render of current skeleton; returns {buffer, metrics} with RMS/peak proof. */
async function renderMixBuffer() {
  if (!skeleton) compile();
  const sr = 44100;
  const dur = ticksToSec(totalTicks()) + 0.5;
  const off = new OfflineAudioContext(2, Math.ceil(sr * dur), sr);
  skeleton.tracks.forEach(track => {
    if (track.muted) return;
    const gScale = Math.pow(10, (track.volume_db || 0) / 20);
    track.events.forEach(ev => {
      if (ev.type !== "NOTE_ON" || ev.velocity === 0) return;
      const rnd = mulberry32(hashSeed(track.track_id + "|" + ev.tick + "|" + (skeleton.generation_seed || 0)));
      const t = ticksToSec(ev.tick);
      const durN = ticksToSec(ev.duration_ticks || TPQ / 2);
      const vel = (ev.velocity || 100) / 127;
      if (track.type === "DRUMS") {
        if (ev.note_number === 36) {
          const o = off.createOscillator(), gn = off.createGain();
          o.frequency.setValueAtTime(150, t);
          o.frequency.exponentialRampToValueAtTime(40, t + 0.12);
          gn.gain.setValueAtTime(0.45 * gScale * vel, t);
          gn.gain.exponentialRampToValueAtTime(0.001, t + 0.25);
          o.connect(gn); gn.connect(off.destination);
          o.start(t); o.stop(t + 0.28);
        } else if (ev.note_number === 38) {
          const len = Math.floor(sr * 0.12);
          const buf = off.createBuffer(1, len, sr);
          const d = buf.getChannelData(0);
          for (let i = 0; i < len; i++) d[i] = (rnd() * 2 - 1) * Math.exp(-12 * i / len);
          const src = off.createBufferSource(), gn = off.createGain();
          src.buffer = buf;
          gn.gain.setValueAtTime(0.35 * gScale * vel, t);
          gn.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
          src.connect(gn); gn.connect(off.destination);
          src.start(t);
        } else {
          const o = off.createOscillator(), gn = off.createGain();
          o.type = "square";
          o.frequency.value = 8000;
          gn.gain.setValueAtTime(0.08 * gScale * vel, t);
          gn.gain.exponentialRampToValueAtTime(0.001, t + 0.04);
          o.connect(gn); gn.connect(off.destination);
          o.start(t); o.stop(t + 0.05);
        }
      } else if (track.type === "BASS" || track.type === "LEAD" || track.type === "PAD" || track.type === "VOCAL" || track.type === "STRINGS") {
        const o = off.createOscillator(), gn = off.createGain();
        o.type = track.type === "BASS" ? "sawtooth" : (track.type === "PAD" ? "triangle" : "sine");
        o.frequency.value = midiToFreq(ev.note_number);
        gn.gain.setValueAtTime(0, t);
        gn.gain.linearRampToValueAtTime(0.14 * gScale * vel, t + 0.02);
        gn.gain.exponentialRampToValueAtTime(0.001, t + Math.max(0.05, durN));
        o.connect(gn); gn.connect(off.destination);
        o.start(t); o.stop(t + durN + 0.05);
      }
    });
  });
  const buffer = await off.startRendering();
  let peak = 0, sumSq = 0, n = 0;
  for (let c = 0; c < buffer.numberOfChannels; c++) {
    const data = buffer.getChannelData(c);
    for (let i = 0; i < data.length; i++) {
      const s = data[i];
      const a = Math.abs(s);
      if (a > peak) peak = a;
      sumSq += s * s;
      n++;
    }
  }
  const rms = n ? Math.sqrt(sumSq / n) : 0;
  const metrics = {
    duration_sec: buffer.duration,
    sample_rate: buffer.sampleRate,
    channels: buffer.numberOfChannels,
    peak: peak,
    rms: rms,
    nonzero: rms > 1e-5,
    frames: buffer.length
  };
  return { buffer, metrics };
}

async function exportWav() {
  if (!skeleton) compile();
  const renderSpec = JSON.parse(serializeProject());
  const expectedRef = durableProjectRef && { ...durableProjectRef };
  const renderSourceAssets = durableSourceAssets.slice();
  setStatus("Rendering mix WAV…", "warn");
  try {
    const { buffer, metrics } = await renderMixBuffer();
    if (!metrics.nonzero) {
      setStatus("Export blocked: silent buffer (RMS=" + metrics.rms.toFixed(6) + ")", "warn");
      return null;
    }
    const wav = audioBufferToWav(buffer);
    const written = await fetch('/api/write_production_file', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Studio-Capability': window.__STUDIO_CAPABILITY__ || '' },
      body: JSON.stringify({ filename: (renderSpec.song_id || 'song') + '_mix.wav', subdirectory: 'audio-masters', data_bytes: Array.from(new Uint8Array(wav)) })
    });
    const artifact = await written.json();
    if (!written.ok || artifact.status !== 'SUCCESS') throw new Error(artifact.error || 'Export persistence failed');
    await commitProjectSnapshot(renderSpec, [artifact.sha256], expectedRef, renderSourceAssets);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([wav], { type: "audio/wav" }));
    a.download = (renderSpec.song_id || "song") + "_mix.wav";
    a.click();
    setStatus(
      "Mix WAV exported · " + metrics.duration_sec.toFixed(1) + "s · peak " +
      metrics.peak.toFixed(3) + " · RMS " + metrics.rms.toFixed(4),
      "ok"
    );
    return metrics;
  } catch (e) {
    setStatus("Export failed: " + e.message, "warn");
    return null;
  }
}

function exportMEG() {
  if (!skeleton) compile();
  logToNative("EXPORT_MEG", "Compiling Cinema Music Event Graph");
  const events = [];
  const bpm = skeleton.timebase.initial_bpm;
  skeleton.structure.sections.forEach(s => {
    events.push({
      type: "SECTION_START", tick: s.start_tick,
      sample: Math.round(ticksToSec(s.start_tick) * 44100),
      name: s.name, vocal_role: s.role, lyrics: s.lyrics || ""
    });
    events.push({
      type: "SECTION_END", tick: s.end_tick,
      sample: Math.round(ticksToSec(s.end_tick) * 44100),
      name: s.name
    });
  });
  const vocal = skeleton.tracks.find(t => t.type === "VOCAL");
  if (vocal) {
    vocal.events.forEach(ev => {
      events.push({
        type: "PHONEME",
        tick: ev.tick,
        sample: Math.round(ticksToSec(ev.tick) * 44100),
        end_sample: Math.round(ticksToSec(ev.tick + (ev.duration_ticks || TPQ / 2)) * 44100),
        phoneme: ev.phoneme || "ah",
        word: ev.word || "",
        note: ev.note_number,
        role: ev.role || "male",
        viseme: (ev.phoneme === "ee" ? "E" : ev.phoneme === "oo" ? "U" : ev.phoneme === "oh" ? "O" : "A")
      });
    });
  }

  // Auto-run cinematic viseme preview from exported phonemes
  const visemeChain = [];
  events.forEach(ev => {
    if (ev.type === "PHONEME" && (ev.viseme || ev.phoneme)) {
      visemeChain.push(ev.viseme || ev.phoneme);
    }
  });
  if (!visemeChain.length) visemeChain.push("A", "E", "O", "U");
  if (window.pulseForgeCinemaSync) {
    logToNative("HARNESS_SOLVER", "Driving viewport with " + visemeChain.length + " visemes");
    window.pulseForgeCinemaSync.animateVocalPerformanceLoop(visemeChain, 280);
    visemeChain.slice(0, 8).forEach(v => {
      const t = window.pulseForgeCinemaSync.solveVisemeMechanics(v);
      logToNative("HARNESS_OUTPUT", "Viseme [" + t.viseme + "] jawY=" + t.jawY + " scaleX=" + t.scaleX);
    });
  }

  events.sort((a, b) => a.tick - b.tick);
  const meg = {
    $schema: "pulseforge.music_event_graph.v2",
    song_id: skeleton.song_id,
    timebase: skeleton.timebase,
    events,
    generated_at: new Date().toISOString()
  };
  const megName = (skeleton.song_id || "song") + "_MusicEventGraph.json";
  savePayload(megName, JSON.stringify(meg, null, 2), "meg", "application/json");
  setStatus("Music Event Graph + viseme preview exported", "ok");
  logToNative("EXPORT_COMPLETE", "MEG written");
}

let verifiedPlayback = null;
let verifiedPlaybackSource = null;

function studioProjectHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-Studio-Capability': window.__STUDIO_CAPABILITY__ || '',
    'X-Studio-Session': window.__STUDIO_SESSION__ || ''
  };
}

function clearVerifiedPlayback() {
  if (verifiedPlayback && verifiedPlayback.media) {
    try { verifiedPlayback.media.pause(); } catch (_) {}
  }
  if (verifiedPlayback && verifiedPlayback.objectUrl) {
    try { URL.revokeObjectURL(verifiedPlayback.objectUrl); } catch (_) {}
  }
  verifiedPlaybackSource = null;
  verifiedPlayback = null;
  if (typeof m045Wave4Clear === "function") m045Wave4Clear();
  window.__M044_PLAYBACK_PROOF__ = null;
  paintVerifiedWaveform();
  window.__M044_PLAYBACK_STARTED__ = false;
  const play = $('btnPlay');
  if (play) { play.disabled = true; play.textContent = 'Play'; }
}

async function sha256Hex(arrayBuffer) {
  const digest = await crypto.subtle.digest('SHA-256', arrayBuffer);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}

async function projectAudioBytes(projectId, revisionId, artifactId) {
  const response = await fetch('/api/projects/audio', {
    method: 'POST',
    headers: studioProjectHeaders(),
    body: JSON.stringify({ projectId, revisionId, artifactId })
  });
  if (!response.ok) {
    let reason = 'HTTP ' + response.status;
    try { const body = await response.json(); reason = body.error || reason; } catch (_) {}
    throw new Error('Audio unavailable: ' + reason);
  }
  return response.arrayBuffer();
}

async function verifyPlayableRevision(result, publishGuard = null, publishPresentation = true) {
  const ids = result && result.revision && result.revision.outputArtifactIds;
  if (!Array.isArray(ids) || ids.length !== 1) throw new Error('Audio unavailable: revision has no single authorized WAV');
  const projectId = result.manifest.projectId;
  const revisionId = result.revision.revisionId;
  const artifactId = ids[0];
  const bytes = await projectAudioBytes(projectId, revisionId, artifactId);
  if (publishGuard && !publishGuard()) return null;
  const wavSha256 = await sha256Hex(bytes);
  if (publishGuard && !publishGuard()) return null;
  if (wavSha256 !== artifactId) throw new Error('Audio unavailable: returned WAV identity mismatch');
  const view = new DataView(bytes);
  const text = (offset, count) => String.fromCharCode(...new Uint8Array(bytes, offset, count));
  if (bytes.byteLength < 44 || text(0, 4) !== 'RIFF' || text(8, 4) !== 'WAVE') {
    throw new Error('Audio unavailable: returned bytes are not a WAV');
  }
  const objectUrl = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }));
  const media = new Audio();
  media.preload = 'auto';
  const decoded = new Promise((resolve, reject) => {
    const done = () => {
      media.removeEventListener('loadedmetadata', loaded);
      media.removeEventListener('error', failed);
    };
    const loaded = () => { done(); resolve(); };
    const failed = () => { done(); reject(new Error('Audio unavailable: browser WAV decode failed')); };
    media.addEventListener('loadedmetadata', loaded, { once: true });
    media.addEventListener('error', failed, { once: true });
  });
  media.src = objectUrl;
  media.load();
  try {
    await decoded;
  } catch (error) {
    URL.revokeObjectURL(objectUrl);
    throw error;
  }
  if (!Number.isFinite(media.duration) || media.duration <= 0) {
    URL.revokeObjectURL(objectUrl);
    throw new Error('Audio unavailable: decoded WAV duration is invalid');
  }
  if (publishGuard && !publishGuard()) {
    media.pause();
    URL.revokeObjectURL(objectUrl);
    return null;
  }
  const playback = { projectId, revisionId, artifactId, wavSha256, media, objectUrl, waveformPeaks: authorizedWaveformPeaks(bytes) };
  if (publishPresentation) {
    verifiedPlayback = playback;
    publishVerifiedPlaybackPresentation(playback);
  }
  return playback;
}

function verifiedPlaybackProof(playback) {
  return {
    projectId: playback.projectId,
    revisionId: playback.revisionId,
    artifactId: playback.artifactId,
    wavSha256: playback.wavSha256,
    decodedWavValidity: true,
    durationSec: playback.media.duration,
    transportSelectedRevision: playback.revisionId
  };
}

// Non-authoritative waveform presentation, sampled only from verified PCM16 WAV.
function authorizedWaveformPeaks(bytes) {
  if (!(bytes instanceof ArrayBuffer) || bytes.byteLength < 44) return null;
  const view = new DataView(bytes);
  const channels = view.getUint16(22, true), bits = view.getUint16(34, true);
  if (channels !== 2 || bits !== 16 || view.getUint16(20, true) !== 1) return null;
  let offset = 12;
  while (offset + 8 <= bytes.byteLength) {
    const tag = String.fromCharCode(...new Uint8Array(bytes, offset, 4));
    const length = view.getUint32(offset + 4, true);
    const first = offset + 8;
    if (first + length > bytes.byteLength) return null;
    if (tag === 'data') {
      const count = Math.floor(length / 4);
      if (!count) return null;
      const peaks = [];
      for (let x = 0; x < 280; x++) {
        const a = Math.floor(x * count / 280);
        const b = Math.max(a + 1, Math.floor((x + 1) * count / 280));
        const step = Math.max(1, Math.floor((b - a) / 12));
        let peak = 0;
        for (let i = a; i < Math.min(count, b); i += step) {
          const k = first + i * 4;
          peak = Math.max(peak, Math.abs(view.getInt16(k, true)) / 32768,
            Math.abs(view.getInt16(k + 2, true)) / 32768);
        }
        peaks.push(peak);
      }
      return peaks;
    }
    offset = first + length + (length % 2);
  }
  return null;
}
function paintVerifiedWaveform(playback = null) {
  const canvas = $('studioWaveformPreview');
  if (!canvas || !canvas.getContext) return;
  const context = canvas.getContext('2d');
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
  canvas.removeAttribute('data-artifact-id');
  if (!playback || !Array.isArray(playback.waveformPeaks)) return;
  context.fillStyle = '#65d2e7';
  const mid = canvas.height / 2;
  playback.waveformPeaks.forEach((peak, x) => {
    const height = Math.max(1, Math.min(1, peak) * (canvas.height - 8));
    context.fillRect(x, mid - height / 2, 1, height);
  });
  canvas.dataset.artifactId = playback.artifactId;
}

function publishVerifiedPlaybackPresentation(playback) {
  window.__M044_PLAYBACK_PROOF__ = verifiedPlaybackProof(playback);
  paintVerifiedWaveform(playback);
  const play = $('btnPlay');
  if (play) play.disabled = false;
  setStatus('Audio verified. Ready to hear.', 'ok');
}

async function renderAndVerifyRevision(saved) {
  const response = await fetch('/api/projects/render', {
    method: 'POST',
    headers: studioProjectHeaders(),
    body: JSON.stringify({
      projectId: saved.manifest.projectId,
      sourceRevisionId: saved.revision.revisionId,
      operationId: 'render:' + saved.revision.revisionId,
      filename: (saved.songSpec.song_id || 'song') + '_' + saved.revision.revisionId.slice(0, 12) + '.wav',
      subdirectory: 'm044'
    })
  });
  let rendered;
  try { rendered = await response.json(); } catch (_) { rendered = null; }
  if (!response.ok || !rendered || rendered.status !== 'SUCCESS') {
    throw new Error('Audio unavailable: ' + ((rendered && rendered.error) || 'render publication failed'));
  }
  showProjectAuthority(rendered);
  await verifyPlayableRevision(rendered);
  return rendered;
}

async function playVerifiedRevision() {
  if (!verifiedPlayback || !verifiedPlayback.media) {
    setStatus('Audio unavailable: no verified revision-bound WAV', 'warn');
    return false;
  }
  try {
    await verifiedPlayback.media.play();
  } catch (error) {
    setStatus('Audio unavailable: browser playback failed', 'warn');
    return false;
  }
  playing = true;
  window.__M044_PLAYBACK_STARTED__ = true;
  const play = $('btnPlay');
  if (play) play.textContent = 'Stop';
  setStatus('Playing verified revision · ' + verifiedPlayback.revisionId, 'ok');
  verifiedPlayback.media.onended = () => {
    playing = false;
    if (play) play.textContent = 'Play';
  };
  return true;
}

let abRevisions = { r1: null, r2: null };
let abRequestGeneration = 0;
window.__M044_AB_SWITCH__ = { state: 'IDLE', generation: 0, targetRevisionId: null };

let abOrigin = null;
let activeABSwitch = null;

function resetProjectComparison() {
  abRevisions = { r1: null, r2: null };
  abOrigin = null;
  abRequestGeneration++;
  if (activeABSwitch) activeABSwitch.abort();
  window.__M044_AB_PROOF__ = null;
  window.__M044_AB_SWITCH__ = { state: 'IDLE', generation: abRequestGeneration, targetRevisionId: null };
  clearVerifiedPlayback();
  playing = false;
  setABControls();
}

async function restoreABPosition(media, position, signal) {
  if (!Number.isFinite(position) || position < 0 || position > media.duration) {
    throw new Error('Selected audio does not cover the comparison position');
  }
  if (media.currentTime !== position) media.currentTime = position;
  if (media.seeking) {
    await new Promise((resolve, reject) => {
      const listeners = new AbortController();
      const options = { signal: listeners.signal };
      function finish(error) {
        clearTimeout(timeout);
        listeners.abort();
        if (error) reject(error);
        else resolve();
      }
      const timeout = setTimeout(() => finish(new Error('Audio seek timed out')), 5000);
      media.addEventListener('seeked', () => finish(), options);
      media.addEventListener('error', () => finish(new Error('Audio seek failed')), options);
      signal.addEventListener('abort', () => finish(new Error('Switch superseded')), options);
    });
  }
  const actual = media.currentTime;
  // Same 50 ms bound as the Studio desktop A/B qualification.
  if (!Number.isFinite(actual) || Math.abs(actual - position) > 0.05) {
    throw new Error('Could not restore the comparison position');
  }
  return actual;
}


function setABControls() {
  const edit = $('btnOctaveEdit');
  if (edit) edit.disabled = !abRevisions.r1 || !!abRevisions.r2;
  const r1 = $('btnABR1'), r2 = $('btnABR2');
  const ready = !!(abRevisions.r1 && abRevisions.r2);
  if (r1) r1.disabled = !ready;
  if (r2) r2.disabled = !ready;
  if ($('abStatus') && !ready) $('abStatus').textContent = 'A/B unavailable until R2 is verified';
}

function revisionRef(result) {
  return {
    projectId: result.manifest.projectId,
    revisionId: result.revision.revisionId,
    artifactId: result.revision.outputArtifactIds[0]
  };
}

function publishABSwitchState(generation, target, state, extra = {}) {
  if (generation !== abRequestGeneration) return false;
  window.__M044_AB_SWITCH__ = {
    generation,
    operationId: 'ab:' + generation + ':' + target.revisionId,
    targetRevisionId: target.revisionId,
    artifactId: target.artifactId,
    state,
    ...extra
  };
  return true;
}


async function applyVerse2BassOctave() {
  if (!durableProjectRef || !abRevisions.r1 || abRevisions.r2) return;
  const baseRef = { ...durableProjectRef };
  clearVerifiedPlayback();
  setStatus('Applying edit…', 'warn');
  try {
    const base = await projectRequest('open', {
      projectId: baseRef.projectId,
      revisionId: baseRef.revisionId
    });
    const verses = base.songSpec.structure.sections.filter(section =>
      section.type === 'verse' || section.name === 'Verse');
    if (verses.length < 2) throw new Error('Verse 2 is unavailable');
    const bassTracks = base.songSpec.tracks.filter(track => track.track_id === 'bass' || track.type === 'BASS');
    if (bassTracks.length !== 1) throw new Error('Bass target is unavailable or ambiguous');
    const edited = window.ScoreCore.transposeSection(base.songSpec, {
      sectionId: verses[1].id,
      trackId: bassTracks[0].track_id,
      semitones: -12
    });
    const committed = await projectRequest('commit', {
      projectId: baseRef.projectId,
      expectedCurrentRevisionId: baseRef.revisionId,
      songSpec: edited,
      sourceAssetDigests: base.revision.sourceAssetDigests,
      outputArtifactIds: [],
      operationId: 'edit:verse2:bass:-12:' + baseRef.revisionId
    });
    const loaded = loadProjectObject(committed.songSpec);
    if (!loaded.ok) throw new Error(loaded.error);
    showProjectAuthority(committed);
    render();
    setStatus('Revision saved. Rendering audio…', 'warn');
    const rendered = await renderAndVerifyRevision(committed);
    abRevisions.r2 = revisionRef(rendered);
    setABControls();
    if ($('abStatus')) $('abStatus').textContent = 'Selected R2 · current';
    window.__M044_R2_PROOF__ = {
      projectId: rendered.manifest.projectId,
      revisionId: rendered.revision.revisionId,
      artifactId: rendered.revision.outputArtifactIds[0],
      parentRevisionId: rendered.revision.parentRevisionId
    };
  } catch (error) {
    clearVerifiedPlayback();
    setStatus('Edit failed: ' + String(error && error.message || error), 'warn');
  }
}

async function selectABRevision(label) {
  const target = abRevisions[label.toLowerCase()];
  if (!target || !abRevisions.r2) return false;
  ++projectOpenGenerationToken; // A/B selection supersedes pending project opens.
  const requestGeneration = ++abRequestGeneration;
  if (activeABSwitch) activeABSwitch.abort();
  const operation = new AbortController();
  activeABSwitch = operation;
  const current = () => requestGeneration === abRequestGeneration && !operation.signal.aborted;
  const from = verifiedPlayback;
  if (from || abOrigin?.pair !== abRevisions) {
    abOrigin = {
      pair: abRevisions,
      revisionId: from?.revisionId ?? null,
      artifactId: from?.artifactId ?? null,
      position: from?.media.currentTime ?? 0,
      resume: Boolean(playing && from && !from.media.paused),
    };
  }
  const origin = abOrigin;
  const scope = { fromRevisionId: origin.revisionId, fromPositionSec: origin.position };
  window.__M044_AB_PROOF__ = null;
  const status = $('abStatus');
  status.textContent = 'Loading ' + label + '…';
  publishABSwitchState(requestGeneration, target, 'SWITCH_REQUESTED', scope);

  let playback = from;
  let staged = null;
  let restoredPosition = origin.position;
  try {
    if (!from || from.projectId !== target.projectId || from.revisionId !== target.revisionId ||
        from.artifactId !== target.artifactId) {
      clearVerifiedPlayback();
      playing = false;
      publishABSwitchState(requestGeneration, target, 'TARGET_LOADING', scope);
      const opened = await projectRequest('open', { projectId: target.projectId, revisionId: target.revisionId });
      if (!current()) return false;
      const ref = revisionRef(opened);
      if (ref.projectId !== target.projectId || ref.revisionId !== target.revisionId ||
          ref.artifactId !== target.artifactId) throw new Error('Opened audio does not match the selected revision');
      staged = await verifyPlayableRevision(opened, current, false);
      if (!current()) return false;
      if (!staged) throw new Error('Selected audio could not be verified');
      playback = staged;
      operation.signal.addEventListener('abort', () => playback.media.pause(), { once: true });
      publishABSwitchState(requestGeneration, target, 'TARGET_VERIFIED', scope);
      restoredPosition = await restoreABPosition(playback.media, origin.position, operation.signal);
      if (!current()) return false;
      publishABSwitchState(requestGeneration, target, 'POSITION_RESTORED', { ...scope, toPositionSec: restoredPosition });
      if (origin.resume) {
        await playback.media.play();
        if (!current()) return false;
        playing = true;
        window.__M044_PLAYBACK_STARTED__ = true;
      }
    }
    // Publish the transport and both proofs together after the last await.
    verifiedPlayback = playback;
    paintVerifiedWaveform(playback);
    const proof = verifiedPlaybackProof(playback);
    window.__M044_PLAYBACK_PROOF__ = proof;
    window.__M044_AB_PROOF__ = {
      ...scope, fromArtifactId: origin.artifactId, toRevisionId: playback.revisionId,
      toArtifactId: playback.artifactId, toPositionSec: restoredPosition,
    };
    publishABSwitchState(requestGeneration, target, 'COMPLETE', {
      ...scope, toPositionSec: restoredPosition, transportSelectedRevision: proof.revisionId, proofRevisionId: proof.revisionId,
    });
    $('btnPlay').disabled = false;
    $('btnPlay').textContent = playing ? 'Stop' : 'Play';
    setStatus(playing ? 'Playing verified revision · ' + playback.revisionId : 'Audio verified. Ready to hear.', 'ok');
    status.textContent = label === 'R2' ? 'Selected R2 · current' : 'Selected R1 · historical';
    return true;
  } catch (error) {
    if (!current()) return false;
    clearVerifiedPlayback();
    playing = false;
    origin.resume = false;
    const reason = error.message || 'Selected audio is unavailable';
    publishABSwitchState(requestGeneration, target, 'FAILED', { ...scope, error: reason });
    status.textContent = 'A/B failed · ' + reason + ' · Select a revision to retry';
    setStatus(status.textContent, 'warn');
    return false;
  } finally {
    if (activeABSwitch === operation) activeABSwitch = null;
    if (staged && verifiedPlayback !== staged) {
      staged.media.pause();
      URL.revokeObjectURL(staged.objectUrl);
    }
  }
}

let m045RequestToken = 0;
let m045TakeToken = 0;
let m045TakeUrl = null;
let m045TakeContext = null;
let m045LocksDirty = false;

function m045ClearTakes() {
  ++m045TakeToken;
  const audio = $("m045TakePreview");
  if (audio) { audio.pause(); audio.removeAttribute("src"); audio.load(); }
  if (m045TakeUrl) URL.revokeObjectURL(m045TakeUrl);
  m045TakeUrl = null;
  m045TakeContext = null;
  const panel = $("m045TakePanel");
  if (panel) panel.hidden = true;
  const buttons = $("m045TakeButtons");
  if (buttons) buttons.replaceChildren();
}

function m045TakeHeaders() {
  return {...studioProjectHeaders(), Authorization:"Bearer " + (window.__STUDIO_SESSION__ || "")};
}

function m045PublishTakes(attempt, pointer) {
  m045ClearTakes();
  if (!attempt || !Array.isArray(attempt.takes) || attempt.takes.length <= 1 || !pointer) return;
  const panel = $("m045TakePanel");
  const buttons = $("m045TakeButtons");
  if (!panel || !buttons) return;
  panel.hidden = false;
  const context = {projectId:pointer.projectId, idempotencyKey:pointer.idempotencyKey};
  m045TakeContext = context;
  attempt.takes.forEach((take, i) => {
    if (take.take_index !== i) return;
    const audition = document.createElement("button");
    audition.type = "button";
    audition.className = "secondary sm";
    audition.textContent = "Audition Take " + (i + 1);
    audition.dataset.m045Audition = String(i);
    audition.onclick = () => m045AuditionTake(i, context).catch(e => setStatus("Take audition failed: " + e.message,"warn"));
    buttons.appendChild(audition);
    const select = document.createElement("button");
    select.type = "button";
    select.className = "secondary sm";
    select.textContent = "Select Take " + (i + 1);
    select.dataset.m045Select = String(i);
    select.onclick = () => m045SelectTake(i, context).catch(e => setStatus("Take promotion failed: " + e.message,"warn"));
    buttons.appendChild(select);
  });
}

async function m045AuditionTake(index, context) {
  const generation = ++m045TakeToken;
  const projectGeneration = m045RequestToken;
  const active = durableProjectRef && {...durableProjectRef};
  if (!active || active.projectId !== context.projectId || m045TakeContext !== context)
    throw new Error("Take project changed");
  const response = await fetch("/api/m045/attempts/take-audio", {
    method:"POST", headers:m045TakeHeaders(),
    body:JSON.stringify({project_id:context.projectId,idempotency_key:context.idempotencyKey,take_index:index})
  });
  if (!response.ok) throw new Error("Take playback not authorized (" + response.status + ")");
  const audioBlob = await response.blob();
  if (generation !== m045TakeToken || projectGeneration !== m045RequestToken ||
      m045TakeContext !== context || !durableProjectRef ||
      durableProjectRef.projectId !== context.projectId) return;
  const media = $("m045TakePreview");
  if (!media) return;
  const priorPosition = Number.isFinite(media.currentTime) ? media.currentTime : 0;
  media.pause();
  if (m045TakeUrl) URL.revokeObjectURL(m045TakeUrl);
  m045TakeUrl = URL.createObjectURL(audioBlob);
  media.src = m045TakeUrl;
  try {
    await new Promise((resolve, reject) => {
      if (media.readyState >= 1) return resolve();
      media.addEventListener("loadedmetadata", resolve, {once:true});
      media.addEventListener("error", () => reject(new Error("Take WAV decode failed")), {once:true});
      media.load();
    });
  } catch (error) {
    if (generation === m045TakeToken) throw error;
    return;
  }
  if (generation !== m045TakeToken || projectGeneration !== m045RequestToken ||
      m045TakeContext !== context || !durableProjectRef ||
      durableProjectRef.projectId !== context.projectId) return;
  if (!Number.isFinite(media.duration) || media.duration <= 0)
    throw new Error("Take WAV duration invalid");
  media.currentTime = Math.min(priorPosition, Math.max(0, media.duration - 0.01));
  $("m045TakeStatus").textContent = "Auditioning Take " + (index + 1) + " · not promoted";
  await media.play().catch(() => {});
}

async function m045SelectTake(index, context) {
  const generation = ++m045TakeToken;
  const projectGeneration = m045RequestToken;
  const active = durableProjectRef && {...durableProjectRef};
  if (!active || active.projectId !== context.projectId || m045TakeContext !== context)
    throw new Error("Take project changed");
  const response = await fetch("/api/m045/attempts/select-take", {
    method:"POST", headers:m045TakeHeaders(), body:JSON.stringify({
      project_id:context.projectId,idempotency_key:context.idempotencyKey,
      take_index:index,expected_current_revision_id:active.revisionId})
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Take promotion rejected");
  if (generation !== m045TakeToken || projectGeneration !== m045RequestToken ||
      m045TakeContext !== context || !durableProjectRef ||
      durableProjectRef.projectId !== context.projectId ||
      durableProjectRef.revisionId !== active.revisionId) return;
  // Read back authoritative revision before updating selected playback or badges.
  const opened = await projectRequest("open",{projectId:context.projectId});
  if (generation !== m045TakeToken || projectGeneration !== m045RequestToken ||
      !durableProjectRef || durableProjectRef.revisionId !== active.revisionId) return;
  if (opened.revision.revisionId !== result.revision.revisionId)
    throw new Error("Selected take was not current on independent readback");
  showProjectAuthority(opened);
  $("m045TakeStatus").textContent = "Take " + (index + 1) + " selected · revision " + result.revision.revisionId;
  m045PublishProof(result.state,result.attempt);
  m045PublishTakes(result.attempt,context);
  setStatus("Selected Take " + (index + 1) + " · re-open to verify audio", "ok");
}



function m045ProofText(state, attempt = {}) {
  const prov = attempt.provenance || {};
  const status = ["COMMITTED", "ASSOCIATED_HISTORICAL"].includes(state) ? state : String(state || "DECLARED");
  const tier = ["P0", "P1", "P2", "P3"].includes(prov.preservation_tier) ? prov.preservation_tier : "PRESERVATION_UNVERIFIED";
  const rights = prov.rights_status || "RIGHTS_UNVERIFIED";
  return [status, tier, prov.provider_id || "PROVIDER_UNVERIFIED", rights, "audio quality UNVERIFIED"].join(" · ");
}
function m045PublishProof(state, attempt) {
  const node = $("m045Proof");
  if (node) node.textContent = m045ProofText(state, attempt);
}
async function submitM045Attempt() {
  const active = durableProjectRef && {...durableProjectRef};
  if (!active || !skeleton) throw new Error("Save or open a project first");
  if (m045LocksDirty) throw new Error("Save Sonic Lock changes before generation");
  if (skeleton.tracks.some(track => track.sonic_lock === true))
    throw new Error("Sonic Lock prevents full-song reconstruction");
  const duration = Number($("m045Duration").value);
  if (!Number.isInteger(duration) || duration < 3 || duration > 210) throw new Error("Duration must be 3–210 seconds");
  const provider = $("m045Provider").value;
  const model = provider === "ace" ? "ace-step-1.5" : "music_v2_5";
  const modelVersion = provider === "ace" ? "ace-step-1.5" : "elevenlabs-music-v2.5";
  const batchCount = Number($("m045BatchCount").value);
  if (!Number.isInteger(batchCount) || batchCount < 1 || batchCount > 4)
    throw new Error("Generation take count must be 1–4");
  if (batchCount > 1 && provider !== "ace")
    throw new Error("Multi-take generation requires ACE-Step");
  const params = {music_length_ms: duration * 1000};
  const start = $("m045BarStart").value.trim();
  const end = $("m045BarEnd").value.trim();
  if (start || end) {
    if (!Number.isInteger(+start) || !Number.isInteger(+end) || +start < 1 || +end <= +start)
      throw new Error("Enter a valid bar range");
    if (provider !== "ace") throw new Error("Repaint currently requires ACE-Step");
    const target = $("m045TargetTrack").value;
    if (!target || !skeleton.tracks.some(track => track.track_id === target && !track.sonic_lock))
      throw new Error("Select an unlocked target track");
    if (batchCount > 1) throw new Error("Multi-take repaint not qualified");
    params.edit_mode = "repaint";
    params.start_bar = +start;
    params.end_bar = +end;
    params.target_track_id = target;
  }
  const generation = ++m045RequestToken;
  const abToken = abRequestGeneration;
  m045PublishProof("DECLARED");
  const body = {
    project_id: active.projectId, base_revision_id: active.revisionId,
    expected_current_revision_id: active.revisionId,
    idempotency_key: crypto.randomUUID(), model_id: model,
    model_version: modelVersion, prompt: ($("prompt").value || "").trim(),
    song_spec: JSON.parse(serializeProject()), lyrics: null, seed: 0, params,
    batch_count:batchCount
  };
  if (!body.prompt) throw new Error("Prompt required");
  const response = await fetch("/api/m045/attempts", {
    method:"POST", headers: {...studioProjectHeaders(), Authorization:"Bearer " + (window.__STUDIO_SESSION__ || "")},
    body: JSON.stringify(body)
  });
  const result = await response.json();
  if (generation !== m045RequestToken || !durableProjectRef ||
      durableProjectRef.projectId !== active.projectId ||
      durableProjectRef.revisionId !== active.revisionId || abToken !== abRequestGeneration) return;
  if (!response.ok) {
    m045PublishProof("DECLARED");
    throw new Error(result.error || "Generation attempt rejected");
  }
  m045PublishProof(result.state, result.attempt);
  if (result.state === "AWAITING_TAKE_SELECTION") {
    const pointer = {projectId:active.projectId,idempotencyKey:body.idempotency_key};
    try { localStorage.setItem("m045_attempt_pointer", JSON.stringify(pointer)); } catch (_) {}
    m045PublishTakes(result.attempt,pointer);
    setStatus("Generation ready · audition takes before selecting a winner","warn");
    return;
  }
  if (["COMMITTED", "ASSOCIATED_HISTORICAL"].includes(result.state)) {
    try { localStorage.setItem("m045_attempt_pointer", JSON.stringify({
      projectId:active.projectId,idempotencyKey:body.idempotency_key
    })); } catch (_) {}
    setStatus("Generation recorded · reopen project for authoritative audio readback", "warn");
  }
}
async function recoverM045Proof() {
  const generation = ++m045RequestToken;
  const active = durableProjectRef && {...durableProjectRef};
  let pointer = null;
  try { pointer = JSON.parse(localStorage.getItem("m045_attempt_pointer") || "null"); } catch (_) {}
  if (!active || !pointer || pointer.projectId !== active.projectId || !pointer.idempotencyKey) {
    m045PublishProof("DECLARED");
    return;
  }
  const response = await fetch("/api/m045/attempts/reconcile",{
    method:"POST",headers:{...studioProjectHeaders(),Authorization:"Bearer " + (window.__STUDIO_SESSION__ || "")},
    body:JSON.stringify({project_id:active.projectId,idempotency_key:pointer.idempotencyKey})
  });
  const result = await response.json();
  if (generation !== m045RequestToken || !durableProjectRef || durableProjectRef.projectId !== active.projectId) return;
  m045PublishProof(response.ok ? result.state : "DECLARED", response.ok ? result.attempt : null);
  m045PublishTakes(response.ok ? result.attempt : null,
                   response.ok ? pointer : null);
}
let projectOpenGenerationToken = 0;
let durableProjectRef = null;
let durableSourceAssets = [];

async function projectRequest(route, payload) {
  const response = await fetch('/api/projects/' + route, {
    method: 'POST',
    headers: studioProjectHeaders(),
    body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok || result.status !== 'SUCCESS') throw new Error(result.error || 'Project request failed');
  return result;
}

function showProjectAuthority(result) {
  if (!durableProjectRef ||
      durableProjectRef.projectId !== result.manifest.projectId ||
      durableProjectRef.revisionId !== result.revision.revisionId) {
    ++m045RequestToken;
    m045ClearTakes();
    m045PublishProof("DECLARED");
  }
  durableProjectRef = { projectId: result.manifest.projectId, revisionId: result.revision.revisionId };
  durableSourceAssets = result.revision.sourceAssetDigests.slice();
  try { localStorage.setItem('sf_project_ref', JSON.stringify(durableProjectRef)); } catch (_) {}
  if ($('projectId')) $('projectId').value = durableProjectRef.projectId;
  if ($('projectRevision')) $('projectRevision').textContent = 'Saved revision: ' + durableProjectRef.revisionId;
  if (typeof renderLyricAuthority === 'function') renderLyricAuthority(result.lyricTimeline || null);
}

async function commitProjectSnapshot(spec, outputArtifactIds, expectedRef, sourceAssets = durableSourceAssets.slice()) {
  const entered = $('projectId') && $('projectId').value.trim();
  if ((!expectedRef && entered) || (expectedRef && entered !== expectedRef.projectId)) throw new Error('Open the selected project before saving, or choose New project');
  const result = await projectRequest('commit', {
    projectId: expectedRef ? expectedRef.projectId : null,
    expectedCurrentRevisionId: expectedRef ? expectedRef.revisionId : null,
    songSpec: spec,
    sourceAssetDigests: sourceAssets,
    outputArtifactIds: outputArtifactIds || []
  });
  const active = durableProjectRef;
  if ((!expectedRef && !active) || (expectedRef && active && expectedRef.projectId === active.projectId && expectedRef.revisionId === active.revisionId)) {
    showProjectAuthority(result);
  }
  return result;
}

async function saveJSON(announce = true) {
  if (!skeleton) compile();
  // Capture draft and expected pointer together; pending edits cannot change the commit.
  const spec = JSON.parse(serializeProject());
  const expected = durableProjectRef && { ...durableProjectRef };
  const result = await commitProjectSnapshot(spec, [], expected);
  m045LocksDirty = false;
  if (announce) setStatus('Project saved · ' + result.manifest.projectId, 'ok');
  return result;
}

async function restoreProjectFromStorage() {
  ++m045RequestToken;
  let id = $('projectId') && $('projectId').value.trim();
  const enteredId = id || '';
  if (!id) {
    // Cache is an address only; authorization and currentness are server-owned.
    try { id = JSON.parse(localStorage.getItem('sf_project_ref') || '{}').projectId; } catch (_) {}
  }
  if (!id) throw new Error('Enter a durable project ID');
  const generation = ++projectOpenGenerationToken;
  const isCurrent = () => {
    const visibleId = $('projectId') && $('projectId').value.trim();
    return generation === projectOpenGenerationToken &&
      (visibleId === id || (!enteredId && !visibleId));
  };
  // Invalidate all previous project, audio, A/B and proof presentation at request start.
  ++abRequestGeneration;
  if (typeof activeABSwitch !== 'undefined' && activeABSwitch) activeABSwitch.abort();
  window.__M044_AB_PROOF__ = null;
  window.__M044_AB_SWITCH__ = {state:'IDLE',generation:abRequestGeneration,targetRevisionId:null};
  abRevisions = {r1:null,r2:null};
  setABControls();
  clearVerifiedPlayback();
  m045PublishProof('DECLARED');
  durableProjectRef = null;
  if ($('projectRevision')) $('projectRevision').textContent = 'Loading selected project…';
  setStatus('Opening selected project · ' + id + '…', 'warn');
  try {
    const result = await projectRequest('open', {projectId:id});
    if (!isCurrent()) return null;
    if (!result.manifest || result.manifest.projectId !== id)
      throw new Error('Project open returned a different project');
    const loaded = loadProjectObject(result.songSpec);
    if (!loaded.ok) throw new Error(loaded.error);
    if (!isCurrent()) return null;
    showProjectAuthority(result);
    m045LocksDirty = false;
    recoverM045Proof().catch(() => { if (isCurrent()) m045PublishProof('DECLARED'); });
    if ($('title')) $('title').value = result.songSpec.title || '';
    if ($('prompt')) $('prompt').value = result.songSpec.prompt || '';
    render();
    setStatus('Opened durable revision · ' + result.revision.revisionId + ' · Verifying audio…', 'warn');
    try {
    const playback = await verifyPlayableRevision(result, isCurrent);
    if (!isCurrent() || !playback) return null;
    const outputs = result.revision.outputArtifactIds || [];
    if (outputs.length === 1) {
      let ancestorId = result.revision.parentRevisionId;
      let previousPlayable = null;
      const seen = new Set();
      while (ancestorId && !seen.has(ancestorId)) {
        seen.add(ancestorId);
        const ancestor = await projectRequest('open', {projectId:id,revisionId:ancestorId});
        if (!isCurrent()) return null;
        if (ancestor.manifest.projectId !== id) throw new Error('Historical project membership mismatch');
        const ancestorOutputs = ancestor.revision.outputArtifactIds || [];
        if (ancestorOutputs.length === 1) { previousPlayable = ancestor; break; }
        ancestorId = ancestor.revision.parentRevisionId;
      }
      if (!isCurrent()) return null;
      abRevisions = previousPlayable
        ? {r1:revisionRef(previousPlayable),r2:revisionRef(result)}
        : {r1:revisionRef(result),r2:null};
      setABControls();
      if (previousPlayable && $('abStatus')) $('abStatus').textContent = 'Selected R2 · current';
    }
    } catch (audioError) {
      if (!isCurrent()) return null;
      clearVerifiedPlayback();
      abRevisions = {r1:null,r2:null};
      setABControls();
      setStatus('Audio unavailable: ' + String(audioError && audioError.message || audioError), 'warn');
    }
    return result;
  } catch (error) {
    if (!isCurrent()) return null; // stale failures cannot erase the new selection
    clearVerifiedPlayback();
    abRevisions = {r1:null,r2:null};
    setABControls();
    durableProjectRef = null;
    if ($('projectRevision')) $('projectRevision').textContent = 'Project unavailable · no selected revision';
    m045PublishProof('DECLARED');
    setStatus('Open failed: ' + String(error && error.message || error), 'warn');
    throw error;
  }
}


$("btnCompile").onclick = generateProject;
$("btnPlay").onclick = () => {
  if (playing && verifiedPlayback && verifiedPlayback.media) {
    verifiedPlayback.media.pause();
    playing = false;
    $("btnPlay").textContent = 'Play';
    setStatus('Stopped');
    return;
  }
  logToNative('TRANSPORT', 'verified revision play');
  playVerifiedRevision();
};
$("btnStop").onclick = () => {
  if (verifiedPlayback && verifiedPlayback.media) verifiedPlayback.media.pause();
  playing = false;
  stopAll();
  if (window.pulseForgeCinemaSync) window.pulseForgeCinemaSync.stopLoop();
  if ($('btnPlay')) $('btnPlay').textContent = 'Play';
  setStatus("Stopped");
  logToNative("TRANSPORT", "stopped");
};
$("btnWav").onclick = exportWav;
$("btnMEG").onclick = exportMEG;
$("btnSave").onclick = () => saveJSON().catch(e => setStatus("Save failed: " + e.message, "warn"));
if ($("btnM045Generate")) $("btnM045Generate").onclick = () =>
  submitM045Attempt().catch(e => setStatus("M045 blocked: " + e.message, "warn"));
$("editTrack").onchange = drawMatrix;
if ($("djTechnique")) $("djTechnique").onchange = drawScratchGrid;
if ($("djDeck")) $("djDeck").onchange = drawScratchGrid;

const lyricsEl = $("lyrics");
if (lyricsEl) {
  lyricsEl.oninput = () => {
    if (!skeleton) return;
    const sec = skeleton.structure.sections[activeSectionIdx];
    if (sec) {
      sec.lyrics = lyricsEl.value;
      rebuildVocalsFromLyrics();
      drawMatrix();
    }
  };
}
const roleEl = $("vocalRole");
if (roleEl) {
  roleEl.onchange = () => {
    if (!skeleton) return;
    const sec = skeleton.structure.sections[activeSectionIdx];
    if (sec) {
      sec.role = roleEl.value;
      rebuildVocalsFromLyrics();
      render();
    }
  };
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {});
  });
}

$("prompt").value = "dark 102 BPM alt hip-hop, F# minor, guitar plucks, male verse, female chorus";
compile();

const btnLoad = $("btnLoad");
const fileIn = $("fileIn");
if (btnLoad && fileIn) {
  btnLoad.onclick = () => fileIn.click();
  fileIn.onchange = (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      try {
        const d = JSON.parse(r.result);
        if (d.structure && d.tracks) {
          const lr = loadProjectObject(d);
          if (!lr.ok) { setStatus("Load failed: " + lr.error, "warn"); return; }
          if ($("title") && d.title) $("title").value = d.title;
          if ($("prompt") && d.prompt) $("prompt").value = d.prompt;
          render();
          setStatus("ScoreGraph loaded", "ok");
        } else setStatus("Not a SongSpec JSON", "warn");
      } catch (err) { setStatus("Load failed: " + err.message, "warn"); }
    };
    r.readAsText(f);
  };
}

logToNative("ENGINE_INIT", "Sound Forge UI ready · Tauri=" + hasNativeShell());



/* Phase 6 UI: mic ingest + look-at armature */
let lookAtTarget = { x: 0, y: 1.75, z: 4 };

async function toggleMicrophoneIngest(btn) {
  if (typeof micActive !== "undefined" && micActive) {
    disconnectLiveMicrophone();
    if (btn) {
      btn.textContent = "Enable Mic Ingest";
      btn.style.background = "";
      btn.style.color = "";
    }
    setStatus("Mic closed", "ok");
    logToNative("MIC_INGEST", "closed");
    return;
  }
  const ok = await initLiveMicrophoneIngest(function (hz) {
    const st = $("micHz");
    if (st) st.textContent = hz.toFixed(1) + " Hz";
    if (window.pulseForgeCinemaSync) {
      const map = ["A", "E", "O", "U"];
      // Map pitch bands roughly to visemes for visual feedback
      let v = "A";
      if (hz < 120) v = "O";
      else if (hz < 180) v = "A";
      else if (hz < 280) v = "E";
      else v = "U";
      window.pulseForgeCinemaSync.solveVisemeMechanics(v);
    }
    logToNative("MIC_TELEMETRY", hz.toFixed(1) + " Hz");
  });
  if (ok) {
    if (btn) {
      btn.textContent = "Mic Active";
      btn.style.background = "var(--ok)";
      btn.style.color = "#000";
    }
    setStatus("Mic ingest active · pitch → viseme", "ok");
    logToNative("MIC_INGEST", "active");
  } else {
    setStatus("Mic unavailable — using synthetic guides", "warn");
    logToNative("MIC_INGEST", "denied");
  }
}

function updateLookAtTrackingTarget(val, dim) {
  lookAtTarget[dim] = parseFloat(val);
  if (window.pulseForgeCinemaSync) {
    window.pulseForgeCinemaSync.solveAnatomicalBones(
      lookAtTarget.x, lookAtTarget.y, lookAtTarget.z
    );
  }
}



/** Invoke Tauri write or browser download for a UTF-8 / binary payload */
function savePayload(filename, data, subdirectory, mime) {
  mime = mime || "application/octet-stream";
  const bytes =
    typeof data === "string"
      ? new TextEncoder().encode(data)
      : data instanceof ArrayBuffer
        ? new Uint8Array(data)
        : data instanceof Uint8Array
          ? data
          : new TextEncoder().encode(String(data));

  function browserFallback() {
    const blob = new Blob([bytes], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    logToNative("EXPORT_BROWSER", filename);
  }

  function tryLocalBroker() {
    return fetch("/api/write_production_file", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Studio-Capability": window.__STUDIO_CAPABILITY__ || "" },
      body: JSON.stringify({
        filename: filename,
        subdirectory: subdirectory || "exports",
        data_bytes: Array.from(bytes)
      })
    }).then(function (res) {
      return res.json().then(function (j) {
        if (!res.ok || j.status !== "SUCCESS") throw new Error(j.error || res.statusText);
        setStatus("Saved: " + j.saved_at, "ok");
        logToNative("LOCAL_BROKER", j.saved_at);
        return j;
      });
    });
  }

  function tryTauri() {
    const args = {
      filename: filename,
      dataBytes: Array.from(bytes),
      subdirectory: subdirectory || "exports"
    };
    if (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) {
      return window.__TAURI__.core.invoke("native_write_production_file", args);
    }
    if (window.__TAURI__ && window.__TAURI__.tauri && window.__TAURI__.tauri.invoke) {
      return window.__TAURI__.tauri.invoke("native_write_production_file", args);
    }
    return Promise.reject(new Error("no tauri"));
  }

  // Order: Tauri → local studio_server broker → browser download
  tryTauri()
    .then(function (path) {
      setStatus("Saved natively: " + path, "ok");
      logToNative("IPC_SUCCESS", path);
    })
    .catch(function () {
      tryLocalBroker().catch(function () {
        browserFallback();
      });
    });
}

/**
 * Frame-quantized armature timeline (30 fps) — OTIO-inspired schema, not full OTIO XML.
 * Sample-indexed viseme + neck yaw + eye rotation tracks from live skeleton / cinema state.
 */
function exportCinematicAnimationTimeline() {
  if (!skeleton) compile();
  logToNative("EXPORT_ANIMATION", "Compiling cinematic armature timeline");

  const fps = 30;
  const sampleRate = 44100;
  const bpm = skeleton.timebase.initial_bpm || 102;
  const totalSec = ticksToSec(totalTicks()) || 8;
  const totalFrames = Math.max(1, Math.floor(totalSec * fps));
  const vocal = skeleton.tracks.find(function (t) { return t.type === "VOCAL"; });

  function visemeAtTick(tick) {
    if (!vocal) return "REST";
    let best = null;
    for (let i = 0; i < vocal.events.length; i++) {
      const e = vocal.events[i];
      if (e.type !== "NOTE_ON") continue;
      if (e.tick <= tick && (!best || e.tick >= best.tick)) best = e;
    }
    if (!best) return "REST";
    const v = (best.viseme || best.phoneme || "A").toUpperCase();
    const alias = { AH: "A", EE: "E", EH: "E", OH: "O", OO: "U" };
    return alias[v] || (["A", "E", "O", "U"].indexOf(v) >= 0 ? v : "A");
  }

  function sectionAtTick(tick) {
    const secs = skeleton.structure.sections || [];
    for (let i = 0; i < secs.length; i++) {
      const s = secs[i];
      if (tick >= s.start_tick && tick < s.end_tick) return s;
    }
    return null;
  }

  const cinema = window.pulseForgeCinemaSync;
  const neckYaw0 =
    cinema && cinema.neckBone ? cinema.neckBone.rotation.y : 0;
  const eyeYaw0 =
    cinema && cinema.leftEye ? cinema.leftEye.rotation.y : 0;

  const tracks = {
    vocal_visemes: [],
    neck_rotation_yaw: [],
    eyes_rotation_yaw: []
  };

  for (let frame = 0; frame < totalFrames; frame++) {
    const tSec = frame / fps;
    const sample = Math.floor(tSec * sampleRate);
    const tick = Math.round((tSec * bpm / 60) * TPQ);
    const sec = sectionAtTick(tick);
    let viseme = "REST";
    if (sec && sec.role !== "none") viseme = visemeAtTick(tick);

    // Optional gentle modulation of neck from look-at if available
    let neck = neckYaw0;
    let eye = eyeYaw0;
    if (cinema && cinema.lookAt) {
      const dx = cinema.lookAt.x || 0;
      const dz = cinema.lookAt.z || 4;
      neck = Math.max(-0.785, Math.min(0.785, Math.atan2(dx, dz) * 0.45));
      eye = Math.max(-0.4, Math.min(0.4, (Math.atan2(dx, dz) - neck) * 0.5));
    }

    tracks.vocal_visemes.push({ frame: frame, sample: sample, tick: tick, value: viseme });
    tracks.neck_rotation_yaw.push({
      frame: frame,
      sample: sample,
      value: parseFloat(neck.toFixed(5))
    });
    tracks.eyes_rotation_yaw.push({
      frame: frame,
      sample: sample,
      value: parseFloat(eye.toFixed(5))
    });
  }

  const timeline = {
    $schema: "pulseforge.cinematic_armature_timeline.v2",
    format: "pulseforge.cinematic_armature_timeline.v2",
    song_id: skeleton.song_id,
    title: skeleton.title || "Song",
    metadata: {
      fps: fps,
      sample_rate: sampleRate,
      total_frames: totalFrames,
      total_samples: Math.floor(totalSec * sampleRate),
      bpm: bpm,
      key: skeleton.timebase.key,
      note: "Frame-quantized guide tracks — not full OpenTimelineIO XML",
      generated_at: new Date().toISOString()
    },
    tracks: tracks
  };

  const filename = (skeleton.song_id || "song") + "_3D_AnimationTimeline.json";
  const json = JSON.stringify(timeline, null, 2);
  savePayload(filename, json, "animation_timelines", "application/json");
  setStatus("3D animation timeline exported · " + totalFrames + " frames @ " + fps + "fps", "ok");
  logToNative("EXPORT_COMPLETE", filename);
}

const btnAnim = $("btnAnim");
if (btnAnim) btnAnim.onclick = exportCinematicAnimationTimeline;


/**
 * OTIO-inspired timeline package (JSON).
 * Not a full OpenTimelineIO Python/C++ schema dump — labeled honestly for NLE import experiments.
 */
function exportOTIOPackage() {
  if (!skeleton) compile();
  logToNative("EXPORT_OTIO", "Compiling OTIO-inspired Timeline.1 package");

  const fps = 30;
  const bpm = skeleton.timebase.initial_bpm || 102;
  const tpq = typeof TPQ !== "undefined" ? TPQ : 960;
  const ledger = typeof getTelemetryLedger === "function" ? getTelemetryLedger() : [];
  const onsets = ledger.filter(function (r) { return r.is_rhythmic_onset; });

  function RT(frames) {
    return { OTIO_SCHEMA: "RationalTime.1", rate: fps, value: Math.max(0, Math.round(frames)) };
  }
  function TR(startF, durF) {
    return { OTIO_SCHEMA: "TimeRange.1", start_time: RT(startF), duration: RT(durF) };
  }

  const trackChildren = [];
  let tickOff = 0;
  (skeleton.structure.sections || []).forEach(function (sec) {
    const secTicks = (sec.bars || 1) * 4 * tpq;
    const startSec = (tickOff / tpq) * (60 / bpm);
    const durSec = (secTicks / tpq) * (60 / bpm);
    const startF = Math.floor(startSec * fps);
    const durF = Math.max(1, Math.floor(durSec * fps));
    const endSec = startSec + durSec;

    const localized = onsets.filter(function (o) {
      const t = o.time_sec != null ? o.time_sec : (o.sample_index / 44100);
      return t >= startSec && t < endSec;
    }).map(function (o) {
      const t = o.time_sec != null ? o.time_sec : (o.sample_index / 44100);
      return {
        OTIO_SCHEMA: "Marker.1",
        name: "Transient_Onset_" + (o.sample_index || 0),
        marked_range: TR(Math.floor(t * fps), 1),
        metadata: { spectral_flux: o.spectral_flux, tick_clock: o.tick_clock }
      };
    });

    // Viseme markers from vocal events in section tick range
    const vocal = skeleton.tracks.find(function (t) { return t.type === "VOCAL"; });
    if (vocal && sec.role !== "none") {
      vocal.events.forEach(function (ev) {
        if (ev.type !== "NOTE_ON") return;
        if (ev.tick < tickOff || ev.tick >= tickOff + secTicks) return;
        const t = ticksToSec(ev.tick);
        localized.push({
          OTIO_SCHEMA: "Marker.1",
          name: "viseme_" + (ev.viseme || ev.phoneme || "A"),
          marked_range: TR(Math.floor(t * fps), Math.max(1, Math.floor(ticksToSec(ev.duration_ticks || tpq / 2) * fps))),
          metadata: { phoneme: ev.phoneme, note: ev.note_number }
        });
      });
    }

    if (sec.role === "none") {
      trackChildren.push({
        OTIO_SCHEMA: "Gap.1",
        name: "Instrumental_Gap_" + sec.name,
        metadata: { section_type: sec.type || sec.role, bars: sec.bars },
        source_range: TR(0, durF),
        markers: localized
      });
    } else {
      trackChildren.push({
        OTIO_SCHEMA: "Clip.1",
        name: "Vocal_Performance_" + sec.name,
        metadata: {
          vocal_role_contract: sec.role,
          raw_lyrics_text: sec.lyrics || "",
          viseme_layout_pattern: ["A", "E", "O", "U"],
          bars: sec.bars
        },
        source_range: TR(0, durF),
        markers: localized
      });
    }
    tickOff += secTicks;
  });

  const videoTrack = {
    OTIO_SCHEMA: "Track.1",
    name: "Vocal_Viseme_Track_Channel",
    kind: "Video",
    children: trackChildren,
    markers: []
  };

  const otioTimeline = {
    OTIO_SCHEMA: "Timeline.1",
    name: ((typeof $ === "function" && $("title") && $("title").value) || skeleton.title || "SARA_TRACK") + " Studio Master Timeline",
    metadata: {
      pulseforge_song_id: skeleton.song_id,
      project_title: (typeof $ === "function" && $("title") && $("title").value) || skeleton.title || "SARA_TRACK",
      generated_timestamp: new Date().toISOString(),
      pulseforge: {
        schema_note: "OTIO-inspired JSON (Timeline.1 / Track.1 / Clip.1 / Gap.1 / Marker.1)",
        bpm: bpm,
        key: skeleton.timebase.key,
        onset_count: onsets.length,
        extracted_transient_onset_count: onsets.length,
        timebase_bpm: bpm,
        timebase_key_scale: skeleton.timebase.key
      }
    },
    tracks: {
      OTIO_SCHEMA: "Stack.1",
      name: "Tracks Stack",
      metadata: {
        timebase_bpm: bpm,
        extracted_transient_onset_count: onsets.length
      },
      children: [videoTrack]
    }
  };

  const filename = (skeleton.song_id || "song") + "_Interchange.otio.json";
  savePayload(filename, JSON.stringify(otioTimeline, null, 2), "otio_packages", "application/json");
  setStatus("OTIO package · " + trackChildren.length + " clips/gaps · " + onsets.length + " onsets", "ok");
  logToNative("EXPORT_COMPLETE", filename);
}


const btnOTIO = $("btnOTIO");
if (btnOTIO) btnOTIO.onclick = exportOTIOPackage;

(function wireShelves() {
  function apply() {
    const lo = $("shelfLow");
    const hi = $("shelfHigh");
    if (typeof setShelfParams === "function" && lo && hi) {
      setShelfParams(parseFloat(lo.value), parseFloat(hi.value));
    }
  }
  const lo = $("shelfLow");
  const hi = $("shelfHigh");
  if (lo) lo.oninput = apply;
  if (hi) hi.oninput = apply;
})();


async function triggerNeuralCompilationPipeline() {
  setStatus("Dispatching hybrid broadcast master…", "warn");
  logToNative("NEURAL_BROKER", "Packaging lyrics + prompt for hybrid proxy");

  const sections = (skeleton && skeleton.structure && skeleton.structure.sections) || [];
  const fullLyrics = sections.map(function (s) {
    return "[" + (s.name || "").toUpperCase() + " - " + String(s.role || "none").toUpperCase() + "]\n" + (s.lyrics || "");
  }).join("\n\n");

  const submission = {
    title: ($("title") && $("title").value) || (skeleton && skeleton.title) || "SARA_RELEASE_TRACK",
    prompt_directive: ($("prompt") && $("prompt").value) || "",
    lyrics: fullLyrics,
    configuration: {
      target_bpm: (skeleton && skeleton.timebase && skeleton.timebase.initial_bpm) || parseInt(($("bpmOverride") && $("bpmOverride").value) || "102", 10),
      target_scale: (skeleton && skeleton.timebase && skeleton.timebase.key) || (($("keyOverride") && $("keyOverride").value) || "F# minor"),
      audio_profile: "broadcast_studio_youtube_master"
    }
  };

  try {
    const res = await fetch("/api/dispatch_neural_compilation", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Studio-Capability": window.__STUDIO_CAPABILITY__ || "" },
      body: JSON.stringify(submission)
    });
    const data = await res.json();
    if (!res.ok || data.status !== "SUCCESS") {
      throw new Error(data.error || res.statusText);
    }
    setStatus("Broadcast master written · " + data.provider, "ok");
    logToNative("BROKER_SUCCESS", data.saved_master_path);
    alert("Hybrid master ready\nWAV: " + data.saved_master_path + "\nOTIO: " + data.saved_otio_path);
  } catch (err) {
    console.warn("[Broker]", err);
    setStatus("Hybrid broker offline — use local Play / WAV export", "warn");
    logToNative("BROKER_FALLBACK", String(err));
  }
}

const btnNeural = $("btnNeural");
if (btnNeural) btnNeural.onclick = function () { triggerNeuralCompilationPipeline(); };


async function runVocalLab() {
  if (!skeleton) compile();
  const vocal = skeleton.tracks.find(function (t) { return t.type === "VOCAL"; });
  const events = vocal ? vocal.events : [];
  const lyrics = (skeleton.structure.sections || []).map(function (s) { return s.lyrics || ""; }).join(" ");
  const roleSec = (skeleton.structure.sections || []).find(function (s) { return s.role && s.role !== "none"; });
  const roleProfile = roleSec ? (roleSec.role === "both" ? "male" : roleSec.role) : "male";
  const qEl = $("vocalQuality");
  const quality = (qEl && qEl.value) || "production";
  setStatus("Vocal lab · " + quality + "…", "warn");
  const receipt = await renderLocalNeuralVocalPhrase(
    events,
    lyrics || "la la late night streetlight",
    roleProfile,
    quality
  );
  if (receipt) {
    setStatus("Vocal · " + (receipt.engine || quality) + " · " + (receipt.asset_hash || "").slice(0, 10), "ok");
    alert(
      "Vocal Lab\n" +
      (receipt.engine || "") + "\n" +
      (receipt.saved_master_path || "") + "\n" +
      (receipt.ceiling_note || "")
    );
  }
}
const btnVocalLab = $("btnVocalLab");
if (btnVocalLab) btnVocalLab.onclick = function () { runVocalLab(); };

const btnVocalLab2 = $("btnVocalLab2");
if (btnVocalLab2) btnVocalLab2.onclick = function () { runVocalLab(); };

if ($('btnOctaveEdit')) $('btnOctaveEdit').onclick = () => applyVerse2BassOctave();
if ($('btnABR1')) $('btnABR1').onclick = () => selectABRevision('R1').catch(e => setStatus('A/B failed: ' + e.message, 'warn'));
if ($('btnABR2')) $('btnABR2').onclick = () => selectABRevision('R2').catch(e => setStatus('A/B failed: ' + e.message, 'warn'));
setABControls();

// Project address survives independently of browser cache; enter it on any fresh client.
if ($('btnOpenProject')) $('btnOpenProject').onclick = () => restoreProjectFromStorage().catch(e => setStatus('Open failed: ' + e.message, 'warn'));
if ($('btnNewProject')) $('btnNewProject').onclick = () => {
  ++projectOpenGenerationToken;
  ++m045RequestToken;
  m045ClearTakes();
  m045LocksDirty = false;
  m045PublishProof("DECLARED");
  durableProjectRef = null; durableSourceAssets = [];
  abRevisions = { r1: null, r2: null };
  abRequestGeneration++;
  window.__M044_AB_SWITCH__ = { state: 'IDLE', generation: abRequestGeneration, targetRevisionId: null };
  clearVerifiedPlayback();
  setABControls();
  renderLyricAuthority(null);
  if ($('projectId')) $('projectId').value = '';
  if ($('projectRevision')) $('projectRevision').textContent = 'Unsaved draft — no durable project yet';
  setStatus('New project draft · Save to create a durable project', 'warn');
};


// M043: lyric edits always advance the durable project. No transcript in localStorage.
let durableLyricTimeline = null;
function renderLyricAuthority(doc) {
  durableLyricTimeline = doc;
  const list = $('lyricWords');
  if (!list) return;
  list.replaceChildren();
  $('lyricStatus').textContent = doc
    ? (doc.status === 'unknown' ? 'No recognized words — transcript unknown.' : 'Guided text · recognition confidence unknown · ' + doc.status)
    : 'No saved lyrics. This tool aligns supplied text to separated speech; it does not transcribe.';
  if (!doc) return;
  for (const word of doc.words) {
    const row = document.createElement('div');
    const label = document.createElement('span');
    label.textContent = word.text + ' · ' + (word.decodedSampleStart / doc.sourceSampleRate).toFixed(3)
      + '–' + (word.decodedSampleEnd / doc.sourceSampleRate).toFixed(3) + ' s · unscored guess ';
    const edit = document.createElement('button');
    edit.textContent = 'Correct word'; edit.className = 'secondary sm';
    edit.onclick = async () => {
      const text = prompt('Correct this word (audio and timing stay unchanged):', word.text);
      if (text === null || text === word.text) return;
      try {
        await saveLyricChange({ action: 'correct', expectedLyricRevisionId: doc.revisionId,
          changes: [{ wordId: word.id, text }], actor: 'local-studio-user', reason: 'Studio word correction' });
      } catch (e) { setStatus('Lyrics not saved: ' + e.message, 'warn'); }
    };
    row.append(label, edit); list.append(row);
  }
}
async function saveLyricChange(fields) {
  if (!durableProjectRef) throw new Error('Save or open a project first');
  const expected = { ...durableProjectRef };
  if ($('projectId').value.trim() !== expected.projectId) throw new Error('Open the selected project first');
  const result = await projectRequest('lyrics', { ...fields, projectId: expected.projectId,
    expectedCurrentRevisionId: expected.revisionId });
  if (durableProjectRef && durableProjectRef.projectId === expected.projectId && durableProjectRef.revisionId === expected.revisionId) {
    showProjectAuthority(result);
    setStatus('Lyrics saved · text correction does not edit audio', 'ok');
  }
  return result;
}
if ($('btnAlignLyrics')) $('btnAlignLyrics').onclick = async () => {
  try {
    if (!durableProjectRef) throw new Error('Save or open a project first');
    const expected = { ...durableProjectRef };
    const file = $('lyricAudio').files[0];
    if (!file || file.size > 16 * 1024 * 1024) throw new Error('Choose a PCM16 WAV under 16 MiB, up to 60 seconds');
    const knownTranscript = $('knownLyricText').value;
    const response = await fetch('/api/write_production_file', { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Studio-Capability': window.__STUDIO_CAPABILITY__ || '' },
      body: JSON.stringify({ filename: 'lyric-source.wav', subdirectory: 'lyric-input',
        data_bytes: Array.from(new Uint8Array(await file.arrayBuffer())) }) });
    const saved = await response.json();
    if (!response.ok || saved.status !== 'SUCCESS') throw new Error(saved.error || 'Audio import failed');
    if (!durableProjectRef || durableProjectRef.projectId !== expected.projectId || durableProjectRef.revisionId !== expected.revisionId)
      throw new Error('Project changed during import; reopen before aligning');
    await saveLyricChange({ action: 'candidate', sourceArtifactId: saved.sha256, knownTranscript, language: 'en' });
  } catch (e) { setStatus('Lyrics not saved: ' + e.message, 'warn'); }
};
/** RS-001/002 responsive presentation bridge. Canonical Studio controls own every action. */
function initStudioResponsiveShell() {
  const byId = id => document.getElementById(id);
  const sourcePlay = byId('btnPlay');
  const sourceStop = byId('btnStop');
  const sourceGenerate = byId('btnM045Generate');
  const projectInput = byId('projectId');
  const projectRevision = byId('projectRevision');
  const headerProject = byId('studioHeaderProjectId');
  const headerRevision = byId('studioHeaderRevision');
  const dockPlay = byId('dockPlay');

  function syncFromAuthority() {
    // Display is derived strictly from canonical fields, never separate project state.
    const rawId = (projectInput && projectInput.value || '').trim();
    headerProject.textContent = rawId || 'Unsaved';
    const revisionText = projectRevision && projectRevision.textContent || '';
    const match = revisionText.match(/Saved revision:\s*([a-f0-9]{64})/i);
    headerRevision.textContent = match ? match[1].slice(0, 12) : 'Draft';
    dockPlay.disabled = !sourcePlay || sourcePlay.disabled;
    dockPlay.textContent = sourcePlay && /stop/i.test(sourcePlay.textContent || '') ? '■ Stop' : '▶ Play';
  }
  function delegate(buttonId, originalId) {
    const button=byId(buttonId);
    const original=byId(originalId);
    if (!button || !original) return;
    button.addEventListener('click', () => {
      if (original.disabled) return;
      original.click();
      queueMicrotask(syncFromAuthority);
    });
  }
  delegate('dockPlay','btnPlay');
  delegate('dockStop','btnStop');
  delegate('dockGenerate','btnM045Generate');
  const modeButtons=[...document.querySelectorAll('#studioModeTabs [data-studio-target]')];
  function activateMode(button) {
    for (const candidate of modeButtons) {
      if (candidate === button) candidate.setAttribute('aria-current','page');
      else candidate.removeAttribute('aria-current');
    }
    const surface=byId(button.dataset.studioTarget);
    if (!surface) return;
    surface.scrollIntoView({behavior:'auto',block:'start'});
    surface.focus({preventScroll:true});
  }
  for (const button of modeButtons) {
    button.addEventListener('click',()=>activateMode(button));
  }
  const change=byId('dockChangeOnly');
  if (change) change.addEventListener('click',()=>{
    const proof=byId('studioModeProof');
    if (proof) activateMode(proof);
    const target=byId('m045TargetTrack');
    if (target) target.focus({preventScroll:true});
  });
  // Never synthesize progress/Proof. Only observe existing owner-controlled fields.
  const observer=new MutationObserver(syncFromAuthority);
  if (projectRevision) observer.observe(projectRevision,{childList:true,characterData:true,subtree:true});
  if (sourcePlay) observer.observe(sourcePlay,{attributes:true,attributeFilter:['disabled'],childList:true,subtree:true});
  if (projectInput) projectInput.addEventListener('input',syncFromAuthority);
  document.addEventListener('focusin',event=>{
    if (event.target===projectInput) syncFromAuthority();
  });
  syncFromAuthority();
  if (modeButtons[0]) modeButtons[0].setAttribute('aria-current','page');
}
initStudioResponsiveShell();


// Wave 004 — presentation only. Studio service remains project/revision/render authority.
let m045Wave4Generation = 0;
let m045Wave4PreviewUrl = null;
let m045Wave4Busy = false;
function m045Wave4Clear() {
  if (typeof m045Wave4ExtraClear === 'function') m045Wave4ExtraClear();
  ++m045Wave4Generation;
  const audio = $("m045Wave4Audio");
  if (audio) { try { audio.pause(); } catch (_) {} audio.removeAttribute("src"); audio.load(); }
  if (m045Wave4PreviewUrl) URL.revokeObjectURL(m045Wave4PreviewUrl);
  m045Wave4PreviewUrl = null;
  if ($("m045Wave4Status")) $("m045Wave4Status").textContent =
    "P3 candidate · Selection changed · rights UNVERIFIED";
  const grantStatus=$("m045SoundtrackGrantStatus");
  if (grantStatus) grantStatus.textContent=
    "NOT ISSUED · Source/project selection changed · Pending grant receipt discarded";
}
function m045Wave4FillOptions() {
  if (!skeleton) return;
  const options = [
    ["m045Wave4Section", (skeleton.structure && skeleton.structure.sections || []).map(x=>[x.id,x.name||x.id])],
    ["m045Wave4Track", (skeleton.tracks||[]).filter(x=>Array.isArray(x.events) &&
      x.events.some(e=>e.type==="NOTE_ON")).map(x=>[x.track_id,x.name||x.track_id])]
  ];
  for (const [id, rows] of options) {
    const element=$(id);
    if (!element) continue;
    const old=element.value;
    element.replaceChildren();
    for (const [value,label] of rows) {
      const option=document.createElement("option");
      option.value=String(value);
      option.textContent=String(label);
      element.appendChild(option);
    }
    if (rows.some(x=>String(x[0])===old)) element.value=old;
  }
}
function m045Wave4Context(audioRequired) {
  if (!durableProjectRef) throw new Error("Save or open an authorized project first");
  const ref={...durableProjectRef};
  if (audioRequired) {
    const p=verifiedPlayback;
    if (!p || p.projectId!==ref.projectId || p.revisionId!==ref.revisionId ||
        typeof p.artifactId!=="string" || !/^[0-9a-f]{64}$/.test(p.artifactId))
      throw new Error("Verify current revision audio before transcription or mastering");
    ref.artifactId=p.artifactId;
  }
  return ref;
}
function m045Wave4Valid(ref,openToken,requestToken) {
  return requestToken===m045Wave4Generation &&
    openToken===projectOpenGenerationToken &&
    durableProjectRef && durableProjectRef.projectId===ref.projectId &&
    durableProjectRef.revisionId===ref.revisionId;
}
async function m045Wave4Post(route,body) {
  const response=await fetch(route,{method:"POST",headers:studioProjectHeaders(),body:JSON.stringify(body)});
  const result=await response.json().catch(()=>({}));
  if (!response.ok || result.status!=="SUCCESS") {
    throw new Error((result.error||"HTTP "+response.status) +
      (response.status===409?" · reopen and read authoritative state":""));
  }
  return result;
}
function m045Wave4Status(message) {
  if ($("m045Wave4Status")) $("m045Wave4Status").textContent=message;
}
async function m045Wave4Action(kind) {
  if (m045Wave4Busy) return;
  const requireAudio = kind!=="preview";
  let ref;
  try { ref=m045Wave4Context(requireAudio); }
  catch (error) { m045Wave4Status("NOT VERIFIED · "+error.message); return; }
  const openToken=projectOpenGenerationToken;
  const token=++m045Wave4Generation;
  const valid=()=>m045Wave4Valid(ref,openToken,token);
  const buttons=["m045Wave4Preview","m045Wave4Transcribe","m045Wave4Master"].map($).filter(Boolean);
  m045Wave4Busy=true;
  buttons.forEach(b=>b.disabled=true);
  m045Wave4Status("Checking authorized revision · "+kind+"…");
  try {
    if(kind==="preview") {
      m045Wave4FillOptions();
      const section=$("m045Wave4Section"),track=$("m045Wave4Track");
      if(!section?.value||!track?.value) throw new Error("Choose a saved section and instrument track");
      const result=await m045Wave4Post("/api/m045/preview-synth",{
        projectId:ref.projectId,revisionId:ref.revisionId,sectionId:section.value,trackId:track.value});
      if (!valid()) return;
      if (result.sourceRevisionId!==ref.revisionId ||
          result.kind!=="NON_AUTHORITATIVE_FM_PREVIEW" ||
          result.audioStatus!=="PREVIEW_NOT_PUBLISHED") throw new Error("Unqualified FM response");
      const binary=atob(result.wavBase64);
      const pcm=Uint8Array.from(binary,ch=>ch.charCodeAt(0));
      const sha=await sha256Hex(pcm.buffer);
      if(!valid()) return;
      if(sha!==result.previewSha256) throw new Error("FM preview digest mismatch");
      if(m045Wave4PreviewUrl) URL.revokeObjectURL(m045Wave4PreviewUrl);
      m045Wave4PreviewUrl=URL.createObjectURL(new Blob([pcm],{type:"audio/wav"}));
      const audio=$("m045Wave4Audio");
      audio.src=m045Wave4PreviewUrl;
      m045Wave4Status("FM PREVIEW · UNPUBLISHED · Not approved audio");
    } else if(kind==="transcribe") {
      const result=await m045Wave4Post("/api/m045/transcribe-midi",{
        projectId:ref.projectId,revisionId:ref.revisionId,artifactId:ref.artifactId});
      if (!valid()) return;
      if(result.sourceRevisionId!==ref.revisionId || result.sourceArtifactId!==ref.artifactId ||
          result.preservationTier!=="P3_RECONSTRUCTION" || result.projectRevisionCommitted!==false)
        throw new Error("Unqualified transcription response");
      m045Wave4Status("P3 MIDI CANDIDATE · "+result.notesDetected+
        " estimated notes · Lossy · Human review required · No project revision changed");
    } else if(kind==="master") {
      const target=Number($("m045Wave4Preset").value);
      if(![-14,-9].includes(target)) throw new Error("Unsupported mastering target");
      const result=await m045Wave4Post("/api/m045/master",{
        projectId:ref.projectId,revisionId:ref.revisionId,artifactId:ref.artifactId,
        expectedCurrentRevisionId:ref.revisionId,targetLufs:target,truePeakCeilingDbtp:-1});
      if(!valid()) return;
      if(result.sourceRevisionId!==ref.revisionId||result.sourceArtifactId!==ref.artifactId||
         result.rightsStatus!=="UNVERIFIED_HELD"||result.releaseCleared!==false||
         !result.telemetry?.true_peak_verified)
        throw new Error("Unqualified mastering receipt; reopen project for authoritative readback");
      const receipt=result.telemetry;
      m045Wave4Status("Master response received · "+receipt.measured_output_lufs+
         " LUFS · "+receipt.measured_output_true_peak_dbtp+
         " dBTP · Rights HELD · Reopening authoritative revision…");
      await restoreProjectFromStorage(); // Authoritative promotion readback, not browser-selected truth.
      if(!durableProjectRef || durableProjectRef.projectId!==ref.projectId ||
         durableProjectRef.revisionId!==result.revisionId ||
         !verifiedPlayback || verifiedPlayback.projectId!==ref.projectId ||
         verifiedPlayback.revisionId!==result.revisionId ||
         verifiedPlayback.artifactId!==result.artifactId ||
         verifiedPlayback.wavSha256!==result.artifactId) {
        m045Wave4Status("Master committed, but audio UNVERIFIED · reopen and inspect; do not retry blindly");
        return;
      }
      m045Wave4Status("Master revision VERIFIED · "+receipt.measured_output_lufs+
         " LUFS · "+receipt.measured_output_true_peak_dbtp+
         " dBTP · Rights UNVERIFIED_HELD · NOT creatively approved");
    }
  } catch(error) {
    if(valid()) m045Wave4Status("NOT VERIFIED · "+error.message);
  } finally {
    m045Wave4Busy=false;
    buttons.forEach(b=>b.disabled=false);
  }
}
if ($("m045Wave4Preview")) $("m045Wave4Preview").onclick=()=>m045Wave4Action("preview");
if ($("m045Wave4Transcribe")) $("m045Wave4Transcribe").onclick=()=>m045Wave4Action("transcribe");
if ($("m045Wave4Master")) $("m045Wave4Master").onclick=()=>m045Wave4Action("master");
// HVC-003: command is authenticated soundtrack-issuer request, NOT film creation.
// Existing Studio project/revision/verified audio are authoritative. No browser
// cache or localStorage entry ever becomes a second selected soundtrack pointer.
if ($("m045CreateMusicVideo")) $("m045CreateMusicVideo").onclick=async()=>{
  const button=$("m045CreateMusicVideo");
  const status=$("m045SoundtrackGrantStatus");
  let ref=null;
  let ownsBusy=false;
  try {
    if (m045Wave4Busy) throw new Error("Another Studio operation is running");
    if (m045LocksDirty) throw new Error("Save pending Sonic Lock changes before issuing any grant");
    ref=m045Wave4Context(true);
    const cinemaProjectId=($("m045CinemaProjectId")?.value||"").trim();
    if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(cinemaProjectId))
      throw new Error("Enter an existing cinema project ID");
    const sectionId=$("m045Wave4Section")?.value;
    if (!sectionId) throw new Error("Select a canonical Studio section first");
    const openToken=projectOpenGenerationToken;
    const token=++m045Wave4Generation;
    const valid=()=>m045Wave4Valid(ref,openToken,token);
    m045Wave4Busy=true;ownsBusy=true;button.disabled=true;
    status.textContent="Checking accepted Studio audio, rights and exact section clock…";
    const response=await fetch("/api/m045/soundtrack-grant",{
      method:"POST",headers:studioProjectHeaders(),
      body:JSON.stringify({projectId:ref.projectId,revisionId:ref.revisionId,
        artifactId:ref.artifactId,cinemaProjectId,sectionId,fps:"24/1"})
    });
    const grant=await response.json().catch(()=>({}));
    if (!valid()) return;
    if (!response.ok) throw new Error(grant.error || ("Issuer HTTP "+response.status));
    if (grant.schema_version!=="sara.soundtrack.grant.v1" ||
        grant.source_project_revision_id!==ref.revisionId ||
        grant.studio_project_id!==ref.projectId ||
        grant.accepted_audio_artifact_id!==ref.artifactId ||
        grant.cinema_project_id!==cinemaProjectId ||
        !/^[a-f0-9]{64}$/.test(grant.signature||""))
      throw new Error("Issuer result does not bind the selected authorized revision");
    status.textContent="GRANT ISSUED for "+sectionId+" · Studio "+
      ref.revisionId.slice(0,12)+" · Frames "+grant.resolved_start_frame+
      "–"+grant.resolved_end_frame_exclusive+
      " · Film NOT created or verified · Await PulseForge authorized consumer";
  } catch(error) {
    if (!ref || durableProjectRef?.projectId===ref.projectId)
      status.textContent="NOT ISSUED · "+String(error.message||error);
  } finally {
    if (ownsBusy) { m045Wave4Busy=false;button.disabled=false; }
  }
};
if ($("m045Wave4Section")) $("m045Wave4Section").onfocus=m045Wave4FillOptions;
if ($("m045Wave4Track")) $("m045Wave4Track").onfocus=m045Wave4FillOptions;
m045Wave4FillOptions();

// Wave004 Sample Lab + Compound Planner: subordinate presentation only.
let m045Wave4ExtraUrl=null;
function m045Wave4ExtraClear() {
  const audio=$('m045Wave4SampleAudio');
  if(audio){audio.pause();audio.removeAttribute('src');audio.load();delete audio.dataset.previewDigest;}
  if(m045Wave4ExtraUrl){URL.revokeObjectURL(m045Wave4ExtraUrl);m045Wave4ExtraUrl=null;}
  if($('m045Wave4PlanResult'))$('m045Wave4PlanResult').textContent='';
  if($('m045Wave4ExtraStatus'))$('m045Wave4ExtraStatus').textContent='Candidate cleared on source/revision selection change.';
}
function m045Wave4ExtraStatus(message){
  const status=$('m045Wave4ExtraStatus');if(status)status.textContent=message;
}
async function m045Wave4ExtraAction(kind){
  if(m045Wave4Busy)return;
  const requireAudio=kind!=='compound';
  let ref;
  try {ref=m045Wave4Context(requireAudio);}
  catch(error){m045Wave4ExtraStatus('NOT VERIFIED · '+String(error.message||error));return;}
  if(m045LocksDirty){m045Wave4ExtraStatus('NOT VERIFIED · Save Sonic Lock changes before preview');return;}
  const openToken=projectOpenGenerationToken;
  const token=++m045Wave4Generation;
  m045Wave4ExtraClear();
  m045Wave4Busy=true;
  const valid=()=>m045Wave4Valid(ref,openToken,token);
  m045Wave4ExtraStatus('Checking lawful revision and requested scope…');
  try {
    let path,body={...ref};
    if(kind==='compound'){
      path='/api/m045/compound-plan';body.instruction=$('m045Wave4CompoundIntent').value;
    }else if(['slice','bass','metal'].includes(kind)){
      path='/api/m045/sample-preview';
      body.transform=kind==='slice'?'slice':kind==='bass'?'lowpass':'metallic_comb';
      body.parameters=kind==='slice'?{startFrame:0,endFrame:44100}:
        kind==='bass'?{startFrame:0,endFrame:44100,cutoffHz:900,q:0.707}:
        {startFrame:0,endFrame:44100,delayMs:3,feedback:0.55};
    }else throw new Error('Operation unqualified');
    const data=await m045Wave4Post(path,body);
    if(!valid())return;
    if(data.projectId!==ref.projectId||data.sourceRevisionId!==ref.revisionId)
      throw new Error('Result does not belong to the selected source revision');
    if(kind==='compound'){
      if(window.ScoreCore?.validateCompoundEditPlan)
        window.ScoreCore.validateCompoundEditPlan(data,skeleton);
      $('m045Wave4PlanResult').textContent=JSON.stringify({
        kind:data.kind,operations:data.operations,preservedSectionIds:data.preservedSectionIds,
        audioPreservationProof:data.audioPreservationProof,revisionCommitted:data.revisionCommitted,
        sourceRevisionId:data.sourceRevisionId},null,2);
      m045Wave4ExtraStatus('PROPOSED · No song change committed; preservation still requires rendering and proof');
    }else{
      if(typeof data.wavBase64!=='string'||data.wavBase64.length>6*1024*1024)
        throw new Error('Candidate preview too large');
      const decoded=atob(data.wavBase64);const bytes=new Uint8Array(decoded.length);
      for(let i=0;i<decoded.length;i++)bytes[i]=decoded.charCodeAt(i);
      const digest=await sha256Hex(bytes.buffer);
      if(!valid())return;
      if(digest!==data.previewArtifactSha256)throw new Error('Sample preview digest mismatch');
      m045Wave4ExtraUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));
      const audio=$('m045Wave4SampleAudio');audio.src=m045Wave4ExtraUrl;
      audio.dataset.previewDigest=digest;audio.load();
      $('m045Wave4PlanResult').textContent=JSON.stringify({
        kind:data.kind,sourceRevisionId:data.sourceRevisionId,
        sourceArtifactId:data.sourceArtifactId,previewArtifactSha256:digest,
        provenance:data.provenance,sourceMutation:data.sourceMutation,
        projectRevisionCommitted:data.projectRevisionCommitted,audioPublication:data.audioPublication},null,2);
      m045Wave4ExtraStatus('UNPUBLISHED SAMPLE PREVIEW · Source intact · Rights UNVERIFIED_HELD · Audition required');
    }
  }catch(error){
    if(valid())m045Wave4ExtraStatus('NOT VERIFIED · '+String(error.message||error));
  }finally{m045Wave4Busy=false;}
}
for(const [id,kind] of Object.entries({
  m045Wave4CompoundBtn:'compound',m045Wave4SampleSlice:'slice',
  m045Wave4SampleBass:'bass',m045Wave4SampleMetal:'metal'})){
  const button=$(id);if(button)button.onclick=()=>m045Wave4ExtraAction(kind);
}
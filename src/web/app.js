const state = {
  timeline: null,
  eventsByClip: {},
  selectedIndex: -1,
  busy: false,
};

const els = {
  musicPath: document.querySelector("#musicPath"),
  clipsDir: document.querySelector("#clipsDir"),
  manualBeats: document.querySelector("#manualBeats"),
  style: document.querySelector("#style"),
  fps: document.querySelector("#fps"),
  maxClips: document.querySelector("#maxClips"),
  resolution: document.querySelector("#resolution"),
  preEventTime: document.querySelector("#preEventTime"),
  postEventTime: document.querySelector("#postEventTime"),
  analyzeBtn: document.querySelector("#analyzeBtn"),
  renderBtn: document.querySelector("#renderBtn"),
  realignBtn: document.querySelector("#realignBtn"),
  saveTimelineBtn: document.querySelector("#saveTimelineBtn"),
  downloadJsonBtn: document.querySelector("#downloadJsonBtn"),
  refreshMediaBtn: document.querySelector("#refreshMediaBtn"),
  loadExampleBeatsBtn: document.querySelector("#loadExampleBeatsBtn"),
  clearBeatsBtn: document.querySelector("#clearBeatsBtn"),
  seekKillBtn: document.querySelector("#seekKillBtn"),
  timelineBody: document.querySelector("#timelineBody"),
  timelineMeta: document.querySelector("#timelineMeta"),
  statusLog: document.querySelector("#statusLog"),
  mediaList: document.querySelector("#mediaList"),
  clipVideo: document.querySelector("#clipVideo"),
  outputVideo: document.querySelector("#outputVideo"),
  selectedClipName: document.querySelector("#selectedClipName"),
  outputPath: document.querySelector("#outputPath"),
  clipMarker: document.querySelector("#clipMarker"),
};

function setBusy(isBusy) {
  state.busy = isBusy;
  for (const button of document.querySelectorAll("button")) {
    button.disabled = isBusy;
  }
}

function log(message) {
  const stamp = new Date().toLocaleTimeString();
  els.statusLog.textContent = `[${stamp}] ${message}\n${els.statusLog.textContent}`;
}

function mediaUrl(path) {
  return `/api/media?path=${encodeURIComponent(path)}`;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function parseManualBeats() {
  const text = els.manualBeats.value.trim();
  if (!text) return [];
  return text
    .split(/[\s,]+/)
    .map((value) => Number.parseFloat(value))
    .filter((value) => Number.isFinite(value) && value >= 0)
    .sort((a, b) => a - b);
}

function basename(path) {
  return String(path).split(/[\\/]/).pop();
}

function round3(value) {
  return Math.round((Number(value) || 0) * 1000) / 1000;
}

async function refreshMedia() {
  const data = await requestJson("/api/media-list");
  const items = [];
  for (const path of data.music) {
    items.push(`<div class="media-item" data-kind="music" data-path="${escapeHtml(path)}">MUSIC ${escapeHtml(basename(path))}</div>`);
  }
  for (const path of data.clips) {
    items.push(`<div class="media-item" data-kind="clip" data-path="${escapeHtml(path)}">CLIP ${escapeHtml(basename(path))}</div>`);
  }
  for (const path of data.outputs) {
    items.push(`<div class="media-item" data-kind="output" data-path="${escapeHtml(path)}">OUTPUT ${escapeHtml(basename(path))}</div>`);
  }
  els.mediaList.innerHTML = items.length ? items.join("") : `<div class="empty-row">No media in data folders</div>`;
}

async function analyze() {
  setBusy(true);
  log("Analyzing beats and clip kill points...");
  try {
    const payload = {
      musicPath: els.musicPath.value.trim(),
      clipsDir: els.clipsDir.value.trim(),
      manualBeats: parseManualBeats(),
      style: els.style.value,
      maxClips: Number.parseInt(els.maxClips.value, 10),
      resolution: els.resolution.value.trim(),
      fps: Number.parseInt(els.fps.value, 10),
      preEventTime: Number.parseFloat(els.preEventTime.value),
      postEventTime: Number.parseFloat(els.postEventTime.value),
    };
    const data = await requestJson("/api/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.timeline = data.timeline;
    state.eventsByClip = data.eventsByClip;
    state.selectedIndex = state.timeline.clips.length ? 0 : -1;
    renderTimeline();
    selectClip(state.selectedIndex);
    log(`Timeline ready: ${state.timeline.clips.length} clips, beats from ${data.beatSource}.`);
  } catch (error) {
    log(`Analyze failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

function renderTimeline() {
  const timeline = state.timeline;
  if (!timeline || !timeline.clips.length) {
    els.timelineBody.innerHTML = `<tr><td class="empty-row" colspan="8">No timeline loaded</td></tr>`;
    els.timelineMeta.textContent = "No timeline loaded";
    return;
  }

  els.timelineMeta.textContent = `${timeline.clips.length} clips • ${timeline.export_resolution} • ${timeline.export_fps} fps`;
  els.timelineBody.innerHTML = timeline.clips.map((clip, index) => {
    return `
      <tr data-index="${index}" class="${index === state.selectedIndex ? "active" : ""}">
        <td>${index + 1}</td>
        <td><div class="clip-name" title="${escapeHtml(clip.clip_path)}">${escapeHtml(basename(clip.clip_path))}</div></td>
        <td><input data-field="target_beat" type="number" step="0.001" min="0" value="${clip.target_beat}"></td>
        <td><input data-field="event_time" type="number" step="0.001" min="0" value="${clip.event_time}"></td>
        <td><input data-field="source_start" type="number" step="0.001" min="0" value="${clip.source_start}"></td>
        <td><input data-field="source_end" type="number" step="0.001" min="0" value="${clip.source_end}"></td>
        <td>${round3(clip.source_end - clip.source_start).toFixed(3)}</td>
        <td class="score">${Number(clip.event_score || 0).toFixed(3)}</td>
      </tr>
    `;
  }).join("");
}

function selectClip(index) {
  if (!state.timeline || index < 0 || index >= state.timeline.clips.length) {
    state.selectedIndex = -1;
    els.clipVideo.removeAttribute("src");
    els.selectedClipName.textContent = "No clip selected";
    els.clipMarker.classList.remove("visible");
    renderTimeline();
    return;
  }
  state.selectedIndex = index;
  const clip = state.timeline.clips[index];
  els.selectedClipName.textContent = basename(clip.clip_path);
  els.clipVideo.src = mediaUrl(clip.clip_path);
  els.clipVideo.onloadedmetadata = () => {
    const duration = els.clipVideo.duration || 0;
    const percent = duration ? Math.max(0, Math.min(1, clip.event_time / duration)) : 0.5;
    els.clipMarker.style.left = `${percent * 100}%`;
    els.clipMarker.classList.add("visible");
  };
  renderTimeline();
}

function seekKillPoint() {
  if (!state.timeline || state.selectedIndex < 0) return;
  const clip = state.timeline.clips[state.selectedIndex];
  els.clipVideo.currentTime = Math.max(0, Number(clip.event_time) - 0.15);
  els.clipVideo.play().catch(() => {});
}

function updateField(row, input) {
  if (!state.timeline) return;
  const index = Number.parseInt(row.dataset.index, 10);
  const field = input.dataset.field;
  const value = round3(input.value);
  const clip = state.timeline.clips[index];
  clip[field] = value;
  if (field === "event_time") {
    const post = Number.parseFloat(els.postEventTime.value) || 0.35;
    clip.source_end = Math.max(clip.source_start + 0.1, round3(value + post));
  }
  if (clip.source_end <= clip.source_start) {
    clip.source_end = round3(clip.source_start + 0.1);
  }
  renderTimeline();
  selectClip(index);
}

function realignTimeline() {
  if (!state.timeline) return;
  const post = Number.parseFloat(els.postEventTime.value) || 0.35;
  let currentOutput = 0;
  for (const clip of state.timeline.clips) {
    const targetBeat = Number(clip.target_beat) || 0;
    const eventTime = Number(clip.event_time) || 0;
    const desiredPre = Math.max(0.05, targetBeat - currentOutput);
    clip.source_start = round3(Math.max(0, eventTime - desiredPre));
    clip.source_end = round3(Math.max(clip.source_start + 0.1, eventTime + post));
    currentOutput += clip.source_end - clip.source_start;
  }
  renderTimeline();
  selectClip(state.selectedIndex);
  log("Timeline realigned from beat and kill point edits.");
}

async function saveTimeline() {
  if (!state.timeline) return;
  setBusy(true);
  try {
    const data = await requestJson("/api/update-timeline", {
      method: "POST",
      body: JSON.stringify({ timeline: state.timeline }),
    });
    state.timeline = data.timeline;
    renderTimeline();
    log(`Timeline saved: ${data.timelinePath}`);
  } catch (error) {
    log(`Save failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function renderOutput() {
  if (!state.timeline) {
    log("Render skipped: no timeline loaded.");
    return;
  }
  setBusy(true);
  log("Rendering montage...");
  try {
    const data = await requestJson("/api/render", {
      method: "POST",
      body: JSON.stringify({ timeline: state.timeline, outputPath: "data/output/montage_ui.mp4" }),
    });
    els.outputVideo.src = `${data.previewUrl}&t=${Date.now()}`;
    els.outputPath.textContent = data.outputPath;
    log(`Render complete: ${data.outputPath}`);
    await refreshMedia();
  } catch (error) {
    log(`Render failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

function downloadJson() {
  if (!state.timeline) return;
  const blob = new Blob([JSON.stringify(state.timeline, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "fragsync_timeline.json";
  anchor.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

els.analyzeBtn.addEventListener("click", analyze);
els.renderBtn.addEventListener("click", renderOutput);
els.realignBtn.addEventListener("click", realignTimeline);
els.saveTimelineBtn.addEventListener("click", saveTimeline);
els.downloadJsonBtn.addEventListener("click", downloadJson);
els.refreshMediaBtn.addEventListener("click", () => refreshMedia().catch((error) => log(error.message)));
els.seekKillBtn.addEventListener("click", seekKillPoint);
els.loadExampleBeatsBtn.addEventListener("click", () => {
  els.manualBeats.value = "0.8, 1.6, 2.4, 3.2, 4.0, 4.8";
});
els.clearBeatsBtn.addEventListener("click", () => {
  els.manualBeats.value = "";
});

els.timelineBody.addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-index]");
  if (row) selectClip(Number.parseInt(row.dataset.index, 10));
});

els.timelineBody.addEventListener("change", (event) => {
  if (event.target.matches("input[data-field]")) {
    updateField(event.target.closest("tr[data-index]"), event.target);
  }
});

els.mediaList.addEventListener("click", (event) => {
  const item = event.target.closest(".media-item");
  if (!item) return;
  const { kind, path } = item.dataset;
  if (kind === "music") {
    els.musicPath.value = path;
  } else if (kind === "clip") {
    els.clipVideo.src = mediaUrl(path);
    els.selectedClipName.textContent = basename(path);
  } else if (kind === "output") {
    els.outputVideo.src = mediaUrl(path);
    els.outputPath.textContent = path;
  }
});

refreshMedia().catch((error) => log(error.message));
renderTimeline();


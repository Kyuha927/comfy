"use strict";

const state = {
  token: sessionStorage.getItem("yue2MusicOsToken") || "",
  projects: [], artifacts: [], providers: [], irs: [], ir: null,
  selectedNoteId: null, hitboxes: [], audioObjectUrl: null, pollTimer: null,
};

const $ = (id) => document.getElementById(id);
const log = (message, data = null) => {
  const stamp = new Date().toLocaleTimeString();
  $("statusLog").textContent = `[${stamp}] ${message}${data ? `\n${JSON.stringify(data, null, 2)}` : ""}`;
};

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set("X-Music-OS-Token", state.token);
  if (options.body && typeof options.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { detail = (await response.json()).detail || detail; } catch (_) { /* no body */ }
    throw new Error(detail);
  }
  return response;
}

async function apiJson(path, options = {}) { return (await api(path, options)).json(); }

function clear(element) { while (element.firstChild) element.firstChild.remove(); }
function option(value, text) { const item = document.createElement("option"); item.value = value; item.textContent = text; return item; }
function pill(text, className = "") { const span = document.createElement("span"); span.className = `pill ${className}`; span.textContent = text; return span; }

async function loadHealth() {
  const health = await apiJson("/api/health");
  const ready = health.note_ir?.ready_provider_ids || [];
  $("connectionStatus").textContent = `Note IR 준비 · 자동 엔진 ${ready.length}`;
  $("connectionStatus").className = "pill ready";
}

async function loadProjects() {
  state.projects = await apiJson("/api/projects");
  const select = $("projectSelect");
  const previous = select.value;
  clear(select); select.append(option("", "선택하세요"));
  for (const project of state.projects) select.append(option(project.id, project.name));
  if (state.projects.some((item) => item.id === previous)) select.value = previous;
}

async function loadProviders() {
  state.providers = await apiJson("/api/note-providers");
  const root = $("providerList"); clear(root); root.classList.remove("empty");
  for (const provider of state.providers) {
    const row = document.createElement("label"); row.className = "provider";
    const checkbox = document.createElement("input"); checkbox.type = "checkbox";
    checkbox.value = provider.provider_id;
    checkbox.dataset.provider = "true";
    const automatic = !["manual", "import"].includes(provider.mode);
    checkbox.disabled = !provider.ready || !automatic;
    if (provider.ready && automatic && provider.tier === "free") checkbox.checked = true;
    const copy = document.createElement("span");
    const strong = document.createElement("b"); strong.textContent = provider.label;
    const small = document.createElement("small");
    small.textContent = `${provider.tier.toUpperCase()} · ${provider.mode}${provider.reason ? ` · ${provider.reason}` : ""}`;
    copy.append(strong, small);
    row.append(checkbox, copy, pill(provider.ready ? "READY" : "SLOT", provider.ready ? "ready" : "muted"));
    root.append(row);
  }
  if (!state.providers.length) { root.textContent = "등록된 엔진이 없습니다."; root.classList.add("empty"); }
}

async function loadProjectData() {
  const projectId = $("projectSelect").value;
  state.artifacts = []; state.irs = []; state.ir = null; state.selectedNoteId = null;
  if (!projectId) { renderAudioOptions(); renderIrOptions(); drawRoll(); return; }
  [state.artifacts, state.irs] = await Promise.all([
    apiJson(`/api/projects/${projectId}/artifacts`),
    apiJson(`/api/projects/${projectId}/note-irs`),
  ]);
  renderAudioOptions(); renderIrOptions();
}

function renderAudioOptions() {
  const select = $("audioSelect"); clear(select); select.append(option("", "오디오를 선택하세요"));
  for (const artifact of state.artifacts.filter((item) => item.kind === "audio")) {
    select.append(option(artifact.id, artifact.name));
  }
}

function renderIrOptions() {
  const select = $("irSelect"); const previous = select.value;
  clear(select); select.append(option("", "분석본을 선택하세요"));
  for (const ir of state.irs) select.append(option(ir.music_ir_id, `${ir.title} · r${ir.current_revision} · ${ir.note_count} notes`));
  if (state.irs.some((item) => item.music_ir_id === previous)) select.value = previous;
  else if (state.irs.length) select.value = state.irs[0].music_ir_id;
  if (select.value) loadIr(select.value).catch(handleError); else clearIr();
}

function selectedProviderIds() {
  return [...document.querySelectorAll('input[data-provider="true"]:checked')].map((item) => item.value);
}

async function startAnalysis() {
  const projectId = $("projectSelect").value; const source = $("audioSelect").value;
  if (!projectId || !source) throw new Error("프로젝트와 원본 음원을 선택하세요.");
  const providerIds = selectedProviderIds();
  if (!providerIds.length) throw new Error("실행 가능한 무료 엔진을 하나 이상 선택하세요. Basic Pitch 설치 또는 외부 엔진 설정이 필요합니다.");
  const payload = {
    project_id: projectId, source_artifact_id: source, provider_ids: providerIds,
    instrument_hint: $("instrumentHint").value.trim() || null,
    tempo_bpm: Number($("tempoInput").value),
    minimum_review_confidence: Number($("confidenceInput").value),
  };
  const job = await apiJson("/api/note-jobs/analyze", { method: "POST", body: JSON.stringify(payload) });
  log("채보 작업을 시작했습니다.", job); pollJob(job.id);
}

function pollJob(jobId) {
  clearTimeout(state.pollTimer);
  const tick = async () => {
    try {
      const job = await apiJson(`/api/note-jobs/${jobId}`);
      log(`채보 작업 ${job.status}`, job.result || { id: job.id });
      if (["succeeded", "failed"].includes(job.status)) {
        if (job.status === "succeeded") await loadProjectData();
        return;
      }
      state.pollTimer = setTimeout(tick, 900);
    } catch (error) { handleError(error); }
  };
  tick();
}

async function importJson(file) {
  const projectId = $("projectSelect").value;
  if (!projectId) throw new Error("프로젝트를 먼저 선택하세요.");
  const payload = JSON.parse(await file.text());
  const body = payload.project_id ? payload : {
    project_id: projectId,
    source_artifact_id: $("audioSelect").value || null,
    title: payload.title || file.name.replace(/\.json$/i, ""),
    provider_id: payload.provider_id || "normalized-json",
    provider_version: payload.provider_version || null,
    provider_tier: payload.tier || "free",
    tempo_bpm: payload.tempo_bpm || Number($("tempoInput").value),
    time_signature: payload.time_signature || { numerator: 4, denominator: 4 },
    tracks: payload.tracks || [], warnings: payload.warnings || [], metadata: payload.metadata || {},
  };
  const ir = await apiJson("/api/note-ir/import", { method: "POST", body: JSON.stringify(body) });
  log("정규화 JSON을 Music IR로 가져왔습니다.", ir.stats); await loadProjectData();
  $("irSelect").value = ir.music_ir_id; await loadIr(ir.music_ir_id);
}

async function loadIr(irId) {
  state.ir = await apiJson(`/api/note-ir/${irId}`); state.selectedNoteId = null;
  $("exportJsonButton").disabled = false; $("exportMidiButton").disabled = false;
  renderStats(); await renderRevisions(); drawRoll(); renderInspector(); await loadSourceAudio();
  log(`Music IR r${state.ir.revision}을 불러왔습니다.`, state.ir.stats);
}

function clearIr() {
  state.ir = null; state.selectedNoteId = null; $("irStats").textContent = "분석본을 선택하면 통계가 표시됩니다.";
  $("revisionList").textContent = "리비전 없음"; $("exportJsonButton").disabled = true; $("exportMidiButton").disabled = true;
  drawRoll(); renderInspector();
}

function renderStats() {
  const root = $("irStats"); clear(root); root.classList.remove("muted");
  const stats = state.ir.stats || {};
  for (const [label, value] of [["음표", stats.note_count], ["검토", stats.review_note_count], ["트랙", stats.track_count], ["평균 신뢰도", Math.round((stats.mean_confidence || 0) * 100) + "%"]]) {
    const item = document.createElement("div"); item.className = "stat";
    const b = document.createElement("b"); b.textContent = String(value ?? 0);
    const span = document.createElement("span"); span.textContent = label; item.append(b, span); root.append(item);
  }
}

async function renderRevisions() {
  const revisions = await apiJson(`/api/note-ir/${state.ir.music_ir_id}/revisions`);
  const root = $("revisionList"); clear(root); root.classList.remove("empty");
  for (const revision of revisions.slice(0, 12)) {
    const row = document.createElement("div"); row.className = "revision";
    const copy = document.createElement("span"); copy.textContent = `r${revision.revision} · ${revision.operation.type || "change"}`;
    const button = document.createElement("button"); button.type = "button"; button.textContent = "복원";
    button.disabled = revision.revision === state.ir.revision;
    button.addEventListener("click", () => restoreRevision(revision.revision).catch(handleError));
    row.append(copy, button); root.append(row);
  }
}

async function restoreRevision(revision) {
  const restored = await apiJson(`/api/note-ir/${state.ir.music_ir_id}/restore`, {
    method: "POST", body: JSON.stringify({ revision, reason: `restore r${revision} from editor` }),
  });
  log(`r${revision} 내용을 새 r${restored.revision}로 복원했습니다.`); await loadIr(restored.music_ir_id); await loadProjectData();
}

function allNotes() {
  if (!state.ir) return [];
  const notes = [];
  state.ir.tracks.forEach((track, trackIndex) => track.notes.forEach((note) => notes.push({ note, track, trackIndex })));
  return notes;
}

function drawRoll() {
  const canvas = $("pianoRoll"); const context = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1; const cssWidth = Math.max(canvas.clientWidth || 900, 820); const cssHeight = 520;
  canvas.width = Math.round(cssWidth * ratio); canvas.height = Math.round(cssHeight * ratio); context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, cssWidth, cssHeight); state.hitboxes = [];
  const notes = allNotes().filter(({ note }) => !note.deleted);
  $("emptyRoll").hidden = Boolean(state.ir && notes.length);
  context.fillStyle = "#0a0e12"; context.fillRect(0, 0, cssWidth, cssHeight);
  if (!notes.length) return;
  const reviewOnly = $("reviewOnly").checked; const threshold = Number($("drawThreshold").value);
  const filtered = notes.filter(({ note }) => (!reviewOnly || note.review_state === "review") && note.confidence.overall >= threshold);
  if (!filtered.length) return;
  const left = 46, top = 16, bottom = 28, right = 16; const width = cssWidth - left - right, height = cssHeight - top - bottom;
  const minPitch = Math.max(0, Math.min(...filtered.map(({ note }) => note.pitch.midi)) - 3);
  const maxPitch = Math.min(127, Math.max(...filtered.map(({ note }) => note.pitch.midi)) + 3);
  const duration = Math.max(1, state.ir.stats?.duration_sec || Math.max(...filtered.map(({ note }) => note.timing.end_sec)));
  context.strokeStyle = "#202832"; context.lineWidth = 1;
  for (let pitch = minPitch; pitch <= maxPitch; pitch++) {
    const y = top + (maxPitch - pitch) / Math.max(1, maxPitch - minPitch + 1) * height;
    if (pitch % 12 === 0) { context.strokeStyle = "#38414b"; context.fillStyle = "#7e8995"; context.fillText(noteName(pitch), 5, y + 4); }
    else context.strokeStyle = "#1b232b";
    context.beginPath(); context.moveTo(left, y); context.lineTo(left + width, y); context.stroke();
  }
  const secondsPerBar = 60 / state.ir.tempo_bpm * state.ir.time_signature.numerator;
  for (let time = 0; time <= duration; time += secondsPerBar) {
    const x = left + time / duration * width; context.strokeStyle = "#2b343e"; context.beginPath(); context.moveTo(x, top); context.lineTo(x, top + height); context.stroke();
    context.fillStyle = "#73808c"; context.fillText(String(Math.round(time / secondsPerBar + 1)), x + 3, cssHeight - 8);
  }
  const rowHeight = Math.max(5, height / Math.max(1, maxPitch - minPitch + 1) * .78);
  for (const { note, trackIndex } of filtered) {
    const x = left + note.timing.start_sec / duration * width;
    const w = Math.max(3, (note.timing.end_sec - note.timing.start_sec) / duration * width);
    const y = top + (maxPitch - note.pitch.midi) / Math.max(1, maxPitch - minPitch + 1) * height - rowHeight / 2;
    const selected = note.note_id === state.selectedNoteId; const review = note.review_state === "review";
    const hue = (155 + trackIndex * 53) % 360;
    context.fillStyle = review ? "#e7c875" : `hsl(${hue} 58% 62%)`; context.fillRect(x, y, w, rowHeight);
    if (selected) { context.strokeStyle = "#ffffff"; context.lineWidth = 2; context.strokeRect(x - 1, y - 1, w + 2, rowHeight + 2); context.lineWidth = 1; }
    state.hitboxes.push({ x, y, w, h: rowHeight, noteId: note.note_id });
  }
}

function noteName(midi) { return ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"][midi % 12] + (Math.floor(midi / 12) - 1); }

function selectedNote() {
  return allNotes().find(({ note }) => note.note_id === state.selectedNoteId)?.note || null;
}

function renderInspector() {
  const note = selectedNote(); $("notePlaceholder").hidden = Boolean(note); $("noteForm").hidden = !note;
  if (!note) return;
  $("noteId").textContent = note.note_id; $("noteConfidence").textContent = `${Math.round(note.confidence.overall * 100)}% · ${note.pitch.name}`;
  $("noteConfidence").className = `pill ${note.review_state === "review" ? "review" : "ready"}`;
  $("pitchInput").value = note.pitch.midi; $("centsInput").value = note.pitch.cents;
  $("startInput").value = note.timing.start_sec; $("endInput").value = note.timing.end_sec;
  $("velocityInput").value = note.velocity; $("noteInstrumentInput").value = note.instrument;
  $("reviewStateInput").value = note.review_state; $("mutedInput").checked = note.muted; $("deletedInput").checked = note.deleted;
  const votes = $("providerVotes"); clear(votes);
  for (const vote of note.provenance || []) {
    const row = document.createElement("div"); row.className = "vote";
    row.textContent = `${vote.provider_id}: ${noteName(vote.pitch_midi)} · ${vote.start_sec.toFixed(3)}–${vote.end_sec.toFixed(3)}s · ${Math.round(vote.confidence * 100)}%`;
    votes.append(row);
  }
  const boundary = $("audioBoundary"); boundary.className = "boundary";
  if (note.audio_editability === "resynthesis-required") { boundary.classList.add("warn"); boundary.textContent = "이 음은 다성 오디오 안에 있을 가능성이 큽니다. Music IR과 MIDI는 즉시 바뀌지만 원본 음원 변경에는 재합성 또는 전문 편집 엔진이 필요합니다."; }
  else if (note.audio_editability === "monophonic-pitch") boundary.textContent = "단선율 스템이면 별도 피치 엔진으로 오디오 반영이 가능합니다. 현재 저장은 비파괴 Music IR 수정입니다.";
  else boundary.textContent = "현재 편집은 Music IR과 MIDI에만 반영됩니다. 원본 오디오는 바뀌지 않습니다.";
}

async function saveNote(event) {
  event.preventDefault(); const note = selectedNote(); if (!state.ir || !note) return;
  const payload = {
    pitch_midi: Number($("pitchInput").value), cents: Number($("centsInput").value),
    start_sec: Number($("startInput").value), end_sec: Number($("endInput").value),
    velocity: Number($("velocityInput").value), instrument: $("noteInstrumentInput").value,
    review_state: $("reviewStateInput").value, muted: $("mutedInput").checked,
    deleted: $("deletedInput").checked, edit_reason: $("editReasonInput").value || "manual note edit",
  };
  const response = await apiJson(`/api/note-ir/${state.ir.music_ir_id}/notes/${note.note_id}`, { method: "PATCH", body: JSON.stringify(payload) });
  state.ir = response.music_ir; state.selectedNoteId = note.note_id; renderStats(); await renderRevisions(); drawRoll(); renderInspector();
  const musicIrId = state.ir.music_ir_id;
  log("음 하나를 새 리비전으로 저장했습니다. 원본 오디오는 변경하지 않았습니다.", response.receipt);
  await loadProjectData();
  $("irSelect").value = musicIrId;
  await loadIr(musicIrId);
}

async function loadSourceAudio() {
  const audio = $("sourceAudio");
  if (state.audioObjectUrl) { URL.revokeObjectURL(state.audioObjectUrl); state.audioObjectUrl = null; }
  audio.removeAttribute("src");
  if (!state.ir?.source_artifact_id) return;
  const response = await api(`/api/artifacts/${state.ir.source_artifact_id}/download`);
  state.audioObjectUrl = URL.createObjectURL(await response.blob()); audio.src = state.audioObjectUrl;
}

async function playSelectedNote() {
  const note = selectedNote(); const audio = $("sourceAudio"); if (!note || !audio.src) throw new Error("원본 음원을 재생할 수 없습니다.");
  audio.currentTime = Math.max(0, note.timing.start_sec - .15); await audio.play();
  const stopAt = note.timing.end_sec + .2;
  const watcher = () => { if (audio.currentTime >= stopAt) { audio.pause(); audio.removeEventListener("timeupdate", watcher); } };
  audio.addEventListener("timeupdate", watcher);
}

async function downloadExport(kind) {
  if (!state.ir) return; const response = await api(`/api/note-ir/${state.ir.music_ir_id}/export.${kind}`);
  const blob = await response.blob(); const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
  anchor.href = url; anchor.download = `music-ir-${state.ir.music_ir_id}-r${state.ir.revision}.${kind}`; document.body.append(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
}

function handleCanvasClick(event) {
  const canvas = $("pianoRoll"); const rect = canvas.getBoundingClientRect();
  const x = (event.clientX - rect.left) * (canvas.clientWidth / rect.width); const y = (event.clientY - rect.top) * (canvas.clientHeight / rect.height);
  const hit = [...state.hitboxes].reverse().find((box) => x >= box.x && x <= box.x + box.w && y >= box.y && y <= box.y + box.h);
  if (hit) { state.selectedNoteId = hit.noteId; drawRoll(); renderInspector(); }
}

function handleError(error) { $("connectionStatus").textContent = "확인 필요"; $("connectionStatus").className = "pill review"; log(`오류: ${error.message}`); }

async function boot() {
  $("tokenButton").addEventListener("click", () => {
    const value = prompt("X-Music-OS-Token 값", state.token);
    if (value !== null) { state.token = value.trim(); sessionStorage.setItem("yue2MusicOsToken", state.token); bootData().catch(handleError); }
  });
  $("refreshButton").addEventListener("click", () => bootData().catch(handleError));
  $("projectSelect").addEventListener("change", () => loadProjectData().catch(handleError));
  $("irSelect").addEventListener("change", (event) => event.target.value ? loadIr(event.target.value).catch(handleError) : clearIr());
  $("analyzeButton").addEventListener("click", () => startAnalysis().catch(handleError));
  $("jsonInput").addEventListener("change", (event) => { const [file] = event.target.files; if (file) importJson(file).catch(handleError); event.target.value = ""; });
  $("reviewOnly").addEventListener("change", drawRoll); $("drawThreshold").addEventListener("input", drawRoll);
  $("pianoRoll").addEventListener("click", handleCanvasClick); $("noteForm").addEventListener("submit", (event) => saveNote(event).catch(handleError));
  $("playNoteButton").addEventListener("click", () => playSelectedNote().catch(handleError));
  $("exportJsonButton").addEventListener("click", () => downloadExport("json").catch(handleError));
  $("exportMidiButton").addEventListener("click", () => downloadExport("mid").catch(handleError));
  window.addEventListener("resize", () => requestAnimationFrame(drawRoll));
  await bootData();
}

async function bootData() { await Promise.all([loadHealth(), loadProjects(), loadProviders()]); await loadProjectData(); log("Note IR 편집실이 준비되었습니다."); }

document.addEventListener("DOMContentLoaded", () => boot().catch(handleError));

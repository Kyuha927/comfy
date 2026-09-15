'use strict';

const state = {
  token: localStorage.getItem('yue2MusicOsToken') || '',
  projectId: localStorage.getItem('yue2MusicOsProject') || '',
  projects: [],
  jobs: [],
  artifacts: [],
  providers: [],
  artifactFilter: 'all',
  audioUrls: { A: null, B: null },
  polling: null,
};

const $ = (id) => document.getElementById(id);
const elements = {
  engineBadge: $('engineBadge'), projectSelect: $('projectSelect'), jobList: $('jobList'),
  artifactList: $('artifactList'), generationScoreSelect: $('generationScoreSelect'),
  transcribeAudioSelect: $('transcribeAudioSelect'), beforeScoreSelect: $('beforeScoreSelect'),
  afterScoreSelect: $('afterScoreSelect'), stripScoreSelect: $('stripScoreSelect'),
  productionGenerationSelect: $('productionGenerationSelect'), providerList: $('providerList'),
  toast: $('toast'), tokenInput: $('tokenInput'), projectDialog: $('projectDialog'),
  settingsDialog: $('settingsDialog'), previewDialog: $('previewDialog'), fileInput: $('fileInput'), uploadZone: $('uploadZone'),
};

function headers(extra = {}) {
  const result = { ...extra };
  if (state.token) result['X-Music-OS-Token'] = state.token;
  return result;
}

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: headers(options.headers || {}) });
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof body === 'object' && body.detail ? body.detail : String(body || response.statusText);
    throw new Error(message);
  }
  return body;
}

function toast(message, error = false) {
  elements.toast.textContent = message;
  elements.toast.classList.toggle('error', error);
  elements.toast.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => elements.toast.classList.remove('show'), 3600);
}

function setBusy(button, busy, label = '처리 중…') {
  if (!button) return;
  if (!button.dataset.label) button.dataset.label = button.textContent;
  button.disabled = busy;
  button.textContent = busy ? label : button.dataset.label;
}

function formatBytes(bytes) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value.toFixed(unit ? 1 : 0)} ${units[unit]}`;
}

function formatTime(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

function clearObjectUrl(slot) {
  if (state.audioUrls[slot]) URL.revokeObjectURL(state.audioUrls[slot]);
  state.audioUrls[slot] = null;
}

async function checkHealth() {
  try {
    const health = await api('/api/health');
    const engine = health.doctor.engine;
    const mock = engine.engine === 'mock';
    const ready = Boolean(engine.ready);
    elements.engineBadge.textContent = mock ? 'MOCK · 안전 데모' : ready ? 'LOCAL · 준비됨' : 'LOCAL · 설정 필요';
    elements.engineBadge.className = `status-pill ${mock || ready ? 'good' : 'warn'}`;
  } catch (error) {
    elements.engineBadge.textContent = '연결 실패';
    elements.engineBadge.className = 'status-pill bad';
    toast(`서버 연결 실패: ${error.message}`, true);
  }
}

async function loadProviders() {
  state.providers = await api('/api/render-providers');
  renderProviders();
}

function renderProviders() {
  elements.providerList.replaceChildren();
  if (!state.providers.length) {
    elements.providerList.className = 'provider-grid empty-state';
    elements.providerList.textContent = '사용 가능한 렌더러가 없습니다.';
    return;
  }
  elements.providerList.className = 'provider-grid';
  for (const provider of state.providers) {
    const label = document.createElement('label'); label.className = `provider-option ${provider.ready ? '' : 'disabled'}`;
    const input = document.createElement('input'); input.type = 'checkbox'; input.value = provider.id; input.disabled = !provider.ready;
    input.checked = provider.id === 'flow-lyria-manual';
    const body = document.createElement('span');
    const title = document.createElement('b'); title.textContent = provider.label;
    const meta = document.createElement('small');
    const execution = provider.live_execution ? '실행 연결' : '수동 패키지';
    meta.textContent = `${execution} · 상업 상태 ${provider.commercial_status}${provider.ready ? '' : ' · 준비 안 됨'}`;
    body.append(title, meta); label.append(input, body); elements.providerList.append(label);
  }
}

function selectedProviderIds() {
  return [...elements.providerList.querySelectorAll('input[type="checkbox"]:checked')].map((input) => input.value);
}

async function loadProjects() {
  state.projects = await api('/api/projects');
  elements.projectSelect.replaceChildren(new Option('프로젝트를 선택하세요', ''));
  for (const project of state.projects) elements.projectSelect.add(new Option(project.name, project.id));
  if (state.projectId && state.projects.some((project) => project.id === state.projectId)) {
    elements.projectSelect.value = state.projectId;
  } else {
    state.projectId = state.projects[0]?.id || '';
    elements.projectSelect.value = state.projectId;
  }
  localStorage.setItem('yue2MusicOsProject', state.projectId);
  await refreshProject();
}

async function refreshProject() {
  if (!state.projectId) {
    state.jobs = []; state.artifacts = [];
    renderJobs(); renderArtifacts(); updateArtifactSelects(); updateGenerationJobs();
    return;
  }
  const [jobs, artifacts] = await Promise.all([
    api(`/api/projects/${state.projectId}/jobs`),
    api(`/api/projects/${state.projectId}/artifacts`),
  ]);
  state.jobs = jobs;
  state.artifacts = artifacts;
  renderJobs(); renderArtifacts(); updateArtifactSelects(); updateGenerationJobs(); managePolling();
}

function renderJobs() {
  elements.jobList.replaceChildren();
  if (!state.jobs.length) {
    elements.jobList.className = 'job-list empty-state';
    elements.jobList.textContent = state.projectId ? '아직 작업 기록이 없습니다.' : '프로젝트를 선택하면 작업이 표시됩니다.';
    return;
  }
  elements.jobList.className = 'job-list';
  for (const job of state.jobs) {
    const card = document.createElement('article'); card.className = 'job-item';
    const header = document.createElement('header');
    const needsReview = job.status === 'succeeded' && Boolean(job.result?.review_required);
    const stateDot = document.createElement('span'); stateDot.className = `job-state ${needsReview ? 'needs-review' : job.status}`;
    const title = document.createElement('b'); title.textContent = needsReview ? `${job.kind} · 검토 필요` : job.kind;
    const time = document.createElement('time'); time.textContent = formatTime(job.created_at);
    header.append(stateDot, title, time);
    const info = document.createElement('p');
    info.textContent = job.status === 'failed'
      ? (job.error || '실패')
      : needsReview
        ? `산출물 ${job.result?.artifact_count ?? 0}개 보존 · 잘림 또는 길이 상태 확인 필요`
        : job.status === 'succeeded'
          ? `${job.result?.artifact_count ?? 0}개 결과 보존`
          : '순차 작업 대기 또는 실행 중';
    card.append(header, info); elements.jobList.append(card);
  }
}

function artifactIcon(kind) {
  return ({ audio: '♪', score: '𝄞', midi: 'M', metadata: '{}', comparison: '↔', text: 'T' })[kind] || '·';
}

function renderArtifacts() {
  elements.artifactList.replaceChildren();
  const visible = state.artifacts.filter((artifact) => state.artifactFilter === 'all' || artifact.kind === state.artifactFilter);
  if (!visible.length) {
    elements.artifactList.className = 'artifact-grid empty-state';
    elements.artifactList.textContent = state.projectId ? '이 조건에 맞는 결과가 없습니다.' : '프로젝트를 선택하면 결과가 표시됩니다.';
    return;
  }
  elements.artifactList.className = 'artifact-grid';
  for (const artifact of visible) {
    const card = document.createElement('article'); card.className = 'artifact-card';
    const icon = document.createElement('div'); icon.className = 'artifact-icon'; icon.textContent = artifactIcon(artifact.kind);
    const body = document.createElement('div');
    const title = document.createElement('strong'); title.textContent = artifact.name; title.title = artifact.name;
    const meta = document.createElement('small'); meta.textContent = `${artifact.kind.toUpperCase()} · ${formatBytes(artifact.size_bytes)} · ${formatTime(artifact.created_at)}`;
    body.append(title, meta);
    const actions = document.createElement('div'); actions.className = 'artifact-actions';
    const download = document.createElement('button'); download.type = 'button'; download.textContent = '다운로드'; download.addEventListener('click', () => downloadArtifact(artifact));
    actions.append(download);
    if (artifact.kind === 'audio') {
      for (const slot of ['A', 'B']) {
        const button = document.createElement('button'); button.type = 'button'; button.textContent = `${slot}에 올리기`; button.addEventListener('click', () => setAudio(slot, artifact)); actions.append(button);
      }
    }
    if (artifact.kind === 'score' || artifact.kind === 'metadata' || artifact.kind === 'text') {
      const preview = document.createElement('button'); preview.type = 'button'; preview.textContent = '내용 보기'; preview.addEventListener('click', () => previewArtifact(artifact)); actions.append(preview);
    }
    card.append(icon, body, actions); elements.artifactList.append(card);
  }
}

function updateSelect(select, artifacts, placeholder) {
  const current = select.value;
  select.replaceChildren(new Option(placeholder, ''));
  for (const artifact of artifacts) select.add(new Option(artifact.name, artifact.id));
  if ([...select.options].some((option) => option.value === current)) select.value = current;
}

function updateArtifactSelects() {
  const scores = state.artifacts.filter((artifact) => artifact.kind === 'score');
  const audio = state.artifacts.filter((artifact) => artifact.kind === 'audio');
  updateSelect(elements.generationScoreSelect, scores, '새 계획 생성');
  updateSelect(elements.transcribeAudioSelect, audio, '업로드한 음원을 선택하세요');
  updateSelect(elements.beforeScoreSelect, scores, '원본 악보 선택');
  updateSelect(elements.afterScoreSelect, scores, '수정 악보 선택');
  updateSelect(elements.stripScoreSelect, scores, '원본 악보 선택');
}

function updateGenerationJobs() {
  const current = elements.productionGenerationSelect.value;
  elements.productionGenerationSelect.replaceChildren(new Option('완료된 생성 작업을 선택하세요', ''));
  const jobs = state.jobs.filter((job) => job.kind === 'generate' && job.status === 'succeeded');
  for (const job of jobs) {
    const count = job.result?.candidate_count ?? '?';
    elements.productionGenerationSelect.add(new Option(`${formatTime(job.created_at)} · 후보 ${count}개 · ${job.id.slice(0, 8)}`, job.id));
  }
  if ([...elements.productionGenerationSelect.options].some((option) => option.value === current)) {
    elements.productionGenerationSelect.value = current;
  } else if (jobs.length) {
    elements.productionGenerationSelect.value = jobs[0].id;
  }
}

function managePolling() {
  const active = state.jobs.some((job) => ['queued', 'running'].includes(job.status));
  if (active && !state.polling) state.polling = setInterval(() => refreshProject().catch((error) => toast(error.message, true)), 1800);
  if (!active && state.polling) { clearInterval(state.polling); state.polling = null; }
}

async function uploadFiles(files) {
  if (!state.projectId) throw new Error('먼저 프로젝트를 만드세요.');
  for (const file of files) {
    const form = new FormData(); form.append('file', file);
    await api(`/api/projects/${state.projectId}/uploads`, { method: 'POST', body: form });
  }
  toast(`${files.length}개 파일을 보존했습니다.`);
  await refreshProject();
}

async function submitJob(path, payload, button) {
  if (!state.projectId) { toast('먼저 프로젝트를 만드세요.', true); return; }
  setBusy(button, true);
  try {
    const job = await api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    toast(`작업 ${job.kind}을(를) 큐에 넣었습니다.`);
    await refreshProject();
  } catch (error) { toast(error.message, true); }
  finally { setBusy(button, false); }
}

async function fetchArtifactBlob(artifact) {
  const response = await fetch(artifact.download_url, { headers: headers() });
  if (!response.ok) throw new Error(`파일을 가져오지 못했습니다 (${response.status})`);
  return response.blob();
}

async function downloadArtifact(artifact) {
  try {
    const blob = await fetchArtifactBlob(artifact);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = artifact.name; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { toast(error.message, true); }
}

async function previewArtifact(artifact) {
  try {
    const blob = await fetchArtifactBlob(artifact);
    const text = await blob.text();
    $('previewTitle').textContent = artifact.name;
    $('previewContent').textContent = text;
    elements.previewDialog.showModal();
    $('previewContent').focus();
  } catch (error) { toast(error.message, true); }
}

async function setAudio(slot, artifact) {
  try {
    const blob = await fetchArtifactBlob(artifact);
    clearObjectUrl(slot);
    const url = URL.createObjectURL(blob); state.audioUrls[slot] = url;
    $(`audio${slot}`).src = url; $(`audio${slot}Title`).textContent = artifact.name;
    toast(`${artifact.name}을(를) ${slot} 슬롯에 올렸습니다.`);
  } catch (error) { toast(error.message, true); }
}

function bindTabs() {
  document.querySelectorAll('.mode-tab').forEach((button) => button.addEventListener('click', () => {
    document.querySelectorAll('.mode-tab').forEach((item) => {
      const selected = item === button;
      item.classList.toggle('active', selected);
      item.setAttribute('aria-selected', String(selected));
    });
    document.querySelectorAll('.tab-panel').forEach((panel) => {
      const active = panel.id === `tab-${button.dataset.tab}`;
      panel.classList.toggle('active', active);
      panel.setAttribute('aria-hidden', String(!active));
    });
  }));
}

function bindEvents() {
  bindTabs();
  document.querySelectorAll('[data-close-dialog]').forEach((button) => button.addEventListener('click', () => $(button.dataset.closeDialog).close()));
  $('openSettings').addEventListener('click', () => { elements.tokenInput.value = state.token; elements.settingsDialog.showModal(); });
  $('saveSettings').addEventListener('click', () => { state.token = elements.tokenInput.value.trim(); localStorage.setItem('yue2MusicOsToken', state.token); setTimeout(() => loadProjects().then(checkHealth).catch((error) => toast(error.message, true)), 0); });
  $('newProjectButton').addEventListener('click', () => { $('projectNameInput').value = ''; elements.projectDialog.showModal(); setTimeout(() => $('projectNameInput').focus(), 50); });
  $('projectForm').addEventListener('submit', async (event) => {
    event.preventDefault(); const button = event.submitter; setBusy(button, true);
    try {
      const project = await api('/api/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: $('projectNameInput').value }) });
      state.projectId = project.id; localStorage.setItem('yue2MusicOsProject', state.projectId); elements.projectDialog.close(); await loadProjects(); toast('새 프로젝트를 만들었습니다.');
    } catch (error) { toast(error.message, true); } finally { setBusy(button, false); }
  });
  elements.projectSelect.addEventListener('change', async () => { state.projectId = elements.projectSelect.value; localStorage.setItem('yue2MusicOsProject', state.projectId); await refreshProject(); });
  $('refreshButton').addEventListener('click', () => refreshProject().catch((error) => toast(error.message, true)));
  elements.fileInput.addEventListener('change', () => { if (elements.fileInput.files.length) uploadFiles([...elements.fileInput.files]).catch((error) => toast(error.message, true)); elements.fileInput.value = ''; });
  for (const event of ['dragenter', 'dragover']) elements.uploadZone.addEventListener(event, (e) => { e.preventDefault(); elements.uploadZone.classList.add('dragging'); });
  for (const event of ['dragleave', 'drop']) elements.uploadZone.addEventListener(event, (e) => { e.preventDefault(); elements.uploadZone.classList.remove('dragging'); });
  elements.uploadZone.addEventListener('drop', (event) => { if (event.dataTransfer.files.length) uploadFiles([...event.dataTransfer.files]).catch((error) => toast(error.message, true)); });

  $('generateForm').addEventListener('submit', (event) => {
    event.preventDefault();
    if (!state.projectId) return toast('먼저 프로젝트를 만드세요.', true);
    const cot = $('cotInput').value;
    const scoreId = elements.generationScoreSelect.value || null;
    if (cot === 'off' && scoreId) return toast('Off 모드는 조건 악보를 받을 수 없습니다.', true);
    submitJob('/api/jobs/generate', {
      project_id: state.projectId, style: $('styleInput').value, lyrics: $('lyricsInput').value,
      cot, seed: Number($('seedInput').value), candidate_count: Number($('candidateInput').value), abc_artifact_id: scoreId,
    }, event.submitter);
  });
  $('transcribeForm').addEventListener('submit', (event) => { event.preventDefault(); submitJob('/api/jobs/transcribe', { project_id: state.projectId, source_artifact_id: elements.transcribeAudioSelect.value, melody_only: $('melodyOnlyInput').checked }, event.submitter); });
  $('compareForm').addEventListener('submit', (event) => { event.preventDefault(); submitJob('/api/jobs/compare', { project_id: state.projectId, before_artifact_id: elements.beforeScoreSelect.value, after_artifact_id: elements.afterScoreSelect.value, voices: $('voicesSelect').value, allow_tempo_change: $('allowTempoInput').checked }, event.submitter); });
  $('stripForm').addEventListener('submit', (event) => { event.preventDefault(); submitJob('/api/jobs/strip-chords', { project_id: state.projectId, source_artifact_id: elements.stripScoreSelect.value, keep_voice: $('keepVoiceSelect').value }, event.submitter); });
  $('rankCandidatesButton').addEventListener('click', (event) => {
    const generationJobId = elements.productionGenerationSelect.value;
    if (!generationJobId) return toast('먼저 완료된 YuE2 생성 작업을 선택하세요.', true);
    submitJob('/api/jobs/rank-candidates', { project_id: state.projectId, generation_job_id: generationJobId }, event.currentTarget);
  });
  $('productionForm').addEventListener('submit', (event) => {
    event.preventDefault();
    const generationJobId = elements.productionGenerationSelect.value;
    const providerIds = selectedProviderIds();
    const commercialIntent = $('commercialIntentInput').checked;
    if (!generationJobId) return toast('완료된 YuE2 생성 작업을 선택하세요.', true);
    if (!providerIds.length) return toast('최종 렌더러를 하나 이상 선택하세요.', true);
    if (commercialIntent && !$('licenseAckInput').checked) return toast('상업 렌더 전 라이선스 확인란을 체크하세요.', true);
    const candidateValue = $('productionCandidateSelect').value;
    submitJob('/api/jobs/production-render', {
      project_id: state.projectId,
      generation_job_id: generationJobId,
      candidate: candidateValue === 'best-technical' ? candidateValue : Number(candidateValue),
      provider_ids: providerIds,
      title: $('productionTitleInput').value,
      notes: $('productionNotesInput').value,
      commercial_intent: commercialIntent,
      license_review_acknowledged: $('licenseAckInput').checked,
    }, event.submitter);
  });

  document.querySelectorAll('.filter-chip').forEach((button) => button.addEventListener('click', () => {
    state.artifactFilter = button.dataset.kind;
    document.querySelectorAll('.filter-chip').forEach((item) => item.classList.toggle('active', item === button)); renderArtifacts();
  }));
  $('swapAudioButton').addEventListener('click', () => {
    const aSrc = $('audioA').src, bSrc = $('audioB').src, aTitle = $('audioATitle').textContent, bTitle = $('audioBTitle').textContent;
    $('audioA').src = bSrc; $('audioB').src = aSrc; $('audioATitle').textContent = bTitle; $('audioBTitle').textContent = aTitle;
    [state.audioUrls.A, state.audioUrls.B] = [state.audioUrls.B, state.audioUrls.A];
  });
  window.addEventListener('beforeunload', () => { clearObjectUrl('A'); clearObjectUrl('B'); });
}

async function boot() {
  bindEvents(); elements.tokenInput.value = state.token;
  await checkHealth();
  try { await loadProviders(); await loadProjects(); } catch (error) { toast(error.message, true); }
}

document.addEventListener('DOMContentLoaded', boot);

// popup.js (Manifest V3)
const DEFAULT_SERVER_URL = 'http://127.0.0.1:6001';
const POLL_INTERVAL_MS = 1000;

document.addEventListener('DOMContentLoaded', async () => {
  const serverUrlInput = document.getElementById('serverUrlInput');
  const directoryInput = document.getElementById('directoryInput');
  const returnDataCheckbox = document.getElementById('returnDataCheckbox');
  const statusMessage = document.getElementById('statusMessage');
  const healthBadge = document.getElementById('healthBadge');
  const healthText = document.getElementById('healthText');
  const downloadsList = document.getElementById('downloadsList');
  const clearDownloadsButton = document.getElementById('clearDownloadsButton');
  const openDirectoryButton = document.getElementById('openDirectoryButton');
  const actionButtons = [
    document.getElementById('youtubeMusicButton'),
    document.getElementById('youtubeButton'),
    document.getElementById('youtubeVideoButton'),
  ];

  // Cargar configuración guardada
  const stored = await chrome.storage.local.get(['serverUrl', 'directory', 'returnData']);
  let initialUrl = stored.serverUrl || DEFAULT_SERVER_URL;
  // Evitar puerto 6000 bloqueado por Chromium (ERR_UNSAFE_PORT)
  if (/^https?:\/\/[^/]+:6000(\/|$)/.test(initialUrl)) {
    initialUrl = DEFAULT_SERVER_URL;
    chrome.storage.local.set({ serverUrl: initialUrl });
  }
  serverUrlInput.value = initialUrl;
  if (stored.directory) {
    directoryInput.value = stored.directory;
  }
  if (stored.returnData !== undefined) {
    returnDataCheckbox.checked = Boolean(stored.returnData);
  }

  const saveSettings = () => {
    chrome.storage.local.set({
      serverUrl: normalizeServerUrl(serverUrlInput.value),
      directory: directoryInput.value.trim(),
      returnData: returnDataCheckbox.checked,
    });
  };

  function normalizeServerUrl(rawUrl) {
    const trimmed = (rawUrl || '').trim();
    if (!trimmed) {
      return DEFAULT_SERVER_URL;
    }
    return trimmed.replace(/\/+$/, '');
  }

  function setStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.className = `status ${type}`;
  }

  function setButtonsDisabled(disabled) {
    for (const button of actionButtons) {
      button.disabled = disabled;
    }
  }

  function formatBytes(bytes) {
    if (bytes === null || bytes === undefined || Number.isNaN(bytes)) {
      return '';
    }
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let value = bytes;
    let idx = 0;
    while (value >= 1024 && idx < units.length - 1) {
      value /= 1024;
      idx += 1;
    }
    return `${value.toFixed(idx >= 2 ? 2 : 0)} ${units[idx]}`;
  }

  function formatEta(seconds) {
    if (seconds === null || seconds === undefined || seconds < 0) {
      return '';
    }
    const total = Math.floor(seconds);
    const hrs = Math.floor(total / 3600);
    const mins = Math.floor((total % 3600) / 60);
    const secs = total % 60;
    const pad = (n) => String(n).padStart(2, '0');
    return hrs > 0 ? `${hrs}:${pad(mins)}:${pad(secs)}` : `${pad(mins)}:${pad(secs)}`;
  }

  function statusLabel(job) {
    switch (job.status) {
      case 'queued':
        return 'En cola';
      case 'downloading':
        return `${job.percent ?? 0}%`;
      case 'processing':
        return 'Convirtiendo...';
      case 'cancelling':
        return 'Cancelando...';
      case 'completed':
        return 'Completado';
      case 'cancelled':
        return 'Cancelado';
      case 'error':
        return 'Error';
      default:
        return job.status;
    }
  }

  function buildMetaDetail(job) {
    if (job.status === 'downloading') {
      const parts = [];
      if (job.total_bytes) {
        parts.push(`${formatBytes(job.downloaded_bytes)} / ${formatBytes(job.total_bytes)}`);
      } else if (job.downloaded_bytes) {
        parts.push(formatBytes(job.downloaded_bytes));
      }
      if (job.speed) {
        parts.push(`${formatBytes(job.speed)}/s`);
      }
      if (job.eta !== null && job.eta !== undefined) {
        parts.push(`ETA ${formatEta(job.eta)}`);
      }
      return parts.join(' · ') || 'Descargando...';
    }
    return job.message || '';
  }

  function renderDownloads(downloads) {
    downloadsList.textContent = '';

    if (!downloads || downloads.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = 'Sin descargas recientes';
      downloadsList.appendChild(empty);
      return;
    }

    for (const job of downloads) {
      const item = document.createElement('div');
      item.className = `download-item ${job.status}`;

      const top = document.createElement('div');
      top.className = 'download-top';

      const title = document.createElement('span');
      title.className = 'download-title';
      title.textContent = job.title;
      title.title = `${job.title} (${job.directory})`;
      top.appendChild(title);

      const isActive = ['queued', 'downloading', 'processing', 'cancelling'].includes(job.status);
      if (isActive) {
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'cancel-btn';
        cancelBtn.textContent = job.status === 'cancelling' ? '...' : 'Cancelar';
        cancelBtn.disabled = job.status === 'cancelling';
        cancelBtn.addEventListener('click', () => cancelDownload(job.id, cancelBtn));
        top.appendChild(cancelBtn);
      }

      const track = document.createElement('div');
      track.className = 'progress-track';
      const fill = document.createElement('div');
      fill.className = 'progress-fill';
      fill.style.width = `${Math.min(100, Math.max(0, job.percent || 0))}%`;
      track.appendChild(fill);

      const meta = document.createElement('div');
      meta.className = 'download-meta';

      const detail = document.createElement('span');
      detail.textContent = buildMetaDetail(job);

      const state = document.createElement('span');
      state.className = 'download-state';
      state.textContent = statusLabel(job);

      meta.appendChild(detail);
      meta.appendChild(state);

      item.appendChild(top);
      item.appendChild(track);
      item.appendChild(meta);
      downloadsList.appendChild(item);
    }
  }

  async function fetchDownloads() {
    const serverUrl = normalizeServerUrl(serverUrlInput.value);
    if (!/^https?:\/\/.+/.test(serverUrl)) {
      return;
    }
    try {
      const res = await fetch(`${serverUrl}/downloads`);
      if (!res.ok) {
        return;
      }
      const data = await res.json();
      renderDownloads(data.downloads || []);
    } catch {
      // Silencioso durante polling si el servidor está apagado
    }
  }

  async function cancelDownload(jobId, buttonEl) {
    const serverUrl = normalizeServerUrl(serverUrlInput.value);
    buttonEl.disabled = true;
    buttonEl.textContent = '...';
    try {
      const res = await fetch(`${serverUrl}/downloads/${encodeURIComponent(jobId)}/cancel`, {
        method: 'POST',
      });
      if (res.ok) {
        setStatus('Cancelación solicitada.', 'info');
        await fetchDownloads();
      }
    } catch {
      setStatus('No se pudo cancelar la descarga.', 'error');
    }
  }

  async function clearFinishedDownloads() {
    const serverUrl = normalizeServerUrl(serverUrlInput.value);
    try {
      await fetch(`${serverUrl}/downloads/clear`, { method: 'POST' });
      await fetchDownloads();
    } catch {
      // ignorar si está offline
    }
  }

  async function openConfiguredDirectory() {
    const serverUrl = normalizeServerUrl(serverUrlInput.value);
    const directory = directoryInput.value.trim();

    if (!/^https?:\/\/.+/.test(serverUrl)) {
      setStatus('La URL del servidor debe iniciar con http:// o https://', 'error');
      return;
    }

    saveSettings();
    openDirectoryButton.disabled = true;

    try {
      const res = await fetch(`${serverUrl}/open-directory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directory }),
      });

      const data = await res.json();
      if (!res.ok || data.status === 'Error') {
        setStatus(data.message || 'No se pudo abrir el directorio.', 'error');
        return;
      }

      setStatus(data.message || 'Directorio abierto.', 'success');
    } catch {
      setStatus(`No se pudo conectar con ${serverUrl} para abrir el directorio.`, 'error');
    } finally {
      openDirectoryButton.disabled = false;
    }
  }

  async function checkServerHealth() {
    const serverUrl = normalizeServerUrl(serverUrlInput.value);
    healthBadge.className = 'health-badge checking';
    healthText.textContent = 'Verificando...';

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      const res = await fetch(`${serverUrl}/health`, { signal: controller.signal });
      clearTimeout(timeout);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      if (data.status === 'ok') {
        healthBadge.className = 'health-badge online';
        healthText.textContent = 'Online';
        await fetchDownloads();
        return;
      }
      throw new Error('Unexpected response');
    } catch {
      healthBadge.className = 'health-badge offline';
      healthText.textContent = 'Offline';
    }
  }

  serverUrlInput.addEventListener('change', () => {
    saveSettings();
    checkServerHealth();
  });
  directoryInput.addEventListener('change', saveSettings);
  returnDataCheckbox.addEventListener('change', saveSettings);
  healthBadge.addEventListener('click', checkServerHealth);
  clearDownloadsButton.addEventListener('click', clearFinishedDownloads);
  openDirectoryButton.addEventListener('click', openConfiguredDirectory);

  for (const button of actionButtons) {
    button.addEventListener('click', handleDownloadClick);
  }

  checkServerHealth();
  const pollTimer = setInterval(fetchDownloads, POLL_INTERVAL_MS);
  window.addEventListener('unload', () => clearInterval(pollTimer));

  async function handleDownloadClick(event) {
    const button = event.currentTarget;
    const service = button.dataset.service;
    const onlyVideo = button.dataset.video === 'true';
    const directory = directoryInput.value.trim();
    const returnData = returnDataCheckbox.checked;
    const serverUrl = normalizeServerUrl(serverUrlInput.value);

    if (!/^https?:\/\/.+/.test(serverUrl)) {
      setStatus('La URL del servidor debe iniciar con http:// o https://', 'error');
      return;
    }

    saveSettings();

    const urlFilter =
      service === 'YouTube Music'
        ? '*://music.youtube.com/*'
        : '*://www.youtube.com/*';

    try {
      setButtonsDisabled(true);
      setStatus(`Buscando pestaña de ${service}...`, 'info');

      let tabs = await chrome.tabs.query({
        active: true,
        currentWindow: true,
        url: urlFilter,
      });

      if (tabs.length === 0) {
        tabs = await chrome.tabs.query({ url: urlFilter });
      }

      if (tabs.length === 0) {
        setStatus(`No se encontró ninguna pestaña de ${service} abierta.`, 'error');
        return;
      }

      const youtubeURL = tabs[0].url;
      setStatus('Enviando solicitud al servidor...', 'info');

      const response = await fetch(`${serverUrl}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ youtubeURL, directory, onlyVideo, returnData }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      if (data.status === 'Error') {
        setStatus(data.message || 'El servidor devolvió un error.', 'error');
        return;
      }

      const msg = data.message || 'Descarga iniciada correctamente.';
      setStatus(msg, 'success');
      await fetchDownloads();

      chrome.runtime.sendMessage({
        type: 'notification',
        options: {
          type: 'basic',
          iconUrl: 'logo16.png',
          title: 'Audio & Video Downloader',
          message: msg,
        },
      });
    } catch (error) {
      setStatus(
        `No se pudo conectar con ${serverUrl}. Verifica que el servidor Flask esté activo.`,
        'error'
      );
      console.error('Error al realizar la petición:', error);
    } finally {
      setButtonsDisabled(false);
    }
  }
});

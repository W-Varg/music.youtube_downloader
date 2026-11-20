// popup.js (Manifest V3)
const DEFAULT_SERVER_URL = 'http://127.0.0.1:6001';

document.addEventListener('DOMContentLoaded', async () => {
  const serverUrlInput = document.getElementById('serverUrlInput');
  const directoryInput = document.getElementById('directoryInput');
  const returnDataCheckbox = document.getElementById('returnDataCheckbox');
  const statusMessage = document.getElementById('statusMessage');
  const healthBadge = document.getElementById('healthBadge');
  const healthText = document.getElementById('healthText');
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

  // Guardar cambios automáticamente
  const saveSettings = () => {
    chrome.storage.local.set({
      serverUrl: normalizeServerUrl(serverUrlInput.value),
      directory: directoryInput.value.trim(),
      returnData: returnDataCheckbox.checked,
    });
  };

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

  checkServerHealth();

  for (const button of actionButtons) {
    button.addEventListener('click', handleDownloadClick);
  }

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

      // Priorizar la pestaña activa en la ventana actual si coincide
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

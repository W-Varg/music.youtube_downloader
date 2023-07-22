// popup.js
document.addEventListener('DOMContentLoaded', function () {
  const youtubeMusicButton = document.getElementById('youtubeMusicButton');
  const youtubeButton = document.getElementById('youtubeButton');
  const directoryInput = document.getElementById('directoryInput');

  // Recuperar el valor del directorio del almacenamiento local
  chrome.storage.local.get('directory', function (result) {
    if (result.directory) {
      directoryInput.value = result.directory;
    }
  });

  youtubeMusicButton.addEventListener('click', downloadFromService);
  youtubeButton.addEventListener('click', downloadFromService);

  function downloadFromService(event) {
    const service = event.target.getAttribute('data-service');
    const directory = directoryInput.value
    const urlFilter = service === 'YouTube Music' ? '*://music.youtube.com/*' : '*://www.youtube.com/*';

    chrome.tabs.query({ url: urlFilter }, function (tabs) {
      makeRequest(tabs, directory, service);
    });
  }

  function makeRequest(tabs, directory, service) {
    chrome.storage.local.set({ 'directory': directory });

    if (tabs.length > 0) {
      const youtubeURL = tabs[0].url;

      fetch('http://172.27.39.12:5000/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          youtubeURL,
          directory,
        }),
      })
        .then(response => {
          if (!response.ok) {
            throw new Error('La petición no fue exitosa.');
          }
          return response.json();
        })
        .then(data => {
          const { audioName } = data;
          const audioURL = `http://172.27.39.12:5000/media/${encodeURIComponent(audioName)}`;

          // Enviar mensaje al servicio de fondo para descargar el archivo
          chrome.runtime.sendMessage({
            action: 'downloadAudio',
            audioURL,
            audioName,
          }, function (response) {
            const { downloadId } = response;
            if (downloadId) {
              showAlert('Descarga de audio en progreso...');
            } else {
              showAlert('Error al iniciar la descarga.');
            }
          });
        })
        .catch(() => showAlert('Error al realizar la petición.'));
    } else {
      showAlert(`No se encontró ninguna pestaña de ${service} abierta.`);
    }
  }

  function showAlert(message) {
    alert(message);
  }
});

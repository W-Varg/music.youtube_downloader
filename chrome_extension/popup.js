// popup.js
document.addEventListener('DOMContentLoaded', function () {
  const youtubeMusicButton = document.getElementById('youtubeMusicButton');
  const youtubeButton = document.getElementById('youtubeButton');
  const youtubeVideoButton = document.getElementById('youtubeVideoButton');
  const returnDataCheckbox = document.getElementById('returnDataCheckbox');
  const directoryInput = document.getElementById('directoryInput');

  // Recuperar el valor del directorio y el estado del checkbox del almacenamiento local
  chrome.storage.local.get(['directory', 'returnData'], function (result) {
    if (result.directory) {
      directoryInput.value = result.directory;
    }
    if (result.returnData !== undefined) {
      returnDataCheckbox.checked = result.returnData;
    }
  });

  youtubeMusicButton.addEventListener('click', downloadFromService);
  youtubeButton.addEventListener('click', downloadFromService);
  youtubeVideoButton.addEventListener('click', downloadFromService);

  function downloadFromService(event) {
    const service = event.target.getAttribute('data-service');
    const directory = directoryInput.value
    const urlFilter = service === 'YouTube Music' ? '*://music.youtube.com/*' : '*://www.youtube.com/*';
    const onlyVideo = event.target.getAttribute('data-video') === 'true';
    const returnData = returnDataCheckbox.checked;

    chrome.tabs.query({ url: urlFilter }, function (tabs) {
      makeRequest(tabs, directory, service, onlyVideo, returnData);
    });
  }

  function makeRequest(tabs, directory, service, onlyVideo, returnData) {
    chrome.storage.local.set({ 'directory': directory, 'returnData': returnData });

    if (tabs.length > 0) {
      const youtubeURL = tabs[0].url;

      fetch('http://172.27.39.12:5000/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ youtubeURL, directory, onlyVideo, returnData }),
      })
        .then(response => {
          if (!response.ok) {
            throw new Error('La petición no fue exitosa.');
          }
          return response.json();
        })
        .then(data => {
          const { audioName, message } = data;
          // const audioURL = `http://172.27.39.12:5000/media/${encodeURIComponent(audioName)}`;
          // showAlert(message);
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

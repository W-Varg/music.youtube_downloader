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

  youtubeMusicButton.addEventListener('click', downloadFromYouTubeMusic);
  youtubeButton.addEventListener('click', downloadFromYouTube);

});

function downloadFromYouTubeMusic() {
  const directoryInput = document.getElementById('directoryInput');
  const directory = directoryInput.value ?? '/home/dev/Music';

  chrome.tabs.query({ url: '*://music.youtube.com/*' }, function (tabs) {
    makeRequest(tabs, directory, 'YouTube Music');
  });
}

function downloadFromYouTube() {
  const directoryInput = document.getElementById('directoryInput');
  const directory = directoryInput.value ?? '/home/dev/Music/youtube';

  chrome.tabs.query({ url: '*://youtube.com/*' }, function (tabs) {
    makeRequest(tabs, directory, 'YouTube');
  });
}

function makeRequest(tabs, directory, text) {
  chrome.storage.local.set({ 'directory': directory });

  if (tabs.length > 0) {
    const youtubeURL = tabs[0].url;

    fetch('http://127.0.0.1:5000/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        link: youtubeURL,
        directory: directory,
      }),
    })
      .then(response => {
        if (!response.ok) {
          throw new Error('La petición no fue exitosa.');
        }
        return response.json();
      })
      .then(data => {
        showAlert(data.message || 'Petición completada.');
      })
      .catch(() => {
        showAlert('Error al realizar la petición.');
      });
  } else {
    showAlert(`No se encontró ninguna pestaña de ${text} abierta.`);
  }
}

function showAlert(message) {
  alert(message);
}

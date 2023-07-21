document.addEventListener('DOMContentLoaded', function () {
  const copyButton = document.getElementById('copyButton');
  copyButton.addEventListener('click', performRequestAndShowAlert);
});

function performRequestAndShowAlert() {
  // Buscar la pestaña que contiene "youtube.com" y obtener su URL completa
  chrome.tabs.query({ url: '*://*.youtube.com/*' }, function (tabs) {
    if (tabs.length > 0) {
      const youtubeURL = tabs[0].url;
      const directory = "/home/dev/Music";

      // Realizar la petición al servidor
      fetch('http://127.0.0.1:5000/', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          "link": youtubeURL,
          "directory": directory
        })
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
      showAlert('No se encontró ninguna pestaña de YouTube abierta.');
    }
  });
}


function showAlert(message) {
  alert(message);
}

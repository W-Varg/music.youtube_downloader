// background.js (Manifest V3 Service Worker)
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message) {
    return false;
  }

  if (message.type === 'notification' && message.options) {
    const options = {
      type: 'basic',
      iconUrl: 'logo16.png',
      title: 'Audio & Video Downloader',
      message: '',
      ...message.options,
    };

    chrome.notifications.create('', options, (notificationId) => {
      if (chrome.runtime.lastError) {
        console.warn('Error al crear notificación:', chrome.runtime.lastError.message);
      }
      sendResponse({ notificationId });
    });
    return true;
  }

  if (message.action === 'downloadAudio') {
    const { audioURL, audioName } = message;
    chrome.downloads.download(
      {
        url: audioURL,
        filename: `${audioName}`,
        saveAs: false,
        conflictAction: 'overwrite',
      },
      (downloadId) => {
        if (chrome.runtime.lastError) {
          console.error('Error en descarga:', chrome.runtime.lastError.message);
          sendResponse({ error: chrome.runtime.lastError.message });
          return;
        }
        sendResponse({ downloadId });
      }
    );
    return true;
  }

  return false;
});

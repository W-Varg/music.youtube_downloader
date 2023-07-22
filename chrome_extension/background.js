chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
    if (message?.type === 'notification') {
        chrome.notifications.create('', message.options);
    }

    if (message.action === 'downloadAudio') {
      const { audioURL, audioName, directory } = message;
      chrome.downloads.download({
        url: audioURL,
        filename: `${audioName}`,
        saveAs: false,
        conflictAction: 'overwrite',
      }, function (downloadId) {
        sendResponse({ downloadId });
      });
      return true; // Permite que sendResponse se llame asincrónicamente
    }
  });
  
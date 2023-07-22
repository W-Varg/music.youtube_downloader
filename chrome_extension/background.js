chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'notification') {
        chrome.notifications.create('', message.options);
    }
});
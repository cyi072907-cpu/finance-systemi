function sendNotification(title, body) {
    if (Notification.permission === "granted") {
        new Notification(title, { body });
    }
}

if ("Notification" in window) {
    Notification.requestPermission();
}
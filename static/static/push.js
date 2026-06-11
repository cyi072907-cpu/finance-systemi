if ("Notification" in window) {
    Notification.requestPermission();
}

function push(title, msg) {
    if (Notification.permission === "granted") {
        new Notification(title, {
            body: msg,
            icon: "/static/icon.png"
        });
    }
}

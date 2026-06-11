const CACHE_NAME = "boss-system-v1";

self.addEventListener("install", event => {
    console.log("SW installed");
});

self.addEventListener("fetch", event => {
    event.respondWith(fetch(event.request));
});
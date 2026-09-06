/* Smart Market Watchlist — Web Push service worker */
self.addEventListener("push", (event) => {
  let payload = { title: "Smart Market Watchlist", body: "New attention alert", data: {} };
  try {
    if (event.data) {
      payload = { ...payload, ...event.data.json() };
    }
  } catch (_) {
    /* keep defaults */
  }
  event.waitUntil(
    self.registration.showNotification(payload.title || "Smart Market Watchlist", {
      body: payload.body || "",
      icon: "/icon-192.svg",
      badge: "/icon-192.svg",
      data: payload.data || {},
      tag: (payload.data && payload.data.event_id) || "smw-alert",
      renotify: true,
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = "/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if ("focus" in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});

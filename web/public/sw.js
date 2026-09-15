/* Service Worker — Web Push do acompanhamento de senha (Next). */
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let data = {
    title: "CompuFlow",
    body: "Atualização da sua senha",
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    tag: "senha",
    requireInteraction: false,
    data: { url: "/" },
  };

  try {
    if (event.data) {
      const parsed = event.data.json();
      data = { ...data, ...parsed, data: { ...data.data, ...(parsed.data || {}) } };
    }
  } catch {
    /* ignore */
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || "/icon-192.png",
      badge: data.badge || "/icon-192.png",
      tag: data.tag,
      requireInteraction: Boolean(data.requireInteraction),
      data: data.data,
      vibrate: data.requireInteraction ? [220, 80, 140, 80, 220] : [140, 70, 140],
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ("focus" in client) {
          if ("navigate" in client) client.navigate(url);
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
    }),
  );
});

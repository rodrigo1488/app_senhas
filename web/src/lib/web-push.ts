/** Utilitários Web Push (VAPID) para /acompanhar/[token]. */

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

export async function ensureServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return null;
  return navigator.serviceWorker.register("/sw.js");
}

export async function subscribePush(token: string): Promise<"granted" | "denied" | "unsupported" | "missing-vapid"> {
  if (typeof window === "undefined" || !("Notification" in window) || !("PushManager" in window)) {
    return "unsupported";
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";

  const reg = await ensureServiceWorker();
  if (!reg) return "unsupported";

  const vapidRes = await fetch("/api/vapid-public-key");
  if (!vapidRes.ok) return "missing-vapid";
  const { publicKey } = (await vapidRes.json()) as { publicKey: string };
  if (!publicKey) return "missing-vapid";

  let subscription = await reg.pushManager.getSubscription();
  if (!subscription) {
    subscription = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource,
    });
  }

  await fetch(`/api/registrar_push/${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subscription }),
  });

  return "granted";
}

/** Utilitários Web Push (VAPID) para /acompanhar/[token]. */

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

function sameApplicationServerKey(subscription: PushSubscription, expected: Uint8Array): boolean {
  const current = subscription.options.applicationServerKey;
  if (!current) return false;
  const bytes = new Uint8Array(current);
  return bytes.length === expected.length && bytes.every((value, index) => value === expected[index]);
}

export async function ensureServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return null;
  return navigator.serviceWorker.register("/sw.js");
}

export async function subscribePush(
  token: string,
): Promise<"granted" | "local-only" | "denied" | "unsupported"> {
  if (typeof window === "undefined" || !("Notification" in window) || !("PushManager" in window)) {
    return "unsupported";
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";

  const reg = await ensureServiceWorker();
  if (!reg) return "unsupported";

  const vapidRes = await fetch("/api/vapid-public-key");
  if (!vapidRes.ok) return "local-only";
  const { publicKey } = (await vapidRes.json()) as { publicKey: string };
  if (!publicKey) return "local-only";

  const applicationServerKey = urlBase64ToUint8Array(publicKey);
  let subscription = await reg.pushManager.getSubscription();
  if (subscription && !sameApplicationServerKey(subscription, applicationServerKey)) {
    await subscription.unsubscribe();
    subscription = null;
  }
  if (!subscription) {
    subscription = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: applicationServerKey as BufferSource,
    });
  }

  const response = await fetch(`/api/registrar_push/${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subscription }),
  });
  if (!response.ok) return "local-only";

  return "granted";
}

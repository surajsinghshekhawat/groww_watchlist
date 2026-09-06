"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchPushStatus,
  fetchVapidPublicKey,
  getApiBaseUrl,
  subscribePush,
  unsubscribePush,
} from "@/lib/api";

const EMBEDDED_VAPID =
  process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY?.trim() ||
  "BMNNsPHveefDIMWOWHs8VBHLEu6Y_dBR7t0RfBsJIBnyIWg5j0_A7TpW930ngUzLJ9Q0nOJFZbidiBQ-RkwLM9o";

function urlBase64ToUint8Array(base64String: string): BufferSource {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

export function PushSettings({ token }: { token: string }) {
  const [subscribed, setSubscribed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [publicKey, setPublicKey] = useState(EMBEDDED_VAPID);

  const refresh = useCallback(async () => {
    setChecking(true);
    let key = EMBEDDED_VAPID;
    try {
      const vapid = await fetchVapidPublicKey();
      if (vapid.public_key) key = vapid.public_key;
      setPublicKey(key);
    } catch {
      // Fall back to embedded demo public key — private key still must exist on API to send
      setPublicKey(EMBEDDED_VAPID);
    }
    try {
      const s = await fetchPushStatus(token);
      setSubscribed(s.subscribed);
      if (!s.configured && !key) {
        setError("Push private key missing on API. Check VAPID_* in repo .env and restart uvicorn.");
      } else {
        setError(null);
      }
    } catch {
      setSubscribed(false);
      // Don't block Enable — subscription still talks to API on click
    } finally {
      setChecking(false);
    }
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function enable() {
    setBusy(true);
    setError(null);
    setHint(null);
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        throw new Error("This browser does not support Web Push.");
      }
      if (!window.isSecureContext && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
        throw new Error("Push requires HTTPS (or localhost).");
      }
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        throw new Error("Notification permission was denied.");
      }

      let key = publicKey;
      try {
        const vapid = await fetchVapidPublicKey();
        if (vapid.public_key) key = vapid.public_key;
      } catch {
        /* use embedded / cached key */
      }
      if (!key) throw new Error("No VAPID public key available.");

      const reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
      await navigator.serviceWorker.ready;
      const existing = await reg.pushManager.getSubscription();
      if (existing) await existing.unsubscribe();

      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(key),
      });
      const json = sub.toJSON();
      if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
        throw new Error("Browser returned an incomplete push subscription.");
      }
      await subscribePush(token, {
        endpoint: json.endpoint,
        keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
      });
      setSubscribed(true);
      setHint(
        "Push enabled. Close this tab to test — Chrome/Edge can still show alerts while the browser is running."
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? `${err.message} (API ${getApiBaseUrl()})`
          : `Could not enable push (API ${getApiBaseUrl()})`
      );
    } finally {
      setBusy(false);
      void refresh();
    }
  }

  async function disable() {
    setBusy(true);
    setError(null);
    try {
      const reg = await navigator.serviceWorker.getRegistration();
      const sub = await reg?.pushManager.getSubscription();
      if (sub) {
        try {
          await unsubscribePush(token, sub.endpoint);
        } catch {
          /* still drop local subscription */
        }
        await sub.unsubscribe();
      }
      setSubscribed(false);
      setHint("Push disabled on this device.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not disable push");
    } finally {
      setBusy(false);
      void refresh();
    }
  }

  return (
    <div className="space-y-3 rounded-xl border border-[var(--line)] bg-ink-900/40 p-5">
      <h3 className="text-sm font-semibold text-white">Browser push alerts</h3>
      <p className="text-xs leading-relaxed text-[var(--muted)]">
        Standard <strong className="font-medium text-white">Web Push (VAPID)</strong> — delivers when
        the tab is closed (browser process may still be running). Use Chrome/Edge on{" "}
        <code className="text-mint-400">localhost</code> / <code className="text-mint-400">127.0.0.1</code>.
      </p>
      <p className="text-[10px] text-[var(--muted)]">API: {getApiBaseUrl()}</p>

      {checking ? (
        <p className="text-xs text-[var(--muted)]">Checking push…</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {!subscribed ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void enable()}
              className="rounded-md bg-mint-500/25 px-3 py-1.5 text-xs text-mint-400 disabled:opacity-50"
            >
              {busy ? "Enabling…" : "Enable push on this device"}
            </button>
          ) : (
            <button
              type="button"
              disabled={busy}
              onClick={() => void disable()}
              className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs text-white disabled:opacity-50"
            >
              {busy ? "…" : "Disable push"}
            </button>
          )}
          <span className="self-center text-[10px] uppercase tracking-wide text-[var(--muted)]">
            {subscribed ? "Subscribed" : "Not subscribed"}
          </span>
        </div>
      )}
      {hint ? <p className="text-xs text-mint-400">{hint}</p> : null}
      {error ? <p className="text-xs text-signal-high">{error}</p> : null}
    </div>
  );
}

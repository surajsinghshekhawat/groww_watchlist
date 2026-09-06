"use client";

import { FormEvent, useEffect, useState } from "react";

import { fetchHealth, getApiBaseUrl, login, register } from "@/lib/api";

export function LoginForm({
  onSuccess,
  bootstrapError,
}: {
  onSuccess: (token: string) => void;
  bootstrapError?: string | null;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("DemoPass123!");
  const [displayName, setDisplayName] = useState("Demo Trader");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [apiHint, setApiHint] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await fetchHealth();
        if (!cancelled) setApiHint(null);
      } catch (err) {
        if (!cancelled) {
          setApiHint(
            err instanceof Error
              ? `API unreachable at ${getApiBaseUrl()} — ${err.message}`
              : `API unreachable at ${getApiBaseUrl()}`
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (bootstrapError) setError(bootstrapError);
  }, [bootstrapError]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const trimmedEmail = email.trim();
      const trimmedName = displayName.trim();
      if (!trimmedEmail || !password) {
        throw new Error("Email and password are required.");
      }
      if (mode === "register" && trimmedName.length < 1) {
        throw new Error("Display name is required.");
      }
      if (mode === "register" && password.length < 10) {
        throw new Error("Password must be at least 10 characters.");
      }

      const auth =
        mode === "login"
          ? await login(trimmedEmail, password)
          : await register(trimmedEmail, password, trimmedName);

      const token = auth?.token?.access_token;
      if (!token) {
        throw new Error("Login succeeded but no access token was returned.");
      }
      onSuccess(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auth failed");
      setBusy(false);
    }
    // On success, parent unmounts this form — don't clear busy (avoids flash)
  }

  return (
    <form
      onSubmit={(e) => void onSubmit(e)}
      className="mx-auto max-w-sm space-y-4 rounded-xl border border-[var(--line)] bg-ink-900/50 p-6"
    >
      <div>
        <h2 className="font-display text-3xl text-white">
          {mode === "login" ? "Sign in" : "Create account"}
        </h2>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Demo: demo@example.com / DemoPass123!
        </p>
      </div>

      {apiHint ? (
        <p className="rounded-md border border-signal-high/40 bg-signal-high/10 px-3 py-2 text-xs text-signal-high">
          {apiHint}
        </p>
      ) : null}

      {mode === "register" ? (
        <label className="block text-xs text-[var(--muted)]">
          Display name
          <input
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-ink-950 px-3 py-2 text-sm text-white"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            disabled={busy}
          />
        </label>
      ) : null}
      <label className="block text-xs text-[var(--muted)]">
        Email
        <input
          className="mt-1 w-full rounded-md border border-[var(--line)] bg-ink-950 px-3 py-2 text-sm text-white"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          type="email"
          required
          autoComplete="username"
          disabled={busy}
        />
      </label>
      <label className="block text-xs text-[var(--muted)]">
        Password
        <input
          className="mt-1 w-full rounded-md border border-[var(--line)] bg-ink-950 px-3 py-2 text-sm text-white"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          required
          minLength={mode === "register" ? 10 : 1}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          disabled={busy}
        />
      </label>
      {error ? (
        <p className="rounded-md border border-signal-high/40 bg-signal-high/10 px-3 py-2 text-xs text-signal-high">
          {error}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-md bg-mint-500/25 py-2 text-sm text-mint-400 hover:bg-mint-500/35 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? "Signing in…" : mode === "login" ? "Continue" : "Register"}
      </button>
      <button
        type="button"
        disabled={busy}
        className="w-full text-xs text-[var(--muted)] underline disabled:opacity-50"
        onClick={() => {
          setMode(mode === "login" ? "register" : "login");
          setError(null);
        }}
      >
        {mode === "login" ? "Need an account? Register" : "Have an account? Sign in"}
      </button>
    </form>
  );
}

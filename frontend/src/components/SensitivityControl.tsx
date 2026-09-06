"use client";

import { useEffect, useState } from "react";

import { fetchSettings, updateSensitivity } from "@/lib/api";

export function SensitivityControl({
  token,
  onChanged,
}: {
  token: string;
  onChanged?: () => void;
}) {
  const [value, setValue] = useState("MEDIUM");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void fetchSettings(token)
      .then((s) => setValue(s.sensitivity))
      .catch(() => undefined);
  }, [token]);

  async function onChange(next: string) {
    setBusy(true);
    try {
      const s = await updateSensitivity(token, next);
      setValue(s.sensitivity);
      onChanged?.();
    } finally {
      setBusy(false);
    }
  }

  return (
    <label className="flex items-center gap-2 text-xs text-[var(--muted)]">
      Sensitivity
      <select
        disabled={busy}
        className="rounded-md border border-[var(--line)] bg-ink-950 px-2 py-1 text-white"
        value={value}
        onChange={(e) => void onChange(e.target.value)}
      >
        <option value="LOW">Low (more alerts)</option>
        <option value="MEDIUM">Medium</option>
        <option value="HIGH">High (HIGH only)</option>
      </select>
    </label>
  );
}

"use client";

export function DataConflictBadge({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div
      className="rounded-lg border border-signal-high/40 bg-signal-high/10 p-3 text-xs text-signal-high"
      role="status"
    >
      <p className="font-semibold">Data conflict</p>
      <p className="mt-1 opacity-90">
        Multiple market sources disagree. This event has been downgraded until the
        data is reconciled.
      </p>
    </div>
  );
}

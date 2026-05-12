"use client";

import { useMemo, useState, type FormEvent } from "react";

type DashboardPayload = {
  user_id: string;
  tracker_id: string;
  pet_id: string | null;
  tracker: {
    model_number?: string;
    state?: string;
    charging_state?: string;
    _trackable_object?: string;
  } | null;
  pet: Record<string, unknown> | null;
  hardware: { battery_level?: number; time?: number; hw_status?: string } | null;
  position: {
    latlong?: [number, number];
    time?: number;
    speed?: number | null;
    altitude?: number | null;
    pos_uncertainty?: number | null;
  } | null;
  health: {
    activityDataSyncedAt?: string;
    activity?: { minutesActive?: number; minutesGoal?: number } | null;
    rest?: { minutesRest?: number } | null;
    sleep?: {
      minutesDaySleep?: number;
      minutesNightSleep?: number;
      minutesCalm?: number;
    } | null;
    restingHeartRate?: {
      status?: string;
      bpm?: number;
      dayOffset?: number;
    } | null;
    restingRespiratoryRate?: {
      status?: string;
      rpm?: number;
      dayOffset?: number;
    } | null;
    healthAlerts?: { unseenCount?: number } | null;
  } | null;
  history: {
    date: string;
    ok: boolean;
    data: unknown;
    error: string | null;
  }[];
  sleep_history: {
    date: string;
    ok: boolean;
    data: unknown;
    error: string | null;
  }[];
  errors: Record<string, string>;
};

function formatRelative(unixSeconds: number | undefined): string {
  if (!unixSeconds) return "";
  const diffSeconds = Date.now() / 1000 - unixSeconds;
  if (diffSeconds < 60) return "just now";
  if (diffSeconds < 3600) return `${Math.round(diffSeconds / 60)} min ago`;
  if (diffSeconds < 86400) return `${Math.round(diffSeconds / 3600)} h ago`;
  return `${Math.round(diffSeconds / 86400)} d ago`;
}

function batteryColor(level: number | undefined): string {
  if (level === undefined) return "bg-neutral-200";
  if (level > 50) return "bg-emerald-500";
  if (level > 20) return "bg-amber-500";
  return "bg-red-500";
}

export default function DashboardPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const response = await fetch("/api/tractive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const json = (await response.json()) as DashboardPayload | { error: string };
      if (!response.ok) {
        setError("error" in json ? json.error : `HTTP ${response.status}`);
        return;
      }
      setData(json as DashboardPayload);
    } catch (thrownError) {
      setError(
        thrownError instanceof Error ? thrownError.message : String(thrownError),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl space-y-6 p-6 sm:p-8">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">
          Tractive dashboard
        </h1>
        <span className="text-xs text-neutral-500">
          test rig · stash before merge
        </span>
      </header>

      {!data && (
        <form
          onSubmit={onSubmit}
          className="space-y-3 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm"
        >
          <label className="block">
            <span className="block text-sm font-medium">Tractive email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
              autoComplete="username"
            />
          </label>
          <label className="block">
            <span className="block text-sm font-medium">Password</span>
            <input
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
              autoComplete="current-password"
            />
          </label>
          <button
            type="submit"
            disabled={loading}
            className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
          >
            {loading ? "Fetching…" : "Fetch tracker data"}
          </button>
        </form>
      )}

      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {data && (
        <>
          <PetHero data={data} />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <BatteryCard hardware={data.hardware} />
            <PositionCard position={data.position} />
            <StatusCard tracker={data.tracker} />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <ActivityCard
              health={data.health}
              streak={
                findFirstNumber(data.history[0]?.data, ["current_streak"]) ?? null
              }
            />
            <SleepCard health={data.health} />
            <VitalsCard health={data.health} />
          </div>
          {data.health?.activityDataSyncedAt && (
            <p className="text-right text-xs text-neutral-500">
              Wellness synced{" "}
              {new Date(data.health.activityDataSyncedAt).toLocaleString()}
            </p>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <HistoryCard
              history={data.history}
              title="Activity"
              extract={extractActivity}
              barClass="bg-emerald-500"
              statLabel="active"
            />
            <HistoryCard
              history={data.sleep_history}
              title="Sleep"
              extract={extractSleep}
              barClass="bg-indigo-500"
              statLabel="sleep"
            />
          </div>

          <details className="rounded-xl border border-neutral-200 bg-white p-4">
            <summary className="cursor-pointer text-sm font-semibold">
              Raw per-day responses
            </summary>
            <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs font-semibold text-neutral-600">
                  activity day_overview
                </p>
                <pre className="mt-1 max-h-96 overflow-auto rounded bg-neutral-50 p-2 text-[11px]">
                  {JSON.stringify(data.history, null, 2)}
                </pre>
              </div>
              <div>
                <p className="text-xs font-semibold text-neutral-600">
                  sleep day_overview
                </p>
                <pre className="mt-1 max-h-96 overflow-auto rounded bg-neutral-50 p-2 text-[11px]">
                  {JSON.stringify(data.sleep_history, null, 2)}
                </pre>
              </div>
            </div>
          </details>

          {Object.keys(data.errors).length > 0 && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm">
              <h2 className="font-semibold">Endpoints that failed</h2>
              <ul className="mt-2 space-y-1">
                {Object.entries(data.errors).map(([key, value]) => (
                  <li key={key} className="font-mono text-xs">
                    <span className="font-semibold">{key}</span>: {value}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setShowRaw((current) => !current)}
              className="text-sm text-neutral-600 underline"
            >
              {showRaw ? "Hide" : "Show"} raw response
            </button>
            {showRaw && (
              <pre className="max-h-150 overflow-auto rounded-lg bg-neutral-900 p-4 text-xs text-neutral-100">
                {JSON.stringify(data, null, 2)}
              </pre>
            )}
          </div>

          <button
            type="button"
            onClick={() => {
              setData(null);
              setShowRaw(false);
            }}
            className="text-sm text-neutral-500 underline"
          >
            ← Sign out / fetch different account
          </button>
        </>
      )}
    </main>
  );
}

function pickString(
  object: Record<string, unknown> | null,
  keys: string[],
): string | null {
  if (!object) return null;
  for (const [key, value] of Object.entries(object)) {
    if (keys.includes(key) && typeof value === "string" && value.length > 0)
      return value;
  }
  for (const value of Object.values(object)) {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const nested = pickString(value as Record<string, unknown>, keys);
      if (nested) return nested;
    }
  }
  return null;
}

function pickNumber(
  object: Record<string, unknown> | null,
  keys: string[],
): number | null {
  if (!object) return null;
  for (const [key, value] of Object.entries(object)) {
    if (keys.includes(key) && typeof value === "number") return value;
  }
  for (const value of Object.values(object)) {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const nested = pickNumber(value as Record<string, unknown>, keys);
      if (nested != null) return nested;
    }
  }
  return null;
}

function PetHero({ data }: { data: DashboardPayload }): React.JSX.Element {
  const name = pickString(data.pet, ["pet_name", "name"]) ?? "Unnamed pet";
  const type = pickString(data.pet, ["pet_type", "species", "animal_type"]);
  const gender = pickString(data.pet, ["gender"]);
  const weightGrams = pickNumber(data.pet, ["weight"]);
  const heightMeters = pickNumber(data.pet, ["height"]);
  const birthday = pickNumber(data.pet, ["birthday"]);
  const dailyActiveMinutesGoal = pickNumber(data.pet, [
    "daily_active_minutes_goal",
  ]);

  const [nowSeconds] = useState(() => Math.floor(Date.now() / 1000));
  const ageYears = useMemo(
    () =>
      birthday
        ? Math.floor((nowSeconds - birthday) / (365.25 * 24 * 60 * 60))
        : null,
    [birthday, nowSeconds],
  );
  const weightKilograms = weightGrams ? (weightGrams / 1000).toFixed(1) : null;
  const heightCentimeters = heightMeters ? Math.round(heightMeters * 100) : null;

  return (
    <section className="rounded-xl border border-neutral-200 bg-linear-to-br from-white to-neutral-50 p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <p className="text-xs uppercase tracking-wide text-neutral-500">
            Pet
          </p>
          <h2 className="text-2xl font-semibold">{name}</h2>
          <p className="mt-1 text-sm text-neutral-600">
            {[
              type,
              gender ? (gender === "M" ? "male" : "female") : null,
              ageYears != null ? `${ageYears}y` : null,
              weightKilograms ? `${weightKilograms} kg` : null,
              heightCentimeters ? `${heightCentimeters} cm` : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {dailyActiveMinutesGoal != null && (
            <p className="mt-2 text-xs text-neutral-500">
              Daily activity goal:{" "}
              <span className="font-medium text-neutral-700">
                {dailyActiveMinutesGoal} min
              </span>
            </p>
          )}
        </div>
        <div className="text-right text-xs text-neutral-500">
          <div>
            tracker{" "}
            <span className="font-mono">{data.tracker?.model_number}</span>
          </div>
          <div className="font-mono">{data.tracker_id}</div>
        </div>
      </div>
    </section>
  );
}

function BatteryCard({
  hardware,
}: {
  hardware: DashboardPayload["hardware"];
}): React.JSX.Element {
  const level = hardware?.battery_level;
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-neutral-500">
        Battery
      </p>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-3xl font-semibold">
          {level !== undefined ? `${level}%` : "—"}
        </span>
        {hardware?.hw_status && (
          <span className="text-xs text-neutral-500">{hardware.hw_status}</span>
        )}
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-neutral-100">
        <div
          className={`h-full ${batteryColor(level)}`}
          style={{ width: `${level ?? 0}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-neutral-500">
        Reported {formatRelative(hardware?.time)}
      </p>
    </div>
  );
}

function PositionCard({
  position,
}: {
  position: DashboardPayload["position"];
}): React.JSX.Element {
  const latLong = position?.latlong;
  const mapsUrl = latLong
    ? `https://www.google.com/maps?q=${latLong[0]},${latLong[1]}`
    : null;
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-neutral-500">
        Last position
      </p>
      <div className="mt-2 font-mono text-sm">
        {latLong ? `${latLong[0].toFixed(5)}, ${latLong[1].toFixed(5)}` : "—"}
      </div>
      <p className="text-xs text-neutral-500">
        {position?.pos_uncertainty != null
          ? `±${position.pos_uncertainty} m`
          : "no accuracy reported"}
        {position?.speed != null ? ` · ${position.speed} m/s` : ""}
      </p>
      <p className="mt-2 text-xs text-neutral-500">
        Reported {formatRelative(position?.time)}
      </p>
      {mapsUrl && (
        <a
          href={mapsUrl}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-block text-xs text-blue-600 underline"
        >
          Open in Google Maps →
        </a>
      )}
    </div>
  );
}

function StatusCard({
  tracker,
}: {
  tracker: DashboardPayload["tracker"];
}): React.JSX.Element {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-neutral-500">
        Tracker
      </p>
      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
        <dt className="text-neutral-500">State</dt>
        <dd>{tracker?.state ?? "—"}</dd>
        <dt className="text-neutral-500">Charging</dt>
        <dd>{tracker?.charging_state ?? "—"}</dd>
        <dt className="text-neutral-500">Model</dt>
        <dd>{tracker?.model_number ?? "—"}</dd>
      </dl>
    </div>
  );
}

function formatMinutes(minutes: number | undefined): string {
  if (minutes == null) return "—";
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

function ActivityCard({
  health,
  streak,
}: {
  health: DashboardPayload["health"];
  streak: number | null;
}): React.JSX.Element {
  const minutes = health?.activity?.minutesActive;
  const goal = health?.activity?.minutesGoal;
  const rest = health?.rest?.minutesRest;
  const percent =
    minutes != null && goal && goal > 0
      ? Math.round((minutes / goal) * 100)
      : null;
  const goalMet = percent != null && percent >= 100;
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="font-semibold">Activity (today)</h3>
        {percent != null && (
          <span
            className={`text-xs ${goalMet ? "font-semibold text-emerald-600" : "text-neutral-500"}`}
          >
            {percent}% of goal{goalMet ? " ·" : ""}
          </span>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-3xl font-semibold">{formatMinutes(minutes)}</span>
        <span className="text-sm text-neutral-500">
          active{goal != null ? ` · goal ${formatMinutes(goal)}` : ""}
        </span>
      </div>
      {percent != null && (
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-neutral-100">
          <div
            className="h-full bg-emerald-500"
            style={{ width: `${Math.min(100, percent)}%` }}
          />
        </div>
      )}
      <div className="mt-3 flex justify-between text-xs text-neutral-500">
        {rest != null && <span>Rest: {formatMinutes(rest)}</span>}
        {streak != null && streak > 0 && (
          <span className="font-medium text-neutral-700">
            {streak}-day streak
          </span>
        )}
      </div>
    </div>
  );
}

function SleepCard({
  health,
}: {
  health: DashboardPayload["health"];
}): React.JSX.Element {
  const night = health?.sleep?.minutesNightSleep;
  const day = health?.sleep?.minutesDaySleep;
  const calm = health?.sleep?.minutesCalm;
  const total =
    night != null || day != null ? (night ?? 0) + (day ?? 0) : undefined;
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <h3 className="font-semibold">Sleep (today)</h3>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-3xl font-semibold">{formatMinutes(total)}</span>
        <span className="text-sm text-neutral-500">total</span>
      </div>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-neutral-500">Night</dt>
        <dd>{formatMinutes(night)}</dd>
        <dt className="text-neutral-500">Day</dt>
        <dd>{formatMinutes(day)}</dd>
        {calm != null && (
          <>
            <dt className="text-neutral-500">Calm</dt>
            <dd>{formatMinutes(calm)}</dd>
          </>
        )}
      </dl>
    </div>
  );
}

function findFirstNumber(data: unknown, keys: string[]): number | null {
  if (!data || typeof data !== "object") return null;
  const object = data as Record<string, unknown>;
  for (const key of keys) {
    if (typeof object[key] === "number") return object[key];
  }
  for (const value of Object.values(object)) {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const result = findFirstNumber(value, keys);
      if (result != null) return result;
    }
  }
  return null;
}

function extractActivity(data: unknown): number | null {
  return findFirstNumber(data, [
    "achieved_minutes",
    "minutesActive",
    "minutes_active",
    "active_minutes",
  ]);
}

function extractSleep(data: unknown): number | null {
  const total = findFirstNumber(data, [
    "minutes_sleep",
    "minutesSleep",
    "totalSleep",
    "achieved_minutes",
    "sleep_minutes",
  ]);
  if (total != null) return total;
  const night = findFirstNumber(data, [
    "minutes_night_sleep",
    "minutesNightSleep",
    "night_sleep",
  ]);
  const day = findFirstNumber(data, [
    "minutes_day_sleep",
    "minutesDaySleep",
    "day_sleep",
  ]);
  if (night != null || day != null) return (night ?? 0) + (day ?? 0);
  return null;
}

function HistoryCard({
  history,
  title,
  extract,
  barClass,
  statLabel,
}: {
  history: DashboardPayload["history"];
  title: string;
  extract: (data: unknown) => number | null;
  barClass: string;
  statLabel: string;
}): React.JSX.Element {
  const successfulEntries = history.filter((entry) => entry.ok);
  const failed = history.length - successfulEntries.length;

  const rows = successfulEntries.map((entry) => ({
    date: entry.date,
    minutes: extract(entry.data),
  }));
  const numbers = rows
    .map((row) => row.minutes)
    .filter((value): value is number => value != null);
  const total = numbers.reduce((sum, value) => sum + value, 0);
  const average = numbers.length ? Math.round(total / numbers.length) : null;
  const maximum = numbers.length ? Math.max(...numbers) : null;
  const minimum = numbers.length ? Math.min(...numbers) : null;

  return (
    <section className="rounded-xl border border-neutral-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="font-semibold">
          {title} (past {history.length} days)
        </h3>
        <span className="text-xs text-neutral-500">
          {successfulEntries.length}/{history.length} fetched
          {failed > 0 ? ` · ${failed} failed` : ""}
        </span>
      </div>

      {successfulEntries.length === 0 ? (
        <p className="mt-2 text-sm text-neutral-500">
          No history fetched. See &ldquo;Endpoints that failed&rdquo; below.
        </p>
      ) : numbers.length === 0 ? (
        <p className="mt-2 text-sm text-neutral-500">
          Days fetched but no {statLabel.toLowerCase()} field found in payload.
          See raw below.
        </p>
      ) : (
        <>
          <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
            <Stat
              label={`Avg ${statLabel}`}
              value={formatMinutes(average ?? undefined)}
            />
            <Stat label="Max" value={formatMinutes(maximum ?? undefined)} />
            <Stat label="Min" value={formatMinutes(minimum ?? undefined)} />
          </div>

          <div className="mt-4">
            <div className="flex h-24 items-end gap-1">
              {rows
                .slice()
                .reverse()
                .map((row) => {
                  const heightPx =
                    row.minutes != null && maximum
                      ? Math.max(4, Math.round((row.minutes / maximum) * 96))
                      : 0;
                  return (
                    <div
                      key={row.date}
                      className="flex flex-1 flex-col items-center gap-1"
                      title={`${row.date}: ${formatMinutes(row.minutes ?? undefined)}`}
                    >
                      <div className="flex w-full flex-1 items-end">
                        <div
                          className={`w-full rounded-t ${barClass}`}
                          style={{ height: `${heightPx}px` }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
            <div className="mt-1 flex gap-1 text-[10px] text-neutral-500">
              {rows
                .slice()
                .reverse()
                .map((row) => (
                  <div key={row.date} className="flex-1 text-center">
                    {row.date.slice(5)}
                  </div>
                ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.JSX.Element {
  return (
    <div className="rounded-lg bg-neutral-50 p-2">
      <div className="text-[10px] uppercase tracking-wide text-neutral-500">
        {label}
      </div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}

function VitalsCard({
  health,
}: {
  health: DashboardPayload["health"];
}): React.JSX.Element {
  const restingHeartRate = health?.restingHeartRate;
  const restingRespiratoryRate = health?.restingRespiratoryRate;
  const alerts = health?.healthAlerts?.unseenCount ?? 0;
  const renderVital = (
    label: string,
    vital: { status?: string; bpm?: number; rpm?: number } | null | undefined,
    unit: string,
  ) => {
    const value = vital?.bpm ?? vital?.rpm;
    if (value != null) {
      return (
        <>
          <dt className="text-neutral-500">{label}</dt>
          <dd className="font-medium">
            {value} <span className="text-xs text-neutral-500">{unit}</span>
          </dd>
        </>
      );
    }
    return (
      <>
        <dt className="text-neutral-500">{label}</dt>
        <dd className="text-xs text-neutral-500">
          {vital?.status === "CALCULATING_BASELINE"
            ? "calculating baseline…"
            : (vital?.status ?? "—")}
        </dd>
      </>
    );
  };
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="font-semibold">Vitals</h3>
        {alerts > 0 && (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            {alerts} alert{alerts > 1 ? "s" : ""}
          </span>
        )}
      </div>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        {renderVital("Resting heart rate", restingHeartRate, "bpm")}
        {renderVital("Resting respiratory", restingRespiratoryRate, "rpm")}
      </dl>
    </div>
  );
}

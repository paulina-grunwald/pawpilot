import { NextResponse } from "next/server";

const TRACTIVE_BASE = "https://graph.tractive.com/4";
const ACTIVITY_PROCESSING_SERVICE_BASE = "https://aps-api.tractive.com/api/1";
const TRACTIVE_CLIENT = "5728aa1fc9077f7c32000186";
const USER_AGENT = "pawpilot-test/0.1 (+https://pawpilot.local)";

type AuthResponse = {
  user_id: string;
  client_id: string;
  expires_at: number;
  access_token: string;
};

type TrackerRef = { _id: string; _type: string };

type HardwareReport = {
  _id?: string;
  time?: number;
  battery_level?: number;
  hw_status?: string;
};

type PositionReport = {
  _id?: string;
  time?: number;
  latlong?: [number, number];
  speed?: number | null;
  altitude?: number | null;
  pos_uncertainty?: number | null;
};

type TrackerDetails = {
  _id?: string;
  model_number?: string;
  state?: string;
  charging_state?: string;
  _trackable_object?: string;
};

type TrackableObject = Record<string, unknown> & {
  _id?: string;
  _type?: string;
};

// shape observed from aps-api.tractive.com/api/1/pet/{id}/health/overview
type HealthOverview = {
  petId?: string;
  activityDataSyncedAt?: string;
  activity?: { minutesActive?: number; minutesGoal?: number } | null;
  rest?: { minutesRest?: number } | null;
  sleep?: {
    minutesDaySleep?: number;
    minutesNightSleep?: number;
    minutesCalm?: number;
  } | null;
  bark?: { count?: number } | null;
  scratch?: { count?: number } | null;
  restingHeartRate?: { status?: string; dayOffset?: number; bpm?: number } | null;
  restingRespiratoryRate?: { status?: string; dayOffset?: number; rpm?: number } | null;
  healthAlerts?: { unseenCount?: number } | null;
};

type FetchResult<T> =
  | { ok: true; data: T; path: string }
  | { ok: false; error: string; path: string };

type DayHistoryEntry = {
  date: string; // YYYY-MM-DD
  ok: boolean;
  data: unknown;
  error: string | null;
};

type DashboardPayload = {
  user_id: string;
  tracker_id: string;
  pet_id: string | null;
  tracker: TrackerDetails | null;
  pet: TrackableObject | null;
  hardware: HardwareReport | null;
  position: PositionReport | null;
  health: HealthOverview | null;
  history: DayHistoryEntry[];
  sleep_history: DayHistoryEntry[];
  errors: Record<string, string>;
};

async function tractiveAuth(
  email: string,
  password: string,
): Promise<AuthResponse> {
  const form = new URLSearchParams({
    platform_email: email,
    platform_token: password,
    grant_type: "tractive",
  });
  const response = await fetch(`${TRACTIVE_BASE}/auth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Tractive-Client": TRACTIVE_CLIENT,
      "User-Agent": USER_AGENT,
      Accept: "application/json",
    },
    body: form.toString(),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `auth failed: ${response.status} ${response.statusText} :: ${text.slice(0, 400)}`,
    );
  }
  return (await response.json()) as AuthResponse;
}

async function authedGet<T>(
  baseUrl: string,
  path: string,
  token: string,
  userId: string,
): Promise<FetchResult<T>> {
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      headers: {
        "X-Tractive-Client": TRACTIVE_CLIENT,
        "X-Tractive-User": userId,
        Authorization: `Bearer ${token}`,
        "User-Agent": USER_AGENT,
        Accept: "application/json",
      },
      cache: "no-store",
    });
    if (!response.ok) {
      const text = await response.text();
      return {
        ok: false,
        path,
        error: `${response.status} ${text.slice(0, 200)}`,
      };
    }
    return { ok: true, path, data: (await response.json()) as T };
  } catch (error) {
    return {
      ok: false,
      path,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

export async function POST(request: Request): Promise<NextResponse> {
  let body: { email?: string; password?: string };
  try {
    body = (await request.json()) as { email?: string; password?: string };
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }
  const { email, password } = body;
  if (!email || !password) {
    return NextResponse.json(
      { error: "email and password required" },
      { status: 400 },
    );
  }

  let auth: AuthResponse;
  try {
    auth = await tractiveAuth(email, password);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "auth error" },
      { status: 401 },
    );
  }

  const graph = <T>(path: string) =>
    authedGet<T>(TRACTIVE_BASE, path, auth.access_token, auth.user_id);
  const activityProcessing = <T>(path: string) =>
    authedGet<T>(
      ACTIVITY_PROCESSING_SERVICE_BASE,
      path,
      auth.access_token,
      auth.user_id,
    );

  const trackersResult = await graph<TrackerRef[]>(
    `/user/${auth.user_id}/trackers`,
  );
  if (!trackersResult.ok) {
    return NextResponse.json(
      { error: `trackers fetch failed: ${trackersResult.error}` },
      { status: 502 },
    );
  }
  if (trackersResult.data.length === 0) {
    return NextResponse.json(
      { error: "no trackers on this account" },
      { status: 404 },
    );
  }

  const trackerId = trackersResult.data[0]._id;
  const errors: Record<string, string> = {};

  const [trackerDetails, trackablesList] = await Promise.all([
    graph<TrackerDetails>(`/tracker/${trackerId}`),
    graph<TrackerRef[]>(`/user/${auth.user_id}/trackable_objects`),
  ]);
  if (!trackerDetails.ok) errors.tracker = trackerDetails.error;
  if (!trackablesList.ok) errors.trackables = trackablesList.error;

  const petId: string | null =
    (trackablesList.ok ? (trackablesList.data[0]?._id ?? null) : null) ??
    (trackerDetails.ok
      ? (trackerDetails.data._trackable_object ?? null)
      : null);

  const HISTORY_DAYS = 7;
  const today = new Date();
  const dayDates: Date[] = [];
  for (let dayIndex = 0; dayIndex < HISTORY_DAYS; dayIndex++) {
    const date = new Date(today);
    date.setDate(date.getDate() - dayIndex);
    dayDates.push(date);
  }

  const dayQuery = (date: Date): string =>
    `local_day=${date.getDate()}&local_month=${date.getMonth() + 1}&local_year=${date.getFullYear()}`;
  const isoDay = (date: Date): string =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

  const noPetResult = <T,>(): FetchResult<T> => ({
    ok: false,
    path: "",
    error: "no pet linked to tracker",
  });

  const [hardware, position, pet, health, ...dayResults] = await Promise.all([
    graph<HardwareReport>(`/device_hw_report/${trackerId}`),
    graph<PositionReport>(`/device_pos_report/${trackerId}`),
    petId
      ? graph<TrackableObject>(`/trackable_object/${petId}`)
      : Promise.resolve(noPetResult<TrackableObject>()),
    petId
      ? activityProcessing<HealthOverview>(`/pet/${petId}/health/overview`)
      : Promise.resolve(noPetResult<HealthOverview>()),
    ...dayDates.flatMap((date) =>
      petId
        ? [
            graph<unknown>(
              `/pet/${petId}/activity/day_overview?${dayQuery(date)}`,
            ),
            graph<unknown>(
              `/pet/${petId}/sleep/day_overview?${dayQuery(date)}`,
            ),
          ]
        : [
            Promise.resolve(noPetResult<unknown>()),
            Promise.resolve(noPetResult<unknown>()),
          ],
    ),
  ]);

  if (!hardware.ok) errors.hardware = hardware.error;
  if (!position.ok) errors.position = position.error;
  if (!pet.ok && petId) errors.pet = pet.error;
  if (!health.ok && petId) errors.health = health.error;

  const buildHistory = (offset: 0 | 1): DayHistoryEntry[] =>
    dayDates.map((date, dayIndex) => {
      const dayResult = dayResults[dayIndex * 2 + offset];
      return {
        date: isoDay(date),
        ok: dayResult.ok,
        data: dayResult.ok ? dayResult.data : null,
        error: dayResult.ok ? null : dayResult.error,
      };
    });
  const history = buildHistory(0);
  const sleepHistory = buildHistory(1);

  const firstActivityFail = history.find((entry) => !entry.ok);
  if (firstActivityFail)
    errors.history = `${firstActivityFail.date}: ${firstActivityFail.error}`;
  const firstSleepFail = sleepHistory.find((entry) => !entry.ok);
  if (firstSleepFail)
    errors.sleep_history = `${firstSleepFail.date}: ${firstSleepFail.error}`;

  const payload: DashboardPayload = {
    user_id: auth.user_id,
    tracker_id: trackerId,
    pet_id: petId,
    tracker: trackerDetails.ok ? trackerDetails.data : null,
    pet: pet.ok ? pet.data : null,
    hardware: hardware.ok ? hardware.data : null,
    position: position.ok ? position.data : null,
    health: health.ok ? health.data : null,
    history,
    sleep_history: sleepHistory,
    errors,
  };

  return NextResponse.json(payload);
}

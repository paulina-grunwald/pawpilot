export function formatMonthDay(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  if (!year || !month || !day) return isoDate;
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.toLocaleDateString("en-US", {
    timeZone: "UTC",
    month: "short",
    day: "numeric",
  });
}

/** Two-letter weekday abbreviation for an ISO date, e.g. "2026-07-15" -> "We". */
export function formatWeekday(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  if (!year || !month || !day) return isoDate;
  const date = new Date(Date.UTC(year, month - 1, day));
  return date
    .toLocaleDateString("en-US", { timeZone: "UTC", weekday: "short" })
    .slice(0, 2);
}

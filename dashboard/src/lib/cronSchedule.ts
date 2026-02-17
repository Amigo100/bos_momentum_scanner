/**
 * Cron schedule constants for the Tweet Command Centre.
 *
 * Source of truth: .github/workflows/live_tweet.yml
 * Updated rarely (only when workflow cron entries change).
 */

export interface CronSlot {
  label: string;
  timeET: string;
  days: number[]; // 0=Sun, 1=Mon, ..., 6=Sat
  critical?: boolean;
  source: "live";
}

/** Active cron slots from live_tweet.yml. */
export const LIVE_CRON_SLOTS: CronSlot[] = [
  { label: "Pre-Market", timeET: "07:30", days: [1, 2, 3, 4, 5], source: "live" },
  { label: "Morning", timeET: "10:00", days: [1, 2, 3, 4, 5], source: "live" },
  { label: "Midday", timeET: "12:30", days: [1, 2, 3, 4, 5], source: "live" },
  { label: "Power Hour", timeET: "15:30", days: [1, 2, 3, 4, 5], source: "live", critical: true },
  { label: "After-Hours", timeET: "18:00", days: [1, 2, 3, 4, 5], source: "live" },
  { label: "Weekend AM", timeET: "10:00", days: [0, 6], source: "live" },
  { label: "Weekend PM", timeET: "16:00", days: [0, 6], source: "live" },
];

/** Batch slot-to-time mapping (weekly/daily queues). */
export const BATCH_SLOT_TIMES: Record<number, string> = {
  1: "07:30",
  2: "10:00",
  3: "12:30",
  4: "15:30",
  5: "18:00",
  6: "17:00",
  7: "18:30",
};

/** Get today's cron slots based on ET day-of-week. */
export function getTodayCronSlots(): CronSlot[] {
  const etDayStr = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
  }).format(new Date());
  const dayMap: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  const dayOfWeek = dayMap[etDayStr] ?? 1;
  return LIVE_CRON_SLOTS.filter((slot) => slot.days.includes(dayOfWeek));
}

/** Compute countdown in milliseconds from "now in ET" to target date/time. */
export function computeCountdownMs(dateStr: string, timeET: string): number {
  const etFormatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const nowParts = Object.fromEntries(
    etFormatter.formatToParts(new Date()).map((p) => [p.type, p.value])
  );
  const nowMins = parseInt(nowParts.hour) * 60 + parseInt(nowParts.minute);
  const nowDateStr = `${nowParts.year}-${nowParts.month}-${nowParts.day}`;

  const [tH, tM] = timeET.split(":").map(Number);
  const targetMins = tH * 60 + tM;

  const [nY, nM, nD] = nowDateStr.split("-").map(Number);
  const [tY, tMo, tD] = dateStr.split("-").map(Number);
  const nowDayMs = Date.UTC(nY, nM - 1, nD);
  const targetDayMs = Date.UTC(tY, tMo - 1, tD);
  const dayDiffMs = targetDayMs - nowDayMs;

  return dayDiffMs + (targetMins - nowMins) * 60000;
}

/** Format a countdown in ms to a human-readable string. */
export function formatCountdown(ms: number): string {
  if (Math.abs(ms) < 60000) return "Due now";
  if (ms < 0) {
    const mins = Math.floor(Math.abs(ms) / 60000);
    if (mins < 60) return `Overdue ${mins}m`;
    const hrs = Math.floor(mins / 60);
    return `Overdue ${hrs}h ${mins % 60}m`;
  }
  const mins = Math.floor(ms / 60000);
  if (mins < 60) return `in ${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `in ${hrs}h ${mins % 60}m`;
  const days = Math.floor(hrs / 24);
  return `in ${days}d ${hrs % 24}h`;
}

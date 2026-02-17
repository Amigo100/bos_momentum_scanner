"use client";

import { useState, useMemo, useEffect } from "react";
import type { EnrichedTweet, EnrichedTweetData, FailedTweet, DailyStats, RollingStats, AccountHealth, LiveWorkflowSummary } from "@/lib/data";
import { getTodayCronSlots, computeCountdownMs, formatCountdown, BATCH_SLOT_TIMES, type CronSlot } from "@/lib/cronSchedule";

// ─── Sub-components ───

function StatusBadge({ status }: { status: EnrichedTweet["displayStatus"] }) {
  const styles: Record<string, { bg: string; color: string; label: string }> = {
    posted: { bg: "rgba(45, 212, 191, 0.15)", color: "var(--accent-teal)", label: "posted" },
    upcoming: { bg: "rgba(251, 191, 36, 0.15)", color: "var(--accent-amber)", label: "upcoming" },
    expired: { bg: "rgba(100, 116, 139, 0.15)", color: "var(--text-muted)", label: "expired" },
    skipped: { bg: "rgba(100, 116, 139, 0.15)", color: "var(--text-muted)", label: "skipped" },
    failed: { bg: "rgba(248, 113, 113, 0.15)", color: "var(--accent-red)", label: "failed" },
    abandoned: { bg: "rgba(167, 139, 250, 0.15)", color: "var(--accent-violet)", label: "not posted" },
  };
  const s = styles[status] || styles.expired;
  return (
    <span className="text-xs px-2.5 py-1 rounded-full font-medium" style={{ background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
}

function SourceBadge({ source }: { source: EnrichedTweet["source"] }) {
  const styles: Record<string, { bg: string; color: string; label: string }> = {
    weekly: { bg: "rgba(96, 165, 250, 0.15)", color: "var(--accent-blue)", label: "Weekly" },
    daily: { bg: "rgba(251, 191, 36, 0.15)", color: "var(--accent-amber)", label: "Daily" },
    live: { bg: "rgba(45, 212, 191, 0.15)", color: "var(--accent-teal)", label: "Live" },
  };
  const s = styles[source] || styles.weekly;
  return (
    <span className="text-xs px-2 py-0.5 rounded font-medium inline-flex items-center gap-1" style={{ background: s.bg, color: s.color }}>
      {source === "live" && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
      {s.label}
    </span>
  );
}

function formatFullDate(dateStr: string): string {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}

function TweetCard({ tweet, isNext, countdown }: { tweet: EnrichedTweet; isNext: boolean; countdown?: string }) {
  const isDimmed = tweet.displayStatus === "expired" || tweet.displayStatus === "abandoned";
  const fullDate = formatFullDate(tweet.scheduled_date);

  return (
    <div
      className="stat-card rounded-xl p-4 mb-3"
      style={{
        opacity: isDimmed ? 0.5 : 1,
        borderColor: isNext ? "rgba(45, 212, 191, 0.4)" : undefined,
        boxShadow: isNext ? "0 0 15px rgba(45, 212, 191, 0.1)" : undefined,
      }}
    >
      {/* Next Tweet Banner with Countdown */}
      {isNext && (
        <div className="flex items-center justify-between mb-3 pb-2" style={{ borderBottom: "1px solid rgba(45, 212, 191, 0.2)" }}>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "var(--accent-teal)" }} />
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--accent-teal)" }}>
              Next to Post
            </span>
          </div>
          {countdown && (
            <span className="text-xs font-mono font-medium" style={{ color: "var(--accent-teal)" }}>
              {countdown}
            </span>
          )}
        </div>
      )}

      {/* Countdown for non-next upcoming tweets */}
      {!isNext && tweet.displayStatus === "upcoming" && countdown && (
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-mono" style={{ color: "var(--accent-amber)" }}>
            {countdown}
          </span>
        </div>
      )}

      {/* Top Row: Status + Source + Category + Full Date + Slot Info */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={tweet.displayStatus} />
          <SourceBadge source={tweet.source} />
          <span className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(167, 139, 250, 0.1)", color: "var(--accent-violet)" }}>
            {tweet.category || "\u2014"}
          </span>
          {tweet.chart_required && (
            <span className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(96, 165, 250, 0.1)", color: "var(--accent-blue)" }}>
              Chart
            </span>
          )}
        </div>
        <div className="text-xs text-right whitespace-nowrap" style={{ color: "var(--text-muted)" }}>
          {fullDate && `${fullDate} \u00B7 `}
          {tweet.slot > 0 && `Slot ${tweet.slot} \u00B7 `}
          {tweet.time && `${tweet.time} ET`}
        </div>
      </div>

      {/* Tweet Text */}
      <p className="text-sm leading-relaxed mb-3" style={{ color: "var(--text-secondary)" }}>
        {tweet.text || "\u2014"}
      </p>

      {/* Bottom Row: Metadata */}
      <div className="flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
        <div className="flex items-center gap-3">
          {tweet.mentioned_tickers && tweet.mentioned_tickers.length > 0 && (
            <span>Tickers: {tweet.mentioned_tickers.join(", ")}</span>
          )}
          <span>{tweet.char_count || 0} chars</span>
          {tweet.chart_path && <span>attached</span>}
        </div>
        <div className="flex items-center gap-3">
          {tweet.posted_at && (
            <span>
              Posted:{" "}
              {new Date(tweet.posted_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/New_York" })} ET
            </span>
          )}
          {tweet.tweet_id && (
            <a
              href={`https://x.com/i/status/${tweet.tweet_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:underline"
              style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--accent-blue)" }}
            >
              View on X
            </a>
          )}
        </div>
      </div>

      {/* Error message for failed tweets */}
      {tweet.displayStatus === "failed" && tweet.error && (
        <div
          className="mt-2 p-2 rounded text-xs"
          style={{
            background: "rgba(248, 113, 113, 0.08)",
            border: "1px solid rgba(248, 113, 113, 0.2)",
            color: "var(--accent-red)",
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {tweet.error}
        </div>
      )}
    </div>
  );
}

function FailedTweetCard({ tweet }: { tweet: FailedTweet }) {
  return (
    <div className="stat-card rounded-xl p-4 mb-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="badge-failed text-xs px-2 py-0.5 rounded-full">FAILED</span>
        <span className="text-xs" style={{ color: "var(--accent-violet)" }}>{tweet.category}</span>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {tweet.timestamp ? new Date(tweet.timestamp).toLocaleDateString() : ""}
        </span>
      </div>
      <p className="text-xs mb-2" style={{ color: "var(--text-secondary)" }}>
        {tweet.text?.substring(0, 200)}...
      </p>
      <div className="flex flex-wrap gap-1">
        {tweet.failures?.map((fail, j) => (
          <span
            key={j}
            className="text-xs px-2 py-0.5 rounded"
            style={{ background: "rgba(248, 113, 113, 0.1)", color: "var(--accent-red)", fontFamily: "'JetBrains Mono', monospace" }}
          >
            {fail}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Live ET Clock ───

function LiveClock() {
  const [time, setTime] = useState("");

  useEffect(() => {
    function tick() {
      setTime(
        new Intl.DateTimeFormat("en-US", {
          timeZone: "America/New_York",
          weekday: "short",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }).format(new Date())
      );
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  if (!time) return null;

  return (
    <div className="flex items-center gap-2">
      <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "var(--accent-green)" }} />
      <span className="text-sm font-mono" style={{ color: "var(--text-primary)" }}>
        {time} ET
      </span>
    </div>
  );
}

// ─── Today's Cron Schedule ───

function TodaySchedule({ tweets }: { tweets: EnrichedTweet[] }) {
  const [slots, setSlots] = useState<CronSlot[]>([]);
  const [now, setNow] = useState("");

  useEffect(() => {
    setSlots(getTodayCronSlots());
    function tick() {
      const parts = new Intl.DateTimeFormat("en-US", {
        timeZone: "America/New_York",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).formatToParts(new Date());
      const h = parts.find((p) => p.type === "hour")?.value || "00";
      const m = parts.find((p) => p.type === "minute")?.value || "00";
      setNow(`${h}:${m}`);
    }
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, []);

  if (slots.length === 0) return null;

  const todayET = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());

  function slotStatus(slot: CronSlot): "done" | "next" | "pending" | "missed" {
    const [sH, sM] = slot.timeET.split(":").map(Number);
    const slotMins = sH * 60 + sM;
    const [nH, nM] = now.split(":").map(Number);
    const nowMins = nH * 60 + nM;

    // Check if any tweet posted today matches this slot window (90-min)
    const todayTweets = tweets.filter(
      (t) =>
        t.displayStatus === "posted" &&
        (t.scheduled_date === todayET || (t.posted_at && t.posted_at.startsWith(todayET)))
    );
    const hasPosted = todayTweets.some((t) => {
      const tTime = t.time || t.posted_at?.slice(11, 16) || "";
      if (!tTime) return false;
      const [tH, tM] = tTime.split(":").map(Number);
      const tMins = tH * 60 + tM;
      return Math.abs(tMins - slotMins) <= 90;
    });

    if (hasPosted) return "done";
    if (nowMins < slotMins) {
      // Is this the next pending slot?
      const pendingSlots = slots
        .filter((s) => {
          const [h, m] = s.timeET.split(":").map(Number);
          return h * 60 + m > nowMins;
        })
        .sort((a, b) => a.timeET.localeCompare(b.timeET));
      if (pendingSlots.length > 0 && pendingSlots[0].timeET === slot.timeET) return "next";
      return "pending";
    }
    return "missed";
  }

  return (
    <div className="stat-card rounded-xl p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
          Today&apos;s Cron Schedule
        </div>
        <div className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
          {now} ET
        </div>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {slots.map((slot, i) => {
          const status = slotStatus(slot);
          const colors = {
            done: { bg: "rgba(45, 212, 191, 0.15)", border: "rgba(45, 212, 191, 0.4)", text: "var(--accent-teal)" },
            next: { bg: "rgba(251, 191, 36, 0.15)", border: "rgba(251, 191, 36, 0.4)", text: "var(--accent-amber)" },
            pending: { bg: "rgba(42, 53, 72, 0.3)", border: "var(--border)", text: "var(--text-muted)" },
            missed: { bg: "rgba(248, 113, 113, 0.1)", border: "rgba(248, 113, 113, 0.3)", text: "var(--accent-red)" },
          };
          const c = colors[status];
          return (
            <div
              key={i}
              className={`flex-shrink-0 rounded-lg px-3 py-2 text-center min-w-[90px] ${status === "next" ? "cron-slot-next" : ""}`}
              style={{ background: c.bg, border: `1px solid ${c.border}` }}
            >
              <div className="text-sm font-medium font-mono" style={{ color: c.text }}>
                {slot.timeET}
              </div>
              <div className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>
                {slot.label}
              </div>
              <div className="text-xs mt-1">
                {status === "done" && <span style={{ color: "var(--accent-teal)" }}>Posted</span>}
                {status === "next" && (
                  <span className="font-mono" style={{ color: "var(--accent-amber)" }}>
                    {formatCountdown(computeCountdownMs(todayET, slot.timeET))}
                  </span>
                )}
                {status === "pending" && <span style={{ color: "var(--text-muted)" }}>--</span>}
                {status === "missed" && <span style={{ color: "var(--accent-red)" }}>Missed</span>}
              </div>
              {slot.critical && (
                <div className="text-[9px] mt-0.5 font-medium" style={{ color: "var(--accent-amber)" }}>
                  CRITICAL
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Daily Success Meter ───

function DailySuccessMeter({ dailyStats }: { dailyStats: Record<string, DailyStats> }) {
  const todayET = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
  const today = dailyStats[todayET];

  if (!today || today.scheduled === 0) {
    return (
      <div className="stat-card rounded-xl p-4 mb-6">
        <div className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
          No tweets scheduled for today ({todayET})
        </div>
      </div>
    );
  }

  const total = today.scheduled;
  const postedPct = (today.posted / total) * 100;
  const failedPct = (today.failed / total) * 100;
  const expiredPct = (today.expired / total) * 100;

  return (
    <div className="stat-card rounded-xl p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
          Today&apos;s Progress
        </div>
        <div className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          {today.posted} of {total} posted
          {today.failed > 0 && (
            <span style={{ color: "var(--accent-red)" }}> &middot; {today.failed} failed</span>
          )}
        </div>
      </div>
      <div className="progress-bar-track">
        <div className="progress-bar-fill" style={{ width: `${postedPct}%`, background: "var(--accent-teal)" }} />
        <div className="progress-bar-fill" style={{ width: `${failedPct}%`, background: "var(--accent-red)", marginLeft: "1px" }} />
        <div className="progress-bar-fill" style={{ width: `${expiredPct}%`, background: "var(--text-muted)", marginLeft: "1px" }} />
      </div>
      <div className="flex gap-4 mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
        <span><span style={{ color: "var(--accent-teal)" }}>{"\u25CF"}</span> Posted: {today.posted}</span>
        {today.failed > 0 && <span><span style={{ color: "var(--accent-red)" }}>{"\u25CF"}</span> Failed: {today.failed}</span>}
        <span><span style={{ color: "var(--accent-amber)" }}>{"\u25CF"}</span> Pending: {today.pending}</span>
        {today.expired > 0 && <span><span style={{ color: "var(--text-muted)" }}>{"\u25CF"}</span> Expired: {today.expired}</span>}
      </div>
    </div>
  );
}

// ─── 7-Day Rolling Stats ───

function RollingStatsRow({ stats }: { stats: RollingStats }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="p-3 rounded-lg text-center" style={{ background: "rgba(42, 53, 72, 0.3)" }}>
        <div className="text-lg font-bold font-mono" style={{ color: "var(--accent-teal)" }}>{stats.posted}</div>
        <div className="text-xs" style={{ color: "var(--text-muted)" }}>Posted (7d)</div>
      </div>
      <div className="p-3 rounded-lg text-center" style={{ background: "rgba(42, 53, 72, 0.3)" }}>
        <div className="text-lg font-bold font-mono" style={{ color: stats.failed > 0 ? "var(--accent-red)" : "var(--text-muted)" }}>
          {stats.failed}
        </div>
        <div className="text-xs" style={{ color: "var(--text-muted)" }}>Failed (7d)</div>
      </div>
      <div className="p-3 rounded-lg text-center" style={{ background: "rgba(42, 53, 72, 0.3)" }}>
        <div
          className="text-lg font-bold font-mono"
          style={{ color: stats.successRate >= 90 ? "var(--accent-green)" : stats.successRate >= 70 ? "var(--accent-amber)" : "var(--accent-red)" }}
        >
          {stats.successRate}%
        </div>
        <div className="text-xs" style={{ color: "var(--text-muted)" }}>Success Rate</div>
      </div>
    </div>
  );
}

// ─── Per-tweet countdowns ───

function useCountdowns(tweets: EnrichedTweet[]): Map<string, string> {
  const [countdowns, setCountdowns] = useState<Map<string, string>>(new Map());

  useEffect(() => {
    const upcomingTweets = tweets.filter((t) => t.displayStatus === "upcoming");
    if (upcomingTweets.length === 0) {
      setCountdowns(new Map());
      return;
    }

    function compute(): Map<string, string> {
      const map = new Map<string, string>();
      for (const t of upcomingTweets) {
        const dateStr = t.scheduled_date;
        const timeStr = t.scheduledTimeET || t.time || BATCH_SLOT_TIMES[t.slot] || "12:00";
        if (!dateStr) continue;
        const ms = computeCountdownMs(dateStr, timeStr);
        const key = t.id || t.sortKey;
        map.set(key, formatCountdown(ms));
      }
      return map;
    }

    setCountdowns(compute());
    const id = setInterval(() => setCountdowns(compute()), 30000);
    return () => clearInterval(id);
  }, [tweets]);

  return countdowns;
}

// ─── Account Health Badge ───

function AccountHealthBadge({ health }: { health: AccountHealth }) {
  const dotColors = {
    active: "var(--accent-green)",
    failing: "var(--accent-red)",
    idle: "var(--text-muted)",
  };

  function timeAgo(iso: string | null): string {
    if (!iso) return "";
    const ms = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(ms / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }

  let label: string;
  if (health.status === "active") {
    label = `Last posted ${timeAgo(health.lastPosted)}`;
  } else if (health.status === "failing") {
    const errHint = health.lastError?.includes("401") ? "auth" : health.lastError?.slice(0, 20) || "error";
    label = `${health.consecutiveFailures} failure${health.consecutiveFailures > 1 ? "s" : ""} (${errHint})`;
  } else {
    label = "No posts";
  }

  return (
    <div className="flex items-center gap-1.5 mt-1">
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{
          background: dotColors[health.status],
          boxShadow: health.status === "failing" ? `0 0 4px ${dotColors.failing}` : undefined,
        }}
      />
      <span className="text-[10px]" style={{ color: dotColors[health.status] }}>
        {label}
      </span>
    </div>
  );
}

// ─── Workflow Run Indicator ───

function WorkflowIndicator({ summary }: { summary: LiveWorkflowSummary }) {
  const isSuccess = summary.lastRunStatus === "success";
  const dotColor = summary.lastRunAt
    ? isSuccess ? "var(--accent-green)" : "var(--accent-red)"
    : "var(--text-muted)";

  function formatTime(iso: string | null): string {
    if (!iso) return "never";
    try {
      return new Intl.DateTimeFormat("en-US", {
        timeZone: "America/New_York",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(new Date(iso));
    } catch {
      return iso.slice(11, 16);
    }
  }

  return (
    <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: dotColor }} />
      <span>
        Last cron: <span className="font-mono">{formatTime(summary.lastRunAt)} ET</span>
        {" "}&middot; {summary.lastRunStatus}
        {" "}&middot; {summary.runsToday} run{summary.runsToday !== 1 ? "s" : ""} today
      </span>
    </div>
  );
}

// ─── Main Component ───

export function TweetDashboard({ data, workflowSummary }: { data: EnrichedTweetData; workflowSummary?: LiveWorkflowSummary }) {
  const [activeAccount, setActiveAccount] = useState<"account1" | "account2" | "account3">("account1");
  const [activeTab, setActiveTab] = useState<"upcoming" | "history" | "issues">("upcoming");

  const accountLabels: Record<string, string> = {
    account1: "Account 1 (@AlexSterlingGBR)",
    account2: "Account 2 (@Rdobrogowska)",
    account3: "Account 3",
  };

  const tweets = data.accounts[activeAccount];
  const rollingStats = data.rollingStats[activeAccount];

  // All tweets from all accounts for schedule matching
  const allTweets = useMemo(
    () => [...data.accounts.account1, ...data.accounts.account2, ...data.accounts.account3],
    [data.accounts]
  );

  // Split into upcoming, history (posted only), issues
  const { upcoming, history, issues } = useMemo(() => {
    const upcoming = tweets
      .filter((t) => t.displayStatus === "upcoming")
      .sort((a, b) => a.sortKey.localeCompare(b.sortKey));

    const history = tweets
      .filter((t) => t.displayStatus === "posted")
      .sort((a, b) => b.sortKey.localeCompare(a.sortKey));

    const issues = tweets
      .filter((t) => ["failed", "abandoned", "expired", "skipped"].includes(t.displayStatus))
      .sort((a, b) => b.sortKey.localeCompare(a.sortKey));

    return { upcoming, history, issues };
  }, [tweets]);

  const displayedTweets = activeTab === "upcoming" ? upcoming : activeTab === "history" ? history : issues;

  // Per-tweet countdowns for upcoming tweets
  const countdowns = useCountdowns(tweets);

  // Find next tweet for this account
  const accountNextTweet = useMemo(() => {
    const up = tweets
      .filter((t) => t.displayStatus === "upcoming")
      .sort((a, b) => a.sortKey.localeCompare(b.sortKey));
    return up.length > 0 ? up[0] : null;
  }, [tweets]);
  const nextTweetId = accountNextTweet?.id;

  // Group by date
  const groupedByDate = useMemo(() => {
    const groups: Record<string, EnrichedTweet[]> = {};
    for (const t of displayedTweets) {
      const dateKey = t.scheduled_date || t.timestamp?.slice(0, 10) || "Unknown";
      if (!groups[dateKey]) groups[dateKey] = [];
      groups[dateKey].push(t);
    }
    for (const key of Object.keys(groups)) {
      groups[key].sort((a, b) =>
        activeTab === "upcoming" ? a.sortKey.localeCompare(b.sortKey) : b.sortKey.localeCompare(a.sortKey)
      );
    }
    return groups;
  }, [displayedTweets, activeTab]);

  const sortedDates = Object.keys(groupedByDate).sort(
    activeTab === "upcoming" ? (a, b) => a.localeCompare(b) : (a, b) => b.localeCompare(a)
  );

  // Today in ET for "(Today)" badge
  const todayET = useMemo(() => {
    try {
      return new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
    } catch {
      return new Date().toISOString().slice(0, 10);
    }
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header with Live Clock */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
            Tweet Command Centre
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {data.stats.posted} posted
            {data.stats.upcoming > 0 && <> &middot; {data.stats.upcoming} upcoming</>}
            {data.stats.failed > 0 && (
              <span style={{ color: "var(--accent-red)" }}> &middot; {data.stats.failed} failed</span>
            )}
            {data.stats.abandoned > 0 && (
              <span style={{ color: "var(--accent-violet)" }}> &middot; {data.stats.abandoned} not posted</span>
            )}
            {data.stats.expired > 0 && <> &middot; {data.stats.expired} expired</>}
            {" "}&middot; {data.stats.total} total
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <LiveClock />
          {workflowSummary && <WorkflowIndicator summary={workflowSummary} />}
        </div>
      </div>

      {/* Today's Cron Schedule */}
      <TodaySchedule tweets={allTweets} />

      {/* Daily Success Meter */}
      <DailySuccessMeter dailyStats={data.dailyStats} />

      {/* Account Tabs */}
      <div className="flex gap-1 mb-4 border-b" style={{ borderColor: "var(--border)" }}>
        {(["account1", "account2", "account3"] as const).map((acct) => {
          const count = data.accounts[acct].length;
          const rolling = data.rollingStats[acct];
          const isActive = activeAccount === acct;
          return (
            <button
              key={acct}
              onClick={() => setActiveAccount(acct)}
              className={`px-4 py-3 text-sm font-medium transition-all ${isActive ? "tab-active" : "tab-inactive"}`}
            >
              <div className="flex items-center gap-1">
                {accountLabels[acct]}
                <span className="text-xs opacity-70">
                  ({count})
                  {rolling && rolling.total > 0 && (
                    <span className="ml-1" style={{ color: rolling.successRate >= 90 ? "var(--accent-green)" : rolling.successRate >= 70 ? "var(--accent-amber)" : "var(--accent-red)" }}>
                      {rolling.successRate}%
                    </span>
                  )}
                </span>
              </div>
              {data.accountHealth[acct] && <AccountHealthBadge health={data.accountHealth[acct]} />}
            </button>
          );
        })}
      </div>

      {/* 7-Day Rolling Stats for Active Account */}
      {rollingStats && rollingStats.total > 0 && (
        <div className="mb-6">
          <RollingStatsRow stats={rollingStats} />
        </div>
      )}

      {/* Upcoming / History / Issues Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab("upcoming")}
          className="text-xs px-4 py-2 rounded-lg font-medium transition-all"
          style={{
            background: activeTab === "upcoming" ? "rgba(251, 191, 36, 0.15)" : "rgba(42, 53, 72, 0.5)",
            color: activeTab === "upcoming" ? "var(--accent-amber)" : "var(--text-muted)",
            border: activeTab === "upcoming" ? "1px solid rgba(251, 191, 36, 0.3)" : "1px solid transparent",
          }}
        >
          Upcoming ({upcoming.length})
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className="text-xs px-4 py-2 rounded-lg font-medium transition-all"
          style={{
            background: activeTab === "history" ? "rgba(45, 212, 191, 0.15)" : "rgba(42, 53, 72, 0.5)",
            color: activeTab === "history" ? "var(--accent-teal)" : "var(--text-muted)",
            border: activeTab === "history" ? "1px solid rgba(45, 212, 191, 0.3)" : "1px solid transparent",
          }}
        >
          History ({history.length})
        </button>
        <button
          onClick={() => setActiveTab("issues")}
          className="text-xs px-4 py-2 rounded-lg font-medium transition-all"
          style={{
            background: activeTab === "issues" ? "rgba(248, 113, 113, 0.15)" : "rgba(42, 53, 72, 0.5)",
            color: activeTab === "issues" ? "var(--accent-red)" : "var(--text-muted)",
            border: activeTab === "issues" ? "1px solid rgba(248, 113, 113, 0.3)" : "1px solid transparent",
          }}
        >
          Issues ({issues.length + data.failed.length})
        </button>
        <span className="text-xs self-center ml-2" style={{ color: "var(--text-muted)" }}>
          {displayedTweets.length} tweets
        </span>
      </div>

      {/* Next Tweet Highlight (only on upcoming tab, per-account) */}
      {activeTab === "upcoming" && accountNextTweet && (
        <div className="mb-6">
          <TweetCard
            tweet={accountNextTweet}
            isNext={true}
            countdown={countdowns.get(accountNextTweet.id || accountNextTweet.sortKey)}
          />
        </div>
      )}

      {/* Timeline by Date */}
      {sortedDates.length === 0 && activeTab !== "issues" && (
        <div className="stat-card rounded-xl p-8 text-center">
          <p style={{ color: "var(--text-muted)" }}>
            {activeTab === "upcoming" ? "No upcoming tweets scheduled." : "No tweet history yet."}
          </p>
        </div>
      )}

      {sortedDates.map((dateKey) => {
        const dayTweets = groupedByDate[dateKey];
        const isToday = dateKey === todayET;
        const dateLabel =
          dateKey !== "Unknown"
            ? new Date(dateKey + "T12:00:00").toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })
            : "Unknown Date";

        return (
          <div key={dateKey} className="mb-8">
            <h3
              className="text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-2"
              style={{ color: "var(--text-muted)" }}
            >
              <span className="w-8 h-px" style={{ background: "var(--border)" }} />
              {dateLabel}
              {isToday && (
                <span
                  className="text-xs px-2 py-0.5 rounded-full font-medium normal-case"
                  style={{ background: "rgba(45, 212, 191, 0.15)", color: "var(--accent-teal)" }}
                >
                  Today
                </span>
              )}
              <span className="font-normal">({dayTweets.length} tweets)</span>
              <span className="flex-1 h-px" style={{ background: "var(--border)" }} />
            </h3>
            {dayTweets.map((t, i) => (
              <TweetCard
                key={`${dateKey}-${i}-${t.id || t.sortKey}`}
                tweet={t}
                isNext={activeTab === "upcoming" && t.id === nextTweetId && t.id !== undefined && t.id !== ""}
                countdown={countdowns.get(t.id || t.sortKey)}
              />
            ))}
          </div>
        );
      })}

      {/* Validation Failures (shown in issues tab) */}
      {activeTab === "issues" && data.failed.length > 0 && (
        <div className="mt-4">
          <h3
            className="text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-2"
            style={{ color: "var(--accent-red)" }}
          >
            <span className="w-8 h-px" style={{ background: "rgba(248, 113, 113, 0.3)" }} />
            Validation Failures ({data.failed.length})
            <span className="flex-1 h-px" style={{ background: "rgba(248, 113, 113, 0.3)" }} />
          </h3>
          {data.failed.slice(0, 10).map((f, i) => (
            <FailedTweetCard key={`fail-${i}`} tweet={f} />
          ))}
        </div>
      )}

      {/* Empty state for issues tab */}
      {activeTab === "issues" && issues.length === 0 && data.failed.length === 0 && (
        <div className="stat-card rounded-xl p-8 text-center">
          <p style={{ color: "var(--text-muted)" }}>No issues found. All tweets are healthy.</p>
        </div>
      )}
    </div>
  );
}

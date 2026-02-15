"use client";

import { useState, useMemo, useEffect } from "react";
import type { EnrichedTweet, EnrichedTweetData, FailedTweet, DailyStats, RollingStats } from "@/lib/data";

// ─── Sub-components ───

function StatusBadge({ status }: { status: EnrichedTweet["displayStatus"] }) {
  const styles: Record<string, { bg: string; color: string }> = {
    posted: { bg: "rgba(45, 212, 191, 0.15)", color: "var(--accent-teal)" },
    upcoming: { bg: "rgba(251, 191, 36, 0.15)", color: "var(--accent-amber)" },
    expired: { bg: "rgba(100, 116, 139, 0.15)", color: "var(--text-muted)" },
    skipped: { bg: "rgba(100, 116, 139, 0.15)", color: "var(--text-muted)" },
    failed: { bg: "rgba(248, 113, 113, 0.15)", color: "var(--accent-red)" },
  };
  const s = styles[status] || styles.expired;
  return (
    <span className="text-xs px-2.5 py-1 rounded-full font-medium" style={{ background: s.bg, color: s.color }}>
      {status}
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
  const isExpired = tweet.displayStatus === "expired";
  const fullDate = formatFullDate(tweet.scheduled_date);

  return (
    <div
      className="stat-card rounded-xl p-4 mb-3"
      style={{
        opacity: isExpired ? 0.5 : 1,
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
              {new Date(tweet.posted_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
            </span>
          )}
          {tweet.tweet_id && (
            <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>ID: {tweet.tweet_id.slice(-8)}</span>
          )}
        </div>
      </div>
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

// ─── Daily Success Meter ───

function DailySuccessMeter({ dailyStats }: { dailyStats: Record<string, DailyStats> }) {
  // Get today in ET
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
            <span style={{ color: "var(--accent-red)" }}> \u00B7 {today.failed} failed</span>
          )}
        </div>
      </div>
      <div className="progress-bar-track">
        <div className="progress-bar-fill" style={{ width: `${postedPct}%`, background: "var(--accent-teal)" }} />
        <div className="progress-bar-fill" style={{ width: `${failedPct}%`, background: "var(--accent-red)", marginLeft: "1px" }} />
        <div className="progress-bar-fill" style={{ width: `${expiredPct}%`, background: "var(--text-muted)", marginLeft: "1px" }} />
      </div>
      <div className="flex gap-4 mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
        <span><span style={{ color: "var(--accent-teal)" }}>\u25CF</span> Posted: {today.posted}</span>
        {today.failed > 0 && <span><span style={{ color: "var(--accent-red)" }}>\u25CF</span> Failed: {today.failed}</span>}
        <span><span style={{ color: "var(--accent-amber)" }}>\u25CF</span> Pending: {today.pending}</span>
        {today.expired > 0 && <span><span style={{ color: "var(--text-muted)" }}>\u25CF</span> Expired: {today.expired}</span>}
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

// ─── Countdown helper ───

function useCountdown(nextTweet: EnrichedTweet | null): string {
  const [countdown, setCountdown] = useState("");

  useEffect(() => {
    if (!nextTweet) return;

    function compute() {
      if (!nextTweet) return "";
      const dateStr = nextTweet.scheduled_date || "";
      const timeStr = nextTweet.time || "12:00";
      if (!dateStr) return "";

      // Get current time in ET via Intl formatter (no Date parsing to avoid UTC issues)
      const etFormatter = new Intl.DateTimeFormat("en-US", {
        timeZone: "America/New_York",
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
        hour12: false,
      });
      const nowParts = Object.fromEntries(
        etFormatter.formatToParts(new Date()).map(p => [p.type, p.value])
      );
      const nowMins = parseInt(nowParts.hour) * 60 + parseInt(nowParts.minute);
      const nowDateStr = `${nowParts.year}-${nowParts.month}-${nowParts.day}`;

      const [tH, tM] = timeStr.split(":").map(Number);
      const targetMins = tH * 60 + tM;

      // Calculate day offset using pure date string math (no Date constructor)
      // Parse YYYY-MM-DD strings to days-since-epoch to get day difference
      const [nY, nM, nD] = nowDateStr.split("-").map(Number);
      const [tY, tMo, tD] = dateStr.split("-").map(Number);
      // Use Date.UTC to get reliable day diff (UTC midnight — no TZ offset ambiguity)
      const nowDayMs = Date.UTC(nY, nM - 1, nD);
      const targetDayMs = Date.UTC(tY, tMo - 1, tD);
      const dayDiffMs = targetDayMs - nowDayMs;
      const diffMs = dayDiffMs + (targetMins - nowMins) * 60000;
      if (Math.abs(diffMs) < 60000) return "Due now";
      if (diffMs < 0) {
        const mins = Math.floor(Math.abs(diffMs) / 60000);
        if (mins < 60) return `Overdue ${mins}m`;
        const hrs = Math.floor(mins / 60);
        return `Overdue ${hrs}h ${mins % 60}m`;
      }
      const mins = Math.floor(diffMs / 60000);
      if (mins < 60) return `in ${mins}m`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return `in ${hrs}h ${mins % 60}m`;
      const days = Math.floor(hrs / 24);
      return `in ${days}d ${hrs % 24}h`;
    }

    setCountdown(compute());
    const id = setInterval(() => setCountdown(compute()), 30000);
    return () => clearInterval(id);
  }, [nextTweet]);

  return countdown;
}

// ─── Main Component ───

export function TweetDashboard({ data }: { data: EnrichedTweetData }) {
  const [activeAccount, setActiveAccount] = useState<"account1" | "account2" | "account3">("account1");
  const [activeTab, setActiveTab] = useState<"upcoming" | "history">("upcoming");
  const accountNextTweet = data.nextTweetByAccount[activeAccount];
  const countdown = useCountdown(accountNextTweet);

  const accountLabels: Record<string, string> = {
    account1: "Account 1 (@AlexSterlingGBR)",
    account2: "Account 2 (@Rdobrogowska)",
    account3: "Account 3",
  };

  const tweets = data.accounts[activeAccount];
  const rollingStats = data.rollingStats[activeAccount];

  // Split into upcoming and history
  const { upcoming, history } = useMemo(() => {
    const upcoming = tweets
      .filter((t) => t.displayStatus === "upcoming")
      .sort((a, b) => a.sortKey.localeCompare(b.sortKey)); // chronological: next first

    const history = tweets
      .filter((t) => t.displayStatus !== "upcoming")
      .sort((a, b) => b.sortKey.localeCompare(a.sortKey)); // reverse-chron: most recent first

    return { upcoming, history };
  }, [tweets]);

  const displayedTweets = activeTab === "upcoming" ? upcoming : history;

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

  const nextTweetId = accountNextTweet?.id;

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
            {data.stats.posted} posted \u00B7 {data.stats.upcoming} upcoming \u00B7 {data.stats.expired} expired \u00B7 {data.stats.total} total
          </p>
        </div>
        <LiveClock />
      </div>

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
              {accountLabels[acct]}
              <span className="ml-2 text-xs opacity-70">
                ({count})
                {rolling && rolling.total > 0 && (
                  <span className="ml-1" style={{ color: rolling.successRate >= 90 ? "var(--accent-green)" : rolling.successRate >= 70 ? "var(--accent-amber)" : "var(--accent-red)" }}>
                    {rolling.successRate}%
                  </span>
                )}
              </span>
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

      {/* Upcoming / History Tabs */}
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
        <span className="text-xs self-center ml-2" style={{ color: "var(--text-muted)" }}>
          {displayedTweets.length} tweets
        </span>
      </div>

      {/* Next Tweet Highlight (only on upcoming tab, per-account) */}
      {activeTab === "upcoming" && accountNextTweet && (
        <div className="mb-6">
          <TweetCard tweet={accountNextTweet} isNext={true} countdown={countdown} />
        </div>
      )}

      {/* Timeline by Date */}
      {sortedDates.length === 0 && (
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
                countdown={activeTab === "upcoming" && t.id === nextTweetId && t.id !== undefined && t.id !== "" ? countdown : undefined}
              />
            ))}
          </div>
        );
      })}

      {/* Validation Failures (always visible at bottom) */}
      {data.failed.length > 0 && (
        <div className="mt-10">
          <h2
            className="text-sm font-semibold uppercase tracking-wider mb-4 flex items-center gap-2"
            style={{ color: "var(--accent-red)" }}
          >
            <span className="w-8 h-px" style={{ background: "rgba(248, 113, 113, 0.3)" }} />
            Validation Failures ({data.failed.length})
          </h2>
          {data.failed.slice(0, 10).map((f, i) => (
            <FailedTweetCard key={`fail-${i}`} tweet={f} />
          ))}
        </div>
      )}
    </div>
  );
}

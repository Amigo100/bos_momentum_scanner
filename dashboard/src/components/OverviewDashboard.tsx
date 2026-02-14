"use client";

import { useState } from "react";
import type {
  SystemHealth,
  WorkflowHealth,
  RollingStats,
  DailyStats,
  SignalsData,
  EquityPoint,
} from "@/lib/data";

interface OverviewProps {
  health: SystemHealth;
  tweetStats: { posted: number; upcoming: number; expired: number; total: number };
  rollingStats: Record<string, RollingStats>;
  dailyStats: Record<string, DailyStats>;
  failedTweetCount: number;
  signals: SignalsData | null;
  openPositions: number;
  closedPositions: number;
  latestEquity: EquityPoint | null;
  substackContent: {
    newsletters: number;
    posts: number;
    notes: number;
    currentWeekPosts: number;
  };
  systemLog: string;
}

export function OverviewDashboard({
  health,
  tweetStats,
  rollingStats,
  failedTweetCount,
  signals,
  openPositions,
  closedPositions,
  latestEquity,
  substackContent,
  systemLog,
}: OverviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyLog = async () => {
    try {
      await navigator.clipboard.writeText(systemLog);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = systemLog;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
            System Overview
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Operational command centre
            {health.lastUpdated && (
              <> &middot; Last workflow {new Date(health.lastUpdated).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</>
            )}
          </p>
        </div>
        <button
          onClick={handleCopyLog}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 cursor-pointer"
          style={{
            background: copied ? "rgba(45, 212, 191, 0.15)" : "rgba(42, 53, 72, 0.5)",
            color: copied ? "var(--accent-teal)" : "var(--text-muted)",
            border: `1px solid ${copied ? "rgba(45, 212, 191, 0.3)" : "var(--border)"}`,
          }}
        >
          {copied ? (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
              Copied!
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
              Copy Full Log
            </>
          )}
        </button>
      </div>

      {/* System Health Banner */}
      <SystemHealthBanner health={health} />

      {/* Workflow Health Grid */}
      <div className="mb-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
          Workflow Health
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {health.workflows.map((w) => (
            <WorkflowCard key={w.workflow} workflow={w} />
          ))}
        </div>
      </div>

      {/* Tweet Pipeline Summary */}
      <TweetPipelineSummary
        stats={tweetStats}
        rollingStats={rollingStats}
        failedCount={failedTweetCount}
      />

      {/* Scanner & Content Summary */}
      <ScannerContentSummary
        signals={signals}
        openPositions={openPositions}
        closedPositions={closedPositions}
        latestEquity={latestEquity}
        substackContent={substackContent}
      />
    </div>
  );
}

// ─── Sub-components ───

function SystemHealthBanner({ health }: { health: SystemHealth }) {
  const styles: Record<string, { bg: string; border: string; color: string }> = {
    operational: {
      bg: "rgba(45, 212, 191, 0.08)",
      border: "rgba(45, 212, 191, 0.3)",
      color: "var(--accent-teal)",
    },
    degraded: {
      bg: "rgba(251, 191, 36, 0.08)",
      border: "rgba(251, 191, 36, 0.3)",
      color: "var(--accent-amber)",
    },
    failing: {
      bg: "rgba(248, 113, 113, 0.08)",
      border: "rgba(248, 113, 113, 0.3)",
      color: "var(--accent-red)",
    },
    unknown: {
      bg: "rgba(100, 116, 139, 0.08)",
      border: "rgba(100, 116, 139, 0.3)",
      color: "var(--text-muted)",
    },
  };
  const s = styles[health.overall] || styles.unknown;

  return (
    <div
      className="rounded-xl p-5 mb-8 flex items-center gap-4"
      style={{ background: s.bg, border: `1px solid ${s.border}` }}
    >
      <div
        className={`w-3 h-3 rounded-full flex-shrink-0 ${health.overall === "operational" ? "animate-pulse" : ""}`}
        style={{ background: s.color }}
      />
      <div>
        <span className="text-lg font-semibold" style={{ color: s.color }}>
          {health.message}
        </span>
        {health.overall === "failing" && (
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Check GitHub Settings &gt; Billing &amp; Plans to resolve spending limit issues
          </p>
        )}
        {health.overall === "unknown" && (
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Workflow status data will appear after workflows run successfully
          </p>
        )}
      </div>
    </div>
  );
}

function WorkflowCard({ workflow: w }: { workflow: WorkflowHealth }) {
  const statusColors: Record<string, string> = {
    healthy: "var(--accent-teal)",
    degraded: "var(--accent-amber)",
    failing: "var(--accent-red)",
    unknown: "var(--text-muted)",
  };

  const statusBg: Record<string, string> = {
    healthy: "rgba(45, 212, 191, 0.15)",
    degraded: "rgba(251, 191, 36, 0.15)",
    failing: "rgba(248, 113, 113, 0.15)",
    unknown: "rgba(100, 116, 139, 0.15)",
  };

  const color = statusColors[w.status] || statusColors.unknown;
  const bg = statusBg[w.status] || statusBg.unknown;

  const lastRunTime = w.lastRun
    ? new Date(w.lastRun.completed_at).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Never";

  return (
    <div className="stat-card rounded-xl p-5" style={{ borderLeft: `3px solid ${color}` }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          {w.displayName}
        </span>
        <span
          className="text-xs px-2.5 py-1 rounded-full font-medium"
          style={{ background: bg, color }}
        >
          {w.status}
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-xs">
          <span style={{ color: "var(--text-muted)" }}>Last run</span>
          <span style={{ color: "var(--text-secondary)" }}>{lastRunTime}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span style={{ color: "var(--text-muted)" }}>Last status</span>
          <span
            style={{
              color:
                w.lastRun?.status === "success"
                  ? "var(--accent-green)"
                  : w.lastRun?.status === "failure"
                    ? "var(--accent-red)"
                    : "var(--text-muted)",
            }}
          >
            {w.lastRun?.status || "N/A"}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span style={{ color: "var(--text-muted)" }}>7-day success</span>
          <span style={{ color: "var(--text-secondary)" }}>
            {w.successesLast7Days}/{w.runsLast7Days}
          </span>
        </div>
        {w.expectedPerWeek > 0 && (
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Expected/week</span>
            <span
              style={{
                color:
                  w.runsLast7Days >= w.expectedPerWeek * 0.7
                    ? "var(--accent-green)"
                    : "var(--accent-red)",
              }}
            >
              {w.runsLast7Days}/{w.expectedPerWeek}
            </span>
          </div>
        )}
        <div className="flex justify-between text-xs">
          <span style={{ color: "var(--text-muted)" }}>Streak</span>
          <span
            style={{
              color:
                w.currentStreak > 0
                  ? "var(--accent-green)"
                  : w.currentStreak < 0
                    ? "var(--accent-red)"
                    : "var(--text-muted)",
            }}
          >
            {w.currentStreak > 0
              ? `${w.currentStreak} wins`
              : w.currentStreak < 0
                ? `${Math.abs(w.currentStreak)} fails`
                : "N/A"}
          </span>
        </div>

        {/* Success rate bar */}
        <div className="mt-2">
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${w.successRate}%`, background: color }}
            />
          </div>
          <div className="text-xs text-right mt-1" style={{ color: "var(--text-muted)" }}>
            {w.successRate}%
          </div>
        </div>
      </div>

      {w.lastRun?.error && (
        <div
          className="mt-3 text-xs p-2 rounded"
          style={{ background: "rgba(248, 113, 113, 0.08)", color: "var(--accent-red)" }}
        >
          {w.lastRun.error}
        </div>
      )}
    </div>
  );
}

function TweetPipelineSummary({
  stats,
  rollingStats,
  failedCount,
}: {
  stats: { posted: number; upcoming: number; expired: number; total: number };
  rollingStats: Record<string, RollingStats>;
  failedCount: number;
}) {
  return (
    <div className="stat-card rounded-xl p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-sm font-semibold uppercase tracking-wider"
          style={{ color: "var(--text-muted)" }}
        >
          Tweet Pipeline
        </h2>
        <a href="/tweets" className="text-xs font-medium" style={{ color: "var(--accent-teal)" }}>
          View Details &rarr;
        </a>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <MiniStat label="Total" value={stats.total} />
        <MiniStat label="Posted" value={stats.posted} color="var(--accent-teal)" />
        <MiniStat label="Upcoming" value={stats.upcoming} color="var(--accent-amber)" />
        <MiniStat
          label="Failed"
          value={failedCount}
          color={failedCount > 0 ? "var(--accent-red)" : "var(--text-muted)"}
        />
      </div>
      <div className="grid grid-cols-3 gap-3">
        {Object.values(rollingStats).map((rs) => (
          <div
            key={rs.account}
            className="p-3 rounded-lg"
            style={{ background: "rgba(42, 53, 72, 0.3)" }}
          >
            <div className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>
              {rs.account}
            </div>
            <div className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              {rs.posted}/{rs.total}
            </div>
            <div
              className="text-xs"
              style={{
                color:
                  rs.successRate >= 80
                    ? "var(--accent-green)"
                    : rs.successRate >= 50
                      ? "var(--accent-amber)"
                      : "var(--accent-red)",
              }}
            >
              {rs.successRate}% success (7-day)
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScannerContentSummary({
  signals,
  openPositions,
  closedPositions,
  latestEquity,
  substackContent,
}: {
  signals: SignalsData | null;
  openPositions: number;
  closedPositions: number;
  latestEquity: EquityPoint | null;
  substackContent: {
    newsletters: number;
    posts: number;
    notes: number;
    currentWeekPosts: number;
  };
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
      {/* Scanner Summary */}
      <div className="stat-card rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Scanner
          </h3>
          <a href="/scanner" className="text-xs" style={{ color: "var(--accent-teal)" }}>
            View &rarr;
          </a>
        </div>
        {signals ? (
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--text-muted)" }}>Last scan</span>
              <span style={{ color: "var(--text-secondary)" }}>
                {signals.timestamp ? signals.timestamp.slice(0, 16) : "N/A"}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--text-muted)" }}>Buy signals</span>
              <span style={{ color: "var(--accent-teal)" }}>
                {signals.buy_signals?.length || 0}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--text-muted)" }}>Exit signals</span>
              <span style={{ color: "var(--accent-red)" }}>
                {signals.sell_signals?.length || 0}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span style={{ color: "var(--text-muted)" }}>Active themes</span>
              <span style={{ color: "var(--text-secondary)" }}>
                {signals.themes?.length || 0}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            No scan data available
          </p>
        )}
      </div>

      {/* Portfolio Snapshot */}
      <div className="stat-card rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Portfolio
          </h3>
          <a href="/" className="text-xs" style={{ color: "var(--accent-teal)" }}>
            View &rarr;
          </a>
        </div>
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Open positions</span>
            <span style={{ color: "var(--text-secondary)" }}>{openPositions}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Closed</span>
            <span style={{ color: "var(--text-secondary)" }}>{closedPositions}</span>
          </div>
          {latestEquity && (
            <>
              <div className="flex justify-between text-xs">
                <span style={{ color: "var(--text-muted)" }}>Return</span>
                <span
                  style={{
                    color:
                      latestEquity.total_return_pct > 0
                        ? "var(--accent-green)"
                        : "var(--accent-red)",
                  }}
                >
                  {latestEquity.total_return_pct > 0 ? "+" : ""}
                  {latestEquity.total_return_pct.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span style={{ color: "var(--text-muted)" }}>Alpha vs SPY</span>
                <span
                  style={{
                    color:
                      latestEquity.alpha_pct > 0
                        ? "var(--accent-teal)"
                        : "var(--accent-red)",
                  }}
                >
                  {latestEquity.alpha_pct > 0 ? "+" : ""}
                  {latestEquity.alpha_pct.toFixed(1)}%
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Substack Content */}
      <div className="stat-card rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Substack
          </h3>
          <a href="/substack" className="text-xs" style={{ color: "var(--accent-teal)" }}>
            View &rarr;
          </a>
        </div>
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Newsletters</span>
            <span style={{ color: "var(--text-secondary)" }}>
              {substackContent.newsletters}
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Posts (total)</span>
            <span style={{ color: "var(--text-secondary)" }}>{substackContent.posts}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>This week</span>
            <span
              style={{
                color:
                  substackContent.currentWeekPosts > 0
                    ? "var(--accent-teal)"
                    : "var(--text-muted)",
              }}
            >
              {substackContent.currentWeekPosts} posts
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>Notes</span>
            <span style={{ color: "var(--text-secondary)" }}>{substackContent.notes}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div>
      <div className="text-xs" style={{ color: "var(--text-muted)" }}>
        {label}
      </div>
      <div className="text-xl font-bold" style={{ color: color || "var(--text-primary)" }}>
        {value}
      </div>
    </div>
  );
}

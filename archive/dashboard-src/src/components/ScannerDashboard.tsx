"use client";

import { useState, useCallback } from "react";
import type { SignalsData, Signal, ThemeData, WeekSummary, HistoricalWinner } from "@/lib/data";

// ─── Client-safe weekToDateRange (same logic as server version) ───

function weekToDateRange(isoWeek: string): string {
  const parts = isoWeek.split("-W");
  if (parts.length !== 2) return isoWeek;
  const year = parseInt(parts[0]);
  const weekNum = parseInt(parts[1]);
  if (isNaN(year) || isNaN(weekNum)) return isoWeek;

  const jan4 = new Date(year, 0, 4);
  const dayOfWeek = jan4.getDay() || 7;
  const monday = new Date(jan4);
  monday.setDate(jan4.getDate() - dayOfWeek + 1 + (weekNum - 1) * 7);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);

  const fmt = (d: Date) =>
    d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return `${fmt(monday)} \u2013 ${fmt(sunday)}`;
}

// ─── Sub-components ───

function ClassBadge({ classification }: { classification: string }) {
  const cls =
    classification === "PRIME"
      ? "theme-prime"
      : classification === "INVESTABLE"
        ? "theme-investable"
        : classification === "SELECTIVE"
          ? "theme-selective"
          : "theme-avoid";
  return <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${cls}`}>{classification}</span>;
}

function ScoreBar({ score, max = 10 }: { score: number; max?: number }) {
  const pct = Math.min((score / max) * 100, 100);
  const color =
    score >= 7.5 ? "var(--accent-teal)" : score >= 6 ? "var(--accent-blue)" : score >= 4.5 ? "var(--accent-amber)" : "var(--accent-red)";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full" style={{ background: "rgba(42, 53, 72, 0.5)" }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-mono" style={{ color, minWidth: 32 }}>
        {score.toFixed(1)}
      </span>
    </div>
  );
}

function DecisionBadge({ decision }: { decision: string }) {
  const d = (decision || "").toUpperCase();
  let bg = "rgba(100, 116, 139, 0.15)";
  let color = "var(--text-muted)";

  if (d === "TRADE" || d === "PASS") {
    bg = "rgba(45, 212, 191, 0.15)";
    color = "var(--accent-teal)";
  } else if (d === "CONSIDER" || d === "CAUTION") {
    bg = "rgba(251, 191, 36, 0.15)";
    color = "var(--accent-amber)";
  } else if (d === "FAIL" || d === "SKIP") {
    bg = "rgba(248, 113, 113, 0.15)";
    color = "var(--accent-red)";
  }

  return (
    <span className="text-xs px-2 py-1 rounded-full font-medium" style={{ background: bg, color }}>
      {decision || "N/A"}
    </span>
  );
}

function RedFlagBadge({ level }: { level?: string }) {
  if (!level) return null;
  const bg =
    level === "CLEAN" ? "rgba(45, 212, 191, 0.1)" : level === "MINOR" ? "rgba(251, 191, 36, 0.1)" : "rgba(248, 113, 113, 0.1)";
  const color =
    level === "CLEAN" ? "var(--accent-teal)" : level === "MINOR" ? "var(--accent-amber)" : "var(--accent-red)";
  return (
    <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: bg, color }}>
      {level}
    </span>
  );
}

// ─── Format-Aware Funnel ───

function ScanFunnel({ stats }: { stats: Record<string, number> }) {
  // Detect format from stats keys
  const isSterlingGrid = stats.price_under_cap !== undefined || stats.hma_slope_rising !== undefined;
  const isLegacy = stats.beta_gte_1_5 !== undefined || stats.beta_gte_2_0 !== undefined || stats.weekly_bos_up !== undefined;

  let steps: { label: string; value: number | undefined; icon: string }[];

  if (isSterlingGrid) {
    steps = [
      { label: "Universe", value: stats.tickers_loaded, icon: "\uD83C\uDF10" },
      { label: "Price Cap", value: stats.price_under_cap, icon: "\uD83D\uDCB0" },
      { label: "HMA Rising", value: stats.hma_slope_rising, icon: "\uD83D\uDCC8" },
      { label: "RSI > 50", value: stats.rsi_above_50, icon: "\u26A1" },
      { label: "MACD Cross", value: stats.macd_cross_up, icon: "\uD83D\uDD04" },
      { label: "UC Rising", value: stats.uc_rising_above, icon: "\uD83C\uDFE6" },
      { label: "Theme OK", value: stats.theme_confirmed, icon: "\uD83C\uDFAF" },
      { label: "Final PASS", value: stats.final_trade, icon: "\u2705" },
    ];
  } else if (isLegacy) {
    steps = [
      { label: "Universe", value: stats.tickers_loaded, icon: "\uD83C\uDF10" },
      { label: "High Beta", value: stats.beta_gte_1_5 ?? stats.beta_gte_2_0, icon: "\uD83D\uDCC8" },
      { label: "BoS Up", value: stats.weekly_bos_up, icon: "\u26A1" },
      { label: "Technical", value: stats.technical_signals, icon: "\uD83D\uDD27" },
      { label: "Theme OK", value: stats.theme_confirmed, icon: "\uD83C\uDFAF" },
      { label: "Final PASS", value: stats.final_trade, icon: "\u2705" },
    ];
  } else {
    // Fallback: show whatever keys we have
    steps = [
      { label: "Universe", value: stats.tickers_loaded, icon: "\uD83C\uDF10" },
      { label: "Technical", value: stats.technical_signals, icon: "\uD83D\uDD27" },
      { label: "Theme OK", value: stats.theme_confirmed, icon: "\uD83C\uDFAF" },
      { label: "Final PASS", value: stats.final_trade, icon: "\u2705" },
    ];
  }

  const colClass = steps.length <= 5 ? "grid-cols-2 md:grid-cols-3 lg:grid-cols-5" :
    steps.length <= 6 ? "grid-cols-2 md:grid-cols-3 lg:grid-cols-6" :
    "grid-cols-2 md:grid-cols-4 lg:grid-cols-8";

  return (
    <div className="stat-card rounded-xl p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
          Screening Funnel
        </h2>
        <span className="text-xs px-2 py-0.5 rounded-full" style={{
          background: isSterlingGrid ? "rgba(45, 212, 191, 0.1)" : "rgba(167, 139, 250, 0.1)",
          color: isSterlingGrid ? "var(--accent-teal)" : "var(--accent-violet)",
        }}>
          {isSterlingGrid ? "Sterling Grid" : isLegacy ? "Legacy Format" : "Unknown Format"}
        </span>
      </div>
      <div className={`grid ${colClass} gap-3`}>
        {steps.map((step, i) => (
          <div key={i} className="text-center p-3 rounded-lg" style={{ background: "rgba(42, 53, 72, 0.3)" }}>
            <div className="text-lg mb-1">{step.icon}</div>
            <div className="text-lg font-bold" style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--text-primary)" }}>
              {step.value ?? "\u2014"}
            </div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>
              {step.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Expandable Signal Card ───

function SignalCard({ signal, isExpanded, onToggle }: { signal: Signal; isExpanded: boolean; onToggle: () => void }) {
  return (
    <div
      className="stat-card rounded-xl overflow-hidden mb-3 cursor-pointer"
      onClick={onToggle}
    >
      {/* Collapsed View */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold" style={{ color: "var(--text-primary)", fontFamily: "'JetBrains Mono', monospace" }}>
              ${signal.symbol}
            </span>
            <span className="text-xs font-mono" style={{ color: "var(--text-secondary)" }}>
              ${signal.price?.toFixed(2)}
            </span>
            <DecisionBadge decision={signal.final_decision} />
            {signal.conviction > 0 && (
              <span className="text-xs" style={{ color: "var(--accent-amber)" }}>
                Conv: {signal.conviction}
              </span>
            )}
            <RedFlagBadge level={signal.red_flag_level} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>{signal.theme}</span>
            <span className="text-xs" style={{ color: "var(--text-muted)", transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
              &#9660;
            </span>
          </div>
        </div>
      </div>

      {/* Expanded View */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t" style={{ borderColor: "var(--border)" }} onClick={(e) => e.stopPropagation()}>
          <div className="grid md:grid-cols-2 gap-4 pt-4">
            {/* Left: Details */}
            <div className="space-y-3">
              {signal.theme_score > 0 && (
                <div>
                  <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>Theme Score</span>
                  <ScoreBar score={signal.theme_score} />
                </div>
              )}
              {signal.theme_verdict && (
                <div className="text-xs">
                  <span style={{ color: "var(--text-muted)" }}>Theme Fit: </span>
                  <span style={{ color: "var(--text-primary)" }}>{signal.theme_verdict}</span>
                </div>
              )}
              {signal.tier && (
                <div className="text-xs">
                  <span style={{ color: "var(--text-muted)" }}>Tier: </span>
                  <span style={{ color: "var(--text-primary)" }}>{signal.tier}</span>
                </div>
              )}
              {signal.beta > 0 && (
                <div className="text-xs">
                  <span style={{ color: "var(--text-muted)" }}>Beta: </span>
                  <span style={{ color: "var(--text-primary)", fontFamily: "'JetBrains Mono', monospace" }}>{signal.beta.toFixed(2)}</span>
                </div>
              )}
              {signal.banker !== undefined && signal.banker > 0 && (
                <div className="text-xs">
                  <span style={{ color: "var(--text-muted)" }}>Banker: </span>
                  <span style={{ color: "var(--text-primary)", fontFamily: "'JetBrains Mono', monospace" }}>{signal.banker.toFixed(1)}</span>
                </div>
              )}
              {signal.return_20d !== undefined && signal.return_20d !== 0 && (
                <div className="text-xs">
                  <span style={{ color: "var(--text-muted)" }}>20d Return: </span>
                  <span className={signal.return_20d > 0 ? "pnl-positive" : "pnl-negative"} style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                    {signal.return_20d > 0 ? "+" : ""}{signal.return_20d.toFixed(1)}%
                  </span>
                </div>
              )}
              {signal.action && (
                <div className="text-xs">
                  <span style={{ color: "var(--text-muted)" }}>Action: </span>
                  <span style={{ color: "var(--accent-teal)" }}>{signal.action}</span>
                </div>
              )}
            </div>

            {/* Right: Factors */}
            <div className="space-y-3">
              {signal.bullish_factors && signal.bullish_factors.length > 0 && (
                <div>
                  <div className="text-xs font-medium mb-1" style={{ color: "var(--accent-green)" }}>Bullish Factors</div>
                  {signal.bullish_factors.map((f, i) => (
                    <div key={i} className="text-xs mb-0.5" style={{ color: "var(--text-secondary)" }}>&bull; {f}</div>
                  ))}
                </div>
              )}
              {signal.risk_factors && signal.risk_factors.length > 0 && (
                <div>
                  <div className="text-xs font-medium mb-1" style={{ color: "var(--accent-red)" }}>Risk Factors</div>
                  {signal.risk_factors.map((f, i) => (
                    <div key={i} className="text-xs mb-0.5" style={{ color: "var(--text-secondary)" }}>&bull; {f}</div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Reasoning */}
          {signal.reasoning && (
            <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(42, 53, 72, 0.5)" }}>
              <div className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>Reasoning</div>
              <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>{signal.reasoning}</p>
            </div>
          )}

          {/* DD Fields */}
          {(signal.dd_verdict || signal.dd_key_catalyst) && (
            <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(42, 53, 72, 0.5)" }}>
              <div className="text-xs font-medium mb-2" style={{ color: "var(--accent-violet)" }}>Deep Due Diligence</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {signal.dd_verdict && (
                  <div>
                    <span style={{ color: "var(--text-muted)" }}>Verdict: </span>
                    <span style={{ color: "var(--text-primary)" }}>{signal.dd_verdict}</span>
                  </div>
                )}
                {signal.dd_conviction !== undefined && (
                  <div>
                    <span style={{ color: "var(--text-muted)" }}>DD Conviction: </span>
                    <span style={{ color: "var(--accent-amber)" }}>{signal.dd_conviction}/10</span>
                  </div>
                )}
                {signal.dd_position_size && (
                  <div>
                    <span style={{ color: "var(--text-muted)" }}>Size: </span>
                    <span style={{ color: "var(--text-primary)" }}>{signal.dd_position_size}</span>
                  </div>
                )}
                {signal.dd_key_catalyst && (
                  <div className="col-span-2">
                    <span style={{ color: "var(--text-muted)" }}>Key Catalyst: </span>
                    <span style={{ color: "var(--text-primary)" }}>{signal.dd_key_catalyst}</span>
                  </div>
                )}
                {signal.dd_fatal_flaw && (
                  <div className="col-span-2">
                    <span style={{ color: "var(--text-muted)" }}>Fatal Flaw: </span>
                    <span style={{ color: "var(--accent-red)" }}>{signal.dd_fatal_flaw}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Catalyst Summary */}
          {signal.catalyst_summary && (
            <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(42, 53, 72, 0.5)" }}>
              <div className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>Catalyst</div>
              <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{signal.catalyst_summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Signal Section ───

function SignalSection({
  title,
  signals,
  color,
  expandedSignal,
  setExpandedSignal,
}: {
  title: string;
  signals: Signal[];
  color: string;
  expandedSignal: string | null;
  setExpandedSignal: (s: string | null) => void;
}) {
  if (!signals || signals.length === 0) return null;

  return (
    <div className="mb-8">
      <h3 className="text-sm font-semibold uppercase tracking-wider mb-3 flex items-center gap-2" style={{ color }}>
        <span className="w-2 h-2 rounded-full" style={{ background: color }} />
        {title} ({signals.length})
      </h3>
      {signals.map((s) => (
        <SignalCard
          key={s.symbol}
          signal={s}
          isExpanded={expandedSignal === s.symbol}
          onToggle={() => setExpandedSignal(expandedSignal === s.symbol ? null : s.symbol)}
        />
      ))}
    </div>
  );
}

// ─── Themes Section ───

function ThemesSection({ themes }: { themes: ThemeData[] }) {
  if (!themes || themes.length === 0) return null;

  return (
    <div className="stat-card rounded-xl overflow-hidden mb-8">
      <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
        <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
          Investment Themes
        </h2>
      </div>
      <div className="p-4 space-y-4">
        {themes
          .sort((a, b) => (b.composite_score || 0) - (a.composite_score || 0))
          .map((theme, i) => (
            <div key={i} className="p-4 rounded-lg" style={{ background: "rgba(42, 53, 72, 0.2)" }}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                    {theme.name}
                  </span>
                  <ClassBadge classification={theme.classification} />
                  {theme.theme_type && (
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>{theme.theme_type}</span>
                  )}
                </div>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Rank #{theme.rank}
                </span>
              </div>
              <ScoreBar score={theme.composite_score || 0} />

              {/* Sub-scores */}
              {(theme.catalyst_score || theme.momentum_score) && (
                <div className="flex gap-4 mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                  {theme.catalyst_score !== undefined && <span>Catalyst: {theme.catalyst_score}/10</span>}
                  {theme.momentum_score !== undefined && <span>Momentum: {theme.momentum_score}/10</span>}
                  {theme.crowding_score !== undefined && <span>Crowding: {theme.crowding_score}/10</span>}
                  {theme.runway_score !== undefined && <span>Runway: {theme.runway_score}/10</span>}
                </div>
              )}

              {theme.thesis_summary && (
                <p className="text-xs mt-2 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {theme.thesis_summary.substring(0, 250)}
                  {theme.thesis_summary.length > 250 ? "..." : ""}
                </p>
              )}
              {theme.key_catalysts && theme.key_catalysts.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {theme.key_catalysts.slice(0, 4).map((cat, j) => (
                    <span key={j} className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(45, 212, 191, 0.08)", color: "var(--accent-teal)" }}>
                      {cat}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}

// ─── Historical Winners ───

function WinnersTable({ winners, label }: { winners: HistoricalWinner[]; label: string }) {
  if (!winners || winners.length === 0) return null;

  return (
    <div className="stat-card rounded-xl overflow-hidden mb-8">
      <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
        <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--accent-green)" }}>
          {label} ({winners.length})
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Entry</th>
              <th>Current</th>
              <th>P&L</th>
              <th>Signal Date</th>
              <th>Theme</th>
            </tr>
          </thead>
          <tbody>
            {winners.map((w, i) => (
              <tr key={i}>
                <td><span className="font-semibold" style={{ color: "var(--text-primary)" }}>${w.ticker}</span></td>
                <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>${w.entry_price?.toFixed(2)}</td>
                <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>${w.current_price?.toFixed(2)}</td>
                <td>
                  <span className={w.pnl_pct > 0 ? "pnl-positive" : "pnl-negative"} style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                    {w.pnl_pct > 0 ? "+" : ""}{w.pnl_pct.toFixed(1)}%
                  </span>
                </td>
                <td className="text-xs">{w.signal_date}</td>
                <td className="text-xs">{w.theme}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Main Component ───

interface ScannerDashboardProps {
  initialSignals: SignalsData | null;
  weeks: WeekSummary[];
  currentWeek: string;
}

export function ScannerDashboard({ initialSignals, weeks, currentWeek }: ScannerDashboardProps) {
  const [selectedWeek, setSelectedWeek] = useState<string>("current");
  const [signals, setSignals] = useState<SignalsData | null>(initialSignals);
  const [loading, setLoading] = useState(false);
  const [expandedSignal, setExpandedSignal] = useState<string | null>(null);

  const loadWeek = useCallback(async (week: string) => {
    if (week === "current") {
      setSignals(initialSignals);
      setSelectedWeek("current");
      setExpandedSignal(null);
      return;
    }

    setLoading(true);
    setExpandedSignal(null);
    try {
      const resp = await fetch(`/api/signals?week=${week}`);
      const data = await resp.json();
      setSignals(data.signals);
      setSelectedWeek(week);
    } catch {
      console.error("Failed to load week signals");
    } finally {
      setLoading(false);
    }
  }, [initialSignals]);

  // Build signal sections from the data
  const passSignals = signals?.pass_signals && signals.pass_signals.length > 0
    ? signals.pass_signals
    : (signals?.buy_signals || []).filter((s) => {
        const d = (s.final_decision || "").toUpperCase();
        return d === "TRADE" || d === "PASS";
      });

  const considerSignals = signals?.consider_signals && signals.consider_signals.length > 0
    ? signals.consider_signals
    : (signals?.buy_signals || []).filter((s) => {
        const d = (s.final_decision || "").toUpperCase();
        return d === "CONSIDER" || d === "CAUTION";
      });

  const assessedSignals = (signals?.assessed_signals || []).filter((s) => {
    const d = (s.final_decision || "").toUpperCase();
    return d === "FAIL" || d === "SKIP";
  });

  const exitSignals = signals?.sell_signals || [];

  if (!initialSignals && weeks.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-4" style={{ color: "var(--text-primary)" }}>Scanner Output</h1>
        <div className="stat-card rounded-xl p-8 text-center">
          <p style={{ color: "var(--text-muted)" }}>No scanner data found. Run the weekly scan to populate this view.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
          Scanner Output
        </h1>
        {signals && (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {selectedWeek === "current" ? "Current" : selectedWeek} \u00B7 {signals.timestamp} \u00B7{" "}
            {signals.stats?.tickers_loaded || 0} scanned \u00B7{" "}
            {passSignals.length} PASS \u00B7 {considerSignals.length} CONSIDER \u00B7{" "}
            {exitSignals.length} exits
          </p>
        )}
      </div>

      {/* Week Selector */}
      <div className="mb-8 overflow-x-auto pb-2">
        <div className="flex gap-2">
          <button
            className={`week-pill ${selectedWeek === "current" ? "week-pill-active" : ""}`}
            onClick={() => loadWeek("current")}
          >
            Current ({currentWeek})
          </button>
          {weeks.map((w) => {
            const isCurrent = w.week === currentWeek;
            const isSelected = selectedWeek === w.week;
            const dateRange = weekToDateRange(w.week);
            const weekNum = w.week.split("-")[1];
            return (
              <button
                key={w.week}
                className={`week-pill ${isSelected ? "week-pill-active" : ""} ${!w.hasSignals ? "week-pill-dimmed" : ""}`}
                onClick={() => w.hasSignals && loadWeek(w.week)}
                disabled={!w.hasSignals}
              >
                {weekNum}: {dateRange}
                {isCurrent && " (Current)"}
              </button>
            );
          })}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="stat-card rounded-xl p-8 text-center mb-8">
          <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading week data...</div>
        </div>
      )}

      {/* Scanner Content */}
      {signals && !loading && (
        <>
          {/* Screening Funnel */}
          <ScanFunnel stats={signals.stats || {}} />

          {/* Signal Sections */}
          <SignalSection
            title="PASS Signals"
            signals={passSignals}
            color="var(--accent-teal)"
            expandedSignal={expandedSignal}
            setExpandedSignal={setExpandedSignal}
          />
          <SignalSection
            title="CONSIDER Signals"
            signals={considerSignals}
            color="var(--accent-amber)"
            expandedSignal={expandedSignal}
            setExpandedSignal={setExpandedSignal}
          />
          <SignalSection
            title="Assessed / Failed"
            signals={assessedSignals}
            color="var(--text-muted)"
            expandedSignal={expandedSignal}
            setExpandedSignal={setExpandedSignal}
          />

          {/* Exit Signals */}
          {exitSignals.length > 0 && (
            <div className="stat-card rounded-xl overflow-hidden mb-8">
              <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
                <h2 className="text-sm font-semibold uppercase tracking-wider flex items-center gap-2" style={{ color: "var(--accent-violet)" }}>
                  <span className="w-2 h-2 rounded-full" style={{ background: "var(--accent-violet)" }} />
                  Exit Signals ({exitSignals.length})
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Ticker</th>
                      <th>Reason</th>
                      <th>Price</th>
                      <th>P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exitSignals.map((s, i) => (
                      <tr key={i}>
                        <td><span className="font-semibold" style={{ color: "var(--text-primary)" }}>${s.symbol}</span></td>
                        <td className="text-xs">{s.reason}</td>
                        <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                          {s.price ? `$${s.price.toFixed(2)}` : "\u2014"}
                        </td>
                        <td>
                          {s.pnl_pct !== undefined && (
                            <span className={s.pnl_pct > 0 ? "pnl-positive" : "pnl-negative"} style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                              {s.pnl_pct > 0 ? "+" : ""}{s.pnl_pct.toFixed(1)}%
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Themes */}
          <ThemesSection themes={signals.themes || []} />

          {/* Historical Winners */}
          {signals.historical_winners && signals.historical_winners.length > 0 && (
            <WinnersTable winners={signals.historical_winners} label="Historical Winners" />
          )}
          {signals.big_wins && signals.big_wins.length > 0 && (
            <WinnersTable winners={signals.big_wins} label="Big Wins" />
          )}

          {/* Entry/Exit Criteria (if present) */}
          {(signals.entry_criteria || signals.exit_criteria) && (
            <div className="stat-card rounded-xl p-6 mb-8">
              <h2 className="text-sm font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
                Criteria
              </h2>
              {signals.entry_criteria && (
                <div className="text-xs mb-2">
                  <span style={{ color: "var(--accent-teal)" }}>Entry: </span>
                  <span style={{ color: "var(--text-secondary)" }}>{signals.entry_criteria}</span>
                </div>
              )}
              {signals.exit_criteria && (
                <div className="text-xs">
                  <span style={{ color: "var(--accent-violet)" }}>Exit: </span>
                  <span style={{ color: "var(--text-secondary)" }}>{signals.exit_criteria}</span>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* No signals for selected week */}
      {!signals && !loading && selectedWeek !== "current" && (
        <div className="stat-card rounded-xl p-8 text-center">
          <p style={{ color: "var(--text-muted)" }}>No scanner data available for {selectedWeek}.</p>
        </div>
      )}
    </div>
  );
}

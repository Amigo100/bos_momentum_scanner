import { getPortfolio, getEquityCurve, enrichPositions, getPortfolioSnapshot } from "@/lib/data";
import { EquityChart } from "@/components/EquityChart";

export const dynamic = "force-dynamic";

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="stat-card rounded-xl p-5">
      <div className="text-xs font-medium uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
        {label}
      </div>
      <div className="text-2xl font-bold" style={{ color: color || "var(--text-primary)" }}>
        {value}
      </div>
      {sub && (
        <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function PnlCell({ value, prefix }: { value: number; prefix?: string }) {
  const isPos = value > 0;
  return (
    <span className={isPos ? "pnl-positive" : value < 0 ? "pnl-negative" : ""} style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "13px" }}>
      {prefix}{isPos ? "+" : ""}{value.toFixed(1)}{prefix ? "" : "%"}
    </span>
  );
}

function MoneyCell({ value, showSign }: { value: number; showSign?: boolean }) {
  const isPos = value > 0;
  const formatted = Math.abs(value).toLocaleString("en-GB", { maximumFractionDigits: 0 });
  return (
    <span
      className={showSign ? (isPos ? "pnl-positive" : value < 0 ? "pnl-negative" : "") : ""}
      style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "13px" }}
    >
      {showSign && value !== 0 ? (isPos ? "+" : "-") : ""}£{formatted}
    </span>
  );
}

export default function PortfolioPage() {
  const positions = getPortfolio();
  const equityCurve = getEquityCurve();
  const enriched = enrichPositions(positions);
  const snapshot = getPortfolioSnapshot();

  const open = enriched.filter((p) => p.status === "OPEN");
  const closed = enriched.filter((p) => p.status !== "OPEN");
  const winners = closed.filter((p) => p.pnl_pct > 0 || (p.exit_price > 0 && p.entry_price > 0 && p.exit_price > p.entry_price));
  const winRate = closed.length > 0 ? Math.round((winners.length / closed.length) * 100) : 0;
  const latest = equityCurve.length > 0 ? equityCurve[equityCurve.length - 1] : null;

  // Totals for open positions
  const totalInvested = open.reduce((sum, p) => sum + p.invested, 0);
  const totalValue = open.reduce((sum, p) => sum + p.currentValue, 0);
  const totalPnlDollars = open.reduce((sum, p) => sum + p.pnlDollars, 0);
  const avgPnl = open.length > 0 ? open.reduce((sum, p) => sum + p.pnl_pct, 0) / open.length : 0;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
          Portfolio Overview
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          {open.length} open positions · {closed.length} closed · Updated{" "}
          {latest ? new Date(latest.date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        <StatCard
          label="NAV"
          value={latest ? `£${latest.nav.toLocaleString("en-GB", { maximumFractionDigits: 0 })}` : "—"}
          sub="Portfolio Value"
        />
        <StatCard
          label="Total Return"
          value={latest ? `${latest.total_return_pct > 0 ? "+" : ""}${latest.total_return_pct.toFixed(1)}%` : "—"}
          color={latest && latest.total_return_pct > 0 ? "var(--accent-green)" : latest && latest.total_return_pct < 0 ? "var(--accent-red)" : undefined}
        />
        <StatCard label="Win Rate" value={`${winRate}%`} sub={`${winners.length}W / ${closed.length - winners.length}L`} />
        <StatCard
          label="Alpha vs SPY"
          value={latest ? `${latest.alpha_pct > 0 ? "+" : ""}${latest.alpha_pct.toFixed(1)}%` : "—"}
          color={latest && latest.alpha_pct > 0 ? "var(--accent-teal)" : "var(--accent-red)"}
        />
        <StatCard
          label="Alpha vs QQQ"
          value={latest && latest.qqq_return_pct !== undefined ? `${(latest.total_return_pct - latest.qqq_return_pct) > 0 ? "+" : ""}${(latest.total_return_pct - latest.qqq_return_pct).toFixed(1)}%` : "—"}
          color={latest && (latest.total_return_pct - (latest.qqq_return_pct || 0)) > 0 ? "var(--accent-teal)" : "var(--accent-red)"}
        />
        <StatCard label="Open Positions" value={`${open.length}`} sub={`£${totalInvested.toLocaleString("en-GB", { maximumFractionDigits: 0 })} deployed`} />
      </div>

      {/* Equity Curve */}
      {equityCurve.length > 0 && (
        <div className="stat-card rounded-xl p-6 mb-8">
          <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
            Equity Curve — Portfolio vs Benchmarks
          </h2>
          <EquityChart data={equityCurve} />
        </div>
      )}

      {/* Benchmark Comparison */}
      {snapshot?.benchmarks && (
        <div className="stat-card rounded-xl overflow-hidden mb-8">
          <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
            <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Benchmark Comparison
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Period</th>
                  <th>Portfolio</th>
                  <th>SPY</th>
                  <th>Alpha</th>
                  <th>Trades</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(snapshot.benchmarks).map(([period, data]) => (
                  <tr key={period}>
                    <td>
                      <span className="font-semibold text-xs uppercase" style={{ color: "var(--text-primary)" }}>{period}</span>
                    </td>
                    <td><PnlCell value={data.portfolio * 100} /></td>
                    <td><PnlCell value={data.spy * 100} /></td>
                    <td><PnlCell value={data.alpha * 100} /></td>
                    <td style={{ color: "var(--text-secondary)" }}>{data.trades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {snapshot.equity.max_drawdown_pct !== undefined && (
            <div className="px-6 py-3 border-t flex items-center gap-4" style={{ borderColor: "var(--border)" }}>
              <span className="text-xs font-medium uppercase" style={{ color: "var(--text-muted)" }}>Max Drawdown</span>
              <span className="text-sm font-semibold" style={{ color: "var(--accent-red)" }}>
                {snapshot.equity.max_drawdown_pct.toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      )}

      {/* Open Positions Table */}
      <div className="stat-card rounded-xl overflow-hidden mb-8">
        <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
          <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            Open Positions
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Entry</th>
                <th>Current</th>
                <th>Invested</th>
                <th>Value</th>
                <th>P&L %</th>
                <th>P&L £</th>
                <th>Days</th>
                <th>Theme</th>
                <th>Lock Status</th>
                <th>Conviction</th>
              </tr>
            </thead>
            <tbody>
              {open
                .sort((a, b) => b.pnl_pct - a.pnl_pct)
                .map((p) => (
                  <tr key={p.ticker}>
                    <td>
                      <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                        ${p.ticker}
                      </span>
                    </td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      ${p.entry_price.toFixed(2)}
                    </td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      {p.current_price > 0 ? `$${p.current_price.toFixed(2)}` : "—"}
                    </td>
                    <td>
                      <MoneyCell value={p.invested} />
                    </td>
                    <td>
                      <MoneyCell value={p.currentValue} />
                    </td>
                    <td>
                      <PnlCell value={p.pnl_pct} />
                    </td>
                    <td>
                      <MoneyCell value={p.pnlDollars} showSign />
                    </td>
                    <td>{p.days_held || "—"}</td>
                    <td>
                      <span className="text-xs px-2 py-1 rounded-full" style={{ background: "rgba(96, 165, 250, 0.1)", color: "var(--accent-blue)" }}>
                        {p.theme || "—"}
                      </span>
                    </td>
                    <td>
                      {p.lockStatus.active ? (
                        <span
                          className="text-xs px-2 py-1 rounded-full font-medium"
                          style={{ background: "rgba(52, 211, 153, 0.15)", color: "var(--accent-green)" }}
                        >
                          {p.lockStatus.trail} trail @ ${p.lockStatus.lockLevel?.toFixed(2)}
                        </span>
                      ) : p.lockStatus.exitType === "ExD" ? (
                        <span className="text-xs" style={{ color: "var(--text-muted)", opacity: 0.7 }}>
                          ExD Exit
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-1 rounded-full font-medium" style={{ background: "rgba(251, 191, 36, 0.1)", color: "var(--accent-amber)" }}>
                          Needs +{p.lockStatus.neededPct?.toFixed(1)}%
                        </span>
                      )}
                    </td>
                    <td>
                      <span style={{ color: "var(--accent-amber)" }}>{p.conviction || "—"}</span>
                    </td>
                  </tr>
                ))}
              {/* Totals Row */}
              {open.length > 0 && (
                <tr style={{ borderTop: "2px solid var(--border)" }}>
                  <td colSpan={3}>
                    <span className="font-semibold text-xs uppercase" style={{ color: "var(--text-muted)" }}>
                      Totals ({open.length} positions)
                    </span>
                  </td>
                  <td>
                    <MoneyCell value={totalInvested} />
                  </td>
                  <td>
                    <MoneyCell value={totalValue} />
                  </td>
                  <td>
                    <PnlCell value={avgPnl} />
                  </td>
                  <td>
                    <MoneyCell value={totalPnlDollars} showSign />
                  </td>
                  <td colSpan={4} />
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Closed Positions */}
      {closed.length > 0 && (
        <div className="stat-card rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
            <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Closed Positions
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Status</th>
                  <th>Entry</th>
                  <th>Exit</th>
                  <th>Invested</th>
                  <th>Return</th>
                  <th>P&L %</th>
                  <th>P&L £</th>
                  <th>Days</th>
                  <th>Theme</th>
                </tr>
              </thead>
              <tbody>
                {closed.map((p) => {
                  const pnl = p.exit_price > 0 && p.entry_price > 0 ? ((p.exit_price - p.entry_price) / p.entry_price) * 100 : p.pnl_pct;
                  return (
                    <tr key={p.ticker + p.exit_date}>
                      <td>
                        <span className="font-semibold" style={{ color: "var(--text-primary)" }}>${p.ticker}</span>
                      </td>
                      <td>
                        <span className={`text-xs px-2 py-1 rounded-full ${p.status === "STOPPED" ? "badge-failed" : "badge-posted"}`}>
                          {p.status}
                        </span>
                      </td>
                      <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>${p.entry_price.toFixed(2)}</td>
                      <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                        {p.exit_price > 0 ? `$${p.exit_price.toFixed(2)}` : "—"}
                      </td>
                      <td>
                        <MoneyCell value={p.invested} />
                      </td>
                      <td>
                        <MoneyCell value={p.currentValue} />
                      </td>
                      <td><PnlCell value={pnl} /></td>
                      <td><MoneyCell value={p.pnlDollars} showSign /></td>
                      <td>{p.days_held || "—"}</td>
                      <td className="text-xs">{p.theme || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

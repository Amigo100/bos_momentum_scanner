"use client";

import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface EquityPoint {
  date: string;
  nav: number;
  total_return_pct: number;
  spy_return_pct: number;
  qqq_return_pct: number;
  spy_value: number;
  qqq_value: number;
}

export function EquityChart({ data }: { data: EquityPoint[] }) {
  const [mode, setMode] = useState<"pct" | "gbp">("pct");

  const formatted = data.map((d) => ({
    ...d,
    label: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
  }));

  // Calculate tick interval so we show ~8-10 labels max
  const tickInterval = Math.max(1, Math.floor(formatted.length / 10));

  return (
    <div>
      {/* Toggle Buttons */}
      <div className="flex gap-2 mb-4 justify-end">
        <button
          onClick={() => setMode("pct")}
          className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all"
          style={{
            background: mode === "pct" ? "rgba(45, 212, 191, 0.15)" : "rgba(42, 53, 72, 0.5)",
            color: mode === "pct" ? "var(--accent-teal)" : "var(--text-muted)",
            border: mode === "pct" ? "1px solid rgba(45, 212, 191, 0.3)" : "1px solid transparent",
          }}
        >
          % Returns
        </button>
        <button
          onClick={() => setMode("gbp")}
          className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all"
          style={{
            background: mode === "gbp" ? "rgba(45, 212, 191, 0.15)" : "rgba(42, 53, 72, 0.5)",
            color: mode === "gbp" ? "var(--accent-teal)" : "var(--text-muted)",
            border: mode === "gbp" ? "1px solid rgba(45, 212, 191, 0.3)" : "1px solid transparent",
          }}
        >
          £ Value
        </button>
      </div>

      <div style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer>
          {mode === "pct" ? (
            <LineChart data={formatted} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(42, 53, 72, 0.5)" />
              <XAxis
                dataKey="label"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#2a3548" }}
                interval={tickInterval}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#2a3548" }}
                tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a2332",
                  border: "1px solid #2a3548",
                  borderRadius: 8,
                  fontSize: 12,
                  color: "#e2e8f0",
                }}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={(value: any, name: any) => {
                  const v = Number(value) || 0;
                  const label = name === "total_return_pct" ? "Portfolio" : name === "spy_return_pct" ? "SPY" : "QQQ";
                  return [`${v > 0 ? "+" : ""}${v.toFixed(2)}%`, label];
                }}
              />
              <Legend
                formatter={(value: string) =>
                  value === "total_return_pct" ? "Portfolio" : value === "spy_return_pct" ? "SPY" : "QQQ"
                }
                wrapperStyle={{ fontSize: 12, color: "#94a3b8" }}
              />
              <Line type="monotone" dataKey="total_return_pct" stroke="#2dd4bf" strokeWidth={2.5} dot={formatted.length < 30 ? { r: 3, fill: "#2dd4bf" } : false} />
              <Line type="monotone" dataKey="spy_return_pct" stroke="#60a5fa" strokeWidth={1.5} dot={false} strokeDasharray="5 5" />
              <Line type="monotone" dataKey="qqq_return_pct" stroke="#a78bfa" strokeWidth={1.5} dot={false} strokeDasharray="3 3" />
            </LineChart>
          ) : (
            <LineChart data={formatted} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(42, 53, 72, 0.5)" />
              <XAxis
                dataKey="label"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#2a3548" }}
                interval={tickInterval}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#2a3548" }}
                tickFormatter={(v: number) => `£${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a2332",
                  border: "1px solid #2a3548",
                  borderRadius: 8,
                  fontSize: 12,
                  color: "#e2e8f0",
                }}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={(value: any, name: any) => {
                  const v = Number(value) || 0;
                  const label = name === "nav" ? "Portfolio" : name === "spy_value" ? "SPY" : "QQQ";
                  return [`£${v.toLocaleString("en-GB", { maximumFractionDigits: 0 })}`, label];
                }}
              />
              <Legend
                formatter={(value: string) =>
                  value === "nav" ? "Portfolio" : value === "spy_value" ? "SPY" : "QQQ"
                }
                wrapperStyle={{ fontSize: 12, color: "#94a3b8" }}
              />
              <Line type="monotone" dataKey="nav" stroke="#2dd4bf" strokeWidth={2.5} dot={formatted.length < 30 ? { r: 3, fill: "#2dd4bf" } : false} />
              <Line type="monotone" dataKey="spy_value" stroke="#60a5fa" strokeWidth={1.5} dot={false} strokeDasharray="5 5" />
              <Line type="monotone" dataKey="qqq_value" stroke="#a78bfa" strokeWidth={1.5} dot={false} strokeDasharray="3 3" />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

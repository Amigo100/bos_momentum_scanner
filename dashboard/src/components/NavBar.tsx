"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

const tabs = [
  { href: "/", label: "Portfolio", icon: "📊" },
  { href: "/substack", label: "Substack", icon: "📰" },
  { href: "/notes", label: "Notes", icon: "📝" },
  { href: "/scanner", label: "Scanner", icon: "🔍" },
  { href: "/tweets", label: "Tweets", icon: "🐦" },
];

interface SystemStatus {
  overall: "operational" | "degraded" | "failing" | "unknown";
  message: string;
}

export function NavBar() {
  const pathname = usePathname();
  const [status, setStatus] = useState<SystemStatus>({ overall: "unknown", message: "Loading..." });

  useEffect(() => {
    fetch("/api/system-status")
      .then((r) => r.json())
      .then((data: SystemStatus) => setStatus(data))
      .catch(() => setStatus({ overall: "unknown", message: "Offline" }));
  }, []);

  const statusColors: Record<string, string> = {
    operational: "var(--accent-teal)",
    degraded: "var(--accent-amber)",
    failing: "var(--accent-red)",
    unknown: "var(--text-muted)",
  };

  const statusBgColors: Record<string, string> = {
    operational: "rgba(45, 212, 191, 0.1)",
    degraded: "rgba(251, 191, 36, 0.1)",
    failing: "rgba(248, 113, 113, 0.1)",
    unknown: "rgba(100, 116, 139, 0.1)",
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b"
      style={{ background: "rgba(10, 14, 23, 0.85)", backdropFilter: "blur(12px)", borderColor: "var(--border)" }}>
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
            style={{ background: "linear-gradient(135deg, var(--accent-teal), var(--accent-blue))" }}>
            SS
          </div>
          <div>
            <span className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>
              Sterling Signals
            </span>
            <span className="text-xs block" style={{ color: "var(--text-muted)" }}>
              Command Centre
            </span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1">
          {tabs.map((tab) => {
            const isActive = tab.href === "/"
              ? pathname === "/"
              : pathname.startsWith(tab.href);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  isActive
                    ? "text-white"
                    : "hover:text-white"
                }`}
                style={{
                  background: isActive ? "rgba(45, 212, 191, 0.1)" : "transparent",
                  color: isActive ? "var(--accent-teal)" : "var(--text-muted)",
                }}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </Link>
            );
          })}
        </div>

        {/* Status */}
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs transition-all hover:opacity-80"
            style={{
              background: statusBgColors[status.overall],
              color: statusColors[status.overall],
            }}
          >
            <span className={`w-1.5 h-1.5 rounded-full bg-current ${status.overall === "operational" ? "animate-pulse" : ""}`} />
            {status.message}
          </Link>
        </div>
      </div>
    </nav>
  );
}

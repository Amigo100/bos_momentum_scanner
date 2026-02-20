"use client";

import { useState } from "react";
import type { ContentProductionGuide } from "@/lib/data";

export function ContentGuideViewer({ guide }: { guide: ContentProductionGuide }) {
  const [copied, setCopied] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(guide.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = guide.markdown;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="mb-10">
      {/* Section Header */}
      <div className="mb-4">
        <h2
          className="text-lg font-bold flex items-center gap-3"
          style={{ color: "var(--text-primary)" }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: "var(--accent-teal)" }}
          />
          Content Production Guide
          {guide.weekNumber && (
            <span
              className="text-xs font-normal px-2 py-0.5 rounded-full"
              style={{
                background: "rgba(45, 212, 191, 0.15)",
                color: "var(--accent-teal)",
              }}
            >
              Week {guide.weekNumber}
            </span>
          )}
        </h2>
        <p className="text-xs mt-1 ml-5" style={{ color: "var(--text-muted)" }}>
          {guide.generatedDate && `Generated ${guide.generatedDate} · `}
          {guide.charCount.toLocaleString()} chars · {guide.lineCount} lines
          {" · "}Attach this document to Claude.ai (Opus 4.6 + extended thinking)
        </p>
      </div>

      {/* Main card */}
      <div
        className="stat-card rounded-xl overflow-hidden"
        style={{ borderLeft: "3px solid var(--accent-teal)" }}
      >
        {/* Toolbar */}
        <div
          className="p-4 flex items-center justify-between"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all"
              style={{
                background: collapsed
                  ? "rgba(42, 53, 72, 0.5)"
                  : "rgba(45, 212, 191, 0.15)",
                color: collapsed ? "var(--text-muted)" : "var(--accent-teal)",
              }}
            >
              {collapsed ? "Show Preview" : "Hide Preview"}
            </button>
            <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
              {guide.lineCount} lines
            </span>
          </div>
          <button
            onClick={handleCopy}
            className="text-sm px-5 py-2.5 rounded-lg font-bold transition-all"
            style={{
              background: copied
                ? "rgba(52, 211, 153, 0.2)"
                : "rgba(45, 212, 191, 0.15)",
              color: copied ? "var(--accent-green)" : "var(--accent-teal)",
              border: copied
                ? "1px solid rgba(52, 211, 153, 0.3)"
                : "1px solid rgba(45, 212, 191, 0.3)",
            }}
          >
            {copied ? "Copied to Clipboard!" : "Copy Full Document"}
          </button>
        </div>

        {/* Content preview */}
        {!collapsed && (
          <div className="p-4">
            <pre
              className="text-xs leading-relaxed whitespace-pre-wrap overflow-auto rounded-lg p-4"
              style={{
                background: "rgba(10, 14, 23, 0.6)",
                color: "var(--text-secondary)",
                maxHeight: 500,
                border: "1px solid var(--border)",
                fontFamily:
                  "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
              }}
            >
              {guide.markdown}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

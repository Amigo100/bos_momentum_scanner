"use client";

import { useState } from "react";

interface SubstackPost {
  filename: string;
  title: string;
  html: string;
  week: string;
  size: number;
}

export function SubstackViewer({
  post,
  variant,
  formatBadge,
}: {
  post: SubstackPost;
  variant?: "post" | "newsletter";
  formatBadge?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const isNewsletter = variant === "newsletter";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(post.html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement("textarea");
      textarea.value = post.html;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const sizeKb = (post.size / 1024).toFixed(1);

  // Get day from filename for color coding
  const day = post.filename.split("_")[0];
  const dayColors: Record<string, string> = {
    monday: "#60a5fa",
    tuesday: "#a78bfa",
    wednesday: "#fbbf24",
    thursday: "#f97316",
    friday: "#2dd4bf",
    saturday: "#34d399",
    sunday: "#f87171",
    newsletter: "#2dd4bf",
    dd: "#60a5fa",
  };

  const dotColor = isNewsletter ? "#2dd4bf" : post.filename.startsWith("dd_") ? "#60a5fa" : dayColors[day] || "var(--accent-teal)";

  // Format badge styles
  const badgeStyles: Record<string, { bg: string; color: string }> = {
    New: { bg: "rgba(52, 211, 153, 0.15)", color: "var(--accent-green)" },
    Legacy: { bg: "rgba(100, 116, 139, 0.15)", color: "var(--text-muted)" },
    "DD Post": { bg: "rgba(96, 165, 250, 0.15)", color: "var(--accent-blue)" },
  };

  return (
    <div
      className="stat-card rounded-xl overflow-hidden"
      style={{
        borderLeft: isNewsletter ? "3px solid var(--accent-teal)" : undefined,
      }}
    >
      {/* Header */}
      <div className="p-4 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ background: dotColor }} />
            {isNewsletter && (
              <span
                className="text-xs px-2 py-0.5 rounded-full font-medium"
                style={{ background: "rgba(45, 212, 191, 0.15)", color: "var(--accent-teal)" }}
              >
                NEWSLETTER
              </span>
            )}
            <span className="text-sm font-semibold capitalize" style={{ color: "var(--text-primary)" }}>
              {post.title}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {formatBadge && badgeStyles[formatBadge] && (
              <span
                className="text-xs px-2 py-0.5 rounded-full font-medium"
                style={{ background: badgeStyles[formatBadge].bg, color: badgeStyles[formatBadge].color }}
              >
                {formatBadge}
              </span>
            )}
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              {sizeKb}KB
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all"
            style={{
              background: expanded ? "rgba(45, 212, 191, 0.15)" : "rgba(42, 53, 72, 0.5)",
              color: expanded ? "var(--accent-teal)" : "var(--text-muted)",
            }}
          >
            {expanded ? "Collapse" : "Preview"}
          </button>
          <button
            onClick={handleCopy}
            className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all"
            style={{
              background: copied ? "rgba(45, 212, 191, 0.15)" : "rgba(42, 53, 72, 0.5)",
              color: copied ? "var(--accent-teal)" : "var(--text-muted)",
            }}
          >
            {copied ? "Copied HTML" : "Copy HTML"}
          </button>
        </div>
      </div>

      {/* Preview */}
      {expanded && (
        <div className="p-4">
          <div
            className="rounded-lg overflow-auto"
            style={{
              maxHeight: isNewsletter ? 600 : 500,
              background: "#0d1117",
              border: "1px solid var(--border)",
            }}
          >
            <iframe
              srcDoc={post.html}
              className="w-full border-0"
              style={{ height: isNewsletter ? 580 : 480, background: "white" }}
              title={post.title}
              sandbox="allow-same-origin"
            />
          </div>
        </div>
      )}
    </div>
  );
}

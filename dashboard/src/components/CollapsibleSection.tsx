"use client";

import { useState } from "react";

export function CollapsibleSection({
  title,
  subtitle,
  defaultOpen = true,
  accentColor = "var(--accent-violet)",
  children,
}: {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  accentColor?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="mb-10">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between mb-4 group"
      >
        <h2
          className="text-lg font-semibold flex items-center gap-3"
          style={{ color: "var(--text-primary)" }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: accentColor }}
          />
          {title}
          {subtitle && (
            <span
              className="text-xs font-normal"
              style={{ color: "var(--text-muted)" }}
            >
              {subtitle}
            </span>
          )}
        </h2>
        <span
          className="text-xs transition-transform"
          style={{
            color: "var(--text-muted)",
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
          }}
        >
          ▼
        </span>
      </button>
      {open && children}
    </div>
  );
}

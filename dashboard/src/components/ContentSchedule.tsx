"use client";

import { useState } from "react";
import type { ScheduleEntry, ContentSchedule as ContentScheduleData, HandbookPrompt } from "@/lib/data";

// ─── Category color mapping ───

const CATEGORY_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  TICKER_DEEP_DIVE: {
    color: "var(--accent-teal)",
    bg: "rgba(45, 212, 191, 0.12)",
    label: "Ticker Deep Dive",
  },
  THEME_ROTATION: {
    color: "var(--accent-blue)",
    bg: "rgba(96, 165, 250, 0.12)",
    label: "Theme Rotation",
  },
  EDUCATIONAL: {
    color: "var(--accent-violet)",
    bg: "rgba(167, 139, 250, 0.12)",
    label: "Educational",
  },
  PERFORMANCE_REVIEW: {
    color: "var(--accent-amber)",
    bg: "rgba(251, 191, 36, 0.12)",
    label: "Performance Review",
  },
  NOTES_ONLY: {
    color: "var(--text-muted)",
    bg: "rgba(100, 116, 139, 0.12)",
    label: "Notes Only",
  },
};

const PROMPT_TYPE_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  post: {
    color: "var(--accent-teal)",
    bg: "rgba(45, 212, 191, 0.12)",
    label: "POST",
  },
  notes: {
    color: "var(--accent-amber)",
    bg: "rgba(251, 191, 36, 0.12)",
    label: "NOTES",
  },
  "trade-alert": {
    color: "var(--accent-red)",
    bg: "rgba(248, 113, 113, 0.12)",
    label: "ALERT",
  },
};

// Day ordering (Sunday first to match our schedule)
const DAY_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function getTodayET(): string {
  try {
    const formatter = new Intl.DateTimeFormat("en-US", {
      weekday: "long",
      timeZone: "America/New_York",
    });
    return formatter.format(new Date());
  } catch {
    return "";
  }
}

// ─── Copy button (reuses SubstackViewer pattern) ───

function CopyButton({ text, label = "Copy Prompt" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="text-xs px-4 py-2 rounded-lg font-semibold transition-all"
      style={{
        background: copied ? "rgba(45, 212, 191, 0.2)" : "rgba(45, 212, 191, 0.1)",
        color: copied ? "var(--accent-green)" : "var(--accent-teal)",
        border: copied ? "1px solid rgba(52, 211, 153, 0.3)" : "1px solid rgba(45, 212, 191, 0.2)",
      }}
    >
      {copied ? "✓ Copied!" : label}
    </button>
  );
}

// ─── Schedule Day Card ───

function DayCard({ entry, isToday }: { entry: ScheduleEntry; isToday: boolean }) {
  const isNotesOnly = entry.category === "NOTES_ONLY" || entry.day === "Saturday";
  const catStyle = CATEGORY_STYLES[entry.category] || CATEGORY_STYLES.NOTES_ONLY;

  return (
    <div
      className="stat-card rounded-xl p-4 flex flex-col gap-2.5 relative"
      style={{
        borderColor: isToday ? "rgba(45, 212, 191, 0.5)" : undefined,
        boxShadow: isToday ? "0 0 16px rgba(45, 212, 191, 0.1)" : undefined,
      }}
    >
      {/* Today indicator */}
      {isToday && (
        <div
          className="absolute -top-px -right-px px-2 py-0.5 rounded-bl-lg rounded-tr-xl text-[10px] font-bold tracking-wider uppercase"
          style={{ background: "var(--accent-teal)", color: "var(--bg-primary)" }}
        >
          Today
        </div>
      )}

      {/* Day name */}
      <div className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
        {entry.day}
      </div>

      {/* Category badge */}
      <span
        className="text-[11px] px-2 py-1 rounded-md font-semibold self-start"
        style={{ background: catStyle.bg, color: catStyle.color }}
      >
        {isNotesOnly ? "Notes Only" : catStyle.label}
      </span>

      {/* Topic */}
      {!isNotesOnly && entry.topic && (
        <div className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          {entry.topic}
        </div>
      )}

      {/* Note types */}
      {entry.note_types && entry.note_types.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-auto pt-1">
          {entry.note_types.map((nt, i) => (
            <span
              key={i}
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{ background: "rgba(100, 116, 139, 0.12)", color: "var(--text-muted)" }}
            >
              {nt}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Prompt Accordion Item ───

function PromptItem({ prompt }: { prompt: HandbookPrompt }) {
  const [expanded, setExpanded] = useState(false);
  const typeStyle = PROMPT_TYPE_STYLES[prompt.type] || PROMPT_TYPE_STYLES.post;

  return (
    <div className="stat-card rounded-xl overflow-hidden">
      {/* Header — click to expand */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between text-left transition-colors"
        style={{ borderBottom: expanded ? "1px solid var(--border)" : undefined }}
      >
        <div className="flex items-center gap-3">
          <span
            className="text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wider"
            style={{ background: typeStyle.bg, color: typeStyle.color }}
          >
            {typeStyle.label}
          </span>
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {prompt.title}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {!expanded && (
            <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
              {prompt.prompt.length.toLocaleString()} chars
            </span>
          )}
          <span
            className="text-xs transition-transform"
            style={{
              color: "var(--text-muted)",
              transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
            }}
          >
            ▼
          </span>
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="p-4">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              {prompt.prompt.split("\n").length} lines · {prompt.prompt.length.toLocaleString()} chars
            </span>
            <CopyButton text={prompt.prompt} />
          </div>
          <pre
            className="text-xs leading-relaxed whitespace-pre-wrap overflow-auto rounded-lg p-4"
            style={{
              background: "rgba(10, 14, 23, 0.6)",
              color: "var(--text-secondary)",
              maxHeight: 400,
              border: "1px solid var(--border)",
              fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
            }}
          >
            {prompt.prompt}
          </pre>
        </div>
      )}
    </div>
  );
}

// ─── Main Component ───

export function ContentSchedule({
  schedule,
  prompts,
}: {
  schedule: ContentScheduleData | null;
  prompts: HandbookPrompt[];
}) {
  const todayET = getTodayET();

  if (!schedule && prompts.length === 0) {
    return null;
  }

  return (
    <div className="mb-10 space-y-8">
      {/* Section Header */}
      <div>
        <h2 className="text-lg font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: "var(--accent-teal)" }}
          />
          Content Schedule & Prompts
          {schedule && (
            <span
              className="text-xs font-normal px-2 py-0.5 rounded-full"
              style={{ background: "rgba(45, 212, 191, 0.15)", color: "var(--accent-teal)" }}
            >
              {schedule.week}
            </span>
          )}
        </h2>
        {schedule && (
          <p className="text-xs mt-1 ml-5" style={{ color: "var(--text-muted)" }}>
            Generated {new Date(schedule.generated).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
            })}
            {" · "}Copy prompts below into Claude.ai with the context document attached
          </p>
        )}
      </div>

      {/* Weekly Schedule Grid */}
      {schedule && schedule.schedule.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: "var(--text-secondary)" }}>
            <span style={{ color: "var(--accent-teal)" }}>▸</span>
            Weekly Schedule
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {DAY_ORDER.map((dayName) => {
              const entry = schedule.schedule.find(
                (e) => e.day.toLowerCase() === dayName.toLowerCase()
              );
              if (!entry) return null;
              return (
                <DayCard
                  key={dayName}
                  entry={entry}
                  isToday={todayET === dayName}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Prompt Library */}
      {prompts.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: "var(--text-secondary)" }}>
            <span style={{ color: "var(--accent-teal)" }}>▸</span>
            Prompt Library
            <span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>
              {prompts.length} prompts
            </span>
          </h3>
          <div className="space-y-2">
            {prompts.map((p) => (
              <PromptItem key={p.id} prompt={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

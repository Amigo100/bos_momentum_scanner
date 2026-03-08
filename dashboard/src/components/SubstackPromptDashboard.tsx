"use client";

import { useState } from "react";
import type { DailyContext, ContentTracker } from "@/lib/data";
import { CollapsibleSection } from "./CollapsibleSection";

interface SubstackPromptDashboardProps {
  context: DailyContext | null;
  tracker: ContentTracker | null;
}

function categoryClass(cat: string | null): string {
  if (!cat) return "pub-pending";
  const lower = cat.toLowerCase();
  if (lower.includes("deep dive")) return "cat-deep-dive";
  if (lower.includes("sector watch")) return "cat-sector-watch";
  if (lower.includes("the edge") || lower.includes("educational")) return "cat-the-edge";
  if (lower.includes("performance")) return "cat-performance";
  return "pub-pending";
}

function statusClass(status: string): string {
  switch (status) {
    case "published": return "pub-published";
    case "pending": return "pub-pending";
    case "generated": return "pub-generated";
    case "skipped": return "badge-skipped";
    default: return "pub-pending";
  }
}

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <button onClick={handleCopy} className="copy-btn">
      {copied ? "Copied!" : label || "Copy"}
    </button>
  );
}

export function SubstackPromptDashboard({ context, tracker }: SubstackPromptDashboardProps) {
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });
  const dayNames = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const todayDayName = dayNames[new Date().getDay()];

  if (!context && !tracker) {
    return (
      <div className="stat-card rounded-xl p-8 text-center">
        <p style={{ color: "var(--text-muted)" }}>
          No daily context available. Run the daily content pipeline to generate today&apos;s assignment.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Section A: Today's Assignment (Hero Card) */}
      {context && (
        <div className="assignment-card">
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                {context.category && (
                  <span className={`text-xs px-3 py-1 rounded-full font-semibold ${categoryClass(context.category)}`}>
                    {context.category}
                  </span>
                )}
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {todayDayName}
                </span>
              </div>
              <h2 className="text-xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
                {context.topic || "No topic assigned"}
              </h2>
              {context.theme && (
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                  Theme: {context.theme}
                </p>
              )}
            </div>
            {context.generatedAt && (
              <span className="text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>
                Generated {context.generatedAt}
              </span>
            )}
          </div>
          {context.reason && (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {context.reason}
            </p>
          )}
        </div>
      )}

      {/* Section B: Post Prompt (Copyable) */}
      {context?.postPrompt && (
        <div className="stat-card rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Post Prompt
            </h3>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              Paste into Claude.ai with daily_context.md attached
            </span>
          </div>
          <div className="prompt-block" style={{ maxHeight: "400px", overflowY: "auto" }}>
            <CopyButton text={context.postPrompt} label="Copy Prompt" />
            {context.postPrompt}
          </div>
        </div>
      )}

      {/* Section C: Notes Prompt (Collapsed by default) */}
      {context?.notesPrompt && (
        <CollapsibleSection
          title="Notes Prompt"
          subtitle="Copy after post is written"
          defaultOpen={false}
          accentColor="var(--accent-amber)"
        >
          <div className="prompt-block" style={{ maxHeight: "400px", overflowY: "auto" }}>
            <CopyButton text={context.notesPrompt} label="Copy Notes Prompt" />
            {context.notesPrompt}
          </div>
        </CollapsibleSection>
      )}

      {/* Section D: This Week's Schedule */}
      {tracker && (
        <div className="stat-card rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Week {tracker.current_week} Schedule
            </h3>
            <div className="flex items-center gap-3">
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {tracker.streak.posts_on_schedule} on schedule
              </span>
            </div>
          </div>
          <div className="grid grid-cols-7 gap-2">
            {tracker.posts.map((post) => {
              const isToday = post.date === today;
              return (
                <div
                  key={post.date}
                  className={`rounded-lg p-3 text-center ${isToday ? "schedule-today" : ""}`}
                  style={{
                    background: isToday ? "rgba(45, 212, 191, 0.05)" : "var(--bg-secondary)",
                    border: isToday ? undefined : "1px solid var(--border)",
                  }}
                >
                  <div className="text-xs font-semibold mb-1" style={{ color: isToday ? "var(--accent-teal)" : "var(--text-muted)" }}>
                    {post.day.slice(0, 3)}
                  </div>
                  <div className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
                    {new Date(post.date + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </div>
                  {post.category ? (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${categoryClass(post.category)}`}>
                      {post.category.length > 12 ? post.category.slice(0, 10) + ".." : post.category}
                    </span>
                  ) : (
                    <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                      Rest
                    </span>
                  )}
                  <div className="mt-2">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${statusClass(post.status)}`}>
                      {post.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Section E: Embedded Context (Collapsible) */}
      {context && (context.marketContext || context.portfolioSnapshot || context.signalData) && (
        <CollapsibleSection
          title="Context Data"
          subtitle="Market, portfolio, signals embedded in today's context"
          defaultOpen={false}
          accentColor="var(--accent-blue)"
        >
          <div className="space-y-4">
            {context.marketContext && (
              <div className="stat-card rounded-xl p-4">
                <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-blue)" }}>
                  Market Context
                </h4>
                <pre className="text-xs whitespace-pre-wrap" style={{ color: "var(--text-secondary)", maxHeight: 200, overflow: "auto" }}>
                  {context.marketContext}
                </pre>
              </div>
            )}
            {context.portfolioSnapshot && (
              <div className="stat-card rounded-xl p-4">
                <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-teal)" }}>
                  Portfolio Snapshot
                </h4>
                <pre className="text-xs whitespace-pre-wrap" style={{ color: "var(--text-secondary)", maxHeight: 200, overflow: "auto" }}>
                  {context.portfolioSnapshot}
                </pre>
              </div>
            )}
            {context.signalData && (
              <div className="stat-card rounded-xl p-4">
                <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-green)" }}>
                  Signal Data
                </h4>
                <pre className="text-xs whitespace-pre-wrap" style={{ color: "var(--text-secondary)", maxHeight: 200, overflow: "auto" }}>
                  {context.signalData}
                </pre>
              </div>
            )}
            {context.themeSummary && (
              <div className="stat-card rounded-xl p-4">
                <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-violet)" }}>
                  Theme Summary
                </h4>
                <pre className="text-xs whitespace-pre-wrap" style={{ color: "var(--text-secondary)", maxHeight: 200, overflow: "auto" }}>
                  {context.themeSummary}
                </pre>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}
    </div>
  );
}

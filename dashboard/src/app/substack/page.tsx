import {
  getSubstackContent,
  getWeeks,
  weekToDateRange,
  getContentSchedule,
  getHandbookPrompts,
  getContentProductionGuide,
} from "@/lib/data";
import { SubstackViewer } from "@/components/SubstackViewer";
import { ContentSchedule } from "@/components/ContentSchedule";
import { ContentGuideViewer } from "@/components/ContentGuideViewer";
import { CollapsibleSection } from "@/components/CollapsibleSection";

export const dynamic = "force-dynamic";

export default function SubstackPage() {
  const content = getSubstackContent("all");
  const weeks = getWeeks();
  const contentSchedule = getContentSchedule();
  const handbookPrompts = getHandbookPrompts();
  const guide = getContentProductionGuide();

  // Day order for sorting posts
  const dayOrder = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

  // Detect old-format post names (pre-update)
  const oldFormatNames = [
    "monday_market_analysis",
    "thursday_theme_spotlight",
    "saturday_weekly_signals",
    "sunday_deep_dive",
  ];

  // ─── Separate current week from archives ───

  const currentNewsletters = content.newsletters.filter((n) => n.week === "current");
  const currentPosts = content.posts.filter((p) => p.week === "current");
  const currentNotes = content.notes.filter((n) => n.week === "current");

  // Archive weeks (everything except "current"), newest first
  const archiveWeekKeys = new Set<string>();
  for (const n of content.newsletters) if (n.week !== "current") archiveWeekKeys.add(n.week);
  for (const p of content.posts) if (p.week !== "current") archiveWeekKeys.add(p.week);
  for (const n of content.notes) if (n.week !== "current") archiveWeekKeys.add(n.week);
  const archiveWeeks = Array.from(archiveWeekKeys).sort().reverse();

  const totalPosts = content.posts.length;
  const totalNewsletters = content.newsletters.length;
  const totalNotes = content.notes.length;

  const currentContentCount =
    currentNewsletters.length + currentPosts.length + currentNotes.length;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
          Substack Content
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Content production tools · {totalNewsletters} newsletters · {totalPosts} posts · {totalNotes} notes
        </p>
      </div>

      {/* ─── SECTION 1: Content Production Guide (PRIMARY TOOL) ─── */}
      {guide && <ContentGuideViewer guide={guide} />}

      {/* ─── SECTION 2: Content Schedule & Prompts (already works) ─── */}
      <ContentSchedule schedule={contentSchedule} prompts={handbookPrompts} />

      {/* ─── SECTION 3: Current Week Content ─── */}
      {currentContentCount > 0 && (
        <CollapsibleSection
          title={`Current Week (${content.currentISOWeek})`}
          subtitle={`${currentNewsletters.length > 0 ? `${currentNewsletters.length} newsletter · ` : ""}${currentPosts.length} posts · ${currentNotes.length} notes`}
          defaultOpen={true}
          accentColor="var(--accent-teal)"
        >
          {/* Newsletter (full width, teal accent) */}
          {currentNewsletters.map((nl, i) => (
            <div key={`nl-current-${i}`} className="mb-4">
              <SubstackViewer
                post={{
                  filename: "newsletter.html",
                  title: "Weekly Newsletter",
                  html: nl.html,
                  week: nl.week,
                  size: nl.size,
                }}
                variant="newsletter"
              />
            </div>
          ))}

          {/* Notes */}
          {currentNotes.length > 0 && (
            <div className="grid md:grid-cols-2 gap-4 mb-4">
              {currentNotes.map((note) =>
                note.format === "html" ? (
                  <SubstackViewer
                    key={`note-current-${note.filename}`}
                    post={{
                      filename: note.filename,
                      title: note.title,
                      html: note.content,
                      week: note.week,
                      size: note.size || note.content.length,
                    }}
                    formatBadge="Note"
                  />
                ) : (
                  <div key={`note-current-${note.filename}`} className="stat-card rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <span
                        className="text-xs px-2 py-0.5 rounded-full font-medium"
                        style={{
                          background: "rgba(251, 191, 36, 0.15)",
                          color: "var(--accent-amber)",
                        }}
                      >
                        NOTE
                      </span>
                      <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                        {note.title}
                      </span>
                    </div>
                    <pre
                      className="text-xs leading-relaxed whitespace-pre-wrap overflow-auto"
                      style={{ color: "var(--text-secondary)", maxHeight: 200 }}
                    >
                      {note.content}
                    </pre>
                  </div>
                )
              )}
            </div>
          )}

          {/* Posts grid */}
          {currentPosts.length > 0 && (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {currentPosts
                .sort((a, b) => {
                  const aDay = dayOrder.findIndex((d) => a.filename.startsWith(d));
                  const bDay = dayOrder.findIndex((d) => b.filename.startsWith(d));
                  return aDay - bDay;
                })
                .map((post) => {
                  const baseName = post.filename.replace(".html", "");
                  const isOldFormat = oldFormatNames.includes(baseName);
                  const isDDPost = baseName.startsWith("dd_");
                  return (
                    <SubstackViewer
                      key={`current-${post.filename}`}
                      post={post}
                      formatBadge={isDDPost ? "DD Post" : isOldFormat ? "Legacy" : "New"}
                    />
                  );
                })}
            </div>
          )}
        </CollapsibleSection>
      )}

      {/* ─── SECTION 4: Archive (collapsed by default) ─── */}
      {archiveWeeks.length > 0 && (
        <CollapsibleSection
          title="Archive"
          subtitle={`${archiveWeeks.length} previous weeks`}
          defaultOpen={false}
          accentColor="var(--accent-violet)"
        >
          {/* Week overview cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
            {weeks.map((w) => {
              const dateRange = weekToDateRange(w.week);
              return (
                <div key={w.week} className="stat-card rounded-xl p-4">
                  <div
                    className="text-xs font-semibold mb-1"
                    style={{ color: "var(--accent-teal)" }}
                  >
                    {w.week.replace("2026-", "")}
                  </div>
                  <div className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
                    {dateRange}
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {w.hasSignals && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          background: "rgba(45, 212, 191, 0.1)",
                          color: "var(--accent-teal)",
                        }}
                      >
                        Signals
                      </span>
                    )}
                    {w.hasNewsletter && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          background: "rgba(96, 165, 250, 0.1)",
                          color: "var(--accent-blue)",
                        }}
                      >
                        Newsletter
                      </span>
                    )}
                    {w.hasSubstackPosts && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          background: "rgba(167, 139, 250, 0.1)",
                          color: "var(--accent-violet)",
                        }}
                      >
                        Posts
                      </span>
                    )}
                    {w.hasNotes && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          background: "rgba(251, 191, 36, 0.1)",
                          color: "var(--accent-amber)",
                        }}
                      >
                        Notes
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Archive week content */}
          {archiveWeeks.map((weekKey) => {
            const weekNewsletters = content.newsletters.filter((n) => n.week === weekKey);
            const weekPosts = content.posts.filter((p) => p.week === weekKey);
            const weekNotes = content.notes.filter((n) => n.week === weekKey);

            if (weekNewsletters.length === 0 && weekPosts.length === 0 && weekNotes.length === 0)
              return null;

            const dateRange = weekToDateRange(weekKey);
            const weekLabel = `${weekKey.replace("2026-", "")}: ${dateRange}`;

            return (
              <div key={weekKey} className="mb-10">
                <h3
                  className="text-base font-semibold mb-4 flex items-center gap-3"
                  style={{ color: "var(--text-primary)" }}
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ background: "var(--accent-violet)" }}
                  />
                  {weekLabel}
                  <span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>
                    {weekNewsletters.length > 0 && `${weekNewsletters.length} newsletter · `}
                    {weekPosts.length} posts
                    {weekNotes.length > 0 && ` · ${weekNotes.length} notes`}
                  </span>
                </h3>

                {/* Newsletter */}
                {weekNewsletters.map((nl, i) => (
                  <div key={`nl-${weekKey}-${i}`} className="mb-4">
                    <SubstackViewer
                      post={{
                        filename: "newsletter.html",
                        title: "Weekly Newsletter",
                        html: nl.html,
                        week: nl.week,
                        size: nl.size,
                      }}
                      variant="newsletter"
                    />
                  </div>
                ))}

                {/* Notes */}
                {weekNotes.length > 0 && (
                  <div className="grid md:grid-cols-2 gap-4 mb-4">
                    {weekNotes.map((note) =>
                      note.format === "html" ? (
                        <SubstackViewer
                          key={`note-${weekKey}-${note.filename}`}
                          post={{
                            filename: note.filename,
                            title: note.title,
                            html: note.content,
                            week: note.week,
                            size: note.size || note.content.length,
                          }}
                          formatBadge="Note"
                        />
                      ) : (
                        <div
                          key={`note-${weekKey}-${note.filename}`}
                          className="stat-card rounded-xl p-4"
                        >
                          <div className="flex items-center gap-2 mb-3">
                            <span
                              className="text-xs px-2 py-0.5 rounded-full font-medium"
                              style={{
                                background: "rgba(251, 191, 36, 0.15)",
                                color: "var(--accent-amber)",
                              }}
                            >
                              NOTE
                            </span>
                            <span
                              className="text-sm font-semibold"
                              style={{ color: "var(--text-primary)" }}
                            >
                              {note.title}
                            </span>
                          </div>
                          <pre
                            className="text-xs leading-relaxed whitespace-pre-wrap overflow-auto"
                            style={{ color: "var(--text-secondary)", maxHeight: 200 }}
                          >
                            {note.content}
                          </pre>
                        </div>
                      )
                    )}
                  </div>
                )}

                {/* Posts */}
                {weekPosts.length > 0 && (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {weekPosts
                      .sort((a, b) => {
                        const aDay = dayOrder.findIndex((d) => a.filename.startsWith(d));
                        const bDay = dayOrder.findIndex((d) => b.filename.startsWith(d));
                        return aDay - bDay;
                      })
                      .map((post) => {
                        const baseName = post.filename.replace(".html", "");
                        const isOldFormat = oldFormatNames.includes(baseName);
                        const isDDPost = baseName.startsWith("dd_");
                        return (
                          <SubstackViewer
                            key={`${post.week}-${post.filename}`}
                            post={post}
                            formatBadge={
                              isDDPost ? "DD Post" : isOldFormat ? "Legacy" : "New"
                            }
                          />
                        );
                      })}
                  </div>
                )}
              </div>
            );
          })}
        </CollapsibleSection>
      )}
    </div>
  );
}

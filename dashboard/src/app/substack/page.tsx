import { getSubstackContent, getWeeks, weekToDateRange, getContentSchedule, getHandbookPrompts } from "@/lib/data";
import { SubstackViewer } from "@/components/SubstackViewer";
import { ContentSchedule } from "@/components/ContentSchedule";

export const dynamic = "force-dynamic";

export default function SubstackPage() {
  const content = getSubstackContent("all");
  const weeks = getWeeks();
  const contentSchedule = getContentSchedule();
  const handbookPrompts = getHandbookPrompts();

  // Build combined week data: newsletters, posts, notes grouped by week
  const weekKeys = new Set<string>();
  weekKeys.add("current");
  for (const n of content.newsletters) weekKeys.add(n.week);
  for (const p of content.posts) weekKeys.add(p.week);
  for (const n of content.notes) weekKeys.add(n.week);

  const weekOrder = Array.from(weekKeys).sort((a, b) => {
    if (a === "current") return -1;
    if (b === "current") return 1;
    return b.localeCompare(a);
  });

  // Day order for sorting posts
  const dayOrder = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

  const totalPosts = content.posts.length;
  const totalNewsletters = content.newsletters.length;
  const totalNotes = content.notes.length;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
          Substack Content
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          {totalNewsletters} newsletters · {totalPosts} posts · {totalNotes} notes · {weekOrder.length} weeks
        </p>
      </div>

      {/* Content Schedule & Prompts */}
      <ContentSchedule schedule={contentSchedule} prompts={handbookPrompts} />

      {/* Week Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
        {weeks.map((w) => {
          const dateRange = weekToDateRange(w.week);
          return (
            <div key={w.week} className="stat-card rounded-xl p-4">
              <div className="text-xs font-semibold mb-1" style={{ color: "var(--accent-teal)" }}>
                {w.week.replace("2026-", "")}
              </div>
              <div className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
                {dateRange}
              </div>
              <div className="flex gap-2 flex-wrap">
                {w.hasSignals && (
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(45, 212, 191, 0.1)", color: "var(--accent-teal)" }}>
                    Signals
                  </span>
                )}
                {w.hasNewsletter && (
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(96, 165, 250, 0.1)", color: "var(--accent-blue)" }}>
                    Newsletter
                  </span>
                )}
                {w.hasSubstackPosts && (
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(167, 139, 250, 0.1)", color: "var(--accent-violet)" }}>
                    Posts
                  </span>
                )}
                {w.hasNotes && (
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(251, 191, 36, 0.1)", color: "var(--accent-amber)" }}>
                    Notes
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Content by Week */}
      {weekOrder.map((weekKey) => {
        const weekNewsletters = content.newsletters.filter((n) => n.week === weekKey);
        const weekPosts = content.posts.filter((p) => p.week === weekKey);
        const weekNotes = content.notes.filter((n) => n.week === weekKey);

        if (weekNewsletters.length === 0 && weekPosts.length === 0 && weekNotes.length === 0) return null;

        const isCurrent = weekKey === "current";
        const dateRange = isCurrent ? "" : weekToDateRange(weekKey);
        const weekLabel = isCurrent
          ? `Current Week (${content.currentISOWeek})`
          : `${weekKey.replace("2026-", "")}: ${dateRange}`;

        // Detect old-format posts (pre-update HTML posts like monday_market_analysis, etc.)
        const oldFormatNames = ["monday_market_analysis", "thursday_theme_spotlight", "saturday_weekly_signals", "sunday_deep_dive"];

        return (
          <div key={weekKey} className="mb-10">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: isCurrent ? "var(--accent-teal)" : "var(--accent-violet)" }}
              />
              {weekLabel}
              {isCurrent && (
                <span className="text-xs font-normal px-2 py-0.5 rounded-full" style={{ background: "rgba(45, 212, 191, 0.15)", color: "var(--accent-teal)" }}>
                  {content.currentISOWeek}
                </span>
              )}
              <span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>
                {weekNewsletters.length > 0 && `${weekNewsletters.length} newsletter · `}
                {weekPosts.length} posts
                {weekNotes.length > 0 && ` · ${weekNotes.length} notes`}
              </span>
            </h2>

            {/* Newsletter (full width, teal accent) */}
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

            {/* Notes (compact cards) */}
            {weekNotes.length > 0 && (
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                {weekNotes.map((note) => (
                  <div key={`note-${weekKey}-${note.filename}`} className="stat-card rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: "rgba(251, 191, 36, 0.15)", color: "var(--accent-amber)" }}>
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
                ))}
              </div>
            )}

            {/* Posts grid */}
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
                      formatBadge={isDDPost ? "DD Post" : isOldFormat ? "Legacy" : "New"}
                    />
                  );
                })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

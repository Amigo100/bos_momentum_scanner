import { getDailyContext, getContentTracker } from "@/lib/data";
import { SubstackPromptDashboard } from "@/components/SubstackPromptDashboard";

export const dynamic = "force-dynamic";

export default function SubstackPage() {
  const context = getDailyContext();
  const tracker = getContentTracker();

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
          Substack
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Today&apos;s post assignment &middot; {context?.category || "No assignment"} &middot;{" "}
          {tracker ? `Week ${tracker.current_week}` : ""}
        </p>
      </div>

      <SubstackPromptDashboard context={context} tracker={tracker} />
    </div>
  );
}

import { getNotesState, getNotesManifest, getGeneratedNotes, getDailyContext } from "@/lib/data";
import { NotesDashboard } from "@/components/NotesDashboard";

export const dynamic = "force-dynamic";

export default function NotesPage() {
  const notesState = getNotesState();
  const manifest = getNotesManifest();
  const generatedNotes = getGeneratedNotes();
  const context = getDailyContext();

  const todaySlots = notesState?.today?.slots || [];
  const publishedCount = notesState?.today?.notes_published || 0;
  const targetCount = notesState?.today?.notes_target || 0;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
          Notes
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          {todaySlots.length} slots today &middot; {publishedCount}/{targetCount} published &middot;{" "}
          {generatedNotes.length} generated &middot;{" "}
          {notesState?.recent?.length || 0} recent
        </p>
      </div>

      <NotesDashboard
        notesState={notesState}
        manifest={manifest}
        generatedNotes={generatedNotes}
        context={context}
      />
    </div>
  );
}

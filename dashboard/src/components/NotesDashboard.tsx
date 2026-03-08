"use client";

import { useState } from "react";
import type { NotesState, NotesManifest, GeneratedNote, DailyContext } from "@/lib/data";

interface NotesDashboardProps {
  notesState: NotesState | null;
  manifest: NotesManifest | null;
  generatedNotes: GeneratedNote[];
  context: DailyContext | null;
}

function statusBadge(status: string) {
  const classes: Record<string, string> = {
    generated: "pub-generated",
    posted: "pub-published",
    pending: "pub-pending",
    failed: "pub-failed",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${classes[status] || "pub-pending"}`}>
      {status}
    </span>
  );
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
    <button onClick={handleCopy} className="copy-btn" style={{ position: "relative" }}>
      {copied ? "Copied!" : label || "Copy HTML"}
    </button>
  );
}

export function NotesDashboard({ notesState, manifest, generatedNotes, context }: NotesDashboardProps) {
  const [expandedNote, setExpandedNote] = useState<number | null>(null);

  if (!notesState && !manifest && generatedNotes.length === 0) {
    return (
      <div className="stat-card rounded-xl p-8 text-center">
        <p style={{ color: "var(--text-muted)" }}>
          No notes data available. Run the daily content pipeline to generate today&apos;s notes.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Section A: Today's Note Schedule */}
      {notesState?.today && (
        <div className="stat-card rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Today&apos;s Notes — {notesState.today.date}
            </h3>
            <div className="flex items-center gap-3">
              <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                {notesState.today.notes_published} / {notesState.today.notes_target} published
              </span>
              <div className="progress-bar-track" style={{ width: 80 }}>
                <div
                  className="progress-bar-fill"
                  style={{
                    width: `${notesState.today.notes_target > 0 ? (notesState.today.notes_published / notesState.today.notes_target) * 100 : 0}%`,
                    background: "var(--accent-amber)",
                  }}
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {notesState.today.slots.map((slot) => {
              const manifestEntry = manifest?.notes.find((n) => n.slot === slot.slot);
              return (
                <div key={slot.slot} className="note-slot">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold" style={{ color: "var(--accent-amber)" }}>
                      Slot {slot.slot}
                    </span>
                    {statusBadge(slot.status)}
                  </div>
                  <div className="text-sm font-medium mb-1" style={{ color: "var(--text-primary)" }}>
                    {slot.note_type.replace(/_/g, " ")}
                  </div>
                  {manifestEntry && (
                    <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {manifestEntry.time_et} ET &middot; {manifestEntry.word_count} words
                    </div>
                  )}
                  {slot.note_id && (
                    <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                      ID: {slot.note_id}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Section B: Notes Prompt (Copyable) */}
      {context?.notesPrompt && (
        <div className="stat-card rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
              Notes Prompt
            </h3>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              Use after writing today&apos;s post
            </span>
          </div>
          <div className="prompt-block" style={{ maxHeight: "300px", overflowY: "auto" }}>
            <CopyButton text={context.notesPrompt} label="Copy Notes Prompt" />
            {context.notesPrompt}
          </div>
        </div>
      )}

      {/* Section C: Generated Notes Preview */}
      {generatedNotes.length > 0 && (
        <div className="stat-card rounded-xl p-6">
          <h3 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
            Generated Notes
          </h3>
          <div className="space-y-3">
            {generatedNotes.map((note) => {
              const isExpanded = expandedNote === note.slot;
              const manifestEntry = manifest?.notes.find((n) => n.slot === note.slot);
              return (
                <div key={note.slot} className="note-slot">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-semibold" style={{ color: "var(--accent-amber)" }}>
                        Slot {note.slot}
                      </span>
                      <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                        {note.type.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                        {note.date}
                      </span>
                      {manifestEntry && (
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                          {manifestEntry.word_count} words
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <CopyButton text={note.html} />
                      <button
                        onClick={() => setExpandedNote(isExpanded ? null : note.slot)}
                        className="text-xs px-3 py-1 rounded-md"
                        style={{
                          background: "rgba(42, 53, 72, 0.5)",
                          color: "var(--text-muted)",
                          border: "1px solid var(--border)",
                        }}
                      >
                        {isExpanded ? "Hide" : "Preview"}
                      </button>
                    </div>
                  </div>
                  {isExpanded && (
                    <div className="mt-3 p-4 rounded-lg" style={{ background: "#fff" }}>
                      <div dangerouslySetInnerHTML={{ __html: note.html }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Section D: Recent History */}
      {notesState?.recent && notesState.recent.length > 0 && (
        <div className="stat-card rounded-xl p-6">
          <h3 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
            Recent Notes
          </h3>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Slot</th>
                  <th>Type</th>
                  <th>Note ID</th>
                </tr>
              </thead>
              <tbody>
                {notesState.recent.map((note, i) => (
                  <tr key={`${note.date}-${note.slot}-${i}`}>
                    <td style={{ color: "var(--text-primary)" }}>{note.date}</td>
                    <td>{note.slot}</td>
                    <td>
                      <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "rgba(251, 191, 36, 0.1)", color: "var(--accent-amber)" }}>
                        {note.note_type.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td style={{ color: "var(--text-muted)", fontFamily: "'JetBrains Mono', monospace", fontSize: "12px" }}>
                      {note.note_id || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

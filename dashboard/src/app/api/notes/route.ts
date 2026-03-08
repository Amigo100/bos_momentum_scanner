import { NextResponse } from "next/server";
import { getNotesState, getNotesManifest, getGeneratedNotes, getDailyContext } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET() {
  const notesState = getNotesState();
  const manifest = getNotesManifest();
  const generatedNotes = getGeneratedNotes();
  const dailyContext = getDailyContext();

  return NextResponse.json({
    notesState,
    manifest,
    generatedNotes: generatedNotes.map((n) => ({
      ...n,
      html: n.html.substring(0, 50000), // cap for API
    })),
    notesPrompt: dailyContext?.notesPrompt || null,
  });
}
